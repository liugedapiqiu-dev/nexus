from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from heart.engine import HeartEngine
from heart.memory import memory_store
from heart.state import HeartState


class RuntimeHeartBridge:
    """Adapter so runtime/orchestrator can use Heart with optional preprocess hooks."""

    def __init__(self):
        self.engine = HeartEngine()

    def assess(
        self,
        user_text: str,
        *,
        session_id: Optional[str] = None,
        heart_state: Optional[Dict[str, Any]] = None,
        write_memory: bool = True,
        tags: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        state = HeartState.from_dict(heart_state) if heart_state else None
        return self.engine.process_input(
            user_text,
            session_id=session_id,
            current_state=state,
            write_memory=write_memory,
            tags=(tags or []) + ["runtime"],
        ).to_dict()

    def build_preprocess_packet(
        self,
        user_text: str,
        *,
        session_id: Optional[str] = None,
        heart_state: Optional[Dict[str, Any]] = None,
        write_memory: bool = False,
        tags: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        result = self.assess(
            user_text,
            session_id=session_id,
            heart_state=heart_state,
            write_memory=write_memory,
            tags=(tags or []) + ["preprocess"],
        )
        policy = result["policy"]
        state = result["state"]
        regulation = result["regulation"]
        context_brief = memory_store.build_context_brief(session_id) if session_id else {"brief": "no_session"}
        profile = context_brief.get("profile") or {}

        reply_guidance = {
            "opening": policy.get("reply_opening"),
            "tone": policy.get("tone"),
            "style": policy.get("response_style"),
            "strategy": policy.get("strategy", []),
            "structure": policy.get("suggested_structure", []),
            "max_questions": policy.get("max_questions", 2),
            "protective_mode": state.get("protective_mode"),
            "trajectory": state.get("trajectory_label"),
            "should_be_brief": policy.get("should_be_brief", False),
            "should_reflect_feelings": policy.get("should_reflect_feelings", False),
            "should_offer_recovery_plan": policy.get("should_offer_recovery_plan", False),
            "session_brief": context_brief.get("brief"),
            "profile_brief": context_brief.get("profile_brief"),
            "long_term_profile": profile,
        }

        return {
            "enabled": True,
            "heart": result,
            "assistant_prompt_prefix": " ".join(policy.get("prompt_modifiers", [])),
            "assistant_prompt_append": self.compose_assistant_prompt(reply_guidance),
            "reply_guidance": reply_guidance,
            "risk_flags": {
                "protective_mode": state.get("protective_mode"),
                "threat_score": result["signal"].get("threat_score", 0.0),
                "stress": state.get("stress", 0.0),
                "safety": state.get("safety", 1.0),
                "trajectory": regulation.get("trajectory_label"),
            },
            "memory_brief": context_brief.get("brief", "no_session"),
            "composer": self.compose_response_plan(reply_guidance),
        }

    def compose_assistant_prompt(self, reply_guidance: Dict[str, Any]) -> str:
        lines = [
            "[Heart Reply Guidance]",
            f"opening={reply_guidance.get('opening')}",
            f"tone={reply_guidance.get('tone')}",
            f"style={reply_guidance.get('style')}",
            f"protective_mode={reply_guidance.get('protective_mode')}",
            f"trajectory={reply_guidance.get('trajectory')}",
            f"max_questions={reply_guidance.get('max_questions')}",
            f"should_be_brief={reply_guidance.get('should_be_brief')}",
            f"should_reflect_feelings={reply_guidance.get('should_reflect_feelings')}",
            f"should_offer_recovery_plan={reply_guidance.get('should_offer_recovery_plan')}",
            f"strategy={', '.join(reply_guidance.get('strategy') or []) or 'none'}",
            f"structure={', '.join(reply_guidance.get('structure') or []) or 'none'}",
        ]
        if reply_guidance.get("session_brief"):
            lines.append(f"session_brief={reply_guidance['session_brief']}")
        if reply_guidance.get("profile_brief"):
            lines.append(f"profile_brief={reply_guidance['profile_brief']}")
        lines.extend([
            "Apply these instructions directly in the final answer, not only as metadata.",
            "If there is tension between completeness and emotional fit, preserve correctness but follow the Heart guidance for tone, opening, pacing, and structure.",
        ])
        return "\n".join(lines)

    def compose_response_plan(self, reply_guidance: Dict[str, Any]) -> Dict[str, Any]:
        opening_map = {
            "stabilize_first": "先稳住对方，再给一个最小可执行动作。",
            "acknowledge_then_focus": "先承接情绪/风险，再快速收束到安全下一步。",
            "warm_start": "先温和回应，再给轻量帮助。",
            "direct": "直接回答，但别显得冷。",
        }
        sentence_target = "short" if reply_guidance.get("should_be_brief") else "medium"
        return {
            "opening_line_rule": opening_map.get(reply_guidance.get("opening"), "先自然开头，再进入帮助。"),
            "sentence_length": sentence_target,
            "question_limit": reply_guidance.get("max_questions", 2),
            "must_include": [
                "情绪贴合" if reply_guidance.get("should_reflect_feelings") else "不必强行情绪镜像",
                "恢复/下一步" if reply_guidance.get("should_offer_recovery_plan") else "直接有效下一步",
            ],
            "structure": reply_guidance.get("structure") or ["answer", "next_step"],
            "strategy": reply_guidance.get("strategy") or [],
        }

    def inject_into_payload(self, payload: Dict[str, Any], packet: Dict[str, Any]) -> Dict[str, Any]:
        payload = deepcopy(payload)
        metadata = dict(payload.get("metadata") or {})
        heart_meta = packet

        description = payload.get("description") or ""
        append = packet.get("assistant_prompt_append") or ""
        composer = packet.get("composer") or {}
        guidance = packet.get("reply_guidance") or {}

        injected_block = "\n\n".join(
            part for part in [
                "[Heart Composer Active]",
                append,
                f"[Heart Response Plan] {composer}",
            ] if part
        ).strip()

        if injected_block:
            payload["description"] = (description + "\n\n" + injected_block).strip() if description else injected_block

        metadata.setdefault("response_guidance", {})
        metadata["response_guidance"]["heart"] = {
            "opening": guidance.get("opening"),
            "tone": guidance.get("tone"),
            "style": guidance.get("style"),
            "structure": guidance.get("structure", []),
            "strategy": guidance.get("strategy", []),
            "composer": composer,
        }
        metadata["heart"] = heart_meta
        metadata.setdefault("preprocess_trace", []).append("heart")
        payload["metadata"] = metadata
        return payload

    def preprocess_task_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = deepcopy(payload)
        metadata = dict(payload.get("metadata") or {})
        hooks = metadata.get("preprocess_hooks") or []
        heart_enabled = bool(metadata.get("heart_preprocess")) or ("heart" in hooks)
        if not heart_enabled:
            return payload

        user_text = "\n\n".join(part for part in [payload.get("title") or payload.get("task") or "", payload.get("description") or ""] if part)
        if not user_text.strip():
            return payload

        packet = self.build_preprocess_packet(
            user_text,
            session_id=metadata.get("session_id") or payload.get("session_id"),
            heart_state=metadata.get("heart_state"),
            write_memory=bool(metadata.get("heart_write_memory", False)),
            tags=["orchestrator_preprocess"],
        )
        return self.inject_into_payload(payload, packet)


runtime_heart = RuntimeHeartBridge()
