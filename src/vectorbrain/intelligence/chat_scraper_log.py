#!/usr/bin/env python3
"""
群聊情报网 - 消息抓取 (网关日志版)
从 OpenClaw 网关日志中读取群聊消息，更可靠且不需要额外 API 权限
"""

import sqlite3
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# VectorBrain 目录
VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
INTELLIGENCE_DIR = VECTORBRAIN_HOME / "intelligence"
DB_DIR = VECTORBRAIN_HOME / "memory"
LOG_DIR = Path("/tmp/openclaw")

# 确保目录存在
INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

# 数据库路径
EPISODIC_DB = DB_DIR / "episodic_memory.db"
STATE_FILE = INTELLIGENCE_DIR / "chat_scraper_state.json"

# 群 ID 到名称的映射
CHAT_NAMES = {
    "oc_9e6a7b5eab816dd3e081ddd1d4eb1565": "蜘蛛侠 Switch 设计沟通",
    "oc_6cb875b970150d9c71de17a154fbf893": "采购信息同步",
    "oc_07dbdcf4d5629024553e21bf485d0012": "醇龙箱包对接",
    "oc_cf8548f2c08dc91ec02a71e99498e744": "监督虾",
    "oc_4f9a5f0e671b6181048ed2964338545b": "agent",
}

# 用户 ID 到名称的映射（从之前的查询结果）
USER_NAMES = {
    "ou_cd2f520717fd4035c6ef3db89a53b748": "[YOUR_NAME]",
    "ou_d37bcc4a4c19f460aecd41d9fde760ba": "黄宗旨",
    "ou_42b5220858a0255fb79474c0568f46ee": "许瑶",
    "ou_9d9f47fa380aa29a4d96e17d2322c08b": "周凡",
    "ou_3b0d48a4e167ab0782a0f144bdb0568f": "张新",
    "ou_6e3402e1d65267de55bce6c2839284e1": "Emeng",
    "ou_cf6c6b3f5f33694abdd9ea755a953503": "易灵",
    "ou_db2ce1dc0712bef63febde15d5fc336b": "陈亮亮",
}

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            chat_name TEXT,
            message_id TEXT UNIQUE,
            sender_id TEXT,
            sender_name TEXT,
            content TEXT NOT NULL,
            timestamp TIMESTAMP,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_chat_time ON conversations(chat_id, timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_message_id ON conversations(message_id)')
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def load_state():
    """加载状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            data = json.load(f)
            # 转换为 set
            return {"processed_msgs": set(data.get("processed_msgs", []))}
    return {"processed_msgs": set()}

def save_state(state):
    """保存状态"""
    # 限制状态文件大小
    state["processed_msgs"] = list(state["processed_msgs"])[-10000:]
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False)

def parse_log_line(line):
    """解析日志行，提取消息信息"""
    try:
        log_entry = json.loads(line)
        
        # 检查是否是飞书群消息
        subsystem = log_entry.get("0", "")
        if "feishu" not in str(log_entry).lower():
            return None
        
        # 查找消息内容
        # 格式：feishu[default]: Feishu[default] message in group oc_xxx: 消息内容
        text = log_entry.get("1", "")
        
        # 匹配消息格式
        match = re.search(r'message in group (\w+): (.+)$', text)
        if not match:
            return None
        
        chat_id = match.group(1)
        content = match.group(2)
        
        # 获取发送者
        sender_match = re.search(r'from (\w+) in', text)
        sender_id = sender_match.group(1) if sender_match else "unknown"
        
        # 获取时间戳
        timestamp = log_entry.get("time", "")
        
        # 生成消息 ID（使用时间戳 + 内容哈希）
        msg_hash = hashlib.md5(f"{timestamp}{content}".encode()).hexdigest()[:16]
        message_id = f"{msg_hash}"
        
        return {
            "chat_id": chat_id,
            "chat_name": CHAT_NAMES.get(chat_id, "未知群"),
            "sender_id": sender_id,
            "sender_name": USER_NAMES.get(sender_id, sender_id),
            "content": content,
            "timestamp": timestamp,
            "message_id": message_id
        }
    except Exception as e:
        return None

def message_exists(message_id):
    """检查消息是否已存在"""
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM conversations WHERE message_id=?", (message_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def save_message(msg):
    """保存消息到数据库"""
    if message_exists(msg["message_id"]):
        return False
    
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO conversations 
            (chat_id, chat_name, message_id, sender_id, sender_name, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            msg["chat_id"],
            msg["chat_name"],
            msg["message_id"],
            msg["sender_id"],
            msg["sender_name"],
            msg["content"],
            msg["timestamp"],
            json.dumps({"source": "gateway_log"})
        ))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def scan_log_file(log_file, state):
    """扫描单个日志文件"""
    if not log_file.exists():
        return 0
    
    count = 0
    processed = state["processed_msgs"]
    
    with open(log_file) as f:
        for line in f:
            msg = parse_log_line(line.strip())
            if msg and msg["message_id"] not in processed:
                if save_message(msg):
                    processed.add(msg["message_id"])
                    count += 1
    
    return count

def main():
    """主函数"""
    import hashlib
    
    print("=" * 70)
    print("🕵️ 群聊情报网 - 消息抓取 (网关日志版)")
    print(f"⏰ 执行时间：{datetime.now().isoformat()}")
    print("=" * 70)
    
    # 初始化数据库
    init_database()
    
    # 加载状态
    state = load_state()
    
    total_new = 0
    
    # 扫描最近的日志文件（最近 7 天）
    today = datetime.now()
    for i in range(7):
        date = today - timedelta(days=i)
        log_file = LOG_DIR / f"openclaw-{date.strftime('%Y-%m-%d')}.log"
        
        if log_file.exists():
            print(f"\n📄 扫描日志：{log_file.name}")
            count = scan_log_file(log_file, state)
            print(f"   新增 {count} 条消息")
            total_new += count
        else:
            print(f"\n⏭️  跳过：{log_file.name} (不存在)")
    
    # 保存状态
    save_state(state)
    
    # 统计
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    c.execute("SELECT chat_name, COUNT(*) FROM conversations GROUP BY chat_name")
    stats = dict(c.fetchall())
    conn.close()
    
    print("\n" + "=" * 70)
    print("📊 本次执行完成")
    print(f"   新增消息：{total_new} 条")
    print("\n📈 数据库统计:")
    for chat_name, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   • {chat_name}: {count} 条")
    print("=" * 70)

if __name__ == "__main__":
    main()
