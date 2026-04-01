#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from runtime.heart_bridge import runtime_heart

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
EPISODIC_DB = VECTORBRAIN_HOME / "memory" / "episodic_memory.db"
STATE_DIR = VECTORBRAIN_HOME / "state"
TRACE_DIR = STATE_DIR / "openclaw_preprocess"
TRACE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PreprocessDecision:
    ok: bool
    mode: str
    trace_id: str
    reason: str = ""
    degraded: bool = False
    prepend_prompt: str = ""
    append_prompt: str = ""
    memory_context: list | None = None
    response_guidance: Dict[str, Any] | None = None
    direct_response: Optional[str] = None
    meta: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data["memory_context"] is None:
            data["memory_context"] = []
        if data["response_guidance"] is None:
            data["response_guidance"] = {}
        if data["meta"] is None:
            data["meta"] = {}
        return data


class UnifiedOpenClawBridge:
    def __init__(self) -> None:
        self.episodic_db = EPISODIC_DB

    def preprocess(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        trace_id = f"vb_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        try:
            normalized = self._normalize_payload(payload)
            text = normalized["text"]
            session_id = normalized.get("session_id")
            recent_memory = self._load_recent_memory(session_id=session_id, limit=3)
            heart_packet = runtime_heart.build_preprocess_packet(
                text,
                session_id=session_id,
                write_memory=False,
                tags=["openclaw", "unified_bridge", normalized.get("channel") or "unknown"],
            )
            decision = self._decide(normalized, heart_packet, recent_memory, trace_id)
            record = {
                "trace_id": trace_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "request": normalized,
                "decision": decision,
            }
            self._persist_trace(trace_id, record)
            self._save_inbound_episode(normalized, trace_id, decision.get("mode", "unknown"))
            return decision
        except Exception as e:
            decision = PreprocessDecision(
                ok=False,
                mode="fail_open",
                trace_id=trace_id,
                reason=f"bridge_exception: {e}",
                degraded=True,
                response_guidance={"fallback": True},
                meta={"error": str(e)},
            ).to_dict()
            self._persist_trace(trace_id, {
                "trace_id": trace_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "request": payload,
                "decision": decision,
            })
            return decision

    def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
        text = (
            payload.get("text")
            or payload.get("content")
            or raw.get("content")
            or raw.get("text")
            or ""
        )
        text = str(text).strip()
        return {
            "session_id": payload.get("session_id") or raw.get("session_id") or payload.get("channel_id") or "unknown_session",
            "channel": payload.get("channel") or raw.get("channel") or "unknown",
            "channel_id": payload.get("channel_id") or raw.get("channelId") or payload.get("session_id") or "unknown_channel",
            "message_id": payload.get("message_id") or raw.get("message_id") or raw.get("id"),
            "sender_id": payload.get("sender_id") or raw.get("senderId") or raw.get("sender_id") or "unknown_sender",
            "sender_name": payload.get("sender_name") or raw.get("senderName") or raw.get("sender_name") or "",
            "text": text,
            "raw": raw or payload,
            "context": payload.get("context") if isinstance(payload.get("context"), dict) else {},
        }

    def _load_recent_memory(self, session_id: Optional[str], limit: int = 3) -> list:
        if not self.episodic_db.exists():
            return []
        conn = sqlite3.connect(str(self.episodic_db))
        try:
            cursor = conn.cursor()
            if session_id:
                like = f'%"session_id": "{session_id}"%'
                cursor.execute(
                    """
                    SELECT timestamp, event_type, content, metadata
                    FROM episodes
                    WHERE metadata LIKE ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (like, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT timestamp, event_type, content, metadata
                    FROM episodes
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            rows = cursor.fetchall()
        finally:
            conn.close()
        result = []
        for ts, event_type, content, metadata in reversed(rows):
            try:
                meta = json.loads(metadata) if metadata else {}
            except Exception:
                meta = {"raw_metadata": metadata}
            result.append({
                "timestamp": ts,
                "event_type": event_type,
                "content": content,
                "metadata": meta,
            })
        return result

    def _decide(self, normalized: Dict[str, Any], heart_packet: Dict[str, Any], recent_memory: list, trace_id: str) -> Dict[str, Any]:
        text = normalized["text"]
        lower = text.lower()
        guidance = {
            "heart": heart_packet.get("reply_guidance", {}),
            "risk_flags": heart_packet.get("risk_flags", {}),
            "composer": heart_packet.get("composer", {}),
        }
        prepend = (heart_packet.get("assistant_prompt_prefix") or "").strip()
        append = (heart_packet.get("assistant_prompt_append") or "").strip()

        if not text:
            return PreprocessDecision(
                ok=False,
                mode="fail_open",
                trace_id=trace_id,
                reason="empty_text",
                degraded=True,
                response_guidance=guidance,
            ).to_dict()

        direct_keywords = ["桥测试", "bridge status", "vectorbrain status", "vb status", "你是谁"]
        if any(k in lower for k in direct_keywords) or text.startswith("/vb"):
            direct_response = self._build_direct_response(normalized, recent_memory)
            return PreprocessDecision(
                ok=True,
                mode="direct_handle",
                trace_id=trace_id,
                reason="direct_keyword_match",
                prepend_prompt=prepend,
                append_prompt=append,
                memory_context=recent_memory,
                response_guidance=guidance,
                direct_response=direct_response,
                meta={"decision_source": "rule", "bridge": "unified_openclaw"},
            ).to_dict()

        protective = bool(heart_packet.get("risk_flags", {}).get("protective_mode"))
        stress = float(heart_packet.get("risk_flags", {}).get("stress") or 0.0)
        threat = float(heart_packet.get("risk_flags", {}).get("threat_score") or 0.0)
        if protective or stress >= 0.45 or threat >= 0.35 or recent_memory:
            reason_bits = []
            if protective:
                reason_bits.append("protective_mode")
            if stress >= 0.45:
                reason_bits.append(f"stress={stress:.2f}")
            if threat >= 0.35:
                reason_bits.append(f"threat={threat:.2f}")
            if recent_memory:
                reason_bits.append(f"recent_memory={len(recent_memory)}")
            return PreprocessDecision(
                ok=True,
                mode="enrich_prompt",
                trace_id=trace_id,
                reason=", ".join(reason_bits) or "heart_or_memory_enrichment",
                prepend_prompt=prepend,
                append_prompt=append,
                memory_context=recent_memory,
                response_guidance=guidance,
                meta={"decision_source": "heart+memory", "bridge": "unified_openclaw"},
            ).to_dict()

        return PreprocessDecision(
            ok=True,
            mode="pass_through",
            trace_id=trace_id,
            reason="default_pass_through",
            memory_context=recent_memory,
            response_guidance=guidance,
            meta={"decision_source": "default", "bridge": "unified_openclaw"},
        ).to_dict()

    def _build_direct_response(self, normalized: Dict[str, Any], recent_memory: list) -> str:
        pieces = [
            "VectorBrain Unified Bridge 在线。",
            f"channel={normalized.get('channel')}",
            f"session={normalized.get('session_id')}",
            f"recent_memory={len(recent_memory)}",
        ]
        if normalized.get("text", "").startswith("/vb"):
            pieces.append(f"echo={normalized['text']}")
        return " | ".join(pieces)

    def _persist_trace(self, trace_id: str, data: Dict[str, Any]) -> None:
        path = TRACE_DIR / f"{trace_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_inbound_episode(self, normalized: Dict[str, Any], trace_id: str, mode: str) -> None:
        if not self.episodic_db.exists():
            return
        conn = sqlite3.connect(str(self.episodic_db))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO episodes (timestamp, worker_id, event_type, content, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "openclaw_unified_bridge",
                    "openclaw_preprocess_inbound",
                    normalized.get("text", ""),
                    json.dumps({
                        "trace_id": trace_id,
                        "mode": mode,
                        "session_id": normalized.get("session_id"),
                        "channel": normalized.get("channel"),
                        "channel_id": normalized.get("channel_id"),
                        "sender_id": normalized.get("sender_id"),
                        "message_id": normalized.get("message_id"),
                    }, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()


unified_bridge = UnifiedOpenClawBridge()
