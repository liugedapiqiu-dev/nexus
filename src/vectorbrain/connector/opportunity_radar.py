#!/usr/bin/env python3
"""
状态标记（2026-03-19）：
- 当前归类：旧旁路候选 / 待依赖核查
- 主判据说明：不要把本脚本当作机会主链结论源
- 处理原则：需先核查 cron/人工调用，再决定是否进一步归档

"""

import sqlite3
import json
import time
import os
import sys
from pathlib import Path

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
COMMON_DIR = VECTORBRAIN_HOME / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from notify_helper import append_pending_notification, send_feishu_message, log_event

# 配置区
DB_PATH = os.path.expanduser("~/.vectorbrain/opportunity/opportunities.db")

def get_pending_opportunities():
    """获取所有高优先级的待处理机会/风险"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # 严格筛选：状态为待处理，且严重程度为高
        cursor.execute("""
        SELECT opportunity_id, type, title, description, suggested_action 
        FROM opportunities 
        WHERE status = 'pending' AND severity = 'high'
        ORDER BY detected_at DESC LIMIT 5
        """)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"❌ 读取数据库失败：{e}")
        return []

def mark_as_notified(opp_id):
    """将机会状态更新为已通知，防止重复轰炸"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # 将 status 从 pending 改为 notified
        cursor.execute("UPDATE opportunities SET status = 'notified' WHERE opportunity_id = ?", (opp_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ 更新状态失败：{e}")
        return False

def send_feishu_alert(title, description, suggested_action):
    """发送飞书消息警报"""
    msg_content = f"🚨 发现系统风险/机会\n\n📌 标题：{title}\n📄 描述：{description}\n💡 建议：{suggested_action}"

    notification = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "risk_alert",
        "title": title,
        "description": description,
        "suggested_action": suggested_action,
        "message": msg_content,
    }

    ok, detail = append_pending_notification(notification, script="opportunity_radar")
    if ok:
        print(f"✅ 通知已写入日志：{detail}")
    else:
        print(f"❌ 写入日志失败：{detail}")
        return False

    send_ok, send_detail = send_feishu_message(
        msg_content,
        target="user:ou_cd2f520717fd4035c6ef3db89a53b748",
        timeout=60,
        script="opportunity_radar",
    )
    if send_ok:
        print("✅ 飞书消息已发送")
    else:
        print(f"⚠️ 飞书发送失败（通知仍已记录到日志）: {send_detail}")

    return True

def radar_sweep():
    print("📡 [雷达扫描] 开始检测高优未处理机会...")
    opportunities = get_pending_opportunities()
    
    if not opportunities:
        print("✅ 当前无高危警报。")
        return

    print(f"⚠️ 发现 {len(opportunities)} 个高危事项，准备通知指挥官！")
    
    for opp in opportunities:
        opp_id, opp_type, title, desc, action = opp
        
        # 1. 发送飞书
        success = send_feishu_alert(title, desc, action)
        
        # 2. 如果发送成功，立刻更新数据库状态闭环
        if success:
            mark_as_notified(opp_id)
            print(f"🔔 已通知并标记：{opp_id} ({title})")
        else:
            print(f"⛔ 通知失败，保留 pending 状态：{opp_id}")
        
        # 防止频率过高触发飞书流控
        time.sleep(1)

if __name__ == "__main__":
    radar_sweep()
