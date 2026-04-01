from __future__ import annotations

from .state import HeartState, PolicyDecision, PerceptionSignal, RegulationDecision


class HeartPolicy:
    def decide(self, state: HeartState, signal: PerceptionSignal, regulation: RegulationDecision) -> PolicyDecision:
        strategy = []
        boundaries = []
        prompt_modifiers = []
        suggested_structure = []
        tone = "steady"
        style = "balanced"
        slow = False
        clarify = False
        comfort = False
        brief = False
        reflect_feelings = False
        recovery_plan = False
        max_questions = 2
        opening = "direct"

        if state.protective_mode == "crisis":
            style = "protective"
            tone = "calm_grounded"
            opening = "stabilize_first"
            strategy += [
                "prioritize_immediate_safety",
                "give_grounding_step",
                "encourage_human_support_now",
                "avoid_information_overload",
            ]
            boundaries += [
                "do_not_be_flippant",
                "do_not_offer_harmful_instructions",
                "do_not_push_complex_plans",
            ]
            suggested_structure += ["acknowledge", "grounding", "safety", "human_support"]
            prompt_modifiers += [
                "Use calm, short, stabilizing language.",
                "Prioritize immediate safety and grounding over completeness.",
                "One concrete next step at a time.",
            ]
            slow = True
            clarify = True
            comfort = True
            brief = True
            reflect_feelings = True
            recovery_plan = True
            max_questions = 1
        elif state.protective_mode == "guarded":
            style = "cautious_support"
            tone = "careful"
            opening = "acknowledge_then_focus"
            strategy += ["de_escalate", "confirm_intent", "give_safe_next_steps", "keep_scope_narrow"]
            boundaries += ["avoid_assumptions", "avoid_high_pressure_tone", "avoid_overpromising"]
            suggested_structure += ["acknowledge", "clarify_if_needed", "safe_next_step"]
            prompt_modifiers += [
                "Be careful with risk and ambiguity.",
                "Ask at most one clarifying question if needed.",
                "Favor safer, reversible actions.",
            ]
            slow = True
            clarify = signal.threat_score > 0.25 or "boundaries" in state.active_needs or "safety" in state.unresolved_needs
            comfort = signal.dominant_emotion in {"sadness", "distress", "anger"}
            reflect_feelings = comfort
            brief = state.arousal > 0.70
            max_questions = 1
            recovery_plan = regulation.trajectory_label in {"recovering", "heavy_but_managed"}
        elif state.protective_mode == "supportive":
            style = "warm_supportive"
            tone = "warm"
            opening = "warm_start"
            strategy += ["validate_emotion", "offer_small_next_step", "reduce_cognitive_load", "protect_recovery"]
            boundaries += ["avoid_cold_efficiency", "avoid_overanalyzing"]
            suggested_structure += ["acknowledge", "normalize", "small_next_step"]
            prompt_modifiers += [
                "Lead with empathy, then help.",
                "Keep steps gentle, concrete, and easy to start.",
            ]
            comfort = True
            reflect_feelings = True
            brief = state.arousal > 0.65
            recovery_plan = True
            max_questions = 1 if state.arousal > 0.6 else 2
        else:
            style = "balanced"
            tone = "steady"
            opening = "direct"
            strategy += ["be_clear", "be_useful", "stay_grounded", "anticipate_next_step"]
            suggested_structure += ["answer", "next_step"]
            prompt_modifiers += [
                "Keep a balanced, competent tone.",
                "Think one step ahead and prevent the next obvious confusion.",
            ]
            if regulation.trajectory_label == "recovering":
                strategy.append("avoid_retriggering_pressure")
                recovery_plan = True

        if "clarity" in state.active_needs:
            strategy.append("structure_answer")
            suggested_structure.append("bullets")
            prompt_modifiers.append("Use clear structure and concrete wording.")
        if "speed" in state.active_needs:
            strategy.append("frontload_answer")
            brief = True
            prompt_modifiers.append("Put the most actionable line first.")
        if "reassurance" in state.unresolved_needs:
            strategy.append("reduce_uncertainty")
            comfort = True
        if "safety" in state.unresolved_needs:
            strategy.append("safety_check")
            slow = True
            brief = True
            max_questions = min(max_questions, 1)
        if regulation.trajectory_label == "escalating":
            strategy.append("contain_escalation")
            prompt_modifiers.append("Do not mirror panic; lower the temperature.")
            slow = True
            brief = True
        elif regulation.trajectory_label in {"recovering", "stabilizing"}:
            strategy.append("reinforce_progress")
            prompt_modifiers.append("Acknowledge improvement without being overly celebratory.")
        if signal.dominant_emotion == "joy" and state.protective_mode == "normal":
            tone = "light_positive"
            strategy.append("match_positive_energy_lightly")

        return PolicyDecision(
            response_style=style,
            strategy=list(dict.fromkeys(strategy)),
            tone=tone,
            boundaries=list(dict.fromkeys(boundaries)),
            should_slow_down=slow,
            should_clarify=clarify,
            should_offer_comfort=comfort,
            should_be_brief=brief,
            should_ask_consent_for_sensitive_actions=True,
            should_reflect_feelings=reflect_feelings,
            should_offer_recovery_plan=recovery_plan,
            max_questions=max_questions,
            reply_opening=opening,
            suggested_structure=list(dict.fromkeys(suggested_structure)),
            prompt_modifiers=list(dict.fromkeys(prompt_modifiers)),
        )


policy_engine = HeartPolicy()
