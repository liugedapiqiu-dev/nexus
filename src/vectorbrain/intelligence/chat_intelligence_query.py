#!/usr/bin/env python3
"""
群聊情报网 - 智能查询接口
用户询问时，根据问题智能分析并回答
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import re

# VectorBrain 目录
VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
INTELLIGENCE_DIR = VECTORBRAIN_HOME / "intelligence"
DB_DIR = VECTORBRAIN_HOME / "memory"

EPISODIC_DB = DB_DIR / "episodic_memory.db"
KNOWLEDGE_DB = DB_DIR / "knowledge_memory.db"

# 查询类型映射
QUERY_PATTERNS = {
    "采购": ["采购", "下单", "订单", "PO", "供应商", "采购单"],
    "质量": ["质量", "问题", "不良", "次品", "缺陷", "验货"],
    "交期": ["交期", "交货", "发货", "到货", "物流", "什么时候"],
    "设计": ["设计", "图纸", "样品", "打样", "确认", "修改"],
    "财务": ["付款", "收款", "发票", "价格", "多少钱", "账单"],
    "通用": ["项目", "进展", "情况", "消息"],
}

def search_messages(query, hours=168):
    """搜索相关消息"""
    if not EPISODIC_DB.exists():
        return []
    
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    # 全文搜索
    c.execute('''
        SELECT chat_id, chat_name, sender_id, content, timestamp
        FROM conversations
        WHERE timestamp >= ? AND content LIKE ?
        ORDER BY timestamp DESC
        LIMIT 20
    ''', (since, f"%{query}%"))
    
    results = c.fetchall()
    conn.close()
    
    return results

def get_chat_activity(chat_name=None, hours=24):
    """获取群活跃度"""
    if not EPISODIC_DB.exists():
        return {}
    
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    if chat_name:
        c.execute('''
            SELECT chat_name, COUNT(*) as count
            FROM conversations
            WHERE timestamp >= ? AND chat_name = ?
            GROUP BY chat_name
        ''', (since, chat_name))
    else:
        c.execute('''
            SELECT chat_name, COUNT(*) as count
            FROM conversations
            WHERE timestamp >= ?
            GROUP BY chat_name
            ORDER BY count DESC
        ''', (since,))
    
    results = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    
    return results

def detect_query_type(question):
    """检测用户问题类型"""
    types = []
    for query_type, keywords in QUERY_PATTERNS.items():
        if any(kw in question for kw in keywords):
            types.append(query_type)
    return types

def answer_question(question, hours=168):
    """智能回答用户问题"""
    print("=" * 70)
    print("🤖 群聊情报网 - 智能查询")
    print(f"问题：{question}")
    print(f"时间范围：最近 {hours} 小时")
    print("=" * 70)
    
    # 检测问题类型
    query_types = detect_query_type(question)
    
    if not query_types:
        print("\n📋 通用查询，搜索所有相关内容...\n")
        query_types = ["通用"]
    
    print(f"🎯 识别类型：{', '.join(query_types)}")
    
    # 搜索相关消息
    all_results = []
    for qt in query_types:
        if qt != "通用":
            # 搜索关键词
            for keyword in QUERY_PATTERNS.get(qt, [qt]):
                results = search_messages(keyword, hours)
                all_results.extend(results)
    
    # 去重
    seen = set()
    unique_results = []
    for r in all_results:
        key = (r[0], r[3])  # chat_id + content
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    if not unique_results:
        print("\n📭 未找到相关信息")
        print("💡 提示：可以尝试问具体的问题，如：")
        print("   • 最近有什么采购订单？")
        print("   • 项目有什么进展？")
        print("   • 有没有质量问题需要处理？")
        return None
    
    # 组织答案
    print("\n" + "=" * 70)
    print("📊 查询结果")
    print("=" * 70)
    
    # 按群分组
    by_chat = {}
    for r in unique_results[:15]:  # 最多显示 15 条
        chat_id, chat_name, sender_id, content, timestamp = r
        if not chat_name:
            chat_name = "未知群"
        
        if chat_name not in by_chat:
            by_chat[chat_name] = []
        
        by_chat[chat_name].append({
            "content": content,
            "sender_id": sender_id,
            "timestamp": timestamp
        })
    
    # 显示结果
    for chat_name, msgs in sorted(by_chat.items(), key=lambda x: -len(x[1])):
        print(f"\n📍 {chat_name} ({len(msgs)} 条)")
        print("-" * 70)
        
        for msg in msgs[:5]:  # 每个群最多 5 条
            content = msg['content']
            # 截取合理长度
            if len(str(content)) > 150:
                content = str(content)[:150] + "..."
            
            # 格式化时间
            ts = msg['timestamp']
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    ts_str = dt.strftime("%m-%d %H:%M")
                except Exception:
                    ts_str = ts[:16]
            else:
                ts_str = "未知时间"
            
            print(f"   [{ts_str}] {content}")
    
    print("\n" + "=" * 70)
    
    # 生成摘要
    print("\n💡 摘要总结")
    print("-" * 70)
    
    total_msgs = len(unique_results)
    chat_count = len(by_chat)
    
    print(f"   • 共找到 {total_msgs} 条相关消息")
    print(f"   • 涉及 {chat_count} 个群")
    
    # 时间范围
    timestamps = []
    for r in unique_results:
        ts = r[4]
        if ts:
            try:
                timestamps.append(datetime.fromisoformat(ts))
            except Exception:
                pass
    
    if timestamps:
        latest = max(timestamps)
        oldest = min(timestamps)
        print(f"   • 时间范围：{oldest.strftime('%m-%d %H:%M')} - {latest.strftime('%m-%d %H:%M')}")
    
    # 如果有关键发现
    if any("急" in str(r[3]) or "紧急" in str(r[3]) for r in unique_results):
        print("\n🚨 发现紧急消息！")
        for r in unique_results:
            if "急" in str(r[3]):
                print(f"   • {r[3][:100]}")
    
    print("\n" + "=" * 70)
    
    return {
        "query": question,
        "types": query_types,
        "results_count": len(unique_results),
        "chats_involved": list(by_chat.keys()),
        "messages": unique_results[:15]
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法：python chat_intelligence_query.py <问题> [小时数]")
        print("示例：python chat_intelligence_query.py '最近有什么采购订单？' 24")
        sys.exit(1)
    
    question = sys.argv[1]
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 168  # 默认 7 天
    
    answer_question(question, hours)
