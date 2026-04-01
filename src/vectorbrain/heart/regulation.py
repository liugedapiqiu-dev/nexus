from __future__ import annotations

from datetime import datetime
from typing import List

from .state import HeartState, PerceptionSignal, RegulationDecision


class HeartRegulator:
    def regulate(self, current: HeartState, signal: PerceptionSignal) -> tuple[HeartState, RegulationDecision]:
        next_state = HeartState.from_dict(current.snapshot())
        reasons: List[str] = []

        prev_valence = current.valence
        prev_arousal = current.arousal
        prev_stress = current.stress
        prev_trust = current.trust
        prev_safety = current.safety
        prev_mode = current.protective_mode

        next_state.updated_at = datetime.utcnow().isoformat()
        next_state.history_size += 1

        baseline = self._clamp((current.emotional_baseline * 0.92) + (signal.sentiment * 0.08), -1.0, 1.0)
        target_valence = self._clamp((signal.sentiment * 0.7) + (baseline * 0.3), -1.0, 1.0)
        next_state.valence = self._clamp((current.valence * 0.72) + (target_valence * 0.28), -1.0, 1.0)
        next_state.emotional_baseline = baseline

        pressure = max(signal.urgency, signal.threat_score, abs(signal.sentiment) * 0.55)
        raw_arousal = (current.arousal * 0.62) + (pressure * 0.38)
        raw_stress = (current.stress * 0.58) + (max(signal.threat_score, signal.urgency, 0.65 if signal.dominant_emotion in {"distress", "anger"} else 0.18) * 0.42)

        support_bonus = signal.support_score + (0.12 if "comfort" in signal.detected_needs else 0.0)
        recovery_window = signal.threat_score < 0.30 and signal.urgency < 0.45
        recovery_factor = 0.0
        recovery_applied = False

        if recovery_window:
            recovery_factor = self._clamp(0.08 + next_state.resilience * 0.18 + support_bonus * 0.15, 0.0, 0.32)
            raw_stress -= recovery_factor
            raw_arousal -= recovery_factor * 0.75
            if signal.sentiment >= -0.2:
                next_state.valence = self._clamp(next_state.valence + recovery_factor * 0.22, -1.0, 1.0)
            recovery_applied = recovery_factor > 0.01
            reasons.append("recovery_window_open")

        next_state.arousal = self._clamp(raw_arousal, 0.0, 1.0)
        next_state.stress = self._clamp(raw_stress, 0.0, 1.0)

        trust_shift = 0.0
        if signal.support_score > 0:
            trust_shift += 0.16 + signal.support_score * 0.12
        elif signal.threat_score > 0.40:
            trust_shift -= 0.08
        else:
            trust_shift += 0.03
        next_state.trust = self._clamp((current.trust * 0.84) + trust_shift, 0.0, 1.0)

        next_state.risk_load = self._clamp((current.risk_load * 0.72) + (signal.threat_score * 0.28), 0.0, 1.0)
        next_state.safety = self._clamp(1.0 - max(signal.threat_score * 0.9, next_state.stress * 0.52, next_state.risk_load * 0.4), 0.0, 1.0)

        volatility = abs(next_state.valence - current.valence) * 0.45 + abs(next_state.stress - current.stress) * 0.55
        next_state.volatility = self._clamp((current.volatility * 0.6) + volatility, 0.0, 1.0)
        next_state.stability = self._clamp((current.stability * 0.7) + ((1.0 - next_state.volatility) * 0.16) + ((1.0 - next_state.stress) * 0.14), 0.0, 1.0)
        next_state.resilience = self._clamp((current.resilience * 0.82) + ((1.0 - signal.threat_score) * 0.08) + (0.10 if recovery_applied else -0.02), 0.0, 1.0)

        if next_state.stress <= 0.34 and next_state.volatility <= 0.20 and signal.threat_score < 0.2:
            next_state.stable_cycles = current.stable_cycles + 1
        else:
            next_state.stable_cycles = max(0, current.stable_cycles - 1)

        if recovery_applied and next_state.stress < current.stress:
            next_state.recovery_cycles = current.recovery_cycles + 1
            next_state.recovery_score = self._clamp((current.recovery_score * 0.7) + 0.22 + recovery_factor * 0.6, 0.0, 1.0)
        else:
            next_state.recovery_cycles = max(0, current.recovery_cycles - 1)
            next_state.recovery_score = self._clamp((current.recovery_score * 0.68) - (0.10 if signal.threat_score > 0.5 else 0.02), 0.0, 1.0)

        next_state.active_needs = list(dict.fromkeys(signal.detected_needs))
        unresolved = list(dict.fromkeys((current.unresolved_needs or []) + signal.detected_needs))
        if recovery_applied and "comfort" not in signal.detected_needs and next_state.stress < 0.35:
            unresolved = [n for n in unresolved if n not in {"comfort", "reassurance"}]
        if signal.threat_score > 0.5 and "safety" not in unresolved:
            unresolved.insert(0, "safety")
        next_state.unresolved_needs = unresolved[:8]
        next_state.last_user_signal = signal.to_dict()

        mode = "normal"
        if signal.threat_score >= 0.85 or next_state.risk_load >= 0.85:
            mode = "crisis"
            reasons.append("high_threat_signal")
        elif signal.threat_score >= 0.45 or next_state.stress >= 0.72 or (prev_mode == "crisis" and next_state.recovery_cycles < 2):
            mode = "guarded"
            reasons.append("elevated_risk_or_stress")
        elif signal.support_score >= 0.30 or "comfort" in next_state.active_needs or signal.dominant_emotion in {"sadness", "distress"}:
            mode = "supportive"
            reasons.append("user_needs_emotional_support")
        elif prev_mode == "guarded" and next_state.stable_cycles < 2 and next_state.stress > 0.35:
            mode = "guarded"
            reasons.append("guarded_mode_decay_delay")
        else:
            reasons.append("steady_interaction")

        next_state.protective_mode = mode

        if signal.threat_score >= 0.75 or next_state.stress - current.stress >= 0.12:
            trajectory = "escalating"
        elif recovery_applied and next_state.recovery_cycles >= 2:
            trajectory = "recovering"
        elif next_state.stable_cycles >= 2 and next_state.stability >= 0.62:
            trajectory = "stabilizing"
        elif next_state.valence >= 0.35 and next_state.stress <= 0.35:
            trajectory = "positive_arc"
        elif next_state.stress >= 0.45 and next_state.recovery_score >= 0.35:
            trajectory = "heavy_but_managed"
        else:
            trajectory = "steady"

        next_state.trajectory_label = trajectory
        note = f"{trajectory}|mode={mode}|stress={next_state.stress:.2f}|trust={next_state.trust:.2f}"
        next_state.trajectory_notes = (current.trajectory_notes + [note])[-8:]
        next_state.dominant_emotion = signal.dominant_emotion if signal.confidence >= 0.28 else current.dominant_emotion
        next_state.meta = dict(current.meta or {})
        next_state.meta.update(
            {
                "predicted_next_risk": round(max(signal.threat_score * 0.8, next_state.risk_load * 0.7, next_state.stress * 0.5), 4),
                "recovery_window": recovery_window,
                "support_bonus": round(support_bonus, 4),
            }
        )

        focus = []
        if "safety" in next_state.unresolved_needs:
            focus.append("stabilize_and_reduce_risk")
        if "clarity" in next_state.active_needs:
            focus.append("explain_clearly")
        if "reassurance" in next_state.unresolved_needs:
            focus.append("reduce_uncertainty")
        if "comfort" in next_state.unresolved_needs:
            focus.append("validate_feelings")
        if "speed" in next_state.active_needs:
            focus.append("prioritize_actionability")
        if trajectory == "recovering":
            focus.append("protect_recovery_momentum")
        if not focus:
            focus.append("maintain_balance")

        summary = f"mode={mode}; trajectory={trajectory}; stress={next_state.stress:.2f}; safety={next_state.safety:.2f}; unresolved={','.join(next_state.unresolved_needs[:3]) or 'none'}"

        decision = RegulationDecision(
            state_delta={
                "valence": round(next_state.valence - prev_valence, 4),
                "arousal": round(next_state.arousal - prev_arousal, 4),
                "stress": round(next_state.stress - prev_stress, 4),
                "trust": round(next_state.trust - prev_trust, 4),
                "safety": round(next_state.safety - prev_safety, 4),
                "recovery_score": round(next_state.recovery_score - current.recovery_score, 4),
                "stability": round(next_state.stability - current.stability, 4),
                "risk_load": round(next_state.risk_load - current.risk_load, 4),
            },
            protective_mode=mode,
            reasoning=reasons,
            recommended_focus=focus,
            trajectory_label=trajectory,
            recovery_applied=recovery_applied,
            summary=summary,
        )
        return next_state, decision

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))


regulator = HeartRegulator()
