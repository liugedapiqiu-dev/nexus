from __future__ import annotations

import re
from typing import Dict, List

from .state import PerceptionSignal


EMOTION_LEXICON: Dict[str, List[str]] = {
    "distress": [
        "难受", "崩溃", "绝望", "痛苦", "焦虑", "烦", "压力", "害怕", "恐慌", "撑不住", "窒息", "慌", "顶不住", "要疯了",
        "stress", "anxious", "panic", "overwhelmed", "breaking down", "can't cope",
    ],
    "anger": ["生气", "愤怒", "火大", "讨厌", "气死", "烦死", "受不了", "无语", "angry", "furious", "annoyed", "pissed"],
    "sadness": ["难过", "伤心", "失落", "委屈", "低落", "沮丧", "sad", "down", "depressed", "upset"],
    "joy": ["开心", "高兴", "兴奋", "满意", "放心", "踏实", "happy", "great", "excited", "relieved", "glad"],
    "care": ["谢谢", "辛苦", "陪我", "安慰", "理解", "拜托", "求你", "support", "help me", "comfort", "thanks"],
    "urgency": ["马上", "立刻", "现在", "紧急", "赶紧", "来不及", "asap", "urgent", "immediately", "right now"],
    "risk": ["自杀", "伤害自己", "不想活", "活不下去", "结束自己", "kill myself", "suicide", "hurt myself", "self-harm"],
}

HIGH_RISK_PATTERNS = [
    "不想活",
    "自杀",
    "伤害自己",
    "活不下去",
    "结束自己",
    "kill myself",
    "suicide",
    "hurt myself",
    "self-harm",
]

MODERATE_RISK_PATTERNS = [
    "撑不住",
    "崩溃",
    "绝望",
    "失控",
    "我完了",
    "顶不住",
    "要疯了",
]

NEED_PATTERNS: Dict[str, List[str]] = {
    "clarity": ["什么意思", "解释", "看不懂", "为什么", "怎么回事", "一步一步", "拆开", "explain", "why", "step by step"],
    "reassurance": ["担心", "害怕", "会不会", "是不是完了", "稳吗", "靠谱吗", "anxious", "worried"],
    "speed": ["快点", "马上", "立刻", "直接说", "先给答案", "urgent", "asap"],
    "comfort": ["安慰", "抱抱", "陪我", "难受", "冷静一下", "缓一缓", "comfort", "support"],
    "boundaries": ["不要", "停", "够了", "别再", "stop", "don't", "算了"],
    "control": ["帮我决定", "替我选", "给方案", "下一步", "what should i do", "choose for me"],
}

POSITIVE_HINTS = ["谢谢", "开心", "放心", "满意", "稳了", "好耶", "good", "great", "love", "relieved"]
NEGATIVE_HINTS = ["糟糕", "烦", "累", "怕", "失望", "慌", "崩", "bad", "terrible", "anxious", "sad"]
HEDGING_PATTERNS = ["可能", "也许", "好像", "似乎", "不太确定", "maybe", "i guess", "not sure"]
INTENSIFIERS = ["很", "太", "特别", "非常", "超级", "真的", "真是", "so ", "too ", "extremely", "really"]
SOFTENERS = ["有点", "一点", "还好", "稍微", "kind of", "a bit", "slightly"]
EXHAUSTION_PATTERNS = ["累死", "好累", "没力气", "脑子转不动", "睡不着", "熬不住", "exhausted", "drained", "burned out"]
CONFUSION_PATTERNS = ["乱", "懵", "不知道", "搞不清", "看不懂", "卡住", "confused", "lost", "stuck"]
REPAIR_PATTERNS = ["好多了", "缓过来", "冷静了", "没那么慌", "稳定些", "better now", "calmer", "i'm okay now"]


class EmotionNeedRecognizer:
    def analyze(self, text: str) -> PerceptionSignal:
        raw_text = text or ""
        lowered = raw_text.lower()
        emotion_scores: Dict[str, float] = {}
        cues: List[str] = []

        for emotion, patterns in EMOTION_LEXICON.items():
            hits = [p for p in patterns if p.lower() in lowered]
            if hits:
                emotion_scores[emotion] = min(1.0, 0.18 * len(hits) + 0.12)
                cues.extend(hits)

        need_hits: Dict[str, int] = {}
        for need, patterns in NEED_PATTERNS.items():
            hits = [p for p in patterns if p.lower() in lowered]
            if hits:
                need_hits[need] = len(hits)
                cues.extend(hits)

        pos = sum(1 for token in POSITIVE_HINTS if token.lower() in lowered)
        neg = sum(1 for token in NEGATIVE_HINTS if token.lower() in lowered)
        sentiment = 0.0 if pos == neg == 0 else max(-1.0, min(1.0, (pos - neg) / max(pos + neg, 1)))

        exclamations = raw_text.count("!") + raw_text.count("！")
        questions = raw_text.count("?") + raw_text.count("？")
        ellipsis = raw_text.count("...") + raw_text.count("……")
        uppercase_ratio = self._uppercase_ratio(raw_text)
        intensifier_hits = sum(1 for token in INTENSIFIERS if token in lowered)
        softener_hits = sum(1 for token in SOFTENERS if token in lowered)
        hedge_hits = sum(1 for token in HEDGING_PATTERNS if token in lowered)
        exhaustion_hits = sum(1 for token in EXHAUSTION_PATTERNS if token in lowered)
        confusion_hits = sum(1 for token in CONFUSION_PATTERNS if token in lowered)
        repair_hits = sum(1 for token in REPAIR_PATTERNS if token in lowered)

        urgency = emotion_scores.get("urgency", 0.0)
        urgency += min(0.22, exclamations * 0.05)
        urgency += 0.12 if re.search(r"\d+\s*(分钟|min|mins|小时|hour)", lowered) else 0.0
        urgency += 0.08 if "来不及" in raw_text else 0.0
        urgency += 0.06 if questions >= 2 else 0.0

        threat = emotion_scores.get("risk", 0.0) + (0.2 if "不要" in raw_text or "stop" in lowered else 0.0)
        if any(p.lower() in lowered for p in HIGH_RISK_PATTERNS):
            threat = max(threat, 0.92)
            cues.append("high_risk_pattern")
        elif any(p.lower() in lowered for p in MODERATE_RISK_PATTERNS):
            threat = max(threat, 0.55)
            cues.append("moderate_risk_pattern")

        support = emotion_scores.get("care", 0.0) + (0.2 if "help" in lowered or "帮我" in raw_text else 0.0)
        support += min(0.18, softener_hits * 0.06)
        support += min(0.14, hedge_hits * 0.04)

        if exhaustion_hits:
            emotion_scores["distress"] = min(1.0, emotion_scores.get("distress", 0.0) + 0.16 * exhaustion_hits)
            need_hits["comfort"] = need_hits.get("comfort", 0) + exhaustion_hits
            cues.append("exhaustion")
        if confusion_hits:
            need_hits["clarity"] = need_hits.get("clarity", 0) + confusion_hits
            cues.append("confusion")
        if repair_hits:
            sentiment = min(1.0, sentiment + 0.22)
            cues.append("repair_signal")

        if intensifier_hits:
            for key in list(emotion_scores.keys()):
                emotion_scores[key] = min(1.0, emotion_scores[key] + min(0.2, intensifier_hits * 0.05))
            cues.append("intensifier")
        if uppercase_ratio > 0.35:
            urgency = min(1.0, urgency + 0.1)
            if sentiment < 0:
                emotion_scores["anger"] = min(1.0, emotion_scores.get("anger", 0.0) + 0.12)
            cues.append("uppercase_emphasis")
        if ellipsis:
            support = min(1.0, support + 0.06)
            cues.append("ellipsis")

        filtered_emotions = {k: v for k, v in emotion_scores.items() if k not in {"urgency", "risk"}}
        if filtered_emotions:
            dominant = max(filtered_emotions, key=filtered_emotions.get)
        elif threat >= 0.6:
            dominant = "distress"
        elif sentiment > 0.3:
            dominant = "joy"
        elif sentiment < -0.3:
            dominant = "sadness"
        else:
            dominant = "neutral"

        if dominant == "neutral" and confusion_hits:
            dominant = "distress"
        if dominant == "sadness" and emotion_scores.get("anger", 0) > 0.35:
            dominant = "anger"
        if repair_hits and dominant in {"sadness", "distress"} and sentiment > -0.15:
            dominant = "neutral"

        confidence = min(
            0.97,
            0.22
            + 0.07 * len(cues)
            + 0.05 * len([k for k, v in need_hits.items() if v > 0])
            + 0.04 * len(filtered_emotions),
        ) if cues or need_hits or filtered_emotions else 0.2

        metadata = {
            "need_hits": need_hits,
            "exclamation_count": exclamations,
            "question_count": questions,
            "ellipsis_count": ellipsis,
            "uppercase_ratio": round(uppercase_ratio, 4),
            "hedge_hits": hedge_hits,
            "softener_hits": softener_hits,
            "intensifier_hits": intensifier_hits,
            "exhaustion_hits": exhaustion_hits,
            "confusion_hits": confusion_hits,
            "repair_hits": repair_hits,
        }

        return PerceptionSignal(
            text=text,
            dominant_emotion=dominant,
            emotion_scores={k: min(1.0, v) for k, v in emotion_scores.items()},
            detected_needs=sorted(need_hits, key=need_hits.get, reverse=True),
            urgency=min(1.0, urgency),
            sentiment=max(-1.0, min(1.0, sentiment)),
            threat_score=min(1.0, threat),
            support_score=min(1.0, support),
            confidence=confidence,
            cues=list(dict.fromkeys(cues))[:18],
            metadata=metadata,
        )

    def _uppercase_ratio(self, text: str) -> float:
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return 0.0
        uppers = [c for c in letters if c.isupper()]
        return len(uppers) / max(len(letters), 1)


recognizer = EmotionNeedRecognizer()
