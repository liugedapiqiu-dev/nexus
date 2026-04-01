from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .state import HeartState, PerceptionSignal, PolicyDecision, RegulationDecision


class EmotionalMemoryStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else Path.home() / ".vectorbrain" / "memory" / "heart_memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS heart_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT,
                timestamp TEXT NOT NULL,
                user_text TEXT NOT NULL,
                dominant_emotion TEXT,
                needs_json TEXT,
                protective_mode TEXT,
                trajectory_label TEXT,
                state_json TEXT NOT NULL,
                policy_json TEXT NOT NULL,
                signal_json TEXT NOT NULL,
                regulation_json TEXT NOT NULL,
                tags_json TEXT,
                summary_text TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS heart_session_summaries (
                session_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                event_count INTEGER NOT NULL,
                dominant_emotion TEXT,
                protective_mode TEXT,
                trajectory_label TEXT,
                avg_valence REAL,
                avg_stress REAL,
                avg_trust REAL,
                top_needs_json TEXT,
                summary_json TEXT,
                last_state_json TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS heart_identity_profiles (
                profile_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                session_count INTEGER NOT NULL,
                event_count INTEGER NOT NULL,
                dominant_emotion TEXT,
                protective_mode TEXT,
                trajectory_label TEXT,
                avg_valence REAL,
                avg_stress REAL,
                avg_trust REAL,
                top_needs_json TEXT,
                top_modes_json TEXT,
                top_trajectories_json TEXT,
                summary_json TEXT,
                last_session_id TEXT
            )
            """
        )
        columns = {row['name'] for row in cur.execute("PRAGMA table_info(heart_events)").fetchall()}
        if "trajectory_label" not in columns:
            cur.execute("ALTER TABLE heart_events ADD COLUMN trajectory_label TEXT")
        if "summary_text" not in columns:
            cur.execute("ALTER TABLE heart_events ADD COLUMN summary_text TEXT")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_heart_session_time ON heart_events(session_id, timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_heart_emotion ON heart_events(dominant_emotion)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_heart_mode ON heart_events(protective_mode)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_heart_trajectory ON heart_events(trajectory_label)")

        conn.commit()
        conn.close()

    def _infer_profile_id(self, session_id: Optional[str]) -> str:
        if not session_id:
            return "global_default"

        text = str(session_id)
        for pattern in [r"ou_[A-Za-z0-9_]+", r"oc_[A-Za-z0-9_]+", r"\+[0-9]{6,}"]:
            m = re.search(pattern, text)
            if m:
                return m.group(0)

        parts = [p for p in re.split(r"[:/\s]+", text) if p]
        if parts:
            tail = parts[-1]
            if len(tail) >= 6 and tail not in {"heartbeat", "main", "default"}:
                return tail[:128]
        return text[:128]

    def write_event(
        self,
        *,
        session_id: Optional[str],
        user_text: str,
        signal: PerceptionSignal,
        state: HeartState,
        regulation: RegulationDecision,
        policy: PolicyDecision,
        tags: Optional[List[str]] = None,
    ) -> str:
        event_id = f"heart_{uuid.uuid4().hex[:12]}"
        summary_text = regulation.summary or f"mode={state.protective_mode}; emotion={signal.dominant_emotion}; needs={','.join(signal.detected_needs[:3]) or 'none'}"
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO heart_events (
                event_id, session_id, timestamp, user_text, dominant_emotion,
                needs_json, protective_mode, trajectory_label, state_json, policy_json, signal_json,
                regulation_json, tags_json, summary_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                session_id,
                datetime.utcnow().isoformat(),
                user_text,
                signal.dominant_emotion,
                json.dumps(signal.detected_needs, ensure_ascii=False),
                state.protective_mode,
                state.trajectory_label,
                json.dumps(state.snapshot(), ensure_ascii=False),
                json.dumps(policy.to_dict(), ensure_ascii=False),
                json.dumps(signal.to_dict(), ensure_ascii=False),
                json.dumps(regulation.to_dict(), ensure_ascii=False),
                json.dumps(tags or [], ensure_ascii=False),
                summary_text,
            ),
        )
        if session_id:
            self._update_session_summary(conn, session_id)
            self._update_profile_summary(conn, self._infer_profile_id(session_id))
        self._update_profile_summary(conn, "global_default")
        conn.commit()
        conn.close()
        return event_id

    def recent(self, session_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        if session_id:
            cur.execute(
                "SELECT * FROM heart_events WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit),
            )
        else:
            cur.execute("SELECT * FROM heart_events ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = f"%{query}%"
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM heart_events
            WHERE user_text LIKE ? OR dominant_emotion LIKE ? OR needs_json LIKE ? OR tags_json LIKE ? OR summary_text LIKE ?
            ORDER BY timestamp DESC LIMIT ?
            """,
            (q, q, q, q, q, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def latest_state(self, session_id: str) -> Optional[HeartState]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT state_json FROM heart_events WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1",
            (session_id,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        try:
            return HeartState.from_dict(json.loads(row["state_json"] or "{}"))
        except Exception:
            return None

    def session_summary(self, session_id: str) -> Dict[str, Any]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM heart_session_summaries WHERE session_id = ?", (session_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"session_id": session_id, "exists": False}
        data = dict(row)
        for key in ("top_needs_json", "summary_json", "last_state_json"):
            try:
                data[key[:-5] if key.endswith("_json") else key] = json.loads(data.get(key) or "{}")
            except Exception:
                data[key[:-5] if key.endswith("_json") else key] = {}
        data["exists"] = True
        return data

    def profile_summary(self, profile_id: str) -> Dict[str, Any]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM heart_identity_profiles WHERE profile_id = ?", (profile_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"profile_id": profile_id, "exists": False}
        data = dict(row)
        for key in ("top_needs_json", "top_modes_json", "top_trajectories_json", "summary_json"):
            try:
                data[key[:-5] if key.endswith("_json") else key] = json.loads(data.get(key) or "{}")
            except Exception:
                data[key[:-5] if key.endswith("_json") else key] = {}
        data["exists"] = True
        return data

    def build_context_brief(self, session_id: str) -> Dict[str, Any]:
        summary = self.session_summary(session_id)
        profile_id = self._infer_profile_id(session_id)
        profile = self.profile_summary(profile_id)

        if not summary.get("exists"):
            base = {"brief": "no_emotional_history", "summary": summary}
        else:
            last_state = summary.get("last_state") or {}
            needs = summary.get("top_needs") or []
            needs_text = ", ".join(needs[:3]) if isinstance(needs, list) else ""
            brief = (
                f"mode={summary.get('protective_mode')}; "
                f"trajectory={summary.get('trajectory_label')}; "
                f"emotion={summary.get('dominant_emotion')}; "
                f"avg_stress={summary.get('avg_stress', 0):.2f}; "
                f"recovery={last_state.get('recovery_score', 0):.2f}; "
                f"top_needs={needs_text or 'none'}"
            )
            base = {"brief": brief, "summary": summary}

        if profile.get("exists"):
            p_needs = profile.get("top_needs") or []
            profile_brief = (
                f"profile={profile_id}; "
                f"long_arc_emotion={profile.get('dominant_emotion')}; "
                f"long_arc_mode={profile.get('protective_mode')}; "
                f"long_arc_trajectory={profile.get('trajectory_label')}; "
                f"sessions={profile.get('session_count', 0)}; "
                f"events={profile.get('event_count', 0)}; "
                f"avg_stress={profile.get('avg_stress', 0):.2f}; "
                f"avg_trust={profile.get('avg_trust', 0):.2f}; "
                f"top_needs={', '.join(p_needs[:3]) or 'none'}"
            )
            base["profile_id"] = profile_id
            base["profile"] = profile
            base["profile_brief"] = profile_brief
            if base["brief"] == "no_emotional_history":
                base["brief"] = f"no_emotional_history; {profile_brief}"
            else:
                base["brief"] = f"{base['brief']}; {profile_brief}"
        return base

    def profile_state_seed(self, session_id: Optional[str]) -> Dict[str, Any]:
        profile_id = self._infer_profile_id(session_id)
        profile = self.profile_summary(profile_id)
        if not profile.get("exists"):
            return {}
        summary = profile.get("summary") or {}
        return {
            "session_id": session_id,
            "dominant_emotion": summary.get("dominant_emotion") or "neutral",
            "emotional_baseline": float(summary.get("avg_valence", 0.0) or 0.0),
            "trust": max(0.2, min(0.95, float(summary.get("avg_trust", 0.5) or 0.5))),
            "stress": max(0.0, min(1.0, float(summary.get("avg_stress", 0.0) or 0.0) * 0.7)),
            "protective_mode": summary.get("protective_mode") or "normal",
            "trajectory_label": summary.get("trajectory_label") or "steady",
            "active_needs": list((summary.get("top_needs") or [])[:3]),
            "meta": {
                "seeded_from_profile": True,
                "profile_id": profile_id,
                "long_term_profile": summary,
            },
        }

    def summarize_recent(self, session_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        rows = self.recent(session_id=session_id, limit=limit)
        emotions: Dict[str, int] = {}
        modes: Dict[str, int] = {}
        needs: Dict[str, int] = {}
        trajectories: Dict[str, int] = {}
        stresses: List[float] = []
        for row in rows:
            emotions[row.get("dominant_emotion") or "unknown"] = emotions.get(row.get("dominant_emotion") or "unknown", 0) + 1
            modes[row.get("protective_mode") or "unknown"] = modes.get(row.get("protective_mode") or "unknown", 0) + 1
            trajectories[row.get("trajectory_label") or "unknown"] = trajectories.get(row.get("trajectory_label") or "unknown", 0) + 1
            try:
                for need in json.loads(row.get("needs_json") or "[]"):
                    needs[need] = needs.get(need, 0) + 1
            except json.JSONDecodeError:
                pass
            try:
                state = json.loads(row.get("state_json") or "{}")
                if isinstance(state.get("stress"), (int, float)):
                    stresses.append(float(state["stress"]))
            except Exception:
                pass
        return {
            "count": len(rows),
            "top_emotions": sorted(emotions.items(), key=lambda x: x[1], reverse=True),
            "top_modes": sorted(modes.items(), key=lambda x: x[1], reverse=True),
            "top_needs": sorted(needs.items(), key=lambda x: x[1], reverse=True),
            "top_trajectories": sorted(trajectories.items(), key=lambda x: x[1], reverse=True),
            "avg_stress": round(sum(stresses) / len(stresses), 4) if stresses else None,
        }

    def _update_session_summary(self, conn: sqlite3.Connection, session_id: str) -> None:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM heart_events WHERE session_id = ? ORDER BY timestamp DESC LIMIT 12",
            (session_id,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        if not rows:
            return

        emotions: Dict[str, int] = {}
        modes: Dict[str, int] = {}
        trajectories: Dict[str, int] = {}
        needs: Dict[str, int] = {}
        valences: List[float] = []
        stresses: List[float] = []
        trusts: List[float] = []
        last_state: Dict[str, Any] = {}

        for row in rows:
            emotions[row.get("dominant_emotion") or "unknown"] = emotions.get(row.get("dominant_emotion") or "unknown", 0) + 1
            modes[row.get("protective_mode") or "unknown"] = modes.get(row.get("protective_mode") or "unknown", 0) + 1
            trajectories[row.get("trajectory_label") or "unknown"] = trajectories.get(row.get("trajectory_label") or "unknown", 0) + 1
            try:
                for need in json.loads(row.get("needs_json") or "[]"):
                    needs[need] = needs.get(need, 0) + 1
            except Exception:
                pass
            try:
                state = json.loads(row.get("state_json") or "{}")
            except Exception:
                state = {}
            if not last_state:
                last_state = state
            for key, bucket in (("valence", valences), ("stress", stresses), ("trust", trusts)):
                if isinstance(state.get(key), (int, float)):
                    bucket.append(float(state[key]))

        top_needs = [k for k, _ in sorted(needs.items(), key=lambda item: item[1], reverse=True)[:5]]
        summary = {
            "dominant_emotion": max(emotions, key=emotions.get),
            "protective_mode": max(modes, key=modes.get),
            "trajectory_label": max(trajectories, key=trajectories.get),
            "avg_valence": round(sum(valences) / len(valences), 4) if valences else 0.0,
            "avg_stress": round(sum(stresses) / len(stresses), 4) if stresses else 0.0,
            "avg_trust": round(sum(trusts) / len(trusts), 4) if trusts else 0.0,
            "top_needs": top_needs,
            "recent_event_summaries": [r.get("summary_text") for r in rows[:3]],
        }

        cur.execute(
            """
            INSERT INTO heart_session_summaries (
                session_id, updated_at, event_count, dominant_emotion, protective_mode, trajectory_label,
                avg_valence, avg_stress, avg_trust, top_needs_json, summary_json, last_state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                event_count = excluded.event_count,
                dominant_emotion = excluded.dominant_emotion,
                protective_mode = excluded.protective_mode,
                trajectory_label = excluded.trajectory_label,
                avg_valence = excluded.avg_valence,
                avg_stress = excluded.avg_stress,
                avg_trust = excluded.avg_trust,
                top_needs_json = excluded.top_needs_json,
                summary_json = excluded.summary_json,
                last_state_json = excluded.last_state_json
            """,
            (
                session_id,
                datetime.utcnow().isoformat(),
                len(rows),
                summary["dominant_emotion"],
                summary["protective_mode"],
                summary["trajectory_label"],
                summary["avg_valence"],
                summary["avg_stress"],
                summary["avg_trust"],
                json.dumps(top_needs, ensure_ascii=False),
                json.dumps(summary, ensure_ascii=False),
                json.dumps(last_state, ensure_ascii=False),
            ),
        )

    def _update_profile_summary(self, conn: sqlite3.Connection, profile_id: str) -> None:
        cur = conn.cursor()
        if profile_id == "global_default":
            cur.execute("SELECT * FROM heart_events ORDER BY timestamp DESC LIMIT 80")
            rows = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT COUNT(DISTINCT session_id) AS c FROM heart_events WHERE session_id IS NOT NULL AND session_id != ''")
            session_count = int((cur.fetchone() or {"c": 0})["c"])
        else:
            like = f"%{profile_id}%"
            cur.execute(
                "SELECT * FROM heart_events WHERE session_id = ? OR session_id LIKE ? ORDER BY timestamp DESC LIMIT 80",
                (profile_id, like),
            )
            rows = [dict(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT COUNT(DISTINCT session_id) AS c FROM heart_events WHERE session_id = ? OR session_id LIKE ?",
                (profile_id, like),
            )
            session_count = int((cur.fetchone() or {"c": 0})["c"])

        if not rows:
            return

        emotions: Dict[str, int] = {}
        modes: Dict[str, int] = {}
        trajectories: Dict[str, int] = {}
        needs: Dict[str, int] = {}
        valences: List[float] = []
        stresses: List[float] = []
        trusts: List[float] = []
        last_session_id = rows[0].get("session_id")

        for row in rows:
            emotions[row.get("dominant_emotion") or "unknown"] = emotions.get(row.get("dominant_emotion") or "unknown", 0) + 1
            modes[row.get("protective_mode") or "unknown"] = modes.get(row.get("protective_mode") or "unknown", 0) + 1
            trajectories[row.get("trajectory_label") or "unknown"] = trajectories.get(row.get("trajectory_label") or "unknown", 0) + 1
            try:
                for need in json.loads(row.get("needs_json") or "[]"):
                    needs[need] = needs.get(need, 0) + 1
            except Exception:
                pass
            try:
                state = json.loads(row.get("state_json") or "{}")
            except Exception:
                state = {}
            for key, bucket in (("valence", valences), ("stress", stresses), ("trust", trusts)):
                if isinstance(state.get(key), (int, float)):
                    bucket.append(float(state[key]))

        top_needs = [k for k, _ in sorted(needs.items(), key=lambda item: item[1], reverse=True)[:6]]
        top_modes = [k for k, _ in sorted(modes.items(), key=lambda item: item[1], reverse=True)[:4]]
        top_trajectories = [k for k, _ in sorted(trajectories.items(), key=lambda item: item[1], reverse=True)[:4]]
        summary = {
            "profile_id": profile_id,
            "dominant_emotion": max(emotions, key=emotions.get),
            "protective_mode": max(modes, key=modes.get),
            "trajectory_label": max(trajectories, key=trajectories.get),
            "avg_valence": round(sum(valences) / len(valences), 4) if valences else 0.0,
            "avg_stress": round(sum(stresses) / len(stresses), 4) if stresses else 0.0,
            "avg_trust": round(sum(trusts) / len(trusts), 4) if trusts else 0.0,
            "top_needs": top_needs,
            "top_modes": top_modes,
            "top_trajectories": top_trajectories,
            "recent_event_summaries": [r.get("summary_text") for r in rows[:5]],
            "long_term_summary": (
                f"长期画像：更常见情绪为 {max(emotions, key=emotions.get)}，常见保护模式 {max(modes, key=modes.get)}，"
                f"轨迹偏向 {max(trajectories, key=trajectories.get)}，主要需要 {', '.join(top_needs[:3]) or 'none'}。"
            ),
        }

        cur.execute(
            """
            INSERT INTO heart_identity_profiles (
                profile_id, updated_at, session_count, event_count, dominant_emotion, protective_mode,
                trajectory_label, avg_valence, avg_stress, avg_trust, top_needs_json, top_modes_json,
                top_trajectories_json, summary_json, last_session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                session_count = excluded.session_count,
                event_count = excluded.event_count,
                dominant_emotion = excluded.dominant_emotion,
                protective_mode = excluded.protective_mode,
                trajectory_label = excluded.trajectory_label,
                avg_valence = excluded.avg_valence,
                avg_stress = excluded.avg_stress,
                avg_trust = excluded.avg_trust,
                top_needs_json = excluded.top_needs_json,
                top_modes_json = excluded.top_modes_json,
                top_trajectories_json = excluded.top_trajectories_json,
                summary_json = excluded.summary_json,
                last_session_id = excluded.last_session_id
            """,
            (
                profile_id,
                datetime.utcnow().isoformat(),
                session_count,
                len(rows),
                summary["dominant_emotion"],
                summary["protective_mode"],
                summary["trajectory_label"],
                summary["avg_valence"],
                summary["avg_stress"],
                summary["avg_trust"],
                json.dumps(top_needs, ensure_ascii=False),
                json.dumps(top_modes, ensure_ascii=False),
                json.dumps(top_trajectories, ensure_ascii=False),
                json.dumps(summary, ensure_ascii=False),
                last_session_id,
            ),
        )


memory_store = EmotionalMemoryStore()
