#!/usr/bin/env python3
"""VectorBrain Skill Tools - OpenClaw skill runtime / delegation bridge."""

from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path

from runtime.tools.registry import tool_registry, Tool
from runtime.skills.registry import skill_registry
from runtime.adapters.openclaw_cli import run_local_agent


async def openclaw_skill_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        skill_name = input.get("skill") or input.get("name")
        task = input.get("task") or input.get("prompt") or ""
        mode = (input.get("mode") or "inspect").strip().lower()
        delegate = bool(input.get("delegate", False) or mode == "delegate")
        channel = input.get("channel")
        session_id = input.get("session_id")
        deliver = bool(input.get("deliver", False))

        if not skill_name:
            return {"success": False, "data": None, "error": "Missing required field: skill"}

        skill = skill_registry.get(skill_name)
        if not skill:
            return {"success": False, "data": None, "error": f"Skill not found: {skill_name}"}

        skill_excerpt = None
        resolved_path = skill.path
        if resolved_path and Path(resolved_path).exists():
            text = Path(resolved_path).read_text(encoding="utf-8", errors="ignore")
            skill_excerpt = text[:8000]

        data: Dict[str, Any] = {
            "skill": skill.to_dict(),
            "task": task,
            "mode": "inspect",
            "skill_excerpt": skill_excerpt,
            "runtime": {
                "delegate_supported": True,
                "transport": "openclaw agent --local",
            },
        }

        if delegate:
            prompt = (
                f"You must apply the OpenClaw skill '{skill.name}'.\n"
                f"Skill path: {skill.path or '(path unavailable)'}\n"
                f"Skill description: {skill.description}\n\n"
                f"User task:\n{task}\n\n"
                f"Required behavior:\n"
                f"1) Load and follow that SKILL.md if the path exists.\n"
                f"2) Complete the task using the skill instructions.\n"
                f"3) Return a concise result with what was done and any limits."
            )
            agent_res = run_local_agent(
                message=prompt,
                timeout=int(input.get("timeout", 300) or 300),
                channel=channel,
                session_id=session_id,
                deliver=deliver,
            )
            data["mode"] = "delegate"
            data["delegate_invocation"] = {
                "channel": channel,
                "session_id": session_id,
                "deliver": deliver,
                "command": agent_res.get("command"),
            }
            data["delegate_response"] = agent_res.get("json") if agent_res.get("json") is not None else agent_res.get("combined")
            if not agent_res.get("ok"):
                return {
                    "success": False,
                    "data": data,
                    "error": agent_res.get("stderr") or f"openclaw agent failed with code {agent_res.get('returncode')}",
                }

        return {"success": True, "data": data, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


async def openclaw_skill_runtime_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(input or {})
    payload["mode"] = payload.get("mode") or "delegate"
    payload["delegate"] = True
    return await openclaw_skill_handler(payload)


def openclaw_skill_score(input: Dict[str, Any]) -> float:
    skill = (input or {}).get("skill")
    task = str((input or {}).get("task") or "").lower()
    score = 0.4
    if skill:
        score += 0.7
    if any(k in task for k in ["skill", "delegate", "workflow", "agent", "按技能"]):
        score += 0.5
    return score


openclaw_skill_tool = Tool(
    name="openclaw_skill",
    display_name="OpenClaw Skill",
    description="Inspect or delegate a task to an OpenClaw skill via the local skill registry",
    capabilities=["skill", "workflow", "instruction"],
    input_schema={
        "type": "object",
        "required": ["skill"],
        "properties": {
            "skill": {"type": "string", "description": "Skill name"},
            "task": {"type": "string", "description": "Task for the skill"},
            "mode": {"type": "string", "description": "inspect or delegate", "default": "inspect"},
            "delegate": {"type": "boolean", "description": "Whether to execute via openclaw agent --local", "default": False},
            "timeout": {"type": "integer", "description": "Delegate timeout seconds", "default": 300},
            "channel": {"type": "string", "description": "Optional OpenClaw channel"},
            "session_id": {"type": "string", "description": "Optional OpenClaw session id"},
            "deliver": {"type": "boolean", "description": "Deliver reply back through OpenClaw channel", "default": False},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "skill": {"type": "object"},
            "task": {"type": "string"},
            "mode": {"type": "string"},
            "skill_excerpt": {"type": ["string", "null"]},
            "delegate_invocation": {},
            "delegate_response": {},
        },
    },
    handler=openclaw_skill_handler,
    score_fn=openclaw_skill_score,
    timeout=360,
    version="2.0",
    allow_dry_run=True,
)

tool_registry.register(openclaw_skill_tool)


openclaw_skill_runtime_tool = Tool(
    name="openclaw_skill_runtime",
    display_name="OpenClaw Skill Runtime",
    description="Delegate a task to a real OpenClaw skill runtime via openclaw agent --local",
    capabilities=["skill_runtime", "delegate", "skill"],
    input_schema=openclaw_skill_tool.input_schema,
    output_schema=openclaw_skill_tool.output_schema,
    handler=openclaw_skill_runtime_handler,
    score_fn=lambda data: openclaw_skill_score(data) + 0.3,
    timeout=420,
    version="2.0",
    allow_dry_run=True,
)

tool_registry.register(openclaw_skill_runtime_tool)
