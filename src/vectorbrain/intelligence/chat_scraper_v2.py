#!/usr/bin/env python3
"""
群聊情报网 - 消息抓取与向量化存储 (V2.0 - Lark SDK 版)
使用 Lark SDK 获取飞书群消息，参考成功脚本的架构
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import time
import argparse
import random

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
COMMON_DIR = VECTORBRAIN_HOME / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from notify_helper import log_event as common_log_event

# 导入 Lark SDK
try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1.model import *
    from lark_oapi.api.im.v1.resource.chat import ListChatRequest
    SDK_AVAILABLE = True
except ImportError:
    print("⚠️ 未安装 lark_oapi SDK")
    print("💡 请运行：pip3 install lark-oapi")
    SDK_AVAILABLE = False
    sys.exit(1)

# ========== 配置区域 ==========
VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
INTELLIGENCE_DIR = VECTORBRAIN_HOME / "intelligence"
DB_DIR = VECTORBRAIN_HOME / "memory"

INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

EPISODIC_DB = DB_DIR / "episodic_memory.db"
KNOWLEDGE_DB = DB_DIR / "knowledge_memory.db"
STATE_FILE = VECTORBRAIN_HOME / "chat_scraper_state.json"
EVENT_LOG_FILE = VECTORBRAIN_HOME / "chat_scraper_log.jsonl"
LOCK_FILE = VECTORBRAIN_HOME / "chat_scraper.lock"

# 监控的群列表（兼容旧配置：作为”名称兜底/白名单”使用）
# 现在默认会动态枚举机器人可见的全部群聊（im.v1.chat.list），然后用该表补齐更友好的群名称。
# 请在 .env 中配置你的飞书群 ID
MONITORED_CHATS = {
    “[YOUR_GROUP_ID_1]”: “群组名称1”,
    “[YOUR_GROUP_ID_2]”: “群组名称2”,
}

# 用户 ID 到名称的映射
# 请在 .env 或配置中配置你的用户 ID
USER_NAMES = {
    “[YOUR_USER_ID]”: “[YOUR_NAME]”,
}
}

# ========== 数据库初始化 ==========
def init_databases():
    """初始化数据库表结构"""
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
            msg_type TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_chat_time ON conversations(chat_id, timestamp)')
    conn.commit()
    conn.close()
    
    # 知识库
    conn = sqlite3.connect(KNOWLEDGE_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            metadata TEXT,
            source TEXT,
            importance REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    
    print("✅ 数据库初始化完成")

# ========== Lark SDK 客户端 ==========
def get_credentials():
    """从 OpenClaw 配置获取飞书凭据"""
    config_file = Path.home() / ".openclaw" / "openclaw.json"
    if not config_file.exists():
        print(f"❌ 未找到配置文件：{config_file}")
        return None, None

    try:
        with open(config_file, encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ OpenClaw 配置文件 JSON 格式错误：{config_file}")
        print(f"   位置：line {e.lineno}, column {e.colno}")
        print("   建议先执行：python3 -m json.tool ~/.openclaw/openclaw.json >/dev/null")
        log_event("run_failed", {
            "reason": "invalid_openclaw_json",
            "file": str(config_file),
            "line": e.lineno,
            "column": e.colno,
            "message": e.msg,
        })
        return None, None
    except Exception as e:
        print(f"❌ 读取 OpenClaw 配置失败：{e}")
        log_event("run_failed", {"reason": "read_openclaw_config_failed", "error": str(e)})
        return None, None

    app_id = config.get("channels", {}).get("feishu", {}).get("appId")
    app_secret = config.get("channels", {}).get("feishu", {}).get("appSecret")
    if app_id and app_secret:
        print(f"✅ 从 OpenClaw 配置读取到 appId: {app_id[:10]}...")
        return app_id, app_secret

    print("❌ OpenClaw 配置中未找到 Feishu appId/appSecret")
    return None, None

def init_client(app_id, app_secret):
    """初始化 Lark 客户端"""
    return lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.WARNING) \
        .build()

# ========== 群列表枚举 ==========
def list_accessible_chats(client):
    """枚举机器人当前可见/可访问的所有群聊（用于自动发现群 id + 群名）"""
    chats = []
    page_token = None

    while True:
        builder = ListChatRequest.builder().page_size(100)
        if page_token:
            builder.page_token(page_token)
        req = builder.build()

        resp = client.im.v1.chat.list(req)
        if not resp.success():
            print(f"❌ 群列表获取失败：{resp.code} {resp.msg}")
            break

        items = resp.data.items or []
        for it in items:
            chat_id = getattr(it, 'chat_id', None)
            name = getattr(it, 'name', None) or ""
            if chat_id:
                chats.append((chat_id, name))

        if not resp.data.has_more:
            break
        page_token = resp.data.page_token

    return chats

# ========== 消息获取 ==========
def fetch_messages(client, chat_id, start_time=None, max_pages=50):
    """使用 Lark SDK 获取群消息

    注意：此前逻辑在遇到 msg_time < start_time 时使用 continue，导致“越翻越旧但仍继续翻页”，
    最终可能出现所有页都显示 0 条（因为全被过滤掉）。

    修复：当按时间倒序翻页时，一旦遇到比 start_time 更早的消息，直接终止分页。
    """
    messages = []
    page_token = None
    page_num = 1

    while True:
        if max_pages and page_num > max_pages:
            break

        builder = ListMessageRequest.builder() \
            .container_id_type("chat") \
            .container_id(chat_id) \
            .page_size(50) \
            .sort_type("ByCreateTimeDesc")

        if page_token:
            builder.page_token(page_token)

        req = builder.build()
        resp = client.im.v1.message.list(req)

        if not resp.success():
            print(f"   ❌ API 错误：{resp.code} {resp.msg}")
            break

        items = resp.data.items or []
        if not items:
            break

        stop_paging = False
        for msg in items:
            ts = int(msg.create_time) // 1000
            msg_time = datetime.fromtimestamp(ts)

            # 时间过滤：因为是倒序，遇到更早的消息就可以停止继续翻页
            if start_time and msg_time < start_time:
                stop_paging = True
                break

            content = parse_message_content(msg)

            messages.append({
                "message_id": msg.message_id,
                "sender_id": msg.sender.id if msg.sender else "unknown",
                "create_time": msg_time.isoformat(),
                "content": content,
                "msg_type": msg.msg_type
            })

        print(f"\r   📥 Page {page_num}: {len(messages)} 条...", end="", flush=True)

        if stop_paging or (not resp.data.has_more):
            break

        page_token = resp.data.page_token
        page_num += 1
        time.sleep(0.1)

    print(f"\n   ✅ 共获取 {len(messages)} 条消息")
    return messages

def parse_message_content(msg):
    """解析消息内容"""
    try:
        content = json.loads(msg.body.content) if msg.body else {}
        
        if msg.msg_type == "text":
            return content.get("text", "")
        elif msg.msg_type == "post":
            text_parts = []
            for element in content.get("content", []):
                for item in element:
                    if item.get("tag") == "text":
                        text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
        elif msg.msg_type == "image":
            return "【图片】"
        elif msg.msg_type == "file":
            return f"【文件：{content.get('file_name', '')}】"
        else:
            return f"【{msg.msg_type}】"
    except:
        return "【解析失败】"

# ========== 数据存储 ==========
def message_exists(message_id):
    """检查消息是否已存在"""
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM conversations WHERE message_id=?", (message_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def save_messages(chat_id, chat_name, messages):
    """保存消息到数据库"""
    conn = sqlite3.connect(EPISODIC_DB)
    c = conn.cursor()
    
    new_count = 0
    for msg in messages:
        if not message_exists(msg["message_id"]):
            sender_name = USER_NAMES.get(msg["sender_id"], msg["sender_id"])
            
            c.execute('''
                INSERT INTO conversations 
                (chat_id, chat_name, message_id, sender_id, sender_name, content, timestamp, msg_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chat_id, chat_name,
                msg["message_id"], msg["sender_id"], sender_name,
                msg["content"], msg["create_time"], msg["msg_type"],
                json.dumps({"source": "lark_sdk"})
            ))
            new_count += 1
    
    conn.commit()
    conn.close()
    return new_count

def extract_knowledge(messages, chat_name):
    """从消息中提取重要知识"""
    keywords = ["采购", "订单", "交期", "质量", "问题", "确认", "样品", "验货", "付款", "合同", "紧急"]
    important = []
    
    for msg in messages[:30]:
        content = msg.get("content", "")
        if any(kw in content for kw in keywords):
            important.append({
                "content": content,
                "chat_name": chat_name,
                "timestamp": msg.get("create_time", ""),
                "importance": 0.8
            })
    
    return important

def save_knowledge(items):
    """保存重要知识"""
    if not items:
        return 0
    
    conn = sqlite3.connect(KNOWLEDGE_DB)
    c = conn.cursor()
    
    count = 0
    for item in items:
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
            pass
    
    conn.commit()
    conn.close()
    return count

# ========== 状态管理 ==========
def log_event(event_type, details):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "details": details,
    }
    try:
        with open(EVENT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def acquire_lock_or_exit():
    """简易防重入：锁文件存在且 pid 存活则退出；否则接管旧锁。"""
    current_pid = os.getpid()

    if LOCK_FILE.exists():
        try:
            data = json.loads(LOCK_FILE.read_text(encoding='utf-8'))
            old_pid = int(data.get('pid', 0))
            if old_pid > 0:
                try:
                    os.kill(old_pid, 0)
                    print(f"⚠️ 检测到已有抓取进程运行中（PID {old_pid}），本次退出")
                    log_event('skip_locked', {"pid": old_pid})
                    sys.exit(0)
                except OSError:
                    pass
        except Exception:
            pass

    LOCK_FILE.write_text(json.dumps({
        "pid": current_pid,
        "started_at": datetime.now().isoformat()
    }, ensure_ascii=False, indent=2), encoding='utf-8')


def release_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def load_state():
    """加载状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            data = json.load(f)
            # 转换为 datetime
            last_check = {}
            for k, v in data.get("last_check", {}).items():
                try:
                    last_check[k] = datetime.fromisoformat(v)
                except Exception as e:
                    common_log_event("chat_scraper_v2", "load_state_invalid_datetime", {"chat_id": k, "value": v, "error": str(e)}, level="warning")
            return {"last_check": last_check, "message_counts": data.get("message_counts", {})}
    return {"last_check": {}, "message_counts": {}}

def save_state(state):
    """保存状态"""
    save_data = {
        "last_check": {k: v.isoformat() for k, v in state["last_check"].items()},
        "message_counts": state["message_counts"]
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

# ========== 主函数 ==========
def _parse_args():
    p = argparse.ArgumentParser(description="Feishu chat scraper (Lark SDK) → VectorBrain episodic_memory.db")
    p.add_argument('--mode', choices=['incremental', 'full'], default='incremental', help='incremental=use state last_check, full=backfill from earliest')
    p.add_argument('--max-pages', type=int, default=0, help='per-chat max pages (0=unlimited)')
    p.add_argument('--shuffle', action='store_true', help='shuffle chat order (helps spread rate limits)')
    p.add_argument('--no-emergency-scan', action='store_true', help='skip emergency_detector scan')
    return p.parse_args()


def main():
    """主函数"""
    args = _parse_args()
    acquire_lock_or_exit()

    try:
        print("=" * 70)
        print("🕵️ 群聊情报网 - 消息抓取 (Lark SDK 版)")
        print(f"⏰ 执行时间：{datetime.now().isoformat()}")
        print(f"🎛️ 模式：{args.mode}  max_pages={args.max_pages or '∞'}")
        print("=" * 70)
        log_event("run_started", {"mode": args.mode, "max_pages": args.max_pages or 0})

        if not SDK_AVAILABLE:
            print("❌ Lark SDK 未安装，退出")
            log_event("run_failed", {"reason": "sdk_unavailable"})
            sys.exit(1)

        # 初始化
        init_databases()

        # 获取凭据
        app_id, app_secret = get_credentials()
        if not app_id or not app_secret:
            print("❌ 未找到飞书凭据，退出")
            log_event("run_failed", {"reason": "missing_credentials"})
            sys.exit(1)

        # 初始化客户端
        client = init_client(app_id, app_secret)
        print("✅ Lark 客户端初始化成功")

        # 加载状态
        state = load_state()

        total_new = 0
        total_knowledge = 0
        total_chats = 0

        # 自动发现机器人可见群聊
        chats_raw = list_accessible_chats(client)
        if not chats_raw:
            print("❌ 未发现任何可访问群聊（机器人可能未入群，或权限不足）")
            log_event("run_failed", {"reason": "no_accessible_chats"})
            return

        # chat.list 返回 name 可能为空；用 MONITORED_CHATS 做兜底显示名
        chats = [(cid, (MONITORED_CHATS.get(cid) or nm or cid)) for cid, nm in chats_raw]

        if args.shuffle:
            random.shuffle(chats)

        print(f"✅ 发现 {len(chats)} 个可访问群聊")

        for chat_id, chat_name in chats:
            total_chats += 1
            print(f"\n📍 检查群：{chat_name}")

            last_check = None if args.mode == 'full' else state["last_check"].get(chat_id)
            messages = fetch_messages(client, chat_id, last_check, max_pages=(args.max_pages or None))

            new_count = 0
            if messages:
                new_count = save_messages(chat_id, chat_name, messages)
                print(f"   💾 新增 {new_count} 条消息")
                total_new += new_count

                knowledge = extract_knowledge(messages, chat_name)
                k_count = save_knowledge(knowledge)
                total_knowledge += k_count
            log_event("chat_checked", {
                "chat_id": chat_id,
                "chat_name": chat_name,
                "mode": args.mode,
                "fetched": len(messages),
                "inserted": new_count
            })

            # 只在增量模式更新 last_check
            if args.mode == 'incremental':
                if messages:
                    try:
                        newest = max(datetime.fromisoformat(m["create_time"]) for m in messages)
                        state["last_check"][chat_id] = newest
                    except Exception:
                        state["last_check"][chat_id] = state["last_check"].get(chat_id)

                state["message_counts"][chat_id] = state["message_counts"].get(chat_id, 0) + len(messages)

        if args.mode == 'incremental':
            save_state(state)

        if not args.no_emergency_scan:
            print("\n🚨 执行紧急消息检测...")
            try:
                from emergency_detector import scan_for_alerts
                alert_count = scan_for_alerts()
                if alert_count > 0:
                    print(f"⚠️ 发现 {alert_count} 条紧急告警，已通知")
            except Exception as e:
                print(f"⚠️ 紧急检测异常：{e}")

        print("\n" + "=" * 70)
        print("📊 执行完成")
        print(f"   群聊数：{total_chats}")
        print(f"   新增消息：{total_new} 条")
        print(f"   提取知识：{total_knowledge} 条")
        print("=" * 70)
        log_event("run_completed", {"mode": args.mode, "chats": total_chats, "inserted": total_new, "knowledge": total_knowledge})
    finally:
        release_lock()


if __name__ == "__main__":
    main()
