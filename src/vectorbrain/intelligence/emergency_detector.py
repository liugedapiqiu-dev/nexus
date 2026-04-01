#!/usr/bin/env python3
"""
群聊情报网 - 紧急消息检测模块
检测紧急情况、情绪异常、高频讨论，并发送飞书通知
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
COMMON_DIR = VECTORBRAIN_HOME / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from notify_helper import send_feishu_message, log_event

# VectorBrain 目录
INTELLIGENCE_DIR = VECTORBRAIN_HOME / "intelligence"
DB_DIR = VECTORBRAIN_HOME / "memory"

EPISODIC_DB = DB_DIR / "episodic_memory.db"
ALERT_LOG = INTELLIGENCE_DIR / "alerts.log"
ALERT_STATE = INTELLIGENCE_DIR / "alert_state.json"

# 用户 ID（健豪）
USER_ID = "ou_cd2f520717fd4035c6ef3db89a53b748"

# ========== 关键词库 ==========

# 🚨 紧急关键词（立即通知）
URGENCY_KEYWORDS = [
    "紧急", "急", "马上", "立即", "立刻", "今天必须", "刻不容缓",
    "出问题", "事故", "投诉", "异常", "故障", "严重", "危险"
]

# 质量问题
QUALITY_ISSUES = [
    "质量", "缺陷", "不良", "次品", "退货", "投诉", "不合格",
    "验货失败", "色差", "破损", "错误", "做错了"
]

# 交期问题
DELIVERY_ISSUES = [
    "延期", "延误", "延迟", "来不及", "赶不上", "超时",
    "物流异常", "没发货", "未到港", "清关问题"
]

# 财务风险
FINANCIAL_RISKS = [
    "付款失败", "价格错误", "订单取消", "退款", "赔款",
    "亏本", "损失", "赔钱", "算错了"
]

# ⚠️ 负面情绪词
NEGATIVE_EMOTIONS = [
    "烦", "累", "难", "无语", "糟糕", "失望", "加班", "痛苦",
    "崩溃", "受不了", "太过分了", "气死", "烦死了"
]

# 冲突信号
CONFLICT_SIGNALS = [
    "不对", "错了", "不是这样", "重新做", "返工", "搞什么",
    "怎么回事", "为什么又", "到底", "怎么又"
]

# ========== 检测函数 ==========

def detect_urgency(content):
    """检测消息是否包含紧急内容"""
    triggers = []
    
    # 紧急关键词
    for kw in URGENCY_KEYWORDS:
        if kw in content:
            triggers.append(f"紧急词：{kw}")
    
    # 质量问题
    for kw in QUALITY_ISSUES:
        if kw in content:
            triggers.append(f"质量问题：{kw}")
    
    # 交期问题
    for kw in DELIVERY_ISSUES:
        if kw in content:
            triggers.append(f"交期问题：{kw}")
    
    # 财务风险
    for kw in FINANCIAL_RISKS:
        if kw in content:
            triggers.append(f"财务风险：{kw}")
    
    return triggers

def detect_emotion(content):
    """检测情绪异常"""
    triggers = []
    
    # 负面情绪词
    neg_count = sum(1 for word in NEGATIVE_EMOTIONS if word in content)
    if neg_count >= 2:
        triggers.append(f"负面情绪：{neg_count}个")
    
    # 冲突信号
    for kw in CONFLICT_SIGNALS:
        if kw in content:
            triggers.append(f"冲突信号：{kw}")
    
    # 语气分析（连续感叹号/问号）
    if content.count("！") >= 3 or content.count("!") >= 3:
        triggers.append("连续感叹号")
    
    if content.count("?") >= 3 or content.count("?") >= 3:
        triggers.append("连续问号")
    
    return triggers

def load_alert_state():
    """加载通知状态（用于去重）"""
    if ALERT_STATE.exists():
        with open(ALERT_STATE) as f:
            return json.load(f)
    return {"notified_msgs": set(), "last_check": None}

def save_alert_state(state):
    """保存通知状态"""
    try:
        from notify_helper import atomic_write_json
        state["notified_msgs"] = list(state["notified_msgs"])[-1000:]
        atomic_write_json(ALERT_STATE, state)
    except Exception as e:
        log_event("emergency_detector", "save_alert_state_failed", {"error": str(e)}, level="warning")

def send_feishu_alert(content):
    """发送飞书私聊通知"""
    ok, detail = send_feishu_message(content, target=f"user:{USER_ID}", timeout=60, script="emergency_detector")
    if ok:
        print("✅ 通知已发送")
        return True
    print(f"❌ 发送失败：{detail}")
    return False

def log_alert(alert):
    """记录告警日志"""
    with open(ALERT_LOG, 'a') as f:
        f.write(f"{datetime.now().isoformat()} | {json.dumps(alert, ensure_ascii=False)}\n")

def check_recent_messages(hours=1):
    """检查最近的消息"""
    if not EPISODIC_DB.exists():
        print("⚠️ 数据库不存在")
        return []
    
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    c.execute('''
        SELECT chat_name, sender_name, content, timestamp, message_id
        FROM conversations
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
    ''', (since,))
    
    messages = c.fetchall()
    conn.close()
    
    return messages

def scan_for_alerts():
    """扫描紧急消息并发送通知"""
    print("=" * 70)
    print("🚨 紧急消息检测")
    print(f"⏰ 扫描时间：{datetime.now().isoformat()}")
    print("=" * 70)
    
    # 加载状态
    state = load_alert_state()
    notified = set(state.get("notified_msgs", []))
    
    # 获取最近 1 小时的消息
    messages = check_recent_messages(hours=1)
    print(f"📊 检测到 {len(messages)} 条新消息")
    
    alerts = []
    
    for msg in messages:
        chat_name, sender_name, content, timestamp, message_id = msg
        
        # 跳过已通知的
        if message_id in notified:
            continue
        
        # 检测紧急内容
        urgency_triggers = detect_urgency(content)
        emotion_triggers = detect_emotion(content)
        
        # 生成告警
        if urgency_triggers:
            alert = {
                "type": "🚨 紧急情况",
                "chat": chat_name,
                "sender": sender_name,
                "content": content,
                "time": timestamp,
                "triggers": urgency_triggers,
                "message_id": message_id
            }
            alerts.append(alert)
            notified.add(message_id)
        
        elif emotion_triggers:
            alert = {
                "type": "⚠️ 情绪异常",
                "chat": chat_name,
                "sender": sender_name,
                "content": content,
                "time": timestamp,
                "triggers": emotion_triggers,
                "message_id": message_id
            }
            alerts.append(alert)
            notified.add(message_id)
    
    # 发送通知
    if alerts:
        print(f"\n🚨 发现 {len(alerts)} 条告警")
        
        # 构建通知内容
        notification = ["🚨 **群聊情报网 - 紧急通知**\n"]
        
        for i, alert in enumerate(alerts[:5], 1):  # 最多 5 条
            notification.append(f"**{i}. {alert['type']}**")
            notification.append(f"📍 群组：{alert['chat']}")
            notification.append(f"👤 发言人：{alert['sender']}")
            notification.append(f"⏰ 时间：{alert['time']}")
            
            # 截取内容
            content_preview = alert['content'][:100] + "..." if len(alert['content']) > 100 else alert['content']
            notification.append(f"💬 内容：{content_preview}")
            
            notification.append(f"🎯 触发：{', '.join(alert['triggers'])}")
            notification.append("")
        
        notification.append("---")
        notification.append(f"*共检测到 {len(alerts)} 条告警，以上为前 5 条*")
        
        # 发送
        alert_content = "\n".join(notification)
        print("\n📤 发送通知:")
        print(alert_content[:500])
        
        send_feishu_alert(alert_content)
        
        # 记录日志
        for alert in alerts:
            log_alert(alert)
    else:
        print("\n✅ 无紧急消息")
    
    # 保存状态
    state["notified_msgs"] = list(notified)
    state["last_check"] = datetime.now().isoformat()
    save_alert_state(state)
    
    print("\n" + "=" * 70)
    return len(alerts)

if __name__ == "__main__":
    scan_for_alerts()