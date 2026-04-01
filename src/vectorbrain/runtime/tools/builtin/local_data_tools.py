#!/usr/bin/env python3
"""VectorBrain Local Data / Execution Tools.

目标：
- 本地 conversations / dashboard / sqlite 数据优先查询
- 提供“自然语言 -> 安全只读 SQL”能力
- 提供接近主会话的本地执行能力，但保持独立子进程执行
- 所有工具都不依赖会话上下文，只依赖显式输入
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from runtime.tools.registry import tool_registry, Tool
from common.notify_helper import build_runtime_env

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
MEMORY_DIR = VECTORBRAIN_HOME / "memory"
MONITOR_DIR = VECTORBRAIN_HOME / "monitor_center"
INTELLIGENCE_DIR = VECTORBRAIN_HOME / "intelligence"

EPISODIC_DB = MEMORY_DIR / "episodic_memory.db"
KNOWLEDGE_DB = MEMORY_DIR / "knowledge_memory.db"
REFLECTION_DB = VECTORBRAIN_HOME / "reflection" / "reflections.db"
TASK_DB = VECTORBRAIN_HOME / "tasks" / "task_queue.db"
GOALS_DB = VECTORBRAIN_HOME / "goals" / "goals.db"
STATUS_JSON = MONITOR_DIR / "status.json"
TASKS_JSON = MONITOR_DIR / "mcp_tasks.json"

DB_ALIASES = {
    "episodic": EPISODIC_DB,
    "episodic_memory": EPISODIC_DB,
    "conversations": EPISODIC_DB,
    "knowledge": KNOWLEDGE_DB,
    "knowledge_memory": KNOWLEDGE_DB,
    "reflection": REFLECTION_DB,
    "reflections": REFLECTION_DB,
    "tasks": TASK_DB,
    "task_queue": TASK_DB,
    "goals": GOALS_DB,
}

READONLY_PREFIXES = ("select ", "pragma ", "with ", "explain ")


def _ensure_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(str(path))


def _expand_local_path(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return str(Path(text).expanduser().resolve())


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[:limit] + "..."


def _safe_json_load(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _format_rows(rows: List[sqlite3.Row], limit: int = 10) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows[:limit]:
        out.append({k: row[k] for k in row.keys()})
    return out


def _extract_int(text: str, default: int = 10, minimum: int = 1, maximum: int = 100) -> int:
    m = re.search(r"(\d+)", text or "")
    value = int(m.group(1)) if m else default
    return max(minimum, min(value, maximum))


def _normalize_ws(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _quoted_value(text: str) -> Optional[str]:
    m = re.search(r"[\"'“”‘’](.+?)[\"'“”‘’]", text or "")
    if m:
        return m.group(1).strip()
    return None


def _extract_keyword_query(text: str) -> Optional[str]:
    quoted = _quoted_value(text)
    if quoted:
        return quoted
    patterns = [
        r"(?:关键词|关键字|keyword)\s*(?:是|为|:|：)?\s*([^,，。\n]+)",
        r"(?:包含|含有|搜索|查找|筛选)\s*([^,，。\n]+)",
        r"(?:with keyword|contains|search for)\s+([^,，。\n]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text or "", flags=re.I)
        if m:
            return m.group(1).strip().strip('"“”')
    return None


def _strip_action_prefixes(text: str) -> str:
    cleaned = str(text or "").strip()
    prefixes = [
        r"帮我查询",
        r"帮我查看",
        r"帮我看",
        r"请帮我查询",
        r"请帮我查看",
        r"请帮我看",
        r"请查询",
        r"请查看",
        r"查询",
        r"查看",
        r"帮我查",
        r"帮我搜",
        r"帮我找",
    ]
    changed = True
    while changed and cleaned:
        changed = False
        for prefix in prefixes:
            new_cleaned = re.sub(rf"^\s*{prefix}\s+", "", cleaned, count=1, flags=re.I)
            if new_cleaned != cleaned:
                cleaned = new_cleaned.strip()
                changed = True
    return cleaned


def _clean_chat_name_candidate(value: str) -> Optional[str]:
    cleaned = _strip_action_prefixes(str(value or ""))
    cleaned = re.sub(
        r"\s*(最近|今天|近24小时|过去\d+小时|\d+\s*条消息|消息|按时间.*|并总结.*|总结.*|列出.*)$",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = cleaned.strip().strip('"“”').strip("，,。.：:；; ")
    if not cleaned:
        return None
    if len(cleaned) > 60:
        return None
    return cleaned


def _extract_chat_name(text: str) -> Optional[str]:
    source = _normalize_ws(text)
    stripped = _strip_action_prefixes(source)
    quoted = _quoted_value(stripped)
    if quoted and any(k in source for k in ["群", "chat", "group"]):
        cleaned = _clean_chat_name_candidate(quoted)
        if cleaned:
            return cleaned
    patterns = [
        r"群名\s*(?:是|为|:|：)?\s*([^,，。\n]+)",
        r"在\s*([^,，。\n]+?群)\s*(?:里|中)?",
        r"(?:chat|group)\s*(?:name)?\s*(?:is|=|:)?\s*([^,，。\n]+)",
        r"(.{2,60}?)\s*(?:最近\s*\d+\s*条消息|最近|今天|近24小时|消息)",
    ]
    for candidate_source in [stripped, source]:
        for pattern in patterns:
            m = re.search(pattern, candidate_source or "", flags=re.I)
            if m:
                cleaned = _clean_chat_name_candidate(m.group(1))
                if cleaned:
                    return cleaned
    return None


def _extract_task_ref(text: str) -> Optional[str]:
    quoted = _quoted_value(text)
    if quoted:
        return quoted
    patterns = [
        r"任务\s*([A-Za-z0-9_\-]{4,})\s*(?:详情|状态|detail)?",
        r"(?:task|任务)\s*(?:id)?\s*[:：=]?\s*([A-Za-z0-9_\-]{4,})",
        r"(?:详情|detail)\s*(?:任务)?\s*([^,，。\n]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text or "", flags=re.I)
        if m:
            return m.group(1).strip().strip('"“”')
    return None


def _is_safe_readonly_sql(query: str) -> Tuple[bool, str]:
    raw = (query or "").strip()
    if not raw:
        return False, "Missing required field: query"
    normalized = " ".join(raw.lower().split())
    if not normalized.startswith(READONLY_PREFIXES):
        return False, "Only SELECT / PRAGMA / WITH / EXPLAIN queries are allowed"
    if ";" in raw.strip().rstrip(";"):
        return False, "Multiple SQL statements are not allowed"
    banned = [" insert ", " update ", " delete ", " drop ", " alter ", " attach ", " detach ", " replace ", " create "]
    padded = f" {normalized} "
    for marker in banned:
        if marker in padded:
            return False, f"Unsafe SQL contains forbidden keyword: {marker.strip()}"
    return True, raw.strip().rstrip(";")


def _run_sql(db_path: Path, sql: str, params: Optional[List[Any]] = None, *, limit: int = 50) -> Tuple[List[sqlite3.Row], str]:
    ok, checked = _is_safe_readonly_sql(sql)
    if not ok:
        raise ValueError(checked)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        sql_to_run = checked
        normalized = " ".join(sql_to_run.lower().split())
        if normalized.startswith(("select ", "with ")) and " limit " not in normalized:
            sql_to_run = f"{sql_to_run} LIMIT {int(limit)}"
        cur.execute(sql_to_run, params or [])
        return cur.fetchall(), sql_to_run
    finally:
        conn.close()


def _conversation_nl_to_sql(text: str, *, default_limit: int = 20, explicit_chat_name: Optional[str] = None) -> Tuple[str, List[Any], Dict[str, Any]]:
    q = _normalize_ws(text)
    q_lower = q.lower()

    limit_match = re.search(r"(?:最近|latest|recent)\s*(\d+)\s*(?:条|則|个)?\s*消息", q, flags=re.I)
    if not limit_match:
        limit_match = re.search(r"(\d+)\s*(?:条|則|个)?\s*消息", q, flags=re.I)
    limit = int(limit_match.group(1)) if limit_match else _extract_int(q, default=default_limit, minimum=1, maximum=100)
    limit = max(1, min(limit, 100))

    chat_name = explicit_chat_name or _extract_chat_name(q)

    conditions: List[str] = []
    params: List[Any] = []
    reason = []

    if chat_name:
        conditions.append("chat_name LIKE ?")
        params.append(f"%{chat_name}%")
        reason.append("chat_name")

    if any(k in q_lower for k in ["今天", "today"]):
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        conditions.append("timestamp >= ?")
        params.append(start_of_day)
        reason.append("today")
    elif any(k in q_lower for k in ["最近24小时", "近24小时", "24小时", "last 24 hours"]):
        since = (datetime.now() - timedelta(hours=24)).isoformat()
        conditions.append("timestamp >= ?")
        params.append(since)
        reason.append("last_24h")

    keyword = _extract_keyword_query(q)
    if keyword:
        conditions.append("content LIKE ?")
        params.append(f"%{keyword}%")
        reason.append("keyword")
    elif not any(k in q_lower for k in ["最近", "latest", "recent", "今天", "today", "24小时", "消息"]) and q:
        conditions.append("content LIKE ?")
        params.append(f"%{q}%")
        reason.append("fallback_keyword")

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = (
        "SELECT chat_id, chat_name, sender_id, sender_name, content, timestamp, message_id "
        "FROM conversations"
        f"{where_clause} ORDER BY timestamp DESC LIMIT ?"
    )
    params.append(limit)
    return sql, params, {"kind": "conversation", "limit": limit, "chat_name": chat_name, "reason": reason, "query": q}


def _task_nl_to_sql(text: str, *, default_limit: int = 10) -> Tuple[str, List[Any], Dict[str, Any]]:
    q = _normalize_ws(text)
    q_lower = q.lower()
    limit = _extract_int(q, default=default_limit, minimum=1, maximum=100)

    if any(k in q_lower for k in ["任务状态", "status summary", "status count", "状态汇总", "各状态"]):
        sql = "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status ORDER BY count DESC, status ASC"
        return sql, [], {"kind": "task_status_summary", "query": q}

    if any(k in q_lower for k in ["最近任务", "latest tasks", "recent tasks", "最近的任务"]) or re.search(r"最近\s*\d*\s*个?\s*任务", q_lower):
        sql = (
            "SELECT task_id, title, status, assigned_worker, created_at, updated_at, completed_at, last_error "
            "FROM tasks ORDER BY COALESCE(updated_at, created_at) DESC LIMIT ?"
        )
        return sql, [limit], {"kind": "recent_tasks", "limit": limit, "query": q}

    task_ref = _extract_task_ref(q)
    if task_ref and any(k in q_lower for k in ["详情", "detail", "状态", "status"]):
        sql = (
            "SELECT task_id, title, description, status, priority, assigned_worker, created_by, created_at, updated_at, completed_at, result, error_message, last_error "
            "FROM tasks WHERE task_id = ? OR title LIKE ? "
            "ORDER BY COALESCE(updated_at, created_at) DESC LIMIT ?"
        )
        return sql, [task_ref, f"%{task_ref}%", limit], {"kind": "task_detail", "task_ref": task_ref, "limit": limit, "query": q}

    if any(k in q_lower for k in ["失败任务", "error tasks", "failed tasks"]):
        sql = (
            "SELECT task_id, title, status, updated_at, error_message, last_error "
            "FROM tasks WHERE status IN ('error', 'failed') ORDER BY COALESCE(updated_at, created_at) DESC LIMIT ?"
        )
        return sql, [limit], {"kind": "failed_tasks", "limit": limit, "query": q}

    raise ValueError("Unable to convert natural language to safe task SQL")


def _nl_to_safe_sql(query: str, db_alias: str, *, default_limit: int = 20, chat_name: Optional[str] = None) -> Tuple[str, List[Any], Dict[str, Any]]:
    alias = (db_alias or "episodic").lower()
    if alias in {"episodic", "episodic_memory", "conversations"}:
        return _conversation_nl_to_sql(query, default_limit=default_limit, explicit_chat_name=chat_name)
    if alias in {"tasks", "task_queue"}:
        return _task_nl_to_sql(query, default_limit=default_limit)
    raise ValueError(f"Natural language SQL not supported for db alias: {alias}")


def _summarize_conversation_rows(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "未找到匹配消息"
    summary_lines = []
    for r in rows[:8]:
        ts = str(r.get("timestamp") or "")
        summary_lines.append(
            f"[{ts}] {r.get('chat_name') or '未知群'} / {r.get('sender_name') or r.get('sender_id') or '未知发送者'}: {_truncate_text(r.get('content'), 120)}"
        )
    return "\n".join(summary_lines)


async def local_conversation_search_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        query = str(input.get("query") or input.get("keyword") or "").strip()
        if not query:
            return {"success": False, "data": None, "error": "Missing required field: query"}

        limit = max(1, min(int(input.get("limit", 20) or 20), 100))
        chat_name = str(input.get("chat_name") or "").strip() or None

        _ensure_exists(EPISODIC_DB)
        sql, params, parsed = _conversation_nl_to_sql(query, default_limit=limit, explicit_chat_name=chat_name)
        rows, executed_sql = _run_sql(EPISODIC_DB, sql, params, limit=limit)
        formatted = _format_rows(rows, limit=limit)
        chats = sorted({str(r.get("chat_name") or "") for r in formatted if r.get("chat_name")})

        return {
            "success": True,
            "data": {
                "query": query,
                "limit": limit,
                "count": len(formatted),
                "chats": chats,
                "results": formatted,
                "summary": _summarize_conversation_rows(formatted),
                "source": str(EPISODIC_DB),
                "resolved_sql": executed_sql,
                "resolved_params": params,
                "parsed": parsed,
            },
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


async def local_dashboard_status_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        status = _safe_json_load(STATUS_JSON, {})
        tasks_data = _safe_json_load(TASKS_JSON, {"tasks": []})
        tasks = tasks_data.get("tasks") or []
        recent_limit = max(1, min(int(input.get("limit", 10) or 10), 50))
        query = str(input.get("query") or "").strip()
        recent_tasks = sorted(tasks, key=lambda t: (t.get("updated_at") or t.get("created_at") or ""), reverse=True)[:recent_limit]
        summary = {
            "status_file": str(STATUS_JSON),
            "tasks_file": str(TASKS_JSON),
            "task_total": len(tasks),
            "queued_or_running": len([t for t in tasks if t.get("status") in {"queued", "running"}]),
            "done": len([t for t in tasks if t.get("status") == "done"]),
            "error": len([t for t in tasks if t.get("status") == "error"]),
            "latest_task": recent_tasks[0] if recent_tasks else None,
        }

        task_query_result: Dict[str, Any] | None = None
        if query:
            try:
                _ensure_exists(TASK_DB)
                sql, params, parsed = _task_nl_to_sql(query, default_limit=recent_limit)
                rows, executed_sql = _run_sql(TASK_DB, sql, params, limit=recent_limit)
                task_query_result = {
                    "query": query,
                    "resolved_sql": executed_sql,
                    "resolved_params": params,
                    "parsed": parsed,
                    "rows": _format_rows(rows, limit=recent_limit),
                    "row_count": min(len(rows), recent_limit),
                    "db_path": str(TASK_DB),
                }
            except Exception as query_err:
                task_query_result = {
                    "query": query,
                    "error": str(query_err),
                }

        return {
            "success": True,
            "data": {
                "summary": summary,
                "status": status,
                "recent_tasks": recent_tasks,
                "task_query": task_query_result,
            },
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


async def local_db_query_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        query = str(input.get("query") or "").strip()
        db_alias = str(input.get("db") or input.get("db_alias") or "episodic").strip().lower()
        limit = max(1, min(int(input.get("limit", 50) or 50), 500))
        chat_name = str(input.get("chat_name") or "").strip() or None
        if not query:
            return {"success": False, "data": None, "error": "Missing required field: query"}

        db_path = DB_ALIASES.get(db_alias)
        if not db_path:
            return {
                "success": False,
                "data": {"available_dbs": {k: str(v) for k, v in DB_ALIASES.items()}},
                "error": f"Unknown db alias: {db_alias}",
            }
        _ensure_exists(db_path)

        params: List[Any] = []
        parsed: Optional[Dict[str, Any]] = None
        ok, checked_or_error = _is_safe_readonly_sql(query)
        if ok:
            sql = checked_or_error
        else:
            sql, params, parsed = _nl_to_safe_sql(query, db_alias, default_limit=limit, chat_name=chat_name)

        rows, executed_sql = _run_sql(db_path, sql, params, limit=limit)
        formatted = _format_rows(rows, limit=limit)
        return {
            "success": True,
            "data": {
                "db": db_alias,
                "db_path": str(db_path),
                "query": executed_sql,
                "original_query": query,
                "resolved_params": params,
                "parsed": parsed,
                "row_count": len(formatted),
                "rows": formatted,
            },
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


async def local_python_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        script = input.get("script")
        code = input.get("code")
        raw_args = input.get("args") or []
        timeout = int(input.get("timeout", 180) or 180)
        cwd = _expand_local_path(input.get("cwd") or str(VECTORBRAIN_HOME)) or str(VECTORBRAIN_HOME)

        if not script and not code:
            return {"success": False, "data": None, "error": "script or code is required"}

        env = build_runtime_env(os.environ.copy())
        env["PYTHONPATH"] = str(VECTORBRAIN_HOME) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

        args: List[str] = []
        for arg in raw_args:
            arg_str = str(arg)
            if arg_str.startswith("~") or arg_str.startswith("/"):
                args.append(_expand_local_path(arg_str) or arg_str)
            else:
                args.append(arg_str)

        resolved_script = _expand_local_path(script) if script else None
        if resolved_script:
            cmd = ["python3", resolved_script, *args]
        else:
            cmd = ["python3", "-c", str(code), *args]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "success": False,
                "data": {"command": cmd, "cwd": cwd, "resolved_script": resolved_script, "resolved_args": args},
                "error": f"local_python timed out after {timeout} seconds",
            }

        out = stdout.decode("utf-8", errors="ignore").strip()
        err = stderr.decode("utf-8", errors="ignore").strip()
        return {
            "success": proc.returncode == 0,
            "data": {
                "command": cmd,
                "cwd": cwd,
                "resolved_script": resolved_script,
                "resolved_args": args,
                "stdout": out,
                "stderr": err,
                "exit_code": proc.returncode,
            },
            "error": None if proc.returncode == 0 else (err or f"exit_code={proc.returncode}"),
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


def _local_query_score(input: Dict[str, Any]) -> float:
    text = " ".join(str(v) for v in (input or {}).values()).lower()
    score = 0.6
    if any(k in text for k in ["feishu", "lark", "conversation", "chat", "群聊", "消息", "本地", "sqlite", "database", "数据库"]):
        score += 0.8
    if any(k in text for k in ["local", "本地", "conversations", "今天", "24小时", "最近消息"]):
        score += 0.4
    return score


def _dashboard_query_score(input: Dict[str, Any]) -> float:
    text = " ".join(str(v) for v in (input or {}).values()).lower()
    score = 0.8
    if any(k in text for k in ["dashboard", "monitor", "看板", "状态页", "任务状态", "最近任务", "任务详情", "task status", "recent tasks"]):
        score += 1.2
    if any(k in text for k in ["task", "tasks", "状态", "status", "运行中", "queued", "done", "error"]):
        score += 0.5
    return score


def _db_query_score(input: Dict[str, Any]) -> float:
    text = " ".join(str(v) for v in (input or {}).values()).lower()
    score = 0.7
    if any(k in text for k in ["sql", "sqlite", "database", "db", "数据库", "conversations", "tasks", "task_queue"]):
        score += 1.0
    if any(k in text for k in ["最近任务", "任务状态", "查询任务", "最近消息", "今天消息"]):
        score += 0.4
    return score


local_conversation_search_tool = Tool(
    name="local_conversation_search",
    display_name="Local Conversation Search",
    description="Search local Feishu/Lark conversations from episodic_memory.db instead of web search",
    capabilities=["local_query", "conversation", "database", "read"],
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 20},
            "chat_name": {"type": "string"},
        },
    },
    output_schema={"type": "object", "properties": {"count": {"type": "integer"}, "results": {"type": "array"}}},
    handler=local_conversation_search_handler,
    score_fn=_local_query_score,
    timeout=60,
    version="2.0",
    allow_dry_run=True,
)

tool_registry.register(local_conversation_search_tool)


local_dashboard_status_tool = Tool(
    name="local_dashboard_status",
    display_name="Local Dashboard Status",
    description="Read monitor_center dashboard/task status from local JSON state and task DB",
    capabilities=["local_query", "dashboard", "monitor", "read"],
    input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 10}, "query": {"type": "string"}}},
    output_schema={"type": "object", "properties": {"summary": {"type": "object"}}},
    handler=local_dashboard_status_handler,
    score_fn=_dashboard_query_score,
    timeout=30,
    version="2.0",
    allow_dry_run=True,
)

tool_registry.register(local_dashboard_status_tool)


local_db_query_tool = Tool(
    name="local_db_query",
    display_name="Local DB Query",
    description="Run safe read-only SQL against local VectorBrain sqlite databases, including NL -> SQL conversion for conversations/tasks",
    capabilities=["local_query", "database", "sqlite", "read"],
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string"},
            "db": {"type": "string", "default": "episodic"},
            "db_alias": {"type": "string"},
            "chat_name": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
    },
    output_schema={"type": "object", "properties": {"rows": {"type": "array"}, "row_count": {"type": "integer"}}},
    handler=local_db_query_handler,
    score_fn=_db_query_score,
    timeout=60,
    version="2.0",
    allow_dry_run=True,
)

tool_registry.register(local_db_query_tool)


local_python_tool = Tool(
    name="local_python",
    display_name="Local Python Runner",
    description="Run local Python code or scripts in an isolated subprocess with VectorBrain PYTHONPATH",
    capabilities=["local_execute", "python", "shell", "execute"],
    input_schema={
        "type": "object",
        "properties": {
            "script": {"type": "string"},
            "code": {"type": "string"},
            "args": {"type": "array"},
            "timeout": {"type": "integer", "default": 180},
            "cwd": {"type": "string"},
        },
    },
    output_schema={"type": "object", "properties": {"stdout": {"type": "string"}, "stderr": {"type": "string"}, "exit_code": {"type": "integer"}}},
    handler=local_python_handler,
    score_fn=lambda data: 1.1 if ((data or {}).get("script") or (data or {}).get("code")) else 0.4,
    timeout=240,
    version="1.0",
    allow_dry_run=False,
)

tool_registry.register(local_python_tool)
