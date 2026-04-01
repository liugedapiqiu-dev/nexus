#!/usr/bin/env python3
"""
Habit Memory 写入器

用途：
- 将用户习惯/偏好/操作风格/表格填写口径写入 ~/.vectorbrain/memory/habit_memory.db
- 与 knowledge / information 使用相同 schema，便于复用主检索链路
"""

import sqlite3
from datetime import datetime
from pathlib import Path

VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
HABIT_DB = VECTORBRAIN_ROOT / 'memory' / 'habit_memory.db'


def ensure_db():
    conn = sqlite3.connect(HABIT_DB)
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            source_worker TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            embedding_vector TEXT
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_habit_category ON knowledge(category)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_habit_key ON knowledge(key)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_habit_updated_at ON knowledge(updated_at)')
    conn.commit()
    conn.close()


def upsert_record(*, key: str, value: str, category: str = 'habit_memory', source_worker: str = 'habit_memory_writer', confidence: float = 1.0):
    ensure_db()
    now = datetime.now().isoformat()
    conn = sqlite3.connect(HABIT_DB)
    conn.execute(
        '''
        INSERT INTO knowledge (category, key, value, source_worker, confidence, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            category=excluded.category,
            value=excluded.value,
            source_worker=excluded.source_worker,
            confidence=excluded.confidence,
            updated_at=excluded.updated_at
        ''',
        (category, key, value, source_worker, confidence, now, now)
    )
    conn.commit()
    conn.close()


if __name__ == '__main__':
    ensure_db()
    print(HABIT_DB)
