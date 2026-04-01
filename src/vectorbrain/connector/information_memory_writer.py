#!/usr/bin/env python3
"""
Information Memory 写入器

用途：
- 将文件/表格/结构化资料写入 ~/.vectorbrain/memory/information_memory.db
- 与知识记忆使用相同 schema，便于复用主检索链路

当前版本：先提供最小可用写入能力，后续可扩展批量导入 / 向量化 / 增量同步。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
INFO_DB = VECTORBRAIN_ROOT / 'memory' / 'information_memory.db'


def ensure_db():
    conn = sqlite3.connect(INFO_DB)
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
    conn.execute('CREATE INDEX IF NOT EXISTS idx_info_category ON knowledge(category)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_info_key ON knowledge(key)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_info_updated_at ON knowledge(updated_at)')
    conn.commit()
    conn.close()


def upsert_record(*, key: str, value: str, category: str = 'information_memory', source_worker: str = 'information_memory_writer', confidence: float = 1.0):
    ensure_db()
    now = datetime.now().isoformat()
    conn = sqlite3.connect(INFO_DB)
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


def import_text_file(path: str, *, key_prefix: Optional[str] = None, category: str = 'information_memory.file'):
    p = Path(path).expanduser().resolve()
    text = p.read_text(encoding='utf-8', errors='ignore')
    key = f"{key_prefix or 'file'}:{p.name}"
    payload = json.dumps({
        'type': 'file_import',
        'path': str(p),
        'filename': p.name,
        'content': text,
    }, ensure_ascii=False)
    upsert_record(key=key, value=payload, category=category, source_worker='information_memory_writer:file')
    return key


if __name__ == '__main__':
    ensure_db()
    print(INFO_DB)
