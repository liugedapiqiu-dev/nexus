#!/usr/bin/env python3
"""
初始化 Information Memory 数据库
位置：~/.vectorbrain/memory/information_memory.db

用途：承载来自表格/文件/资料的结构化信息记忆，并进入 VectorBrain 全局检索链路。
"""

import sqlite3
from pathlib import Path

VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
MEMORY_DIR = VECTORBRAIN_ROOT / 'memory'
INFO_DB = MEMORY_DIR / 'information_memory.db'

SCHEMA = """
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
);
CREATE INDEX IF NOT EXISTS idx_info_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_info_key ON knowledge(key);
CREATE INDEX IF NOT EXISTS idx_info_updated_at ON knowledge(updated_at);
"""


def main():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INFO_DB)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(INFO_DB)


if __name__ == '__main__':
    main()
