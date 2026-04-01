from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, field, fields
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PerceptionSignal:
    text: str
    dominant_emotion: str = "neutral"
    emotion_scores: Dict[str, float] = field(default_factory=dict)
    detected_needs: List[str] = field(default_factory=list)
    urgency: float = 0.0
    sentiment: float = 0.0  # -1..1
    threat_score: float = 0.0
    support_score: float = 0.0
    confidence: float = 0.0
    cues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegulationDecision:
    state_delta: Dict[str, float] = field(default_factory=dict)
    protective_mode: str = "normal"
    reasoning: List[str] = field(default_factory=list)
    recommended_focus: List[str] = field(default_factory=list)
    trajectory_label: str = "steady"
    recovery_applied: bool = False
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyDecision:
    response_style: str = "balanced"
    strategy: List[str] = field(default_factory=list)
    tone: str = "steady"
    boundaries: List[str] = field(default_factory=list)
    should_slow_down: bool = False
    should_clarify: bool = False
    should_offer_comfort: bool = False
    should_be_brief: bool = False
    should_ask_consent_for_sensitive_actions: bool = True
    should_reflect_feelings: bool = False
    should_offer_recovery_plan: bool = False
    max_questions: int = 2
    reply_opening: str = "direct"
    suggested_structure: List[str] = field(default_factory=list)
    prompt_modifiers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HeartState:
    session_id: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    dominant_emotion: str = "neutral"
    valence: float = 0.0   # -1..1
    emotional_baseline: float = 0.0  # -1..1 long arc baseline
    arousal: float = 0.0   # 0..1
    trust: float = 0.5     # 0..1
    stress: float = 0.0    # 0..1
    safety: float = 1.0    # 0..1
    resilience: float = 0.55  # 0..1 ability to recover
    recovery_score: float = 0.0  # 0..1 current recovery momentum
    stability: float = 0.5  # 0..1 steadiness over time
    volatility: float = 0.0  # 0..1 how jumpy recent updates are
    risk_load: float = 0.0  # 0..1 accumulated risk residue
    protective_mode: str = "normal"  # normal|guarded|supportive|crisis
    active_needs: List[str] = field(default_factory=list)
    unresolved_needs: List[str] = field(default_factory=list)
    memory_keys: List[str] = field(default_factory=list)
    trajectory_label: str = "steady"
    trajectory_notes: List[str] = field(default_factory=list)
    stable_cycles: int = 0
    recovery_cycles: int = 0
    last_user_signal: Optional[Dict[str, Any]] = None
    last_policy: Optional[Dict[str, Any]] = None
    history_size: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "HeartState":
        if not data:
            return cls()

        allowed = {f.name: f for f in fields(cls)}
        payload: Dict[str, Any] = {}
        extras: Dict[str, Any] = {}

        for key, value in dict(data).items():
            if key in allowed:
                payload[key] = value
            else:
                extras[key] = value

        for name, f in allowed.items():
            if name not in payload:
                if f.default is not MISSING:
                    payload[name] = f.default
                elif f.default_factory is not MISSING:  # type: ignore[attr-defined]
                    payload[name] = f.default_factory()  # type: ignore[misc]

        state = cls(**payload)
        if extras:
            state.meta = dict(state.meta or {})
            state.meta.setdefault("legacy_payload", {}).update(extras)
        return state
