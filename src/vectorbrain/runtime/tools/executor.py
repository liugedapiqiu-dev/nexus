#!/usr/bin/env python3
"""
VectorBrain Tool Executor - Stage 3

执行工具调用，处理超时、验证、日志记录、事件发布
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
import time
import os

# 添加 VectorBrain 到路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from runtime.tools.registry import Tool, tool_registry, validate_input, log_tool_execution
from runtime.tools.router import tool_router
from runtime.tools.event_bus import event_bus, emit_step_executed, emit_tool_called, emit_task_started, emit_task_completed
from runtime.tools.context import ExecutionContext, resolve_templates
from runtime.tools.trace import ExecutionTrace, summarize_exec_result


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class PlanStep:
    """执行计划步骤（v0.2-ready: 支持 DAG 依赖）。

    Attributes:
        id: 步骤唯一 ID（推荐来自 workflow 文件；用于 context 引用与 DAG 依赖）
        tool: 工具名称（可选，为 None 时由 Router 根据 capability 决定）
        capability: 能力（可选，用于自动选择工具）
        depends_on: 依赖的 step.id 列表（DAG）；顺序执行时可为空
        input: 输入数据（可包含模板）
        timeout: 超时时间（可选）
        dry_run: 是否干跑
    """

    id: Optional[str] = None
    tool: Optional[str] = None
    capability: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    input: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None

    # Reliability (v0.3)
    max_retries: int = 0
    retry_backoff: float = 0.5
    retryable_errors: List[str] = field(default_factory=list)
    on_error: str = "fail"  # fail | fail_fast | continue | ignore

    dry_run: bool = False


@dataclass
class Plan:
    """
    执行计划
    
    Attributes:
        task_id: 任务 ID
        steps: 执行步骤列表
        created_at: 创建时间
    """
    task_id: str
    steps: List[PlanStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_step(self, tool: str, input: Dict[str, Any] = None, **kwargs):
        """添加执行步骤"""
        self.steps.append(PlanStep(
            tool=tool,
            input=input or {},
            **kwargs
        ))


@dataclass
class ExecutionResult:
    """
    执行结果
    
    Attributes:
        success: 是否成功
        step_results: 各步骤结果
        error: 错误信息
    """
    success: bool
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    
    def add_result(self, step_index: int, tool: str, result: Dict):
        """添加步骤结果"""
        self.step_results.append({
            "step": step_index,
            "tool": tool,
            "result": result,
            "success": result.get("success", False)
        })


# ============================================================================
# Tool Executor 类
# ============================================================================

class ToolExecutor:
    """
    工具执行器
    
    负责执行工具调用，处理超时、验证、日志记录
    """
    
    def __init__(self, registry=None, router=None, log_dir: str = None):
        """
        初始化执行器
        
        Args:
            registry: ToolRegistry 实例
            router: ToolRouter 实例
            log_dir: 日志目录
        """
        self.registry = registry or tool_registry
        self.router = router or tool_router
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".vectorbrain" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _is_retryable_error(self, error: Any, retryable_errors: Optional[List[str]] = None) -> bool:
        if not error:
            return False
        msg = str(error)
        patterns = retryable_errors or []
        if not patterns:
            return False
        msg_lower = msg.lower()
        return any(p.lower() in msg_lower for p in patterns)

    def _normalize_local_tool_input(self, tool: Tool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Best-effort path normalization for local executors.

        Some callers pass '~/.vectorbrain/...' literally. Expand it before the
        tool handler runs so subprocess cwd/script/args never receive a raw '~'.
        """
        normalized = dict(input_data or {})
        if tool.name != "local_python":
            return normalized

        def _expand(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, str):
                text = value.strip()
                if text.startswith("~") or text.startswith("/"):
                    return str(Path(os.path.expanduser(text)).resolve())
                return value
            if isinstance(value, list):
                return [_expand(v) for v in value]
            return value

        for key in ("script", "cwd", "args"):
            if key in normalized:
                normalized[key] = _expand(normalized.get(key))
        return normalized

    async def execute_tool(
        self,
        tool: Tool,
        input_data: Dict[str, Any],
        timeout: int = None,
        *,
        max_retries: int = 0,
        retry_backoff: float = 0.5,
        retryable_errors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute a single tool with validation, timeout and (optional) retry."""
        input_data = self._normalize_local_tool_input(tool, input_data)

        # 验证输入
        try:
            validate_input(tool.input_schema, input_data)
        except ValueError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Input validation failed: {str(e)}",
            }

        attempts = 0
        last_result: Optional[Dict[str, Any]] = None

        while True:
            attempts += 1
            try:
                result = await asyncio.wait_for(
                    tool.handler(input_data),
                    timeout=timeout or tool.timeout,
                )
            except asyncio.TimeoutError:
                result = {
                    "success": False,
                    "data": None,
                    "error": f"Tool {tool.name} timed out after {timeout or tool.timeout} seconds",
                }
            except Exception as e:
                result = {
                    "success": False,
                    "data": None,
                    "error": f"Tool execution failed: {str(e)}",
                }

            # annotate attempts for observability
            if isinstance(result, dict):
                result.setdefault("meta", {})
                if isinstance(result.get("meta"), dict):
                    result["meta"]["attempt"] = attempts
                    result["meta"]["max_retries"] = max_retries

            last_result = result
            if result.get("success"):
                return result

            # decide retry
            if attempts > max_retries:
                return result

            err = result.get("error")
            if retryable_errors and (not self._is_retryable_error(err, retryable_errors=retryable_errors)):
                return result

            # exponential backoff
            delay = float(retry_backoff or 0.0) * (2 ** (attempts - 1))
            await asyncio.sleep(delay)
    
    async def execute_plan(self, plan: Plan, dry_run: bool = False) -> ExecutionResult:
        # DAG mode auto-switch: if any step has depends_on, run DAG executor
        if any(getattr(s, "depends_on", None) for s in plan.steps):
            from runtime.tools.dag_executor import execute_plan_dag
            return await execute_plan_dag(self, plan, dry_run=dry_run)

        """
        执行计划（多个步骤）

        - 支持 capability-only step（由 Router 解析具体工具）
        - 支持 ExecutionContext：步骤结果写入 context，后续步骤可引用模板变量

        Args:
            plan: 执行计划
            dry_run: 是否干跑（不实际执行）

        Returns:
            ExecutionResult
        """
        result = ExecutionResult(success=True)

        # 初始化执行上下文
        ctx = ExecutionContext(task={
            "task_id": plan.task_id,
            "created_at": plan.created_at,
            "title": getattr(plan, "title", ""),
            "input": getattr(plan, "title", ""),
        })

        # 初始化 Trace
        trace = ExecutionTrace(task_id=plan.task_id)
        trace.workflow = getattr(plan, "workflow", None) or None
        plan_start = time.time()

        print(f"\n{'='*60}")
        print(f"Executing Plan: {plan.task_id}")
        print(f"Steps: {len(plan.steps)}")
        print(f"Dry Run: {dry_run}")
        print(f"{'='*60}\n")

        # 发布任务开始事件
        await emit_task_started(plan.task_id)

        for i, step in enumerate(plan.steps):
            # 显示步骤信息（支持 capability-only）
            step_display = step.tool or f"[{step.capability}]"
            print(f"[Step {i+1}/{len(plan.steps)}] {step_display}")
            
            # 发布步骤开始事件
            await event_bus.emit("step.started", {
                "task_id": plan.task_id,
                "step_index": i,
                "tool": step_display,
                "capability": step.capability
            })
            
            # 干跑模式
            if dry_run or step.dry_run:
                print(f"  [DRY RUN] Would execute {step_display}")
                step_result = {
                    "success": True,
                    "data": {"dry_run": True},
                    "error": None
                }
                result.add_result(i, step_display, step_result)
                await event_bus.emit("step.completed", {
                    "task_id": plan.task_id,
                    "step_index": i,
                    "tool": step_display,
                    "dry_run": True
                })
                continue
            
            # 先解析输入（用于 Router Scoring）
            # step_id：优先用 step.id（workflow 中的稳定 id），否则退化为 capability/tool
            step_id = step.id or f"{step.capability or step.tool or 'step'}"
            if step_id in ctx.steps:
                step_id = f"{step_id}_{i}"

            try:
                resolved_input = resolve_templates(step.input, ctx)
            except Exception as e:
                # Context safe resolver should prevent most crashes, but keep a guard rail
                resolved_input = step.input
                await event_bus.emit("step.template_error", {
                    "task_id": plan.task_id,
                    "step_index": i,
                    "step_id": step_id,
                    "error": str(e),
                })

            # 获取工具：优先使用 step.tool，否则通过 capability 评分路由
            tool = None

            step_start = time.time()
            step_start_ts = datetime.now().isoformat()

            if step.tool:
                # 直接指定工具
                tool = self.registry.get(step.tool)
            elif step.capability:
                # 通过 capability 评分路由选择最佳工具
                tool = self.router.route_best(step.capability, resolved_input)
                if tool:
                    print(f"  [Router] Resolved [{step.capability}] → {tool.name}")
                    # 打印评分信息（仅调试）
                    try:
                        s = tool.score(resolved_input)
                        print(f"  [Router] Score: {s:.3f}")
                    except Exception:
                        pass

            if not tool:
                error_msg = f"Tool not found: {step.tool or step.capability}"
                print(f"  ❌ {error_msg}")
                step_result = {
                    "success": False,
                    "data": None,
                    "error": error_msg
                }
                result.add_result(i, step_display, step_result)
                result.success = False

                await event_bus.emit("step.failed", {
                    "task_id": plan.task_id,
                    "step_index": i,
                    "tool": step_display,
                    "capability": step.capability,
                    "error": error_msg
                })
                continue

            # 执行工具
            exec_result = await self.execute_tool(
                tool=tool,
                input_data=resolved_input,
                timeout=step.timeout,
                max_retries=getattr(step, "max_retries", 0) or 0,
                retry_backoff=getattr(step, "retry_backoff", 0.5) or 0.5,
                retryable_errors=getattr(step, "retryable_errors", None) or None,
            )

            # Failure strategy (sequential mode): decide whether to mark plan failed
            on_error = (getattr(step, "on_error", None) or "fail").lower().strip()
            stop_after_step = False
            if not exec_result.get("success"):
                if on_error in ("ignore", "continue"):
                    # non-fatal: keep result.success as-is
                    pass
                else:
                    result.success = False
                if on_error == "fail_fast":
                    stop_after_step = True

            step_end_ts = datetime.now().isoformat()
            step_duration = time.time() - step_start
            step_duration_ms = int(step_duration * 1000)

            # 写入 context
            ctx.set_step_result(step_id, exec_result)
            ctx.vars["last_step_id"] = step_id
            ctx.vars["last_result"] = exec_result

            # 也将 resolved_input 记录进去，方便后续引用
            ctx.steps.setdefault("_inputs", {})
            ctx.steps["_inputs"][step_id] = resolved_input

            # 写入 trace
            trace.add_step({
                "step_index": i,
                "step_id": step_id,
                "capability": step.capability,
                "tool": tool.name,
                "input": resolved_input,
                "start_ts": step_start_ts,
                "end_ts": step_end_ts,
                "duration_ms": step_duration_ms,
                "duration_seconds": step_duration,
                "output_summary": summarize_exec_result(exec_result),
            })
            
            # 记录结果（用 step_display / tool.name 代替 None）
            result.add_result(i, tool.name, exec_result)
            
            # 记录日志（用 resolved_input）
            log_tool_execution(
                task_id=plan.task_id,
                tool_name=tool.name,
                input_data=resolved_input,
                result=exec_result,
                log_dir=str(self.log_dir)
            )

            # fail_fast: stop after we have recorded trace/log/events for this step
            if 'stop_after_step' in locals() and stop_after_step:
                break
            
            # 打印结果并发布事件
            if exec_result.get("success"):
                print(f"  ✅ Success")
                await event_bus.emit("step.completed", {
                    "task_id": plan.task_id,
                    "step_index": i,
                    "tool": tool.name,
                    "capability": step.capability,
                    "result": exec_result
                })
            else:
                print(f"  ❌ Failed: {exec_result.get('error')}")
                await event_bus.emit("step.failed", {
                    "task_id": plan.task_id,
                    "step_index": i,
                    "tool": tool.name,
                    "capability": step.capability,
                    "error": exec_result.get('error'),
                    "on_error": getattr(step, "on_error", "fail"),
                    "attempt": (exec_result.get("meta") or {}).get("attempt"),
                    "duration_ms": step_duration_ms,
                    "end_ts": step_end_ts,
                })
        
        # 发布任务完成事件
        await emit_task_completed(plan.task_id, result.success)

        # 完成并保存 trace
        total = time.time() - plan_start
        trace.finish(success=result.success, total_seconds=total)
        trace_path = trace.save()
        print(f"[Trace] Saved: {trace_path}")
        
        print(f"\n{'='*60}")
        print(f"Plan Execution {'Completed' if result.success else 'Failed'}")
        print(f"Total time: {total:.2f}s")
        print(f"{'='*60}\n")
        
        return result


# ============================================================================
# 全局执行器实例
# ============================================================================

tool_executor = ToolExecutor()


# ============================================================================
# 辅助函数
# ============================================================================

def create_plan(task_id: str, steps: List[Dict]) -> Plan:
    """
    创建执行计划（辅助函数）
    
    Args:
        task_id: 任务 ID
        steps: 步骤列表 [{"tool": "...", "input": {...}}, ...]
        
    Returns:
        Plan 实例
    """
    plan = Plan(task_id=task_id)
    
    for step_data in steps:
        plan.add_step(**step_data)
    
    return plan


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    # 加载工具
    tool_registry.load_builtin_tools()
    
    async def test():
        print("=== 测试 1: 执行单个工具 ===")
        tool = tool_registry.get("web_search")
        result = await tool_executor.execute_tool(
            tool=tool,
            input_data={"query": "test query"}
        )
        print(f"Result: {result}\n")
        
        print("=== 测试 2: 执行计划 ===")
        plan = create_plan("test_plan_001", [
            {"tool": "web_search", "input": {"query": "shadcn ui"}},
            {"tool": "web_fetch", "input": {"url": "https://example.com"}},
            {"tool": "write_file", "input": {"path": "~/test_output.txt", "content": "Test content"}}
        ])
        
        result = await tool_executor.execute_plan(plan)
        print(f"Plan Success: {result.success}")
        print(f"Steps Executed: {len(result.step_results)}\n")
        
        print("=== 测试 3: 干跑模式 ===")
        plan = create_plan("test_plan_002", [
            {"tool": "exec_shell", "input": {"cmd": "rm -rf /"}}  # 危险命令，干跑不实际执行
        ])
        
        result = await tool_executor.execute_plan(plan, dry_run=True)
        print(f"Dry Run Success: {result.success}\n")
    
    asyncio.run(test())
