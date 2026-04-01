#!/usr/bin/env python3
"""
🧠 VectorBrain 全局 Token 追踪器

功能：
- 拦截所有 LLM API 调用（DashScope、Ollama）
- 从 API 响应中提取真实的 input_tokens 和 output_tokens
- 统计所有会话的 token 使用情况
- 支持按会话、按模型、按时间范围查询

作者：[YOUR_AI_NAME] 🧠
版本：1.0 (2026-03-13)
"""

import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List
import threading
import httpx

# 数据库路径
DB_PATH = Path.home() / '.vectorbrain' / 'state' / 'global_token_stats.db'

def init_db():
    """初始化数据库"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 创建 token 使用记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            session_key TEXT,
            model TEXT NOT NULL,
            provider TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            duration_ms INTEGER,
            request_id TEXT,
            metadata TEXT
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON token_usage(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON token_usage(session_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_model ON token_usage(model)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_provider ON token_usage(provider)')
    
    # 创建汇总表（按天）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT PRIMARY KEY,
            total_input INTEGER DEFAULT 0,
            total_output INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            request_count INTEGER DEFAULT 0,
            unique_sessions INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Token 追踪数据库初始化完成：{DB_PATH}")

def log_token_usage(
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    session_key: str = None,
    session_id: str = None,
    duration_ms: int = None,
    request_id: str = None,
    metadata: dict = None
):
    """
    记录一次 token 使用
    
    Args:
        model: 模型名称 (e.g., "qwen3.5-plus")
        provider: 提供商 ("dashscope" | "ollama")
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
        session_key: 会话标识
        session_id: 会话 ID
        duration_ms: 请求耗时（毫秒）
        request_id: 请求 ID
        metadata: 额外元数据
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    total_tokens = input_tokens + output_tokens
    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
    
    cursor.execute('''
        INSERT INTO token_usage 
        (timestamp, session_id, session_key, model, provider, input_tokens, output_tokens, total_tokens, duration_ms, request_id, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, session_id, session_key, model, provider, input_tokens, output_tokens, total_tokens, duration_ms, request_id, metadata_json))
    
    # 更新每日汇总
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        INSERT INTO daily_summary (date, total_input, total_output, total_tokens, request_count, unique_sessions)
        VALUES (?, ?, ?, ?, 1, 1)
        ON CONFLICT(date) DO UPDATE SET
            total_input = total_input + ?,
            total_output = total_output + ?,
            total_tokens = total_tokens + ?,
            request_count = request_count + 1
    ''', (today, input_tokens, output_tokens, total_tokens, input_tokens, output_tokens, total_tokens))
    
    conn.commit()
    conn.close()

def get_token_stats(days: int = 7, session_key: str = None) -> Dict:
    """
    获取 token 使用统计
    
    Args:
        days: 统计天数
        session_key: 可选，只统计特定会话
    
    Returns:
        统计字典
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 基础查询条件
    where_clause = f"timestamp >= datetime('now', '-{days} days')"
    if session_key:
        where_clause += f" AND session_key = '{session_key}'"
    
    # 总体统计
    cursor.execute(f'''
        SELECT 
            SUM(input_tokens) as total_input,
            SUM(output_tokens) as total_output,
            SUM(total_tokens) as total_tokens,
            COUNT(*) as request_count,
            COUNT(DISTINCT session_key) as unique_sessions
        FROM token_usage
        WHERE {where_clause}
    ''')
    summary = dict(cursor.fetchone())
    
    # 按模型统计
    cursor.execute(f'''
        SELECT model, provider, 
               SUM(input_tokens) as input_tokens,
               SUM(output_tokens) as output_tokens,
               SUM(total_tokens) as total_tokens,
               COUNT(*) as request_count
        FROM token_usage
        WHERE {where_clause}
        GROUP BY model, provider
        ORDER BY total_tokens DESC
    ''')
    by_model = [dict(row) for row in cursor.fetchall()]
    
    # 按天统计（最近 7 天）
    cursor.execute(f'''
        SELECT 
            date(timestamp) as date,
            SUM(input_tokens) as input_tokens,
            SUM(output_tokens) as output_tokens,
            SUM(total_tokens) as total_tokens,
            COUNT(*) as request_count
        FROM token_usage
        WHERE {where_clause}
        GROUP BY date(timestamp)
        ORDER BY date DESC
    ''')
    by_day = [dict(row) for row in cursor.fetchall()]
    
    # 最近使用记录
    cursor.execute(f'''
        SELECT * FROM token_usage
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT 20
    ''')
    recent = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'summary': summary or {},
        'by_model': by_model,
        'by_day': by_day,
        'recent': recent,
        'period_days': days,
        'session_key': session_key
    }

def get_daily_summary(date: str = None) -> Dict:
    """获取指定日期的汇总（默认今天）"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('SELECT * FROM daily_summary WHERE date = ?', (date,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

# HTTP 代理拦截器（用于拦截 DashScope API 调用）
class TokenTrackingProxy:
    """
    HTTP 代理，拦截 LLM API 调用并记录 token 使用
    """
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def request(self, method: str, url: str, **kwargs):
        """拦截 HTTP 请求"""
        start_time = time.time()
        
        # 发送请求
        response = await self.client.request(method, url, **kwargs)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 检查是否是 LLM API 调用
        if self._is_llm_api(url, response):
            try:
                self._extract_and_log_tokens(response, duration_ms)
            except Exception as e:
                print(f"⚠️ Token 提取失败：{e}")
        
        return response
    
    def _is_llm_api(self, url: str, response) -> bool:
        """检查是否是 LLM API 调用"""
        llm_endpoints = [
            'dashscope.aliyuncs.com',
            'openai.com/v1',
            'ollama'
        ]
        return any(ep in url for ep in llm_endpoints)
    
    def _extract_and_log_tokens(self, response, duration_ms: int):
        """从 API 响应中提取 token 使用"""
        try:
            data = response.json()
            usage = data.get('usage', {})
            
            if usage:
                input_tokens = usage.get('input_tokens', usage.get('prompt_tokens', 0))
                output_tokens = usage.get('output_tokens', usage.get('completion_tokens', 0))
                model = data.get('model', 'unknown')
                request_id = data.get('request_id', data.get('id', None))
                
                log_token_usage(
                    model=model,
                    provider='dashscope' if 'dashscope' in str(response.url) else 'ollama',
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration_ms=duration_ms,
                    request_id=request_id
                )
                print(f"📊 Token 记录：{model} - 输入 {input_tokens} / 输出 {output_tokens}")
        except Exception as e:
            print(f"⚠️ 提取 token 失败：{e}")

# ===== 命令行工具 =====
if __name__ == '__main__':
    import sys
    
    # 初始化数据库
    init_db()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'stats':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            stats = get_token_stats(days=days)
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        elif cmd == 'today':
            summary = get_daily_summary()
            if summary:
                print(f"📊 今日 Token 使用统计")
                print(f"  输入：{summary['total_input']:,}")
                print(f"  输出：{summary['total_output']:,}")
                print(f"  总计：{summary['total_tokens']:,}")
                print(f"  请求数：{summary['request_count']:,}")
            else:
                print("📊 今日暂无数据")
        
        elif cmd == 'recent':
            stats = get_token_stats(days=1)
            for record in stats['recent'][:10]:
                print(f"{record['timestamp'][:19]} | {record['model']:20} | 输入 {record['input_tokens']:5} / 输出 {record['output_tokens']:5}")
        
        else:
            print("用法:")
            print("  python3 global_token_tracker.py stats [days]")
            print("  python3 global_token_tracker.py today")
            print("  python3 global_token_tracker.py recent")
    else:
        print("🧠 VectorBrain 全局 Token 追踪器")
        print("=" * 60)
        print("数据库:", DB_PATH)
        print()
        print("用法:")
        print("  stats [days]  - 查看最近 N 天统计")
        print("  today         - 查看今日统计")
        print("  recent        - 查看最近使用记录")
        print()
        print("示例:")
        print("  python3 global_token_tracker.py stats 7")
        print("  python3 global_token_tracker.py today")
