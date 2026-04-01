#!/usr/bin/env python3
"""
状态标记（2026-03-19）：
- 当前归类：专题群旁路脚本 / 非飞书全群抓取主链
- 主判据替代：飞书全群抓取主链为 `intelligence/chat_scraper_v2.py`
- 处理原则：仅保留专题场景参考，不能覆盖全群抓取口径


蜘蛛侠 Switch 设计沟通群监控脚本（方案 A - 被动接收模式）
- 使用 lark_oapi SDK 获取群消息
- 只在工作日工作时间分析（周一到周五 9:00-12:30, 14:00-18:00）
- 过滤已读消息和无意义内容
- 分析发消息人的岗位和意图
- 飞书私聊汇报给健豪
"""

import lark_oapi as lark
from lark_oapi.api.im.v1.model import *
import json
import sqlite3
import os
import sys
from datetime import datetime, timedelta
import subprocess
from pathlib import Path

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
COMMON_DIR = VECTORBRAIN_HOME / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from notify_helper import atomic_write_json, send_feishu_message, log_event


# ========== 配置 ==========
APP_ID = "cli_a9b65317fc79dbc4"
APP_SECRET = "OsxOHrSEPZPsvC55fR1lKdtUDpdH5sx2"
CHAT_ID = "oc_9e6a7b5eab816dd3e081ddd1d4eb1565"
CHAT_NAME = "蜘蛛侠 Switch 设计沟通"
USER_ID = "ou_cd2f520717fd4035c6ef3db89a53b748"  # 健豪的飞书 ID
LAST_CHECK_FILE = "/home/user/.vectorbrain/state/spiderman_group_last_msg_id.txt"
VECBRAIN_DB = "/home/user/.vectorbrain/memory/knowledge_memory.db"

# 成员信息
MEMBERS = {
    "ou_d37bcc4a4c19f460aecd41d9fde760ba": {"name": "黄宗旨", "role": "设计主管", "dept": "设计部"},
    "ou_cd2f520717fd4035c6ef3db89a53b748": {"name": "[YOUR_NAME]", "role": "老板", "dept": "管理层"},
    "ou_42b5220858a0255fb79474c0568f46ee": {"name": "许瑶", "role": "管理助理", "dept": "管理层"},
    "ou_9d9f47fa380aa29a4d96e17d2322c08b": {"name": "周凡", "role": "产品开发", "dept": "产品开发部", "note": "急性子，口头汇报"},
    "ou_3b0d48a4e167ab0782a0f144bdb0568f": {"name": "张新", "role": "产品开发助理", "dept": "产品开发部", "note": "记录官"},
    "ou_6e3402e1d65267de55bce6c2839284e1": {"name": "Emeng", "role": "领导", "dept": "管理层"},
    "ou_cf6c6b3f5f33694abdd9ea755a953503": {"name": "易灵", "role": "产品开发助理", "dept": "产品开发部", "note": "记录官"},
    "ou_db2ce1dc0712bef63febde15d5fc336b": {"name": "陈亮亮", "role": "物流", "dept": "物流部"},
}

# 无意义内容过滤
STOP_WORDS = {'收到', '好的', '明白', 'OK', 'ok', '嗯', '哦', '啊', '哈', '了', '的', '是', '在', '有'}

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def init_client():
    return lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).log_level(lark.LogLevel.WARNING).build()

def get_last_msg_id():
    try:
        with open(LAST_CHECK_FILE, 'r', encoding='utf-8') as f:
            raw = f.read().strip()
        if not raw:
            return None
        if raw.startswith('{'):
            data = json.loads(raw)
            return data.get('last_msg_id')
        return raw
    except Exception as e:
        log_event("monitor_spiderman_group_v2", "get_last_msg_id_failed", {"error": str(e)}, level="warning")
        return None

def save_last_msg_id(msg_id):
    atomic_write_json(Path(LAST_CHECK_FILE), {"last_msg_id": msg_id, "updated_at": datetime.now().isoformat()})

def is_work_time():
    now = datetime.now()
    if now.weekday() >= 5:  # 周末
        log("❌ 周末，不监控")
        return False
    hour = now.hour + now.minute / 60
    if (9 <= hour < 12.5) or (14 <= hour < 18):
        return True
    log(f"❌ 非工作时间（当前：{hour:.2f}），不监控")
    return False

def get_messages_since(client, last_msg_id):
    """获取上次检查后的新消息"""
    messages = []
    page_token = None
    
    log("📥 开始获取群消息...")
    
    while True:
        builder = ListMessageRequest.builder() \
            .container_id_type("chat") \
            .container_id(CHAT_ID) \
            .page_size(50) \
            .sort_type("ByCreateTimeAsc")
        
        if page_token:
            builder.page_token(page_token)
        
        req = builder.build()
        resp = client.im.v1.message.list(req)
        
        if not resp.success():
            log(f"❌ 获取消息失败：{resp.msg}")
            break
        
        for msg in resp.data.items:
            # 如果有 last_msg_id，只获取之后的消息
            if last_msg_id and msg.message_id <= last_msg_id:
                continue
            
            # 跳过无意义消息
            if should_skip_message(msg):
                continue
            
            messages.append(parse_message(msg))
        
        if not resp.data.has_more:
            break
        
        page_token = resp.data.page_token
    
    log(f"✅ 获取到 {len(messages)} 条新消息")
    return messages

def should_skip_message(msg):
    """过滤无意义的消息"""
    # 跳过系统消息（如果有）
    if msg.msg_type == "system":
        return True
    
    # 跳过表情包、图片等
    if msg.msg_type in ['sticker', 'image', 'file', 'video', 'audio']:
        return True
    
    # 跳过太短的消息
    content = msg.body.content if msg.body else ""
    if isinstance(content, str) and len(content) < 3:
        return True
    
    # 跳过纯语气词
    if content.strip() in STOP_WORDS:
        return True
    
    return False

def parse_message(msg):
    """解析消息对象"""
    # 获取消息内容
    content_txt = ""
    if msg.body and msg.body.content:
        try:
            body_json = json.loads(msg.body.content)
            if msg.msg_type == "text":
                content_txt = body_json.get("text", "")
            elif msg.msg_type == "post":
                content_txt = " ".join([item.get("text", "") for element in body_json.get("content", []) for item in element if item.get("tag") == "text"])
            else:
                content_txt = f"【{msg.msg_type}】"
        except Exception as e:
            log_event("monitor_spiderman_group_v2", "parse_message_body_failed", {"error": str(e)}, level="warning")
            content_txt = str(msg.body.content)[:50]
    
    # 处理时间
    msg_time = datetime.now()
    try:
        create_ts = int(msg.create_time) if isinstance(msg.create_time, str) else msg.create_time
        msg_time = datetime.fromtimestamp(create_ts / 1000)
    except Exception as e:
        log_event("monitor_spiderman_group_v2", "parse_message_time_failed", {"error": str(e)}, level="warning")
    
    return {
        "message_id": msg.message_id,
        "sender_id": msg.sender.id if msg.sender else "",
        "content": content_txt,
        "time": msg_time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": msg.msg_type
    }

def analyze_intent(content, member_info):
    """分析消息意图"""
    intent = "普通交流"
    urgency = "普通"
    
    # 关键词匹配
    if any(kw in content for kw in ['急', '赶紧', '马上', '快点', '紧急']):
        urgency = "紧急"
    
    if any(kw in content for kw in ['问题', '错误', '不行', '失败', 'bug', '报错']):
        intent = "问题反馈"
    elif any(kw in content for kw in ['完成', '好了', 'ok', '搞定', '上线']):
        intent = "进度汇报"
    elif any(kw in content for kw in ['需要', '想要', '要', '帮忙', '请']):
        intent = "需求提出"
    elif any(kw in content for kw in ['设计', '图', '修改', '调整', '颜色', '字体']):
        intent = "设计相关"
    elif any(kw in content for kw in ['会议', '开会', '几点', '时间']):
        intent = "会议安排"
    
    return {
        "intent": intent,
        "urgency": urgency
    }

def generate_vector(content, member_info, analysis):
    """生成消息的向量表示"""
    vector_content = f"""
群组：蜘蛛侠 Switch 设计沟通
发送人：{member_info.get('name', '未知')}
岗位：{member_info.get('role', '未知')}
部门：{member_info.get('dept', '未知')}
时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
意图：{analysis.get('intent', '未知')}
紧急度：{analysis.get('urgency', '未知')}
内容：{content}
"""
    return vector_content

def save_to_vectorbrain(messages):
    """保存消息到 VectorBrain 向量数据库（可选，失败不影响主流程）"""
    import subprocess
    
    try:
        conn = sqlite3.connect(VECBRAIN_DB)
        cursor = conn.cursor()
        
        for msg in messages:
            sender_id = msg.get('sender_id', '')
            member_info = MEMBERS.get(sender_id, {"name": "未知", "role": "未知", "dept": "未知"})
            analysis = analyze_intent(msg['content'], member_info)
            
            # 生成向量内容
            vector_content = generate_vector(msg['content'], member_info, analysis)
            
            # 用 bge-m3 生成向量（设置超时，避免卡顿）
            try:
                result = subprocess.run(
                    ['ollama', 'run', 'bge-m3', vector_content[:4000]],
                    capture_output=True, text=True, timeout=60  # 30 秒超时
                )
                
                if result.returncode == 0:
                    vector_str = result.stdout.strip()
                else:
                    log(f"⚠️ 向量生成失败，跳过：{msg['message_id']}")
                    continue
            except subprocess.TimeoutExpired:
                log(f"⚠️ 向量生成超时，跳过：{msg['message_id']}")
                continue
            
            # 存入数据库
            key = f"spiderman_msg_{msg['message_id']}_{msg['time'].replace(':', '').replace(' ', '_')}"
            value = json.dumps({
                "group": CHAT_NAME,
                "sender": member_info.get('name', '未知'),
                "role": member_info.get('role', '未知'),
                "content": msg['content'],
                "time": msg['time'],
                "intent": analysis.get('intent', '未知'),
                "urgency": analysis.get('urgency', '普通')
            }, ensure_ascii=False)
            
            cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, confidence, embedding_vector, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            """, ('spiderman_group_messages', key, value, 'monitor_script', 1.0, vector_str))
            
            log(f"  ✅ 已保存：{member_info.get('name', '未知')} - {msg['content'][:30]}...")
        
        conn.commit()
        conn.close()
        log(f"✅ 向量库更新完成")
    except Exception as e:
        log(f"⚠️ 向量库保存失败（不影响汇报）：{e}")

def send_feishu_notification(report):
    """发送飞书私聊通知"""
    if not report:
        return
    
    msg_content = f"🕷️ **蜘蛛侠群监控汇报**\n\n"
    msg_content += f"监控时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    msg_content += f"新消息数：{len(report)}\n\n"
    
    for item in report:
        msg_content += f"---\n"
        msg_content += f"👤 **{item['sender']}** ({item['role']})\n"
        if item.get('note'):
            msg_content += f"📝 备注：{item['note']}\n"
        msg_content += f"🎯 意图：{item['intent']}\n"
        msg_content += f"⚡ 紧急度：{item['urgency']}\n"
        msg_content += f"💬 内容：{item['content_preview']}\n\n"
    
    ok, detail = send_feishu_message(msg_content, target=f"user:{USER_ID}", timeout=60, script="monitor_spiderman_group_v2")
    
    if ok:
        log("✅ 飞书通知已发送")
    else:
        log(f"❌ 发送失败：{detail[:200]}")

def main():
    log("=" * 50)
    log("🕷️ 蜘蛛侠 Switch 设计沟通群监控开始")
    log("=" * 50)
    
    # 检查工作时间
    if not is_work_time():
        log("❌ 非工作时间，跳过监控")
        return
    
    client = init_client()
    last_msg_id = get_last_msg_id()
    log(f"上次消息 ID: {last_msg_id or '首次运行'}")
    
    # 获取新消息
    messages = get_messages_since(client, last_msg_id)
    
    if not messages:
        log("✅ 无新消息")
        return
    
    # 保存到向量库
    save_to_vectorbrain(messages)
    
    # 生成汇报
    report = []
    for msg in messages:
        sender_id = msg.get('sender_id', '')
        member_info = MEMBERS.get(sender_id, {"name": "未知", "role": "未知", "note": ""})
        analysis = analyze_intent(msg['content'], member_info)
        
        report.append({
            "sender": member_info.get('name', '未知'),
            "role": member_info.get('role', '未知'),
            "note": member_info.get('note', ''),
            "content_preview": msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content'],
            "intent": analysis['intent'],
            "urgency": analysis['urgency']
        })
    
    # 发送汇报
    if report:
        send_feishu_notification(report)
    
    # 保存最后消息 ID
    if messages:
        save_last_msg_id(messages[-1]['message_id'])
    
    log("=" * 50)
    log("🕷️ 监控完成")
    log("=" * 50)

if __name__ == "__main__":
    main()
