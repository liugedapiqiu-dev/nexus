from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from .memory import EmotionalMemoryStore, memory_store
from .perception import EmotionNeedRecognizer, recognizer
from .policy import HeartPolicy, policy_engine
from .regulation import HeartRegulator, regulator
from .state import HeartState


@dataclass
class HeartResult:
    state: Dict[str, Any]
    signal: Dict[str, Any]
    regulation: Dict[str, Any]
    policy: Dict[str, Any]
    memory_event_id: Optional[str] = None
    memory_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HeartEngine:
    def __init__(
        self,
        *,
        recognizer_: Optional[EmotionNeedRecognizer] = None,
        regulator_: Optional[HeartRegulator] = None,
        policy_: Optional[HeartPolicy] = None,
        memory_: Optional[EmotionalMemoryStore] = None,
    ):
        self.recognizer = recognizer_ or recognizer
        self.regulator = regulator_ or regulator
        self.policy = policy_ or policy_engine
        self.memory = memory_ or memory_store

    def process_input(
        self,
        text: str,
        *,
        session_id: Optional[str] = None,
        current_state: Optional[HeartState | Dict[str, Any]] = None,
        write_memory: bool = True,
        tags: Optional[list[str]] = None,
    ) -> HeartResult:
        if isinstance(current_state, HeartState):
            state = current_state
        elif current_state:
            state = HeartState.from_dict(current_state)
        elif session_id:
            state = self.memory.latest_state(session_id) or HeartState.from_dict(self.memory.profile_state_seed(session_id) or {}) or HeartState(session_id=session_id)
        else:
            state = HeartState()

        if session_id and not state.session_id:
            state.session_id = session_id

        signal = self.recognizer.analyze(text)
        next_state, regulation = self.regulator.regulate(state, signal)
        if session_id:
            next_state.session_id = session_id
        policy = self.policy.decide(next_state, signal, regulation)
        next_state.last_policy = policy.to_dict()

        memory_event_id = None
        if write_memory:
            memory_event_id = self.memory.write_event(
                session_id=session_id,
                user_text=text,
                signal=signal,
                state=next_state,
                regulation=regulation,
                policy=policy,
                tags=tags,
            )
            next_state.memory_keys = (next_state.memory_keys + [memory_event_id])[-20:]

        memory_summary = self.memory.session_summary(session_id) if session_id else None
        context_brief = self.memory.build_context_brief(session_id) if session_id else None
        if memory_summary and memory_summary.get("exists"):
            next_state.meta = dict(next_state.meta or {})
            next_state.meta["session_emotional_summary"] = memory_summary.get("summary")
        if context_brief:
            next_state.meta = dict(next_state.meta or {})
            if context_brief.get("profile"):
                next_state.meta["long_term_profile"] = context_brief.get("profile")
            if context_brief.get("profile_brief"):
                next_state.meta["profile_brief"] = context_brief.get("profile_brief")

        return HeartResult(
            state=next_state.snapshot(),
            signal=signal.to_dict(),
            regulation=regulation.to_dict(),
            policy=policy.to_dict(),
            memory_event_id=memory_event_id,
            memory_summary=memory_summary,
        )


def process_message(text: str, **kwargs) -> Dict[str, Any]:
    return HeartEngine().process_input(text, **kwargs).to_dict()
