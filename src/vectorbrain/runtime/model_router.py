#!/usr/bin/env python3
"""VectorBrain Model Router - v3 scored routing"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ModelProfile:
    name: str
    provider: str
    strengths: List[str]
    max_context: int = 128000
    cost_tier: str = "medium"
    latency_tier: str = "medium"
    recommended_for: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


DEFAULT_MODELS = {
    "fast-general": ModelProfile(
        name="fast-general",
        provider="default",
        strengths=["classification", "routing", "simple_qa", "light_planning"],
        max_context=64000,
        cost_tier="low",
        latency_tier="low",
        recommended_for=["search_only", "default", "send_message"],
    ),
    "reasoning-general": ModelProfile(
        name="reasoning-general",
        provider="default",
        strengths=["planning", "synthesis", "analysis", "multi_step_reasoning"],
        max_context=128000,
        cost_tier="medium",
        latency_tier="medium",
        recommended_for=["search_and_save", "read_file", "fetch_only", "skill"],
    ),
    "code-agent": ModelProfile(
        name="code-agent",
        provider="default",
        strengths=["coding", "shell", "debugging", "workflow_authoring"],
        max_context=128000,
        cost_tier="medium",
        latency_tier="medium",
        recommended_for=["exec_command"],
    ),
    "long-context": ModelProfile(
        name="long-context",
        provider="default",
        strengths=["large_documents", "summarization", "context_heavy_tasks"],
        max_context=1000000,
        cost_tier="high",
        latency_tier="high",
        recommended_for=["document_heavy", "multi_source_research"],
    ),
}


class ModelRouter:
    def __init__(self, models: Optional[Dict[str, ModelProfile]] = None):
        self.models = models or DEFAULT_MODELS

    def list_models(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.models.values()]

    def get(self, name: str) -> Optional[ModelProfile]:
        return self.models.get(name)

    def rank_task(self, task_title: str, task_description: str = "", *, workflow: Optional[str] = None, route_kind: Optional[str] = None) -> List[Dict[str, Any]]:
        text = f"{task_title or ''} {task_description or ''}".lower()
        ranked: List[Dict[str, Any]] = []

        for model in self.models.values():
            score = 0.0
            reasons: List[str] = []

            if route_kind == "skill" and model.name == "reasoning-general":
                score += 5.0
                reasons.append("skill_guided_task")
            if workflow == "exec_command" and model.name == "code-agent":
                score += 5.0
                reasons.append("workflow_exec_command")
            if workflow == "local_python_exec" and model.name == "code-agent":
                score += 5.0
                reasons.append("workflow_local_python_exec")
            if workflow in {"search_and_save", "fetch_only", "read_file", "local_conversation_query", "local_dashboard_query", "local_db_query"} and model.name == "reasoning-general":
                score += 4.0
                reasons.append("analysis_workflow")
            if workflow in {"search_only", "default", "send_message"} and model.name == "fast-general":
                score += 3.0
                reasons.append("fast_path_workflow")

            if any(k in text for k in ["code", "script", "shell", "terminal", "debug", "bugfix", "stack trace"]):
                if model.name == "code-agent":
                    score += 4.0
                    reasons.append("coding_or_shell_signal")
            if any(k in text for k in ["analyze", "research", "compare", "summarize", "plan", "workflow"]):
                if model.name == "reasoning-general":
                    score += 3.0
                    reasons.append("analysis_signal")
            if any(k in text for k in ["long", "large", "many files", "full context", "huge", "document"]):
                if model.name == "long-context":
                    score += 5.0
                    reasons.append("long_context_signal")
            if any(k in text for k in ["quick", "fast", "brief", "simple"]):
                if model.name == "fast-general":
                    score += 2.0
                    reasons.append("fast_signal")

            # slight priors
            if model.name == "fast-general":
                score += 0.5
            if model.name == "reasoning-general":
                score += 0.75

            ranked.append({"model": model.name, "provider": model.provider, "score": round(score, 3), "reasons": reasons})

        ranked.sort(key=lambda x: (-x["score"], x["model"]))
        return ranked

    def route_task(self, task_title: str, task_description: str = "", *, workflow: Optional[str] = None, explicit_model: Optional[str] = None, route_kind: Optional[str] = None) -> Dict[str, Any]:
        if explicit_model:
            model = self.get(explicit_model)
            if model:
                return {
                    "model": model.name,
                    "provider": model.provider,
                    "reason": "explicit_override",
                    "workflow": workflow,
                    "route_kind": route_kind,
                    "ranked_models": self.rank_task(task_title, task_description, workflow=workflow, route_kind=route_kind),
                }

        ranked = self.rank_task(task_title, task_description, workflow=workflow, route_kind=route_kind)
        chosen = ranked[0]
        return {
            "model": chosen["model"],
            "provider": chosen["provider"],
            "reason": chosen["reasons"][0] if chosen["reasons"] else "default_ranked_choice",
            "workflow": workflow,
            "route_kind": route_kind,
            "ranked_models": ranked,
        }


model_router = ModelRouter()
