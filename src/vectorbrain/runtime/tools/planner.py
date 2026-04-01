#!/usr/bin/env python3
"""
VectorBrain Task Planner - Stage 2 (Workflow 化)

将用户任务拆解成可执行的步骤计划
使用 Intent → Workflow 模式（替代 Keyword → Tool）
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# 添加 VectorBrain 到路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from runtime.tools.executor import Plan, PlanStep, create_plan
from runtime.tools.router import tool_router
from runtime.tools.registry import tool_registry
from runtime.workflows.loader import load_workflow, WorkflowNotFound


# ============================================================================
# Workflow 定义
# ============================================================================

WORKFLOWS = {
    # 本地消息 / 对话查询
    "local_conversation_query": [
        {"id": "conversation_search", "tool": "local_conversation_search", "capability": "local_query", "input_template": {"query": "{task}", "hours": 168, "limit": 20}},
    ],

    # 本地 dashboard / monitor 状态查询
    "local_dashboard_query": [
        {"id": "dashboard_status", "tool": "local_dashboard_status", "capability": "local_query", "input_template": {"query": "{task}", "limit": 10}},
    ],

    # 本地 sqlite / db 读查询
    "local_db_query": [
        {"id": "db_query", "tool": "local_db_query", "capability": "local_query", "input_template": {"query": "{content}", "db": "episodic", "limit": 50}},
    ],

    # 本地 Python 独立执行
    "local_python_exec": [
        {"id": "local_python", "tool": "local_python", "capability": "local_execute", "input_template": {"script": "{path}", "cwd": "~/.vectorbrain"}},
    ],

    # 搜索并保存文件
    "search_and_save": [
        {"id": "search", "capability": "search", "input_template": {"query": "{task}"}},
        # fetch 使用 search 的第一个结果 URL
        {"id": "fetch", "capability": "fetch", "depends_on": ["search"], "input_template": {"url": "{steps.search.data.results[0].url}"}},
        # write 写入 fetch 的内容
        {"id": "write", "capability": "write", "depends_on": ["fetch"], "input_template": {"path": "~/vectorbrain_output.txt", "content": "{steps.fetch.data.content}"}},
    ],

    # DAG 示例：两个抓取并行，再汇总写入
    "dag_parallel_fetch": [
        {"id": "fetch_a", "capability": "fetch", "input_template": {"url": "{url}"}},
        {"id": "fetch_b", "capability": "fetch", "input_template": {"url": "https://example.com"}},
        {"id": "write", "capability": "write", "depends_on": ["fetch_a", "fetch_b"], "input_template": {"path": "~/vectorbrain_parallel_output.txt", "content": "A:\n{steps.fetch_a.data.content}\n\nB:\n{steps.fetch_b.data.content}"}},
    ],
    
    # 仅搜索
    "search_only": [
        {"id": "search", "capability": "search", "input_template": {"query": "{task}"}},
    ],
    
    # 抓取网页
    "fetch_only": [
        {"id": "fetch", "capability": "fetch", "input_template": {"url": "{url}"}},
    ],
    
    # 读取文件
    "read_file": [
        {"id": "read", "capability": "read", "input_template": {"path": "{path}"}},
    ],
    
    # 写入文件
    "write_file": [
        {"id": "write", "capability": "write", "input_template": {"path": "~/vectorbrain_output.txt", "content": "{content}"}},
    ],
    
    # 执行命令
    "exec_command": [
        {"id": "exec", "capability": "shell", "input_template": {"cmd": "{cmd}"}},
    ],
    
    # 发送消息
    "send_message": [
        {"id": "send", "capability": "message", "input_template": {"channel": "{channel}", "message": "{message}"}},
    ],
    
    # 默认工作流（搜索）
    "default": [
        {"id": "search", "capability": "search", "input_template": {"query": "{task}"}},
    ],
}


# ============================================================================
# Intent Detection
# ============================================================================


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(kw in text for kw in keywords)


def _is_script_status_query(full_text: str) -> bool:
    query_verbs = ["检查", "查看", "看", "确认", "查询", "状态", "结果", "进度", "有没有", "是否"]
    status_phrases = [
        "成功运行", "执行结果", "跑完", "成功", "完成", "状态", "结果", "日志", "输出",
        "有没有跑完", "是否成功", "执行成功", "运行结果", "run result", "status",
    ]
    script_subjects = ["脚本", "script", "python", ".py", "会话系统", "任务", "task", "dashboard", "monitor"]
    return _contains_any(full_text, query_verbs) and _contains_any(full_text, status_phrases) and _contains_any(full_text, script_subjects)


def _is_explicit_local_python_exec(full_text: str) -> bool:
    exec_verbs = ["执行脚本", "运行脚本", "运行本地", "执行本地", "运行 python", "执行 python", "run script", "execute script"]
    python_targets = ["python", "脚本", "script", ".py"]
    if _contains_any(full_text, exec_verbs) and _contains_any(full_text, python_targets):
        return True
    if ".py" in full_text and _contains_any(full_text, ["运行", "执行", "run", "execute"]):
        return True
    return False


def detect_intent(task_title: str, task_description: str = None) -> str:
    """
    检测任务意图
    
    Args:
        task_title: 任务标题
        task_description: 任务描述
        
    Returns:
        意图名称（匹配 WORKFLOWS 的键）
    """
    title = task_title.lower()
    description = (task_description or "").lower()
    full_text = f"{title} {description}"
    
    # 复杂任务信号：这类任务不应该被 local_conversation_query 拦截
    complex_task_signals = [
        ".xls", ".xlsx", ".csv", ".pdf", ".doc", ".docx", ".pptx",  # 文件类型
        "帮我", "帮我做", "帮我处理", "帮我分析", "帮我生成", "帮我写",  # 明确要求执行
        "处理数据", "分析数据", "生成报告", "数据分析", "excel", "spreadsheet",
        "后台执行", "后台运行", "异步执行", "background",
    ]
    is_complex_task = any(kw in full_text for kw in complex_task_signals)

    local_chat_signals = [
        "feishu", "lark", "群聊", "聊天", "conversation", "conversations", "消息", "chat", "群名",
        "最近消息", "今天消息", "24小时消息", "新增消息", "新增", "会话数据", "本地会话", "本地飞书", "飞书抓取",
    ]
    local_dashboard_signals = [
        "dashboard", "monitor center", "monitor_center", "任务面板", "看板", "状态页", "任务状态", "最近任务", "任务详情",
        "脚本状态", "脚本结果", "执行结果", "运行结果", "脚本有没有跑完", "脚本是否成功", "会话系统脚本是否成功运行",
        "dashboard数据", "本地 dashboard",
    ]
    local_db_signals = ["sqlite", "database", "db", "数据库", "表", "sql", "conversations 表", "episodic_memory", "task_queue", "tasks表", "本地数据库"]
    notify_signals = ["notify", "notification", "发送结果", "通知我", "发给我", "完成后通知"]

    # 检查组合意图
    has_search = any(kw in full_text for kw in ["search", "find", "lookup", "research", "搜索", "查找"]) 
    has_save = any(kw in full_text for kw in ["save", "file", "write", "download", "保存", "写入"])
    has_fetch = any(kw in full_text for kw in ["fetch", "grab", "crawl", "get content", "http", "url", "website", "网页", "抓取"])
    has_read = any(kw in full_text for kw in ["read", "parse", "analyze", "读取", "分析"])
    has_exec = any(kw in full_text for kw in ["exec", "run command", "shell", "terminal", "bash", "命令"]) 
    has_send = any(kw in full_text for kw in ["send", "message", "notify", "tell", "发送", "通知"]) or any(kw in full_text for kw in notify_signals)

    # 第一优先级：本地任务优先，不落 web_search
    if any(kw in full_text for kw in local_dashboard_signals) or _is_script_status_query(full_text):
        return "local_dashboard_query"
    if _is_explicit_local_python_exec(full_text):
        return "local_python_exec"
    # 只有非复杂任务才走本地对话查询
    if not is_complex_task and any(kw in full_text for kw in local_chat_signals):
        return "local_conversation_query"
    if any(kw in full_text for kw in local_db_signals):
        return "local_db_query"
    
    # 优先级匹配
    if "dag" in full_text or "parallel" in full_text:
        return "dag_parallel_fetch"

    if has_search and has_save:
        return "search_and_save"
    elif has_search:
        return "search_only"
    elif has_fetch:
        return "fetch_only"
    elif has_read:
        return "read_file"
    elif has_exec:
        return "exec_command"
    elif has_send:
        return "send_message"
    elif has_save:
        return "write_file"
    else:
        return "default"


# ============================================================================
# Task Planner 类
# ============================================================================

class TaskPlanner:
    """
    任务规划器
    
    使用 Intent → Workflow 模式
    """
    
    def __init__(self, router=None):
        """
        初始化规划器
        
        Args:
            router: ToolRouter 实例
        """
        self.router = router or tool_router
    
    def create_plan(self, task_id: str, task_title: str, task_description: str = None) -> Plan:
        """
        创建执行计划
        
        Args:
            task_id: 任务 ID
            task_title: 任务标题
            task_description: 任务描述（可选）
            
        Returns:
            Plan 实例
        """
        print(f"\n{'='*60}")
        print(f"Creating Plan: {task_title}")
        print(f"{'='*60}\n")
        
        # 检测意图
        intent = detect_intent(task_title, task_description)
        print(f"[Planner] Detected intent: {intent}")
        
        # 获取工作流（优先从 ~/.vectorbrain/workflows/ 加载，其次回退到内置 WORKFLOWS）
        try:
            wf = load_workflow(intent)
            workflow_steps = wf.get("steps", [])
            print(f"[Planner] Using workflow from file: {wf.get('name')} ({len(workflow_steps)} steps)")
        except WorkflowNotFound:
            workflow_steps = WORKFLOWS.get(intent, WORKFLOWS["default"])
            print(f"[Planner] Using builtin workflow: {intent} ({len(workflow_steps)} steps)")

        # 生成步骤
        steps = self._generate_steps(intent, workflow_steps, task_title, task_description)
        
        # 创建计划
        plan = Plan(
            task_id=task_id,
            steps=steps,
            created_at=datetime.now().isoformat()
        )
        # 补充 plan 元信息（trace / context 可能用到）
        plan.title = task_title
        plan.intent = intent
        plan.workflow = intent
        
        print(f"\nPlan created with {len(steps)} steps\n")
        
        return plan
    
    def _generate_steps(self, intent: str, workflow: List[Dict], task_title: str, task_description: str = None) -> List[PlanStep]:
        """
        根据工作流生成步骤
        
        Args:
            intent: 意图名称
            workflow: 工作流定义
            task_title: 任务标题
            task_description: 任务描述
            
        Returns:
            PlanStep 列表
        """
        steps = []
        
        # 提取上下文信息
        context = self._extract_context(task_title, task_description)
        
        for i, step_config in enumerate(workflow):
            capability = step_config.get("capability")
            if not capability:
                raise ValueError(f"Workflow step missing capability: {step_config}")

            # 支持两种格式：input_template（内置）或 input（文件）
            input_template = step_config.get("input_template") or step_config.get("input") or {}
            
            # 填充输入模板
            input_data = self._fill_template(input_template, context, task_title, task_description)

            step_id = step_config.get("id") or f"step_{i+1}"
            explicit_tool = step_config.get("tool")
            
            # 创建步骤（优先使用 workflow step 的 id；tool 可显式指定，否则由 Router 决定）
            step = PlanStep(
                id=step_id,
                tool=explicit_tool,
                capability=capability,
                depends_on=step_config.get("depends_on", []) or [],
                input=input_data,
                timeout=step_config.get("timeout"),
                max_retries=step_config.get("max_retries", 0) or 0,
                retry_backoff=step_config.get("retry_backoff", 0.5) or 0.5,
                retryable_errors=step_config.get("retryable_errors", []) or [],
                on_error=step_config.get("on_error", "fail") or "fail",
            )
            
            steps.append(step)
        
        # 打印步骤
        print("Generated Steps:")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. [{step.capability}] → {step.input}")
        
        print()
        
        return steps
    
    def _extract_context(self, task_title: str, task_description: str = None) -> Dict[str, Any]:
        """
        从任务中提取上下文信息
        
        Args:
            task_title: 任务标题
            task_description: 任务描述
            
        Returns:
            上下文字典
        """
        import re
        
        text = f"{task_title} {task_description or ''}"
        context = {
            "task": task_title,
            "description": task_description or "",
        }
        
        # 提取 URL
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        url_matches = re.findall(url_pattern, text)
        if url_matches:
            context["url"] = url_matches[0]
        
        # 提取文件路径
        path_pattern = r'(~/[\w\-\.\/]+|/[\w\-\.\/]+\.[\w]+)'
        path_matches = re.findall(path_pattern, text)
        for match in path_matches:
            if match.startswith('~/') or '.' in match:
                context["path"] = match
                break
        
        # 提取命令（引号内内容）
        cmd_pattern = r'["\']([^"\']+)["\']'
        cmd_matches = re.findall(cmd_pattern, text)
        if cmd_matches:
            context["cmd"] = cmd_matches[0]
        
        # 提取渠道
        if "feishu" in text.lower() or "lark" in text.lower():
            context["channel"] = "feishu"
        elif "telegram" in text.lower():
            context["channel"] = "telegram"
        elif "slack" in text.lower():
            context["channel"] = "slack"
        
        return context
    
    def _fill_template(self, template: Dict[str, Any], context: Dict[str, Any], task_title: str, task_description: str = None) -> Dict[str, Any]:
        """
        填充输入模板
        
        Args:
            template: 输入模板
            context: 上下文信息
            task_title: 任务标题
            task_description: 任务描述
            
        Returns:
            填充后的输入数据
        """
        result = {}
        
        for key, value in template.items():
            if isinstance(value, str):
                # 替换占位符
                filled = value
                filled = filled.replace("{task}", task_title)
                filled = filled.replace("{content}", task_description or task_title)
                filled = filled.replace("{url}", context.get("url", "https://example.com"))
                filled = filled.replace("{path}", context.get("path", "~/vectorbrain_output.txt"))
                filled = filled.replace("{cmd}", context.get("cmd", task_title))
                filled = filled.replace("{channel}", context.get("channel", "feishu"))
                filled = filled.replace("{message}", task_description or task_title)
                
                # 特殊占位符（需要运行时数据）
                if "{search_result_url}" in filled:
                    filled = filled.replace("{search_result_url}", "https://example.com")  # 由 Executor 填入
                if "{fetch_result}" in filled:
                    filled = filled.replace("{fetch_result}", task_description or task_title)  # 由 Executor 填入

                # 如果是运行时表达式（steps/task/vars），保留给 ExecutionContext 解析
                runtime_expr_prefixes = ("{steps.", "{task.", "{vars.")
                if any(token in value for token in runtime_expr_prefixes):
                    result[key] = value
                else:
                    result[key] = filled
            else:
                result[key] = value
        
        return result


# ============================================================================
# 全局规划器实例
# ============================================================================

task_planner = TaskPlanner()


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    # 加载工具
    tool_registry.load_builtin_tools()
    
    print("=== 测试 1: 搜索并保存 (search_and_save) ===")
    plan = task_planner.create_plan(
        task_id="test_001",
        task_title="Search for shadcn ui documentation and save to file",
        task_description="Find the official documentation and save summary"
    )
    print(f"Steps: {len(plan.steps)}")
    for step in plan.steps:
        print(f"  - {step.capability}: {step.input}")
    
    print("\n=== 测试 2: 仅搜索 (search_only) ===")
    plan = task_planner.create_plan(
        task_id="test_002",
        task_title="Search for Python best practices"
    )
    print(f"Steps: {len(plan.steps)}")
    
    print("\n=== 测试 3: 读取文件 (read_file) ===")
    plan = task_planner.create_plan(
        task_id="test_003",
        task_title="Read file ~/config.txt"
    )
    print(f"Steps: {len(plan.steps)}")
    
    print("\n=== 测试 4: 默认 (default) ===")
    plan = task_planner.create_plan(
        task_id="test_004",
        task_title="What is the weather today?"
    )
    print(f"Steps: {len(plan.steps)}")
    
    print("\n✅ Workflow Planner 测试完成！")
