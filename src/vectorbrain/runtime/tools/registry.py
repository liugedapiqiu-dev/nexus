# SSOT NOTE: This registry is discovery/metadata only. It is not a system source of truth for execution state, runtime status, or final verification.
#!/usr/bin/env python3
"""
VectorBrain Tool Registry
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Any, Optional
import asyncio
import json
from pathlib import Path
from datetime import datetime


@dataclass
class Tool:
    name: str
    display_name: str
    description: str
    capabilities: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler: Callable
    score_fn: Optional[Callable[[Dict[str, Any]], float]] = None
    timeout: int = 60
    version: str = "1.0"
    allow_dry_run: bool = True
    source: str = "builtin"
    tags: Optional[List[str]] = None

    def score(self, input_data: Optional[Dict[str, Any]] = None) -> float:
        if self.score_fn is None:
            return 1.0
        try:
            return float(self.score_fn(input_data or {}))
        except Exception:
            return 0.0


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._loaded = False

    def register(self, tool: Tool):
        self.tools[tool.name] = tool
        print(f"[tool registered] {tool.name} ({tool.display_name})")

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list(self) -> List[Tool]:
        return list(self.tools.values())

    def summary(self):
        print(f"\n{'='*60}")
        print("VectorBrain Tool Registry")
        print(f"{'='*60}")
        print(f"Tools loaded: {len(self.tools)}\n")
        for tool in self.tools.values():
            caps = ", ".join(tool.capabilities)
            print(f"  {tool.name:20} | {tool.display_name:20} | {caps}")
        print(f"{'='*60}\n")

    def capability_map(self) -> Dict[str, List[str]]:
        cap_map = {}
        for tool in self.tools.values():
            for cap in tool.capabilities:
                cap_map.setdefault(cap, []).append(tool.name)
        return cap_map

    def get_by_capability(self, capability: str) -> List[Tool]:
        return [tool for tool in self.tools.values() if capability in tool.capabilities]

    def load_builtin_tools(self):
        if self._loaded:
            return
        print("[info] Loading builtin tools...")
        try:
            from runtime.tools.builtin import web_tools  # noqa:F401
            from runtime.tools.builtin import file_tools  # noqa:F401
            from runtime.tools.builtin import shell_tools  # noqa:F401
            from runtime.tools.builtin import message_tools  # noqa:F401
            from runtime.tools.builtin import skill_tools  # noqa:F401
            from runtime.tools.builtin import local_data_tools  # noqa:F401
            self._loaded = True
            print(f"[info] Builtin tools loaded: {len(self.tools)} tools")
        except ImportError as e:
            print(f"[warning] Could not load builtin tools: {e}")
            print("[info] Run 'vectorbrain doctor' after implementing all tools")

    def to_json(self) -> Dict[str, Any]:
        return {
            "tools": len(self.tools),
            "capabilities": self.capability_map(),
            "tool_list": [self._tool_json(tool) for tool in self.tools.values()],
        }

    def _tool_json(self, tool: Tool) -> Dict[str, Any]:
        return {
            "name": tool.name,
            "display_name": tool.display_name,
            "description": tool.description,
            "capabilities": tool.capabilities,
            "version": tool.version,
            "source": tool.source,
            "allow_dry_run": tool.allow_dry_run,
            "input_schema": tool.input_schema,
            "output_schema": tool.output_schema,
            "tags": tool.tags or [],
        }

    def to_mcp_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "title": tool.display_name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "annotations": {
                    "capabilities": tool.capabilities,
                    "version": tool.version,
                    "allow_dry_run": tool.allow_dry_run,
                    "source": tool.source,
                },
            }
            for tool in self.tools.values()
        ]


tool_registry = ToolRegistry()


def validate_input(schema: Dict, data: Dict):
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")


async def run_tool(tool: Tool, input_data: Dict) -> Dict:
    validate_input(tool.input_schema, input_data)
    try:
        result = await asyncio.wait_for(tool.handler(input_data), timeout=tool.timeout)
        return result
    except asyncio.TimeoutError:
        return {"success": False, "data": None, "error": f"Tool {tool.name} timed out after {tool.timeout} seconds"}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


def log_tool_execution(task_id: str, tool_name: str, input_data: Dict, result: Dict, log_dir: str = None):
    if log_dir is None:
        log_dir = Path.home() / ".vectorbrain" / "logs"
    log_file = Path(log_dir) / "tool_execution.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "tool": tool_name,
        "input": input_data,
        "result": result,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
