#!/usr/bin/env python3
"""
Layer: runtime
Status: primary
Boundary: runtime service surface for MCP/JSON-RPC; exposes runtime, not source-of-truth storage.
Architecture refs:
- architecture/layer-manifest.md
- architecture/runtime-boundary-rules.md

VectorBrain MCP Server v3 - stdio JSON-RPC, MCP-shaped responses.
"""

from __future__ import annotations

import asyncio
import json
import sys
import contextlib
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path.home() / ".vectorbrain"))

with contextlib.redirect_stdout(sys.stderr):
    from runtime.model_router import model_router
    from runtime.orchestrator import mcp_orchestrator, OrchestratorTask
    from runtime.tools.registry import tool_registry
    from runtime.tools.planner import detect_intent
    from runtime.workflows.loader import load_workflow
    from runtime.skills.registry import skill_registry
    from runtime.tools.executor import tool_executor
    from runtime.tools.router import tool_router


SERVER_INFO = {
    "name": "vectorbrain-mcp-orchestrator",
    "version": "0.3.0",
    "protocolVersion": "2024-11-05",
    "transport": "stdio-jsonrpc",
}


def _ok(id_value: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "result": result}


def _err(id_value: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": id_value, "error": {"code": code, "message": message}}
    if data is not None:
        payload["error"]["data"] = data
    return payload


def _tool_result_to_mcp(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
        "structuredContent": result,
        "isError": not bool(result.get("success")),
    }


async def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    with contextlib.redirect_stdout(sys.stderr):
        tool_registry.load_builtin_tools()
        tool = tool_registry.get(name)
        if not tool:
            raise ValueError(f"unknown tool: {name}")
        result = await tool_executor.execute_tool(tool=tool, input_data=arguments or {}, timeout=tool.timeout)
    return _tool_result_to_mcp(result)


async def handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    id_value = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    try:
        with contextlib.redirect_stdout(sys.stderr):
            if method == "ping":
                return _ok(id_value, {"pong": True, **SERVER_INFO})

            if method == "initialize":
                tool_registry.load_builtin_tools()
                skill_registry.load()
                return _ok(id_value, {
                    "protocolVersion": SERVER_INFO["protocolVersion"],
                    "serverInfo": {"name": SERVER_INFO["name"], "version": SERVER_INFO["version"]},
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "experimental": {
                            "orchestrate": True,
                            "skills": True,
                            "routing": True,
                            "workflows": True,
                        },
                    },
                    "instructions": "Use tools/list then tools/call, or orchestrate/task/route for routed execution.",
                })

            if method == "notifications/initialized":
                return _ok(id_value, {"ack": True})

            if method == "tools/list":
                tool_registry.load_builtin_tools()
                return _ok(id_value, {"tools": tool_registry.to_mcp_tools()})

            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if not name:
                    return _err(id_value, -32602, "missing tool name")
                return _ok(id_value, await _call_tool(name, arguments))

            if method == "skills/list":
                return _ok(id_value, skill_registry.to_json())

            if method == "skills/match":
                title = params.get("title") or params.get("task") or ""
                description = params.get("description") or ""
                return _ok(id_value, {
                    "match": skill_registry.match_task(title, description).to_dict() if skill_registry.match_task(title, description) else None,
                    "ranked": skill_registry.rank_task(title, description, limit=int(params.get("limit", 5) or 5)),
                })

            if method == "task/route":
                title = params.get("title") or params.get("task") or ""
                description = params.get("description") or ""
                if not title:
                    return _err(id_value, -32602, "missing title")
                task = OrchestratorTask(title=title, description=description, workflow=params.get("workflow"), skill=params.get("skill"), model=params.get("model"))
                return _ok(id_value, mcp_orchestrator.route_task(task))

            if method == "tool/rank":
                capability = params.get("capability")
                if not capability:
                    return _err(id_value, -32602, "missing capability")
                ranked = tool_router.rank(capability, params.get("input") or {})
                return _ok(id_value, {
                    "capability": capability,
                    "ranked_tools": [{k: v for k, v in item.items() if k != "tool"} for item in ranked],
                })

            if method == "model/route":
                title = params.get("title") or params.get("task") or ""
                description = params.get("description") or ""
                workflow = params.get("workflow") or detect_intent(title, description)
                return _ok(id_value, model_router.route_task(title, description, workflow=workflow, explicit_model=params.get("model")))

            if method == "workflow/load":
                name = params.get("name")
                if not name:
                    return _err(id_value, -32602, "missing workflow name")
                wf = load_workflow(name)
                return _ok(id_value, wf)

            if method == "orchestrate":
                result = await mcp_orchestrator.orchestrate(params, dry_run=bool(params.get("dry_run", False)))
                return _ok(id_value, result)

            return _err(id_value, -32601, f"method not found: {method}")
    except Exception as e:
        return _err(id_value, -32000, str(e))


async def main() -> None:
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as e:
            sys.stdout.write(json.dumps(_err(None, -32700, f"parse error: {e}"), ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue
        resp = await handle_request(req)
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
