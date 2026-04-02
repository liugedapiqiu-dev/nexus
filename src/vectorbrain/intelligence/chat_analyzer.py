#!/usr/bin/env python3
"""
群聊情报网 - 情报分析总结
分析所有群的聊天记录，生成情报报告
只在用户询问时执行
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# VectorBrain 目录
VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
INTELLIGENCE_DIR = VECTORBRAIN_HOME / "intelligence"
DB_DIR = VECTORBRAIN_HOME / "memory"

# 数据库路径
EPISODIC_DB = DB_DIR / "episodic_memory.db"
KNOWLEDGE_DB = DB_DIR / "knowledge_memory.db"

# 群名称映射
# 请在 .env 或配置中配置你的飞书群 ID
CHAT_NAMES = {
    "[YOUR_GROUP_ID_1]": "群组名称1",
    "[YOUR_GROUP_ID_2]": "群组名称2",
}

# 重要关键词分类
KEYWORD_CATEGORIES = {
    "采购": ["采购", "下单", "订单", "PO", "采购单"],
    "生产": ["生产", "加工", "工厂", "车间", "排期"],
    "质量": ["质量", "问题", "不良", "缺陷", "次品", "验货"],
    "交期": ["交期", "交货", "发货", "物流", "快递", "到货"],
    "财务": ["付款", "收款", "发票", "对账", "价格", "金额"],
    "设计": ["设计", "图纸", "样品", "打样", "确认", "修改"],
    "紧急": ["紧急", "急", "尽快", "马上", "立即", "今天"],
}

def get_recent_messages(hours=24):
    """获取最近 N 小时的消息"""
    if not EPISODIC_DB.exists():
        print("⚠️ 情景数据库不存在")
        return []
    
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    c.execute('''
        SELECT chat_id, chat_name, sender_id, content, timestamp, message_id
        FROM conversations
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
    ''', (since,))
    
    messages = c.fetchall()
    conn.close()
    
    return messages

def get_important_knowledge(hours=24):
    """获取最近的重要消息（直接从 episodic_db 查询）"""
    if not EPISODIC_DB.exists():
        print("⚠️ 情景数据库不存在")
        return []
    
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    # 直接查询包含关键词的消息
    c.execute('''
        SELECT chat_name, sender_name, content, timestamp
        FROM conversations
        WHERE timestamp >= ?
        AND (
            content LIKE '%紧急%' OR
            content LIKE '%问题%' OR
            content LIKE '%确认%' OR
            content LIKE '%采购%' OR
            content LIKE '%订单%' OR
            content LIKE '%质量%'
        )
        ORDER BY timestamp DESC
        LIMIT 50
    ''', (since,))
    
    items = c.fetchall()
    conn.close()
    
    # 转换为统一格式
    results = []
    for item in items:
        results.append({
            "chat_name": item[0],
            "sender_name": item[1],
            "content": item[2],
            "timestamp": item[3],
            "importance": 0.8
        })
    
    return results

def categorize_message(content):
    """对消息进行分类"""
    if not content:
        return []
    
    categories = []
    content_str = str(content).lower()
    
    for category, keywords in KEYWORD_CATEGORIES.items():
        if any(kw in content_str for kw in keywords):
            categories.append(category)
    
    return categories

def analyze_messages(messages):
    """分析消息，提取关键信息"""
    # 按群分组
    by_chat = defaultdict(list)
    by_category = defaultdict(list)
    urgent_messages = []
    
    for msg in messages:
        chat_id, chat_name, sender_id, content, timestamp, message_id = msg
        
        if not chat_name:
            chat_name = CHAT_NAMES.get(chat_id, "未知群")
        
        # 分类
        categories = categorize_message(content)
        
        msg_data = {
            "chat_id": chat_id,
            "chat_name": chat_name,
            "sender_id": sender_id,
            "content": content,
            "timestamp": timestamp,
            "categories": categories
        }
        
        by_chat[chat_name].append(msg_data)
        
        for cat in categories:
            by_category[cat].append(msg_data)
        
        # 紧急消息
        if "紧急" in categories:
            urgent_messages.append(msg_data)
    
    return {
        "by_chat": dict(by_chat),
        "by_category": dict(by_category),
        "urgent": urgent_messages,
        "total": len(messages)
    }

def generate_report(hours=24):
    """生成情报报告"""
    print("=" * 70)
    print("🕵️ 群聊情报网 - 情报分析报告")
    print(f"⏰ 时间范围：最近 {hours} 小时")
    print(f"📅 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 获取数据
    messages = get_recent_messages(hours)
    knowledge = get_important_knowledge(hours)
    
    if not messages:
        print("\n📭 最近没有新消息")
        return None
    
    # 分析消息
    analysis = analyze_messages(messages)
    
    # ===== 报告内容 =====
    
    # 1. 总体统计
    print("\n📊 总体统计")
    print("-" * 70)
    print(f"   总消息数：{analysis['total']} 条")
    print(f"   涉及群数：{len(analysis['by_chat'])} 个")
    print(f"   紧急消息：{len(analysis['urgent'])} 条")
    
    # 2. 紧急消息（优先显示）
    if analysis['urgent']:
        print("\n🚨 紧急消息")
        print("-" * 70)
        for msg in analysis['urgent'][:5]:
            print(f"   【{msg['chat_name']}】{msg['content'][:100]}")
            print(f"   时间：{msg['timestamp']}")
            print()
    
    # 3. 按类别统计
    if analysis['by_category']:
        print("\n📋 按类别统计")
        print("-" * 70)
        for category, msgs in sorted(analysis['by_category'].items(), key=lambda x: -len(x[1])):
            print(f"   {category}: {len(msgs)} 条")
    
    # 4. 各群动态
    print("\n🏢 各群动态")
    print("-" * 70)
    for chat_name, msgs in sorted(analysis['by_chat'].items(), key=lambda x: -len(x[1])):
        print(f"\n   📍 {chat_name} ({len(msgs)} 条)")
        
        # 显示最近 3 条
        for msg in msgs[:3]:
            content = msg['content'][:80] + "..." if len(str(msg['content'])) > 80 else msg['content']
            cats = " | ".join(msg['categories']) if msg['categories'] else "普通"
            print(f"      • [{cats}] {content}")
    
    # 5. 重要知识
    if knowledge:
        print("\n💡 重要知识提取")
        print("-" * 70)
        for i, item in enumerate(knowledge[:10], 1):
            content, metadata, source, importance = item
            meta = json.loads(metadata) if metadata else {}
            chat_name = meta.get("chat_name", "未知")
            print(f"   {i}. 【{chat_name}】(重要度：{importance:.1f})")
            print(f"      {content[:100]}...")
    
    # 6. 需要关注的信息
    print("\n⚠️ 需要重视的信息")
    print("-" * 70)
    
    # 找出可能重要的模式
    important_items = []
    
    # 采购相关
    if "采购" in analysis['by_category']:
        important_items.append(("🛒 采购动态", analysis['by_category']['采购']))
    
    # 质量问题
    if "质量" in analysis['by_category']:
        important_items.append(("⚠️ 质量问题", analysis['by_category']['质量']))
    
    # 交期相关
    if "交期" in analysis['by_category']:
        important_items.append(("📦 交期信息", analysis['by_category']['交期']))
    
    # 财务相关
    if "财务" in analysis['by_category']:
        important_items.append(("💰 财务事项", analysis['by_category']['财务']))
    
    if not important_items:
        print("   暂无需要特别重视的信息")
    else:
        for title, items in important_items:
            print(f"\n   {title}")
            for item in items[:3]:
                content = str(item['content'])[:80]
                print(f"      • {content}...")
    
    print("\n" + "=" * 70)
    print("📝 报告结束")
    print("=" * 70)
    
    # 保存报告
    report_file = INTELLIGENCE_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(report_file, 'w') as f:
        f.write(f"群聊情报网 - 情报分析报告\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"时间范围：最近 {hours} 小时\n")
        f.write(f"总消息数：{analysis['total']} 条\n\n")
        # 简化保存
        for chat_name, msgs in analysis['by_chat'].items():
            f.write(f"\n{chat_name}:\n")
            for msg in msgs[:10]:
                f.write(f"  - {msg['content']}\n")
    
    print(f"📄 报告已保存：{report_file}")
    
    return analysis

def quick_summary(hours=24):
    """快速摘要（用于简短汇报）"""
    messages = get_recent_messages(hours)
    
    if not messages:
        return "📭 最近没有新消息"
    
    analysis = analyze_messages(messages)
    
    summary = []
    
    # 统计
    summary.append(f"📊 最近{hours}小时：{analysis['total']}条消息")
    
    # 紧急
    if analysis['urgent']:
        summary.append(f"🚨 {len(analysis['urgent'])}条紧急消息")
    
    # 重点类别
    key_categories = ["采购", "质量", "交期", "财务"]
    for cat in key_categories:
        if cat in analysis['by_category']:
            summary.append(f"• {cat}: {len(analysis['by_category'][cat])}条")
    
    # 最活跃的群
    if analysis['by_chat']:
        most_active = max(analysis['by_chat'].items(), key=lambda x: len(x[1]))
        summary.append(f"💬 最活跃：{most_active[0]} ({most_active[1]}条)")
    
    return "\n".join(summary)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        print(quick_summary(hours))
    else:
        hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
        generate_report(hours)
