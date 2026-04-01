#!/usr/bin/env python3
"""
会话历史自动归档系统（增强版）
将 OpenClaw 会话 jsonl 可靠归档到 VectorBrain 的 episodic_memory.db

核心改进：
1. 真正幂等：基于 logical_session_id + record_fingerprint 去重
2. 真正增量：文件变化后可重扫全文件，但只插入未归档记录
3. 可恢复：使用 archive_ingest_records 作为数据库级去重注册表
4. 可跳过：文件哈希未变化时直接跳过
5. 可追溯：详细 run_summary / success / error 日志
"""

import os
import sys
import json
import sqlite3
import hashlib
import fcntl
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

def _get_dynamic_paths():
    """动态获取路径，支持从 nexus_config 读取"""
    HOME = Path.home()
    VECTORBRAIN_DIR = HOME / ".vectorbrain"
    OPENCLAW_DIR = HOME / ".openclaw"

    # 尝试从 nexus_config 读取
    nexus_config_path = VECTORBRAIN_DIR / ".nexus_config.json"
    if nexus_config_path.exists():
        try:
            with open(nexus_config_path) as f:
                config = json.load(f)
            if "paths" in config:
                return (
                    Path(config["paths"]["openclaw"]["sessions"]),
                    Path(config["paths"]["vectorbrain"]["memory"]) / "episodic_memory.db",
                    Path(config["paths"]["vectorbrain"]["root"]) / "archive_state.json",
                    Path(config["paths"]["vectorbrain"]["root"]) / "archive_log.jsonl",
                )
        except:
            pass

    # 默认路径
    return (
        OPENCLAW_DIR / "agents" / "main" / "sessions",  # SESSIONS_DIR
        VECTORBRAIN_DIR / "memory" / "episodic_memory.db",  # EPISODIC_DB
        VECTORBRAIN_DIR / "archive_state.json",  # ARCHIVE_STATE_FILE
        VECTORBRAIN_DIR / "archive_log.jsonl",  # ARCHIVE_LOG_FILE
    )

SESSIONS_DIR, EPISODIC_DB, ARCHIVE_STATE_FILE, ARCHIVE_LOG_FILE = _get_dynamic_paths()
LOCK_FILE = Path('/tmp/session_archiver.lock')


class SessionArchiver:
    def __init__(self):
        self.archived_sessions = self._load_archive_state()
        self.session_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "inserted_total": 0,
            "seen_records_total": 0,
            "duplicate_records_total": 0,
            "bootstrapped_registry": 0,
        }

    # ---------------------------------------------------------------------
    # state / logs
    # ---------------------------------------------------------------------
    def _load_archive_state(self) -> Dict[str, Any]:
        if ARCHIVE_STATE_FILE.exists():
            try:
                with open(ARCHIVE_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    return state.get("archived_sessions", {})
            except Exception as e:
                print(f"⚠️ 读取状态文件失败：{e}")
        return {}

    def _save_archive_state(self):
        state = {
            "last_updated": datetime.now().isoformat(),
            "archived_sessions": self.archived_sessions,
            "stats": self.session_stats,
        }
        try:
            with open(ARCHIVE_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存状态文件失败：{e}")

    def _log_archive_event(self, event_type: str, session_id: str, details: str):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "session_id": session_id,
            "details": details,
        }
        try:
            with open(ARCHIVE_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ 写入日志失败：{e}")

    # ---------------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------------
    def _logical_session_id(self, session_file: Path) -> str:
        # 统一把 xxx.jsonl / xxx.jsonl.reset.xxx / xxx.jsonl.deleted.xxx 归到同一个逻辑会话 ID
        return session_file.name.split('.jsonl')[0]

    def _get_session_hash(self, file_path: Path) -> str:
        # 全文件哈希，保证变化判断准确
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def _canonical_json(self, record: Dict[str, Any]) -> str:
        return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _record_fingerprint(self, logical_session_id: str, record: Dict[str, Any], raw_line: str) -> str:
        # 优先使用稳定 record id；没有则使用规范化 JSON 哈希
        record_id = record.get("id")
        if record_id:
            return f"id:{logical_session_id}:{record_id}"
        canonical = self._canonical_json(record) if isinstance(record, dict) else raw_line.strip()
        digest = hashlib.md5(canonical.encode('utf-8')).hexdigest()
        return f"hash:{logical_session_id}:{digest}"

    def _should_archive(self, session_file: Path) -> bool:
        logical_session_id = self._logical_session_id(session_file)
        current_hash = self._get_session_hash(session_file)
        archived_info = self.archived_sessions.get(logical_session_id)
        if archived_info and archived_info.get("file_hash") == current_hash:
            print(f"  ⏭️  已归档且无更新：{logical_session_id}")
            self.session_stats["skipped"] += 1
            return False
        if archived_info:
            print(f"  📝 检测到更新，执行真增量归档：{logical_session_id}")
        return True

    def _parse_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        messages = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    raw = line.rstrip("\n")
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        mode = os.getenv("SESSION_ARCHIVER_MODE", "raw").strip().lower()
                        if mode == "raw":
                            messages.append({
                                "line_num": line_num,
                                "record": record,
                                "raw_line": raw,
                            })
                        else:
                            if record.get("type") != "message":
                                continue
                            role = (record.get("message", {}) or {}).get("role")
                            if role not in ("user", "assistant"):
                                continue
                            messages.append({
                                "line_num": line_num,
                                "record": record,
                                "raw_line": raw,
                            })
                    except json.JSONDecodeError as e:
                        print(f"    ⚠️  第{line_num}行 JSON 解析失败：{e}")
        except Exception as e:
            print(f"  ❌ 读取文件失败：{e}")
        return messages

    # ---------------------------------------------------------------------
    # db bootstrap / dedupe registry
    # ---------------------------------------------------------------------
    def _ensure_support_tables(self, conn: sqlite3.Connection):
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS archive_ingest_records (
                logical_session_id TEXT NOT NULL,
                record_fingerprint TEXT NOT NULL,
                record_id TEXT,
                line_num INTEGER,
                source_file TEXT,
                source_file_hash TEXT,
                archived_at TEXT NOT NULL,
                PRIMARY KEY (logical_session_id, record_fingerprint)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_archive_ingest_source_file ON archive_ingest_records(source_file)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_archive_ingest_record_id ON archive_ingest_records(record_id)"
        )
        conn.commit()

    def _bootstrap_registry_from_existing(self, conn: sqlite3.Connection):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archive_ingest_records")
        existing_registry = cursor.fetchone()[0]
        if existing_registry > 0:
            return

        print("🔧 首次启动：从已有归档记录引导去重注册表...")
        inserted = 0
        scan_cursor = conn.cursor()
        scan_cursor.execute(
            "SELECT metadata FROM episodes WHERE worker_id IN ('session_archiver', 'session_archiver_backfill')"
        )
        rows = scan_cursor.fetchall()
        for (meta_text,) in rows:
            if not meta_text:
                continue
            try:
                meta = json.loads(meta_text)
            except Exception:
                continue

            logical_session_id = meta.get("session_id")
            source_file = meta.get("session_file") or logical_session_id
            record_id = meta.get("record_id") or meta.get("message_id")
            line_num = meta.get("line_num")
            source_file_hash = meta.get("source_file_hash")

            if not logical_session_id:
                continue

            if record_id:
                fingerprint = f"id:{logical_session_id}:{record_id}"
            else:
                # 对历史旧记录，没有 raw_line 就退化成 line_num 粗粒度指纹
                if line_num is None:
                    continue
                fingerprint = f"legacy-line:{logical_session_id}:{line_num}"

            cursor.execute(
                """
                INSERT OR IGNORE INTO archive_ingest_records
                (logical_session_id, record_fingerprint, record_id, line_num, source_file, source_file_hash, archived_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    logical_session_id,
                    fingerprint,
                    record_id,
                    line_num,
                    source_file,
                    source_file_hash,
                    datetime.now().isoformat(),
                )
            )
            inserted += cursor.rowcount

        conn.commit()
        self.session_stats["bootstrapped_registry"] = inserted
        print(f"✅ 去重注册表引导完成：{inserted} 条")

    # ---------------------------------------------------------------------
    # content extraction / insert
    # ---------------------------------------------------------------------
    def _extract_content(self, record: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
        message_data = record.get("message", {}) or {}
        role = message_data.get("role", "unknown")
        extra_meta = {}

        if record.get("type") == "message":
            content_list = message_data.get("content", [])
            if isinstance(content_list, list):
                parts = []
                for item in content_list:
                    if isinstance(item, dict):
                        if item.get("type") == "text" and item.get("text"):
                            parts.append(item.get("text"))
                        elif item.get("type") and item.get("type") != "text":
                            parts.append(f"[{item.get('type')}]")
                content_text = " ".join(parts).strip()
            else:
                content_text = str(content_list).strip()
            event_type = f"message:{role}"
        else:
            event_type = f"raw:{record.get('type', 'unknown')}"
            content_text = self._canonical_json(record)[:10000]

        return content_text, event_type, extra_meta

    def _insert_to_db(self, session_file: Path, messages: List[Dict[str, Any]], file_hash: str):
        logical_session_id = self._logical_session_id(session_file)
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = sqlite3.connect(EPISODIC_DB)
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")

            self._ensure_support_tables(conn)
            self._bootstrap_registry_from_existing(conn)

            inserted_count = 0
            duplicate_count = 0

            for msg in messages:
                record = msg["record"]
                line_num = msg["line_num"]
                raw_line = msg["raw_line"]

                try:
                    content_text, event_type, extra_meta = self._extract_content(record)
                    if not content_text.strip():
                        continue

                    record_id = record.get("id")
                    fingerprint = self._record_fingerprint(logical_session_id, record, raw_line)

                    # 先尝试写入去重注册表；如果已存在，则跳过主表插入
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO archive_ingest_records
                        (logical_session_id, record_fingerprint, record_id, line_num, source_file, source_file_hash, archived_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            logical_session_id,
                            fingerprint,
                            record_id,
                            line_num,
                            session_file.name,
                            file_hash,
                            datetime.now().isoformat(),
                        )
                    )
                    if cursor.rowcount == 0:
                        duplicate_count += 1
                        continue

                    metadata = {
                        "session_id": logical_session_id,
                        "session_file": session_file.name,
                        "record_id": record_id,
                        "line_num": line_num,
                        "role": (record.get("message", {}) or {}).get("role", "unknown"),
                        "timestamp": record.get("timestamp"),
                        "parent_id": record.get("parentId"),
                        "source_file_hash": file_hash,
                        "record_type": record.get("type"),
                        "fingerprint": fingerprint,
                        **extra_meta,
                    }

                    cursor.execute(
                        """
                        INSERT INTO episodes (timestamp, worker_id, event_type, content, metadata, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.get("timestamp", datetime.now().isoformat()),
                            "session_archiver",
                            event_type,
                            content_text[:10000],
                            json.dumps(metadata, ensure_ascii=False),
                            datetime.now().isoformat(),
                        )
                    )
                    inserted_count += 1

                except Exception as e:
                    print(f"    ⚠️  插入第{line_num}条消息失败：{e}")

            conn.commit()

            self.archived_sessions[logical_session_id] = {
                "archived_at": datetime.now().isoformat(),
                "message_count": inserted_count,
                "seen_records": len(messages),
                "duplicate_records": duplicate_count,
                "file_hash": file_hash,
                "source_file": session_file.name,
            }

            self.session_stats["success"] += 1
            self.session_stats["inserted_total"] += inserted_count
            self.session_stats["seen_records_total"] += len(messages)
            self.session_stats["duplicate_records_total"] += duplicate_count
            self._log_archive_event(
                "success",
                logical_session_id,
                f"归档 {inserted_count} 条；重复跳过 {duplicate_count} 条；读取 {len(messages)} 条；source={session_file.name}",
            )
            print(f"  ✅ 归档成功：新增 {inserted_count} 条，重复跳过 {duplicate_count} 条")

        except Exception as e:
            if conn:
                conn.rollback()
            self.session_stats["failed"] += 1
            self._log_archive_event("error", logical_session_id, str(e))
            print(f"  ❌ 归档失败：{e}")
            raise
        finally:
            if conn:
                conn.close()

    # ---------------------------------------------------------------------
    # public api
    # ---------------------------------------------------------------------
    def archive_session(self, session_file: Path):
        logical_session_id = self._logical_session_id(session_file)
        print(f"\n📦 处理会话：{logical_session_id}")
        try:
            if not self._should_archive(session_file):
                return

            self.session_stats["total"] += 1
            messages = self._parse_jsonl(session_file)
            if not messages:
                print("  ⏭️  没有消息需要归档")
                self.session_stats["skipped"] += 1
                return

            print(f"  📊 找到 {len(messages)} 条记录")
            file_hash = self._get_session_hash(session_file)
            self._insert_to_db(session_file, messages, file_hash)
            self._save_archive_state()

        except Exception as e:
            print(f"  ❌ 处理失败：{e}")

    def run(self):
        start_ts = datetime.now().isoformat()
        exit_code = 0

        print("=" * 60)
        print("🚀 会话历史自动归档系统（真增量版）")
        print(f"⏰ 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        if not SESSIONS_DIR.exists():
            print(f"❌ 会话目录不存在：{SESSIONS_DIR}")
            exit_code = 2
            self._log_archive_event(
                "run_summary",
                "__all__",
                json.dumps({
                    "start_ts": start_ts,
                    "end_ts": datetime.now().isoformat(),
                    "exit_code": exit_code,
                    "stats": self.session_stats,
                    "error": f"sessions_dir_missing:{SESSIONS_DIR}",
                    "mode": os.getenv("SESSION_ARCHIVER_MODE", "raw"),
                }, ensure_ascii=False),
            )
            return

        session_files = []
        for f in SESSIONS_DIR.glob("*.jsonl"):
            if not any(x in f.name for x in ['.deleted', '.backup', '.reset', '.merged', '.backup2']):
                session_files.append(f)

        print(f"\n📁 发现 {len(session_files)} 个活跃会话文件")

        for session_file in sorted(session_files, key=lambda f: f.stat().st_mtime, reverse=True):
            self.archive_session(session_file)

        self._save_archive_state()

        print("\n" + "=" * 60)
        print("📊 归档统计")
        print("=" * 60)
        print(f"  总处理数：{self.session_stats['total']}")
        print(f"  成功：{self.session_stats['success']}")
        print(f"  失败：{self.session_stats['failed']}")
        print(f"  跳过（无更新/无消息）: {self.session_stats['skipped']}")
        print(f"  本次插入总条数：{self.session_stats['inserted_total']}")
        print(f"  本次读取记录总数：{self.session_stats['seen_records_total']}")
        print(f"  本次重复跳过总数：{self.session_stats['duplicate_records_total']}")
        print(f"  去重注册表引导数：{self.session_stats['bootstrapped_registry']}")
        print("=" * 60)

        end_ts = datetime.now().isoformat()
        self._log_archive_event(
            "run_summary",
            "__all__",
            json.dumps({
                "start_ts": start_ts,
                "end_ts": end_ts,
                "exit_code": exit_code,
                "stats": self.session_stats,
                "mode": os.getenv("SESSION_ARCHIVER_MODE", "raw"),
            }, ensure_ascii=False),
        )


if __name__ == "__main__":
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, 'w') as lockf:
        try:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('⏭️  检测到已有 session_archiver 实例在运行，当前退出')
            sys.exit(0)

        archiver = SessionArchiver()
        archiver.run()
