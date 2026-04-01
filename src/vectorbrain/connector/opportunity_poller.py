#!/usr/bin/env python3
"""
状态标记（2026-03-19）：
- 当前归类：辅助层 / 待依赖核查
- 主判据说明：机会数据事实仍以 `opportunity/opportunities.db` 为准
- 处理原则：是否为现行自动化主入口仍需核查调度依赖


VectorBrain Opportunity Poller - 机会扫描轮询脚本

功能：
1. 轮询 opportunities.db 查找 pending + high severity 的机会
2. 输出格式化的消息内容（供 OpenClaw 发送）
3. 更新状态为 addressed

用法：
python ~/.vectorbrain/connector/opportunity_poller.py
"""

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime

# VectorBrain 路径
VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
OPPORTUNITY_DB = VECTORBRAIN_ROOT / 'opportunity' / 'opportunities.db'
PENDING_QUEUE_FILE = VECTORBRAIN_ROOT / 'state' / 'pending_notifications.json'

def check_opportunities():
    """
    查询 pending + high severity 的机会
    
    Returns:
        list: 待通知的机会列表
    """
    if not OPPORTUNITY_DB.exists():
        print(f"❌ 数据库不存在：{OPPORTUNITY_DB}")
        return []
    
    try:
        conn = sqlite3.connect(str(OPPORTUNITY_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询 pending + high 的机会
        cursor.execute("""
            SELECT opportunity_id, type, title, description, severity, suggested_action, detected_at
            FROM opportunities
            WHERE status = 'pending' AND severity = 'high'
            ORDER BY detected_at DESC
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        opportunities = []
        for row in rows:
            opportunities.append({
                'opportunity_id': row['opportunity_id'],
                'type': row['type'],
                'title': row['title'],
                'description': row['description'],
                'severity': row['severity'],
                'suggested_action': row['suggested_action'],
                'detected_at': row['detected_at']
            })
        
        return opportunities
        
    except Exception as e:
        print(f"❌ 查询失败：{e}")
        return []

def update_status(opportunity_id):
    """
    更新机会状态为 addressed
    
    Args:
        opportunity_id: 机会 ID
    """
    try:
        conn = sqlite3.connect(str(OPPORTUNITY_DB))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE opportunities
            SET status = 'addressed', addressed_at = ?
            WHERE opportunity_id = ?
        """, (datetime.now().isoformat(), opportunity_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 已更新状态：{opportunity_id}")
        
    except Exception as e:
        print(f"❌ 更新状态失败：{e}")

def write_pending_queue(opportunities, message):
    """
    写入待通知队列文件
    
    Args:
        opportunities: 机会列表
        message: 格式化消息
    """
    try:
        # 确保目录存在
        PENDING_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        queue_data = {
            'timestamp': datetime.now().isoformat(),
            'count': len(opportunities),
            'opportunities': opportunities,
            'message': message,
            'status': 'pending'
        }
        
        with open(PENDING_QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已写入待通知队列：{PENDING_QUEUE_FILE}")
        
    except Exception as e:
        print(f"❌ 写入队列失败：{e}")

def format_message(opportunities):
    """
    格式化飞书消息内容
    
    Args:
        opportunities: 机会列表
    
    Returns:
        str: 格式化的消息内容
    """
    if not opportunities:
        return None
    
    message = "🚨 **VectorBrain 机会提醒**\n\n"
    message += f"发现 {len(opportunities)} 条高优先级机会/风险：\n\n"
    
    for i, opp in enumerate(opportunities, 1):
        message += f"**{i}. {opp['title']}**\n"
        message += f"类型：{opp['type']}\n"
        message += f"严重程度：🔴 {opp['severity']}\n"
        message += f"描述：{opp['description']}\n"
        message += f"建议行动：{opp['suggested_action']}\n"
        message += f"发现时间：{opp['detected_at']}\n"
        message += "\n---\n\n"
    
    message += "\n_此消息由 VectorBrain Opportunity Poller 自动生成_"
    
    return message

def main(auto_update=False):
    """主函数
    
    Args:
        auto_update: 是否自动更新状态为 addressed
    """
    print(f"🔍 开始轮询机会...")
    print(f"数据库：{OPPORTUNITY_DB}")
    print(f"自动更新：{'是' if auto_update else '否'}")
    print("")
    
    # 查询机会
    opportunities = check_opportunities()
    
    if not opportunities:
        print("✅ 未发现高优先级机会")
        return
    
    print(f"📌 发现 {len(opportunities)} 条高优先级机会：\n")
    
    # 输出机会详情
    for opp in opportunities:
        print(f"ID: {opp['opportunity_id']}")
        print(f"标题：{opp['title']}")
        print(f"类型：{opp['type']}")
        print(f"严重程度：{opp['severity']}")
        print(f"描述：{opp['description']}")
        print(f"建议行动：{opp['suggested_action']}")
        print("")
    
    # 输出格式化消息（供 OpenClaw 使用）
    print("=" * 60)
    print("📱 飞书消息内容：")
    print("=" * 60)
    message = format_message(opportunities)
    print(message)
    print("=" * 60)
    
    # 输出 JSON 格式（供程序使用）
    print("")
    print("📄 JSON 输出：")
    print(json.dumps({
        'count': len(opportunities),
        'opportunities': opportunities,
        'message': message
    }, indent=2, ensure_ascii=False))
    
    # 自动更新状态 + 写入待通知队列
    if auto_update and opportunities:
        print("")
        print("🔄 自动更新状态为 'addressed'...")
        for opp in opportunities:
            update_status(opp['opportunity_id'])
        print("✅ 状态更新完成")
        
        # 写入待通知队列（供 OpenClaw 心跳时发送）
        print("")
        print("📥 写入待通知队列...")
        write_pending_queue(opportunities, message)
        print("✅ 队列写入完成")
    else:
        # 询问是否更新状态
        print("")
        print("⚠️  请确认后手动更新状态为 'addressed'")
        print("命令示例：")
        for opp in opportunities:
            print(f"  sqlite3 {OPPORTUNITY_DB} \"UPDATE opportunities SET status='addressed', addressed_at=datetime('now') WHERE opportunity_id='{opp['opportunity_id']}';\"")

if __name__ == '__main__':
    main()
