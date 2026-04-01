#!/usr/bin/env python3
"""
Layer: runtime
Status: primary
Boundary: runtime core orchestrator; may call intelligence/tool/workflow components, but remains runtime-owned.
Architecture refs:
- architecture/layer-manifest.md
- architecture/runtime-boundary-rules.md

VectorBrain MCP Orchestrator v3 - routed, scored, and skill-runtime aware.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable

sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from runtime.model_router import model_router
from runtime.tools.executor import tool_executor, ExecutionResult, Plan, PlanStep
from runtime.tools.planner import task_planner, detect_intent
from runtime.tools.registry import tool_registry
from runtime.tools.router import tool_router
from runtime.workflows.loader import load_workflow, WorkflowNotFound, WorkflowValidationError
from runtime.skills.registry import skill_registry
from common.notify_helper import notify_feishu_and_queue, DEFAULT_FEISHU_TARGET


@dataclass
class OrchestratorTask:
    title: str
    description: str = ""
    task_id: Optional[str] = None
    skill: Optional[str] = None
    workflow: Optional[str] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def ensure_id(self) -> str:
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:12]}"
        return self.task_id


class MCPOrchestrator:
    SILENCE_PATTERNS = [
        "不用通知我",
        "不要通知我",
        "静默执行",
        "只执行不要发消息",
        "不要提醒我",
    ]

    def __init__(self):
        tool_registry.load_builtin_tools()
        skill_registry.load()
        self.preprocessors: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.register_preprocessor("heart", self._heart_preprocess)

    def register_preprocessor(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self.preprocessors[name] = fn

    def _heart_preprocess(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        from runtime.heart_bridge import runtime_heart

        return runtime_heart.preprocess_task_payload(payload)

    def _has_silence_intent(self, payload: Dict[str, Any]) -> bool:
        texts = [
            str(payload.get("title") or ""),
            str(payload.get("task") or ""),
            str(payload.get("description") or ""),
        ]
        metadata = payload.get("metadata") or {}
        for key in ("raw_text", "user_text", "text", "prompt"):
            if metadata.get(key):
                texts.append(str(metadata.get(key)))
        haystack = "\n".join(t for t in texts if t).lower()
        return any(pattern.lower() in haystack for pattern in self.SILENCE_PATTERNS)

    def _resolve_notify_defaults(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        updated = dict(payload)
        metadata = dict(updated.get("metadata") or {})
        notify = metadata.get("notify")

        explicit_notify = isinstance(notify, dict) and any(
            key in notify for key in ("enabled", "channel", "target", "message", "timeout")
        )
        silence = self._has_silence_intent(updated)

        if explicit_notify:
            resolved_notify = dict(notify or {})
        else:
            resolved_notify = {
                "enabled": True,
                "channel": "feishu",
                "target": DEFAULT_FEISHU_TARGET,
            }

        resolved_notify.setdefault("channel", "feishu")
        resolved_notify.setdefault("target", DEFAULT_FEISHU_TARGET)
        resolved_notify["enabled"] = False if silence else bool(resolved_notify.get("enabled", True))
        resolved_notify["silence_detected"] = silence
        resolved_notify["default_applied"] = not explicit_notify

        metadata["notify"] = resolved_notify
        updated["metadata"] = metadata
        return updated

    def apply_preprocessors(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        metadata = dict(payload.get("metadata") or {})
        hooks = metadata.get("preprocess_hooks") or []
        use_heart = bool(metadata.get("heart_preprocess")) or ("heart" in hooks)
        updated = dict(payload)
        if use_heart and "heart" in self.preprocessors:
            updated = self.preprocessors["heart"](updated)
        updated = self._resolve_notify_defaults(updated)
        return updated

    def _workflow_status(self, requested_workflow: str) -> Dict[str, Any]:
        workflow_source = "builtin"
        workflow_exists = False
        workflow_error = None
        try:
            load_workflow(requested_workflow)
            workflow_exists = True
            workflow_source = "file"
        except WorkflowNotFound:
            workflow_exists = requested_workflow in {"search_and_save", "search_only", "fetch_only", "read_file", "write_file", "exec_command", "send_message", "default", "dag_parallel_fetch", "local_conversation_query", "local_dashboard_query", "local_db_query", "local_python_exec"}
            workflow_source = "builtin" if workflow_exists else "missing"
        except WorkflowValidationError as e:
            workflow_exists = False
            workflow_error = str(e)
            workflow_source = "invalid"
        return {
            "workflow": requested_workflow,
            "workflow_exists": workflow_exists,
            "workflow_source": workflow_source,
            "workflow_error": workflow_error,
        }

    def _tool_candidates(self, task: OrchestratorTask, requested_workflow: str) -> List[Dict[str, Any]]:
        candidate_caps: List[str] = []
        if task.skill:
            candidate_caps.append("skill")
        workflow_to_cap = {
            "search_only": "search",
            "search_and_save": "search",
            "fetch_only": "fetch",
            "read_file": "read",
            "write_file": "write",
            "exec_command": "shell",
            "send_message": "message",
            "local_conversation_query": "local_query",
            "local_dashboard_query": "local_query",
            "local_db_query": "local_query",
            "local_python_exec": "local_execute",
        }
        if requested_workflow in workflow_to_cap:
            candidate_caps.append(workflow_to_cap[requested_workflow])

        is_local_first_workflow = requested_workflow in {"local_conversation_query", "local_dashboard_query", "local_db_query", "local_python_exec"}
        title_desc = f"{task.title} {task.description}".lower()
        if any(k in title_desc for k in ["skill", "delegate", "代理", "技能"]):
            candidate_caps.append("skill")
        if any(k in title_desc for k in ["feishu", "lark", "conversation", "conversations", "dashboard", "sqlite", "database", "db", "本地", "群聊", "消息", "数据库", "任务状态", "最近任务", "任务详情", "今天消息", "24小时消息", "会话数据", "飞书抓取"]):
            candidate_caps.append("local_query")
        if any(k in title_desc for k in ["python script", ".py", "执行本地", "local execute", "运行 python", "执行 python"]):
            candidate_caps.append("local_execute")
        if not is_local_first_workflow and any(k in title_desc for k in ["search", "find", "lookup", "搜索"]):
            candidate_caps.append("search")
        if not is_local_first_workflow and any(k in title_desc for k in ["fetch", "url", "http", "website", "抓取", "网页"]):
            candidate_caps.append("fetch")
        if any(k in title_desc for k in ["read", "file", "path", "读取"]):
            candidate_caps.append("read")
        if any(k in title_desc for k in ["write", "save", "create", "写入"]):
            candidate_caps.append("write")
        if not is_local_first_workflow and any(k in title_desc for k in ["shell", "command", "bash", "终端", "命令"]):
            candidate_caps.append("shell")
        if not is_local_first_workflow and any(k in title_desc for k in ["send", "message", "notify", "发送", "消息", "通知"]):
            candidate_caps.append("message")

        seen = set()
        candidates: List[Dict[str, Any]] = []
        signal_input = {
            "task": task.title if not task.description else f"{task.title}\n\n{task.description}",
            "query": task.title,
        }
        if task.skill:
            signal_input["skill"] = task.skill
        for cap in candidate_caps:
            if cap in seen:
                continue
            seen.add(cap)
            ranked = tool_router.rank(cap, signal_input)
            if ranked:
                candidates.append({
                    "capability": cap,
                    "ranked_tools": [
                        {k: v for k, v in item.items() if k != "tool"}
                        for item in ranked[:5]
                    ],
                })
        return candidates

    def route_task(self, task: OrchestratorTask) -> Dict[str, Any]:
        requested_workflow = task.workflow or detect_intent(task.title, task.description)
        workflow_state = self._workflow_status(requested_workflow)
        ranked_skills = skill_registry.rank_task(task.title, task.description, limit=5)
        matched_skill = skill_registry.get(task.skill) if task.skill else (ranked_skills[0]["skill"] if ranked_skills and ranked_skills[0]["score"] >= 2.5 else None)
        if isinstance(matched_skill, dict):
            matched_skill_name = matched_skill.get("name")
            matched_skill = skill_registry.get(matched_skill_name) if matched_skill_name else None

        title_desc = f"{task.title} {task.description}".lower()
        explicit_skill_signal = bool(task.skill)
        semantic_skill_signal = any(k in title_desc for k in ["skill", "delegate", "use ", "按技能", "调用技能"])

        if (explicit_skill_signal or semantic_skill_signal) and matched_skill:
            route_kind = "skill"
        elif workflow_state["workflow_exists"]:
            route_kind = "workflow"
        elif matched_skill:
            route_kind = "skill"
        else:
            route_kind = "tool"

        skill_route = {
            "kind": route_kind,
            "skill": matched_skill.to_dict() if matched_skill else None,
            "intent": requested_workflow,
            **workflow_state,
            "ranked_skills": ranked_skills,
            "tool_candidates": self._tool_candidates(task, requested_workflow),
        }

        model_route = model_router.route_task(
            task.title,
            task.description,
            workflow=requested_workflow,
            explicit_model=task.model,
            route_kind=route_kind,
        )

        return {"skill_route": skill_route, "model_route": model_route}

    def plan_task(self, task: OrchestratorTask, routing: Optional[Dict[str, Any]] = None):
        routing = routing or self.route_task(task)
        route_kind = routing.get("skill_route", {}).get("kind")
        matched_skill = routing.get("skill_route", {}).get("skill")

        if route_kind == "skill" and matched_skill:
            plan = Plan(
                task_id=task.ensure_id(),
                steps=[
                    PlanStep(
                        id="skill_runtime",
                        tool="openclaw_skill_runtime",
                        capability="skill",
                        input={
                            "skill": matched_skill["name"],
                            "task": task.title if not task.description else f"{task.title}\n\n{task.description}",
                            "mode": "delegate",
                        },
                    )
                ],
            )
            plan.title = task.title
            plan.intent = "skill"
            plan.workflow = matched_skill["name"]
            return plan

        return task_planner.create_plan(
            task_id=task.ensure_id(),
            task_title=task.title,
            task_description=task.description,
        )

    async def execute_task(self, task: OrchestratorTask, *, dry_run: bool = False) -> Dict[str, Any]:
        task.ensure_id()
        routing = self.route_task(task)
        plan = self.plan_task(task, routing=routing)
        exec_result: ExecutionResult = await tool_executor.execute_plan(plan, dry_run=dry_run)

        result = {
            "task": {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "created_at": datetime.now().isoformat(),
                "metadata": task.metadata or {},
                "response_guidance": ((task.metadata or {}).get("response_guidance") or {}),
            },
            "routing": routing,
            "plan": {
                "task_id": plan.task_id,
                "intent": getattr(plan, "intent", None),
                "workflow": getattr(plan, "workflow", None),
                "steps": [
                    {
                        "id": s.id,
                        "tool": s.tool,
                        "capability": s.capability,
                        "depends_on": s.depends_on,
                        "input": s.input,
                    }
                    for s in plan.steps
                ],
            },
            "execution": {
                "success": exec_result.success,
                "error": exec_result.error,
                "step_results": exec_result.step_results,
            },
        }

        notify_meta = (task.metadata or {}).get("notify") or {}
        should_notify = bool(notify_meta.get("enabled"))
        if should_notify and not dry_run:
            target = notify_meta.get("target")
            channel = str(notify_meta.get("channel") or "feishu")
            if exec_result.success:
                summary = notify_meta.get("message") or f"任务《{task.title}》完成"
            else:
                failure_reason = exec_result.error or "未知原因"
                summary = notify_meta.get("message") or f"任务《{task.title}》失败：{failure_reason}"
            if channel != "feishu":
                result["notification"] = {
                    "sent": False,
                    "error": f"unsupported notify channel: {channel}",
                    "target": target,
                    "summary": summary,
                }
            else:
                notif = notify_feishu_and_queue(
                    summary,
                    {
                        "type": "task_result",
                        "task_id": task.task_id,
                        "title": task.title,
                        "success": exec_result.success,
                        "reason": None if exec_result.success else (exec_result.error or "未知原因"),
                    },
                    target=target,
                    timeout=int(notify_meta.get("timeout", 60) or 60),
                    script="runtime.orchestrator",
                )
                notif["summary"] = summary
                result["notification"] = notif
                if not notif.get("sent"):
                    result["execution"].setdefault("warnings", []).append(
                        f"notification_failed: {notif.get('send_detail') or notif.get('queue_detail') or 'unknown'}"
                    )
        else:
            result["notification"] = {
                "sent": False,
                "skipped": True,
                "reason": "notify_disabled" if not should_notify else "dry_run",
                "notify": notify_meta,
            }

        return result

    async def orchestrate(self, payload: Dict[str, Any], *, dry_run: bool = False) -> Dict[str, Any]:
        payload = self.apply_preprocessors(payload)
        task = OrchestratorTask(
            title=payload.get("title") or payload.get("task") or "",
            description=payload.get("description") or "",
            task_id=payload.get("task_id"),
            skill=payload.get("skill"),
            workflow=payload.get("workflow"),
            model=payload.get("model"),
            metadata=payload.get("metadata") or {},
        )
        if not task.title:
            raise ValueError("payload.title or payload.task is required")
        return await self.execute_task(task, dry_run=dry_run)


mcp_orchestrator = MCPOrchestrator()


async def orchestrate(payload: Dict[str, Any], *, dry_run: bool = False) -> Dict[str, Any]:
    return await mcp_orchestrator.orchestrate(payload, dry_run=dry_run)


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py '<task title>'")
        raise SystemExit(1)
    payload = {"title": sys.argv[1], "description": " ".join(sys.argv[2:])}
    print(json.dumps(asyncio.run(orchestrate(payload, dry_run=False)), ensure_ascii=False, indent=2))
