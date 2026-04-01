#!/usr/bin/env python3
"""Workflow Loader

Loads user-defined workflows from ~/.vectorbrain/workflows/.

We avoid external deps (PyYAML) to keep the runtime self-contained.
Use TOML as the default format (via stdlib tomllib).

File formats supported:
- .toml (preferred): parsed by tomllib
- .json: parsed by json

Workflow schema (common):
{
  "name": "search_and_save",
  "steps": [
     {"id":"search", "capability":"search", "input": {"query":"{task.input}"}},
     ...
  ]
}
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from runtime.workflows.graph import WorkflowGraph, WorkflowCycleError

try:
    import tomllib  # py>=3.11
except Exception:  # pragma: no cover
    tomllib = None


VECTORBRAIN_ROOT = Path.home() / ".vectorbrain"
WORKFLOW_DIR = VECTORBRAIN_ROOT / "workflows"


class WorkflowNotFound(FileNotFoundError):
    pass


class WorkflowValidationError(ValueError):
    """Raised when a workflow file is malformed."""
    pass


REQUIRED_STEP_FIELDS = ["id", "capability", "input"]
# Optional reliability fields:
# - timeout: number (seconds)
# - max_retries: int
# - retry_backoff: number (seconds)
# - retryable_errors: list[str] (substring match)
# - on_error: str (fail|fail_fast|continue|ignore)
# depends_on is optional; defaults to []


def validate_workflow(wf: Dict[str, Any], *, source: Path) -> None:
    """Validate normalized workflow dict.

    Ensures user gets a clear, early error message.
    """
    steps = wf.get("steps")
    if steps is None:
        raise WorkflowValidationError(f"{source}: workflow missing 'steps'")
    if not isinstance(steps, list):
        raise WorkflowValidationError(f"{source}: workflow.steps must be a list")
    if len(steps) == 0:
        raise WorkflowValidationError(f"{source}: workflow.steps is empty")

    step_ids = set()
    for i, step in enumerate(steps):
        if isinstance(step, dict) and isinstance(step.get('id'), str):
            step_ids.add(step.get('id'))

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise WorkflowValidationError(f"{source}: Step[{i}] must be an object")

        missing = [k for k in REQUIRED_STEP_FIELDS if k not in step]
        if missing:
            sid = step.get("id", f"#{i}")
            raise WorkflowValidationError(
                f"{source}: Step[{sid}] missing required field(s): {', '.join(missing)}"
            )

        if not isinstance(step["id"], str) or not step["id"].strip():
            raise WorkflowValidationError(f"{source}: Step[{i}] invalid id")
        if not isinstance(step["capability"], str) or not step["capability"].strip():
            raise WorkflowValidationError(f"{source}: Step[{step['id']}] invalid capability")
        if not isinstance(step["input"], dict):
            raise WorkflowValidationError(f"{source}: Step[{step['id']}] input must be an object")

        # depends_on validation (optional)
        deps = step.get("depends_on", [])
        if deps is None:
            deps = []
            step["depends_on"] = []

        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            raise WorkflowValidationError(f"{source}: Step[{step['id']}] depends_on must be a list of strings")

        if step["id"] in deps:
            raise WorkflowValidationError(f"{source}: Step[{step['id']}] cannot depend on itself")

        for d in deps:
            if d not in step_ids:
                raise WorkflowValidationError(f"{source}: Step[{step['id']}] depends_on references unknown step: {d}")

        # reliability fields validation (optional)
        if "timeout" in step and step["timeout"] is not None and not isinstance(step["timeout"], (int, float)):
            raise WorkflowValidationError(f"{source}: Step[{step['id']}] timeout must be number (seconds)")

        if "max_retries" in step and step["max_retries"] is not None and not isinstance(step["max_retries"], int):
            raise WorkflowValidationError(f"{source}: Step[{step['id']}] max_retries must be int")

        if "retry_backoff" in step and step["retry_backoff"] is not None and not isinstance(step["retry_backoff"], (int, float)):
            raise WorkflowValidationError(f"{source}: Step[{step['id']}] retry_backoff must be number")

        if "retryable_errors" in step and step["retryable_errors"] is not None:
            r = step["retryable_errors"]
            if not isinstance(r, list) or any(not isinstance(x, str) for x in r):
                raise WorkflowValidationError(f"{source}: Step[{step['id']}] retryable_errors must be list[str]")

        if "on_error" in step and step["on_error"] is not None:
            oe = str(step["on_error"]).lower().strip()
            if oe not in ("fail", "fail_fast", "continue", "ignore"):
                raise WorkflowValidationError(f"{source}: Step[{step['id']}] on_error must be fail|fail_fast|continue|ignore")


def _read_toml(path: Path) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("tomllib not available")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_workflow(name: str) -> Dict[str, Any]:
    """Load a workflow by name from WORKFLOW_DIR."""
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)

    candidates = [
        WORKFLOW_DIR / f"{name}.toml",
        WORKFLOW_DIR / f"{name}.json",
    ]

    for p in candidates:
        if p.exists():
            if p.suffix == ".toml":
                data = _read_toml(p)
            else:
                data = _read_json(p)

            # normalize
            wf = {
                "name": data.get("name") or name,
                "intent": data.get("intent"),
                "steps": data.get("steps") or [],
            }

            # validate early with friendly error
            validate_workflow(wf, source=p)

            # DAG cycle detection (load-time)
            try:
                g = WorkflowGraph.from_steps(wf["steps"])
                g.topological_sort()
            except WorkflowCycleError as e:
                raise WorkflowValidationError(f"{p}: {str(e)}")
            except Exception as e:
                # keep error message actionable
                raise WorkflowValidationError(f"{p}: invalid DAG: {str(e)}")

            return wf

    raise WorkflowNotFound(f"Workflow '{name}' not found in {WORKFLOW_DIR}")
