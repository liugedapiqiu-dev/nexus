#!/usr/bin/env python3
"""
群聊情报网 - 消息抓取与向量化存储
使用 Lark SDK 获取飞书群消息，每小时自动执行
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

# 尝试导入 lark_oapi SDK
try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1.model import *
    SDK_AVAILABLE = True
except ImportError:
    print("⚠️ 未安装 lark_oapi SDK，请运行：pip install lark-oapi")
    SDK_AVAILABLE = False

# VectorBrain 目录
VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
INTELLIGENCE_DIR = VECTORBRAIN_HOME / "intelligence"
DB_DIR = VECTORBRAIN_HOME / "memory"

# 确保目录存在
INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

# 数据库路径
KNOWLEDGE_DB = DB_DIR / "knowledge_memory.db"
EPISODIC_DB = DB_DIR / "episodic_memory.db"
STATE_FILE = INTELLIGENCE_DIR / "chat_scraper_state.json"

# 需要监控的群列表
# 请在 .env 或 openclaw.json 中配置你的飞书群 ID
MONITORED_CHATS = {
    "[YOUR_GROUP_ID_1]": "群组名称1",
    "[YOUR_GROUP_ID_2]": "群组名称2",
}

# 从 OpenClaw 配置读取凭据
def get_lark_credentials():
    """从 OpenClaw 配置获取飞书凭据"""
    openclaw_config = Path.home() / ".openclaw" / "openclaw.json"
    
    if openclaw_config.exists():
        with open(openclaw_config) as f:
            config = json.load(f)
            app_id = config.get("channels", {}).get("feishu", {}).get("appId")
            app_secret = config.get("channels", {}).get("feishu", {}).get("appSecret")
            
            if app_id and app_secret:
                print(f"✅ 从 OpenClaw 配置读取到 appId: {app_id[:10]}...")
                return app_id, app_secret
    
    return None, None

def init_client(app_id, app_secret):
    """初始化 Lark 客户端"""
    return lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.WARNING) \
        .build()

def fetch_chat_messages_with_sdk(client, chat_id, start_time=None):
    """使用 Lark SDK 获取群消息"""
    messages = []
    page_token = None
    page_num = 1
    
    print(f"   📥 正在同步消息流...")
    
    while True:
        # 构建请求（参考成功的脚本）
        builder = ListMessageRequest.builder() \
            .container_id_type("chat") \
            .container_id(chat_id) \
            .page_size(50) \
            .sort_type("ByCreateTimeDesc")  # 按时间降序，获取最新的
        
        if page_token:
            builder.page_token(page_token)
            
        req = builder.build()
        resp = client.im.v1.message.list(req)
        
        if not resp.success():
            print(f"   ❌ 接口异常：{resp.msg}")
            break
        
        items = resp.data.items or []
        if not items:
            break
        
        # 处理消息
        for msg in items:
            ts = int(msg.create_time) // 1000
            dt_str = datetime.fromtimestamp(ts).isoformat()
            
            # 检查是否超过起始时间
            if start_time:
                msg_time = datetime.fromtimestamp(ts)
                if msg_time < start_time:
                    continue
            
            messages.append({
                "message_id": msg.message_id,
                "sender_id": msg.sender.id if msg.sender else "unknown",
                "create_time": dt_str,
                "content": msg.body.content if msg.body else "",
                "msg_type": msg.msg_type
            })
        
        print(f"\r   ✅ [Page {page_num}] 已获取 {len(messages)} 条消息...", end="", flush=True)
        
        if not resp.data.has_more:
            break
        
        page_token = resp.data.page_token
        page_num += 1
    
    print(f"\n   共获取 {len(messages)} 条消息")
    return messages

def load_state():
    """加载上次执行状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_check": {}, "message_counts": {}}

def save_state(state):
    """保存执行状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_feishu_token():
    """获取飞书 access_token"""
    import requests
    
    # 尝试从 OpenClaw 配置文件读取
    openclaw_config = Path.home() / ".openclaw" / "openclaw.json"
    
    if openclaw_config.exists():
        with open(openclaw_config) as f:
            config = json.load(f)
            # OpenClaw 配置格式：channels.feishu
            appId = config.get("channels", {}).get("feishu", {}).get("appId")
            appSecret = config.get("channels", {}).get("feishu", {}).get("appSecret")
            
            if appId and appSecret:
                print(f"✅ 从 OpenClaw 配置读取到 appId: {appId[:10]}...")
            else:
                print("⚠️ OpenClaw 配置中没有飞书凭据")
                appId = None
                appSecret = None
    else:
        print("⚠️ 未找到 OpenClaw 配置文件")
        appId = None
        appSecret = None
    
    if not appId or not appSecret:
        # 尝试从环境变量读取
        appId = os.getenv("FEISHU_APP_ID")
        appSecret = os.getenv("FEISHU_APP_SECRET")
    
    if not appId or not appSecret:
        print("⚠️ 缺少飞书 API 配置")
        print("💡 请确保 ~/.openclaw/openclaw.json 中有飞书配置")
        return None
    
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(token_url, json={"app_id": appId, "app_secret": appSecret})
    data = resp.json()
    
    if data.get("code") != 0:
        print(f"⚠️ 获取 token 失败：{data}")
        return None
    
    return data["tenant_access_token"]

def fetch_chat_messages(chat_id, token, start_time=None):
    """获取群聊消息"""
    import requests
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 尝试飞书 API v1 - message 列表接口
    # 使用 chat_id 作为 container_id，不需要 container_id_type 参数
    messages_url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/messages?order=desc"
    
    if start_time:
        messages_url += f"&start_time={int(start_time.timestamp() * 1000)}"
    
    try:
        resp = requests.get(messages_url, headers=headers, timeout=30)
        data = resp.json()
        
        if data.get("code") != 0:
            print(f"⚠️ 获取群 {chat_id} 消息失败：{data}")
            return []
        
        items = data.get("data", {}).get("items", [])
        return items
    except Exception as e:
        print(f"⚠️ 请求失败：{e}")
        return []

def message_exists(chat_id, message_id):
    """检查消息是否已存在"""
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM conversations WHERE chat_id=? AND message_id=?", (chat_id, message_id))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def save_message(chat_id, chat_name, message):
    """保存单条消息到数据库"""
    message_id = message.get("message_id", "")
    sender_id = message.get("sender_id", "")
    content = message.get("content", "")
    timestamp = message.get("create_time", "")
    
    # 解析消息内容
    if isinstance(content, dict):
        content = content.get("text", "")
    if isinstance(timestamp, int):
        timestamp = datetime.fromtimestamp(timestamp / 1000).isoformat()
    
    # 检查是否已存在
    if message_exists(chat_id, message_id):
        return False
    
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO conversations 
            (chat_id, chat_name, message_id, sender_id, sender_name, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_id,
            chat_name,
            message_id,
            sender_id,
            message.get("sender_type", ""),
            content,
            timestamp,
            json.dumps({"message_type": message.get("message_type", "")})
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"⚠️ 保存消息失败：{e}")
        return False
    finally:
        conn.close()

def extract_knowledge(messages, chat_name):
    """从消息中提取重要知识"""
    # 简单规则：包含特定关键词的消息标记为重要
    keywords = ["采购", "订单", "交期", "质量", "问题", "确认", "样品", "验货", "付款", "合同"]
    
    important_messages = []
    for msg in messages[:20]:  # 只分析最近 20 条
        content = msg.get("content", "")
        if isinstance(content, dict):
            content = content.get("text", "")
        
        # 检查是否包含关键词
        if any(kw in str(content) for kw in keywords):
            important_messages.append({
                "content": content,
                "chat_name": chat_name,
                "timestamp": msg.get("create_time", ""),
                "importance": 0.8
            })
    
    return important_messages

def save_knowledge(knowledge_items):
    """保存重要知识到知识库"""
    if not knowledge_items:
        return 0
    
    conn = sqlite3.connect(KNOWLEDGE_DB)
    c = conn.cursor()
    
    count = 0
    for item in knowledge_items:
        try:
            c.execute('''
                INSERT INTO knowledge (content, metadata, source, importance)
                VALUES (?, ?, ?, ?)
            ''', (
                item["content"],
                json.dumps({"chat_name": item["chat_name"], "timestamp": item["timestamp"]}),
                "chat_intelligence",
                item["importance"]
            ))
            count += 1
        except Exception as e:
            print(f"⚠️ 保存知识失败：{e}")
    
    conn.commit()
    conn.close()
    return count

def main():
    """主函数"""
    print("=" * 60)
    print("🕵️ 群聊情报网 - 消息抓取")
    print(f"⏰ 执行时间：{datetime.now().isoformat()}")
    print("=" * 60)
    
    # 初始化数据库
    init_databases()
    
    # 加载状态
    state = load_state()
    
    # 获取 token
    token = get_feishu_token()
    if not token:
        print("❌ 无法获取飞书 token，退出")
        sys.exit(1)
    
    total_new = 0
    all_messages = {}
    
    # 遍历所有群
    for chat_id, chat_name in MONITORED_CHATS.items():
        print(f"\n📍 检查群：{chat_name}")
        
        # 获取上次检查时间
        last_check = state.get("last_check", {}).get(chat_id)
        start_time = None
        if last_check:
            start_time = datetime.fromisoformat(last_check)
            print(f"   上次检查：{last_check}")
        
        # 获取消息
        messages = fetch_chat_messages(chat_id, token, start_time)
        print(f"   获取到 {len(messages)} 条消息")
        
        # 保存新消息
        new_count = 0
        chat_messages = []
        for msg in messages:
            if save_message(chat_id, chat_name, msg):
                new_count += 1
                chat_messages.append(msg)
        
        print(f"   ✅ 新增 {new_count} 条消息")
        total_new += new_count
        all_messages[chat_name] = chat_messages
        
        # 更新状态
        state.setdefault("last_check", {})[chat_id] = datetime.now().isoformat()
        state.setdefault("message_counts", {})[chat_id] = state["message_counts"].get(chat_id, 0) + new_count
    
    # 提取并保存重要知识
    print("\n🧠 提取重要知识...")
    all_knowledge = []
    for chat_name, messages in all_messages.items():
        knowledge = extract_knowledge(messages, chat_name)
        all_knowledge.extend(knowledge)
    
    knowledge_count = save_knowledge(all_knowledge)
    print(f"✅ 保存 {knowledge_count} 条重要知识")
    
    # 保存状态
    save_state(state)
    
    # 保存详细日志
    log_file = INTELLIGENCE_DIR / f"chat_log_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(log_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_new_messages": total_new,
            "total_knowledge_items": knowledge_count,
            "messages_by_chat": {k: len(v) for k, v in all_messages.items()}
        }, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"📊 本次执行完成")
    print(f"   新增消息：{total_new} 条")
    print(f"   提取知识：{knowledge_count} 条")
    print(f"   日志文件：{log_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
