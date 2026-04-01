#!/usr/bin/env python3
"""VectorBrain Execution Context (Stage 2+)

Purpose:
- Store step outputs during execution (data-driven workflows)
- Resolve templates against context, e.g.
  - {steps.search.data.results[0].url}
  - {steps.fetch.data.content}
  - {task.task_id}

Design goals:
- Minimal, dependency-free
- Safe resolution (no eval)

Notes:
- `resolve_expr` is strict (raises on missing keys/indexes).
- `safe_resolve_expr` is forgiving (returns None/default instead of raising).
- `resolve_templates` uses safe resolution to avoid crashing workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import re


_TEMPLATE_RE = re.compile(r"\{([^{}]+)\}")


@dataclass
class ExecutionContext:
    """Holds task/step state during execution."""

    task: Dict[str, Any] = field(default_factory=dict)
    steps: Dict[str, Any] = field(default_factory=dict)  # step_id -> result
    vars: Dict[str, Any] = field(default_factory=dict)

    def set_step_result(self, step_id: str, result: Any) -> None:
        self.steps[step_id] = result

    def get(self, expr: str, default: Any = None) -> Any:
        return safe_resolve_expr(expr, self, default=default)


def _parse_tokens(expr: str):
    """Parse expression tokens supporting dot + [index].

    Example: steps.search.data.results[0].url
      -> ['steps','search','data','results',0,'url']
    """
    tokens = []
    i = 0
    buf = ""

    def flush_buf():
        nonlocal buf
        if buf:
            tokens.append(buf)
            buf = ""

    while i < len(expr):
        ch = expr[i]
        if ch == '.':
            flush_buf()
            i += 1
            continue
        if ch == '[':
            flush_buf()
            j = expr.find(']', i)
            if j == -1:
                raise ValueError(f"Unclosed index in expr: {expr}")
            idx_raw = expr[i + 1:j].strip()
            if idx_raw.isdigit() or (idx_raw.startswith('-') and idx_raw[1:].isdigit()):
                tokens.append(int(idx_raw))
            else:
                # support string keys: ['foo'] or ["foo"]
                if (idx_raw.startswith("'") and idx_raw.endswith("'")) or (
                    idx_raw.startswith('"') and idx_raw.endswith('"')
                ):
                    tokens.append(idx_raw[1:-1])
                else:
                    tokens.append(idx_raw)
            i = j + 1
            continue
        buf += ch
        i += 1

    flush_buf()
    return tokens


def _dig(value: Any, token: Any) -> Any:
    """Unsafe dig (raises on missing). Kept for strict resolver."""
    if isinstance(token, int):
        return value[token]
    if isinstance(value, dict):
        return value[token]
    return getattr(value, token)


def _safe_dig(value: Any, token: Any, default: Any = None) -> Any:
    """Safe dig: returns default on KeyError/IndexError/TypeError/etc."""
    try:
        if isinstance(token, int):
            if not isinstance(value, (list, tuple)):
                return default
            return value[token]
        if isinstance(value, dict):
            return value.get(token, default)
        # object attribute
        return getattr(value, token)
    except (KeyError, IndexError, ValueError, TypeError):
        return default


def resolve_expr(expr: str, ctx: ExecutionContext) -> Any:
    """Resolve an expression like steps.search.data.results[0].url (strict)."""
    expr = expr.strip()
    tokens = _parse_tokens(expr)
    if not tokens:
        raise ValueError("empty expr")

    root = tokens[0]
    if root == "task":
        cur: Any = ctx.task
    elif root == "steps":
        cur = ctx.steps
    elif root == "vars":
        cur = ctx.vars
    else:
        raise KeyError(f"Unknown root '{root}' in expr '{expr}'")

    for tok in tokens[1:]:
        cur = _dig(cur, tok)

    return cur


def safe_resolve_expr(expr: str, ctx: ExecutionContext, default: Any = None) -> Any:
    """Resolve expression safely.

    Returns `default` (None by default) when:
    - unknown root
    - missing dict key
    - list index out of range
    - type mismatch
    - any parse error
    """
    try:
        expr = (expr or "").strip()
        tokens = _parse_tokens(expr)
        if not tokens:
            return default

        root = tokens[0]
        if root == "task":
            cur: Any = ctx.task
        elif root == "steps":
            cur = ctx.steps
        elif root == "vars":
            cur = ctx.vars
        else:
            return default

        for tok in tokens[1:]:
            cur = _safe_dig(cur, tok, default=default)
            if cur is default:
                return default

        return cur
    except Exception:
        return default


def resolve_templates(obj: Any, ctx: ExecutionContext) -> Any:
    """Resolve templates in dict/list/str recursively.

    Rules:
    - If a string is exactly "{expr}", return the resolved value preserving type.
    - Otherwise, do string substitution (resolved values cast to str).
    """
    if isinstance(obj, dict):
        return {k: resolve_templates(v, ctx) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_templates(v, ctx) for v in obj]
    if isinstance(obj, str):
        m = _TEMPLATE_RE.fullmatch(obj.strip())
        if m:
            return safe_resolve_expr(m.group(1), ctx, default=None)

        def _sub(match: re.Match):
            val = safe_resolve_expr(match.group(1), ctx, default=None)
            return "" if val is None else str(val)

        return _TEMPLATE_RE.sub(_sub, obj)

    return obj
