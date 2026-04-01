#!/usr/bin/env python3
"""DAG Executor (v0.2)

Runs a workflow plan as a DAG with parallel execution.

Design:
- Uses WorkflowGraph (nodes/deps/reverse) built from Plan.steps (PlanStep dataclasses)
- Maintains ready / running / started / completed sets
- Uses existing ToolExecutor.execute_tool + Router + Context + Trace

This module is intentionally self-contained so ToolExecutor can delegate to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Set, Tuple
import asyncio
import time

from runtime.workflows.graph import WorkflowGraph
from runtime.tools.context import ExecutionContext, resolve_templates
from runtime.tools.trace import ExecutionTrace, summarize_exec_result
from runtime.tools.registry import log_tool_execution
from runtime.tools.event_bus import event_bus, emit_task_started, emit_task_completed


@dataclass
class DAGRunOptions:
    fail_fast: bool = False          # if True, cancel running tasks on first failure
    max_concurrency: Optional[int] = None  # None = unlimited


class DAGExecutor:
    def __init__(self, tool_executor: Any):
        # tool_executor is runtime.tools.executor.ToolExecutor
        self.tool_executor = tool_executor
        self.registry = tool_executor.registry
        self.router = tool_executor.router
        self.log_dir = tool_executor.log_dir

    async def run(self, plan: Any, dry_run: bool = False, options: Optional[DAGRunOptions] = None):
        """Execute a Plan as DAG if it has dependencies."""
        options = options or DAGRunOptions()

        result = self.tool_executor._new_execution_result() if hasattr(self.tool_executor, "_new_execution_result") else None
        # Fallback to importing ExecutionResult type from executor if helper not provided
        if result is None:
            from runtime.tools.executor import ExecutionResult  # local import to avoid circular
            result = ExecutionResult(success=True)

        # Context + Trace
        ctx = ExecutionContext(task={
            "task_id": plan.task_id,
            "created_at": plan.created_at,
            "title": getattr(plan, "title", ""),
            "input": getattr(plan, "title", ""),
        })

        trace = ExecutionTrace(task_id=plan.task_id)
        trace.workflow = getattr(plan, "workflow", None) or getattr(plan, "intent", None) or None
        plan_start = time.time()

        # Build graph + validate DAG ordering
        graph = WorkflowGraph.from_steps(plan.steps)
        graph.topological_sort()  # raises if cycle

        # Map step_id -> original index for stable output ordering
        id_to_index: Dict[str, int] = {}
        for idx, s in enumerate(plan.steps):
            sid = getattr(s, "id", None)
            if sid:
                id_to_index[sid] = idx

        completed: Set[str] = set()
        started: Set[str] = set()
        failed_fatal: Set[str] = set()      # failures that should block downstream
        failed_ignored: Set[str] = set()    # failures with on_error=ignore/continue
        skipped: Set[str] = set()

        # Failure strategy
        fail_fast_triggered: bool = False

        running: Dict[asyncio.Task, str] = {}
        ready: Set[str] = set(graph.roots())

        await emit_task_started(plan.task_id)

        async def run_step(sid: str):
            step = graph.nodes[sid]

            # Resolve input templates
            try:
                resolved_input = resolve_templates(getattr(step, "input", {}), ctx)
            except Exception as e:
                resolved_input = getattr(step, "input", {})
                await event_bus.emit("step.template_error", {
                    "task_id": plan.task_id,
                    "step_id": sid,
                    "error": str(e),
                })

            # Choose tool (scoring router)
            tool = None
            if getattr(step, "tool", None):
                tool = self.registry.get(step.tool)
            else:
                tool = self.router.route_best(step.capability, resolved_input)

            if tool is None:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Tool not found for step {sid} ({getattr(step,'tool',None) or getattr(step,'capability',None)})",
                }, resolved_input, None, 0.0

            # Emit step.started with resolved tool
            step_start_ts = time.time()
            step_start_iso = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(step_start_ts))
            await event_bus.emit("step.started", {
                "task_id": plan.task_id,
                "step_id": sid,
                "tool": tool.name,
                "capability": step.capability,
                "start_ts": step_start_iso,
            })

            t0 = time.time()
            exec_result = await self.tool_executor.execute_tool(
                tool=tool,
                input_data=resolved_input,
                timeout=getattr(step, "timeout", None),
                max_retries=getattr(step, "max_retries", 0) or 0,
                retry_backoff=getattr(step, "retry_backoff", 0.5) or 0.5,
                retryable_errors=getattr(step, "retryable_errors", None) or None,
            )
            step_end_ts = time.time()
            duration = step_end_ts - t0
            duration_ms = int(duration * 1000)
            step_end_iso = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(step_end_ts))

            # Save to context
            ctx.set_step_result(sid, exec_result)
            ctx.vars["last_step_id"] = sid
            ctx.vars["last_result"] = exec_result
            ctx.steps.setdefault("_inputs", {})
            ctx.steps["_inputs"][sid] = resolved_input

            # Log
            log_tool_execution(
                task_id=plan.task_id,
                tool_name=tool.name,
                input_data=resolved_input,
                result=exec_result,
                log_dir=str(self.log_dir),
            )

            # Trace
            trace.add_step({
                "step_index": id_to_index.get(sid, -1),
                "step_id": sid,
                "capability": step.capability,
                "tool": tool.name,
                "input": resolved_input,
                "start_ts": step_start_iso,
                "end_ts": step_end_iso,
                "duration_ms": duration_ms,
                "duration_seconds": duration,
                "output_summary": summarize_exec_result(exec_result),
            })

            # Result aggregation (tool name, not None)
            result.add_result(id_to_index.get(sid, -1), tool.name, exec_result)

            # Emit step.completed/failed
            if exec_result.get("success"):
                await event_bus.emit("step.completed", {
                    "task_id": plan.task_id,
                    "step_id": sid,
                    "tool": tool.name,
                    "capability": step.capability,
                    "end_ts": step_end_iso,
                    "duration_ms": duration_ms,
                })
            else:
                await event_bus.emit("step.failed", {
                    "task_id": plan.task_id,
                    "step_id": sid,
                    "tool": tool.name,
                    "capability": step.capability,
                    "error": exec_result.get("error"),
                    "end_ts": step_end_iso,
                    "duration_ms": duration_ms,
                })

            return exec_result, resolved_input, tool.name, duration

        def deps_satisfied(sid: str) -> bool:
            dset = graph.deps.get(sid, set())
            return dset.issubset(completed)

        def blocked_by_failure(sid: str) -> bool:
            dset = graph.deps.get(sid, set())
            return len(dset.intersection(failed_fatal)) > 0

        async def start_ready():
            nonlocal ready
            while ready:
                # optional concurrency gate
                if options.max_concurrency is not None and len(running) >= options.max_concurrency:
                    return

                sid = ready.pop()
                if sid in started or sid in completed or sid in skipped:
                    continue
                if blocked_by_failure(sid):
                    skipped.add(sid)
                    continue
                if not deps_satisfied(sid):
                    # should not happen if ready computed correctly
                    continue

                started.add(sid)
                task = asyncio.create_task(run_step(sid))
                running[task] = sid

        def recompute_ready():
            for sid in graph.get_ready(completed):
                if sid in started or sid in completed or sid in skipped:
                    continue
                if blocked_by_failure(sid):
                    skipped.add(sid)
                    continue
                ready.add(sid)

        # main loop
        recompute_ready()
        while ready or running:
            await start_ready()

            if not running:
                # nothing can run (likely blocked)
                break

            done, _pending = await asyncio.wait(set(running.keys()), return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                sid = running.pop(t)
                try:
                    exec_result, *_ = await t
                except Exception as e:
                    exec_result = {"success": False, "data": None, "error": str(e)}

                if exec_result.get("success"):
                    completed.add(sid)
                else:
                    completed.add(sid)

                    # step-level failure strategy
                    step_obj = graph.nodes.get(sid)
                    on_error = getattr(step_obj, "on_error", None) or (step_obj.get("on_error") if isinstance(step_obj, dict) else None) or "fail"
                    on_error = str(on_error).lower().strip()

                    if on_error in ("ignore", "continue"):
                        failed_ignored.add(sid)
                        # do not block downstream
                    else:
                        failed_fatal.add(sid)
                        result.success = False

                    if on_error == "fail_fast" or options.fail_fast:
                        fail_fast_triggered = True
                        # cancel remaining
                        for rt in list(running.keys()):
                            rt.cancel()
                        running.clear()
                        ready.clear()
                        break

                recompute_ready()

        # If some steps never ran due to fatal failure blocks, mark overall as failed
        if skipped:
            result.success = False

        total = time.time() - plan_start
        trace.finish(success=result.success, total_seconds=total)
        trace_path = trace.save()

        await emit_task_completed(plan.task_id, result.success)
        await event_bus.emit("trace.saved", {"task_id": plan.task_id, "path": str(trace_path)})

        return result


async def execute_plan_dag(tool_executor: Any, plan: Any, dry_run: bool = False) -> Any:
    """Convenience wrapper used by ToolExecutor."""
    return await DAGExecutor(tool_executor).run(plan, dry_run=dry_run)
