#!/usr/bin/env python3
"""
VectorBrain V3 - Knowledge Memory Database

存储从经验中提炼的规律和模式
"""

import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import time

DB_PATH = Path.home() / ".vectorbrain/memory/knowledge_memory.db"


def init_knowledge_db():
    """初始化知识记忆数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_type TEXT,
            description TEXT,
            confidence REAL,
            usage_count INTEGER,
            created_at REAL
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type ON knowledge_patterns(pattern_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_confidence ON knowledge_patterns(confidence)")
    
    conn.commit()
    conn.close()
    print(f"✅ Knowledge Memory 数据库已初始化：{DB_PATH}")
    return DB_PATH


def insert_pattern(pattern: Dict):
    """
    插入一条知识模式
    
    Args:
        pattern: {
            "pattern_id": str,
            "pattern_type": str,
            "description": str,
            "confidence": float (0-1),
            "usage_count": int (default 0)
        }
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO knowledge_patterns VALUES (?, ?, ?, ?, ?, ?)
    """, (
        pattern["pattern_id"],
        pattern["pattern_type"],
        pattern["description"],
        pattern["confidence"],
        pattern.get("usage_count", 0),
        time.time()
    ))
    
    conn.commit()
    conn.close()


def load_patterns() -> List[Tuple]:
    """加载所有知识模式"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM knowledge_patterns
        ORDER BY confidence DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows


def load_patterns_by_type(pattern_type: str) -> List[Tuple]:
    """按类型加载知识模式"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM knowledge_patterns
        WHERE pattern_type = ?
        ORDER BY confidence DESC
    """, (pattern_type,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows


def get_pattern_by_id(pattern_id: str) -> Optional[Tuple]:
    """根据 ID 查询知识模式"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM knowledge_patterns
        WHERE pattern_id = ?
    """, (pattern_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row


def increment_usage_count(pattern_id: str):
    """增加模式使用次数"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE knowledge_patterns
        SET usage_count = usage_count + 1
        WHERE pattern_id = ?
    """, (pattern_id,))
    
    conn.commit()
    conn.close()


def get_pattern_count() -> int:
    """获取知识模式总数"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM knowledge_patterns")
    count = cursor.fetchone()[0]
    
    conn.close()
    return count


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Knowledge Memory...")
    init_knowledge_db()
    
    # 插入测试数据
    import uuid
    
    test_pattern = {
        "pattern_id": f"pattern_{uuid.uuid4().hex[:8]}",
        "pattern_type": "slow_task",
        "description": "Tasks with execution_time > 5s frequently appear",
        "confidence": 0.7
    }
    
    insert_pattern(test_pattern)
    print(f"✅ 插入测试模式成功")
    print(f"📊 当前模式数：{get_pattern_count()}")
    
    # 查询测试
    patterns = load_patterns()
    print(f"📋 所有模式:")
    for p in patterns:
        print(f"  - {p[1]}: {p[2]} (confidence: {p[3]})")
