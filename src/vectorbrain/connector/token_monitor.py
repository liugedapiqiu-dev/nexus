#!/usr/bin/env python3
"""
Token 使用监控 - 记录每条消息的输入输出 token 数
"""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
import tiktoken

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
COMMON_DIR = VECTORBRAIN_HOME / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from notify_helper import log_event

LOG_FILE = Path.home() / '.vectorbrain' / 'connector' / 'feishu_messages.log'
STATS_FILE = Path.home() / '.vectorbrain' / 'state' / 'token_stats.db'

def get_token_count(text):
    """计算 token 数（使用 cl100k_base 编码）"""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(str(text)))
    except Exception as e:
        log_event("token_monitor", "get_token_count_fallback", {"error": str(e)}, level="warning")
        # 简单估算：中文约 1.5 token/字，英文约 0.75 token/词
        return len(str(text)) * 1.5

def init_db():
    """初始化数据库"""
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STATS_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            direction TEXT,
            content_type TEXT,
            token_count INTEGER,
            char_count INTEGER,
            message_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_tokens(direction, content, message_id=None):
    """记录 token 使用"""
    token_count = get_token_count(content)
    char_count = len(str(content))
    timestamp = datetime.now().isoformat()
    
    conn = sqlite3.connect(STATS_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO token_stats (timestamp, direction, content_type, token_count, char_count, message_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (timestamp, direction, 'text', token_count, char_count, message_id))
    conn.commit()
    conn.close()
    
    return token_count

def get_stats(days=7):
    """获取统计数据"""
    conn = sqlite3.connect(STATS_FILE)
    cursor = conn.cursor()
    
    # 总统计
    cursor.execute('''
        SELECT direction, SUM(token_count), COUNT(*), AVG(token_count)
        FROM token_stats
        WHERE timestamp >= datetime('now', '-{} days')
        GROUP BY direction
    '''.format(days))
    summary = cursor.fetchall()
    
    # 今日统计
    cursor.execute('''
        SELECT direction, SUM(token_count), COUNT(*)
        FROM token_stats
        WHERE date(timestamp) = date('now')
        GROUP BY direction
    ''')
    today = cursor.fetchall()
    
    conn.close()
    
    return {
        'summary': summary,
        'today': today
    }

if __name__ == '__main__':
    init_db()
    stats = get_stats()
    print("=== Token 使用统计 ===")
    print(f"\n今日:")
    for row in stats['today']:
        print(f"  {row[0]}: {row[1]} tokens ({row[2]} 条)")
    print(f"\n最近 7 天:")
    for row in stats['summary']:
        print(f"  {row[0]}: {row[1]} tokens (平均 {row[3]:.1f}/条)")
