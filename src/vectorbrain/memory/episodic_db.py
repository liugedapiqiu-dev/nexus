#!/usr/bin/env python3
"""
VectorBrain V3 - Episodic Memory Database

记录任务执行的具体事件（发生了什么）
"""

import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional

DB_PATH = Path.home() / ".vectorbrain/memory/episodic_memory.db"


def init_episodic_db():
    """初始化情景记忆数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            episode_id TEXT PRIMARY KEY,
            task_id TEXT,
            timestamp REAL,
            task_type TEXT,
            task_input TEXT,
            task_output TEXT,
            status TEXT,
            execution_time REAL,
            success INTEGER
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_episode_task ON episodes(task_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_episode_timestamp ON episodes(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_episode_status ON episodes(status)")
    
    conn.commit()
    conn.close()
    print(f"✅ Episodic Memory 数据库已初始化：{DB_PATH}")
    return DB_PATH


def insert_episode(data: Tuple):
    """
    插入一条经验记录
    
    Args:
        data: (episode_id, task_id, timestamp, task_type, task_input, task_output, status, execution_time, success)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    
    conn.commit()
    conn.close()


def load_recent_episodes(limit: int = 100) -> List[Tuple]:
    """
    加载最近的 N 条经验记录
    
    Args:
        limit: 返回数量限制
    
    Returns:
        episodes list
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM episodes
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows


def get_episode_by_task_id(task_id: str) -> Optional[Tuple]:
    """根据 task_id 查询经验记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM episodes
        WHERE task_id = ?
    """, (task_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row


def get_episode_count() -> int:
    """获取经验记录总数"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM episodes")
    count = cursor.fetchone()[0]
    
    conn.close()
    return count


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Episodic Memory...")
    init_episodic_db()
    
    # 插入测试数据
    import uuid
    import time
    
    test_data = (
        f"ep_{uuid.uuid4().hex[:16]}",
        "task_test_001",
        time.time(),
        "shell",
        "echo hello",
        "hello",
        "done",
        0.5,
        1
    )
    
    insert_episode(test_data)
    print(f"✅ 插入测试数据成功")
    print(f"📊 当前记录数：{get_episode_count()}")
