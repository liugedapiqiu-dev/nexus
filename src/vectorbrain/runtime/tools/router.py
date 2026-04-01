#!/usr/bin/env python3
"""
VectorBrain Tool Router - scored routing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from typing import List, Optional, Dict, Any
from runtime.tools.registry import Tool, tool_registry


class ToolRouter:
    """根据能力与输入语义选择最佳工具。"""

    def __init__(self, registry=None):
        self.registry = registry or tool_registry

    def route(self, capability: str) -> List[Tool]:
        tools = self.registry.get_by_capability(capability)
        return sorted(tools, key=lambda t: t.name)

    def _heuristic_bonus(self, tool: Tool, capability: str, input_data: Optional[dict] = None) -> float:
        data = input_data or {}
        bonus = 0.0
        text = " ".join(str(v) for v in data.values() if isinstance(v, (str, int, float))).lower()

        if capability == "fetch" and tool.name == "web_fetch" and str(data.get("url", "")).startswith(("http://", "https://")):
            bonus += 1.5
        if capability == "search" and tool.name == "web_search" and data.get("query"):
            bonus += 1.5
        if capability == "read" and tool.name == "read_file" and data.get("path"):
            bonus += 1.5
        if capability == "write" and tool.name == "write_file" and data.get("path") is not None:
            bonus += 1.5
        if capability == "shell" and tool.name == "exec_shell" and data.get("cmd"):
            bonus += 1.5
        if capability == "message" and tool.name == "send_message" and data.get("message"):
            bonus += 1.5
        if capability == "skill" and tool.name == "openclaw_skill" and data.get("skill"):
            bonus += 2.0
        if capability == "local_query" and tool.name in {"local_conversation_search", "local_dashboard_status", "local_db_query"}:
            bonus += 2.2
        if capability == "local_execute" and tool.name == "local_python":
            bonus += 1.8

        local_signals = ["feishu", "lark", "conversation", "conversations", "chat", "dashboard", "monitor_center", "sqlite", "database", "db", "本地", "群聊", "消息", "数据库", "任务状态", "最近任务", "任务详情", "今天消息", "24小时消息"]
        if any(k in text for k in local_signals):
            if tool.name in {"local_conversation_search", "local_dashboard_status", "local_db_query"}:
                bonus += 1.8
            if tool.name == "web_search":
                bonus -= 1.1
            if tool.name == "web_fetch":
                bonus -= 0.6

        if any(k in text for k in ["http://", "https://", "url", "website", "网页"]):
            if tool.name == "web_fetch":
                bonus += 0.5
        if any(k in text for k in ["search", "find", "lookup", "搜索", "查找"]):
            if tool.name == "web_search":
                bonus += 0.5
        if any(k in text for k in ["file", "path", "文件", "读取", "写入"]):
            if tool.name in {"read_file", "write_file"}:
                bonus += 0.5
        if any(k in text for k in ["bash", "shell", "terminal", "命令"]):
            if tool.name == "exec_shell":
                bonus += 0.5
        if any(k in text for k in ["skill", "delegate", "代理", "技能"]):
            if tool.name == "openclaw_skill":
                bonus += 0.5

        return bonus

    def rank(self, capability: str, input_data: Optional[dict] = None) -> List[Dict[str, Any]]:
        ranked = []
        for tool in self.route(capability):
            base = tool.score(input_data or {})
            bonus = self._heuristic_bonus(tool, capability, input_data)
            total = round(base + bonus, 4)
            ranked.append({
                "tool": tool,
                "tool_name": tool.name,
                "base_score": round(base, 4),
                "heuristic_bonus": round(bonus, 4),
                "score": total,
                "capabilities": list(tool.capabilities),
            })
        ranked.sort(key=lambda x: (-x["score"], x["tool_name"]))
        return ranked

    def route_best(self, capability: str, input_data: Optional[dict] = None) -> Optional[Tool]:
        ranked = self.rank(capability, input_data)
        return ranked[0]["tool"] if ranked else None

    def route_task(self, task_title: str) -> List[Tool]:
        title = task_title.lower()
        selected_tools = []

        if any(kw in title for kw in ["search", "find", "lookup"]):
            selected_tools.extend(self.route("search"))
        if any(kw in title for kw in ["fetch", "grab", "download", "crawl"]):
            selected_tools.extend(self.route("fetch"))
        if any(kw in title for kw in ["read", "parse", "analyze"]):
            selected_tools.extend(self.route("read"))
        if any(kw in title for kw in ["write", "create", "save", "generate"]):
            selected_tools.extend(self.route("write"))
        if any(kw in title for kw in ["exec", "run", "command", "shell"]):
            selected_tools.extend(self.route("shell"))
        if any(kw in title for kw in ["send", "message", "notify", "alert"]):
            selected_tools.extend(self.route("message"))
        if any(kw in title for kw in ["skill", "delegate", "agent"]):
            selected_tools.extend(self.route("skill"))

        unique_tools = []
        seen_names = set()
        for tool in selected_tools:
            if tool.name not in seen_names:
                unique_tools.append(tool)
                seen_names.add(tool.name)
        return unique_tools

    def summary(self):
        print("\n" + "="*60)
        print("VectorBrain Tool Router")
        print("="*60)
        cap_map = self.registry.capability_map()
        print(f"Capabilities: {len(cap_map)}")
        print(f"Tools: {len(self.registry.list())}")
        print()
        for cap, tools in sorted(cap_map.items()):
            print(f"  {cap:20} → {', '.join(tools)}")
        print("="*60 + "\n")


tool_router = ToolRouter()


if __name__ == "__main__":
    tool_registry.load_builtin_tools()
    print("=== 测试 1: 按能力查询 ===")
    tools = tool_router.route("research")
    print(f"research → {[t.name for t in tools]}")

    print("\n=== 测试 2: 获取最佳工具 ===")
    tool = tool_router.route_best("coding")
    print(f"coding → {tool.name if tool else None}")

    print("\n=== 测试 3: 评分 ===")
    ranked = tool_router.rank("fetch", {"url": "https://example.com"})
    print(ranked)
