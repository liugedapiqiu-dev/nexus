#!/usr/bin/env python3
"""
将蜘蛛侠群历史消息转为向量数据库
"""

import sqlite3
import subprocess
import json
import re
from datetime import datetime

# 配置
REPORT_FILE = "/home/user/Desktop/智能体 3.0/飞书/群消息_高级洞察报告/蜘蛛侠 Switch 设计沟通_20260309_高级报表.md"
VECBRAIN_DB = "/home/user/.vectorbrain/memory/knowledge_memory.db"
CHAT_NAME = "蜘蛛侠 Switch 设计沟通"

# 成员信息
MEMBERS = {
    "黄宗旨": {"role": "设计主管", "dept": "设计部"},
    "[YOUR_NAME]": {"role": "老板", "dept": "管理层"},
    "许瑶": {"role": "管理助理", "dept": "管理层"},
    "周凡": {"role": "产品开发", "dept": "产品开发部", "note": "急性子，口头汇报"},
    "张新": {"role": "产品开发助理", "dept": "产品开发部", "note": "记录官"},
    "Emeng": {"role": "领导", "dept": "管理层"},
    "易灵": {"role": "产品开发助理", "dept": "产品开发部", "note": "记录官"},
    "陈亮亮": {"role": "物流", "dept": "物流部"},
}

def parse_messages_from_markdown(filepath):
    """从 Markdown 报表中解析消息"""
    messages = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到"详细对话日志"部分
    match = re.search(r'## 5\. 📝 详细对话日志', content)
    if not match:
        print("❌ 未找到详细对话日志部分")
        return []
    
    log_content = content[match.start():]
    
    # 解析表格行
    lines = log_content.split('\n')
    for line in lines[3:]:  # 跳过表头
        if not line.strip() or line.startswith('##'):
            break
        
        # 解析：| 时间 | 发送人 | 内容详情 |
        parts = line.split('|')
        if len(parts) >= 4:
            time_str = parts[1].strip()
            sender = parts[2].strip()
            content_txt = parts[3].strip().replace('<br>', '\n').replace('\\|', '|')
            
            if time_str and sender and content_txt:
                messages.append({
                    "time": time_str,
                    "sender": sender,
                    "content": content_txt
                })
    
    print(f"✅ 解析到 {len(messages)} 条消息")
    return messages

def generate_vector_content(msg):
    """生成向量化内容"""
    member_info = MEMBERS.get(msg['sender'], {"role": "未知", "dept": "未知"})
    
    return f"""
群组：{CHAT_NAME}
发送人：{msg['sender']}
岗位：{member_info.get('role', '未知')}
部门：{member_info.get('dept', '未知')}
时间：{msg['time']}
内容：{msg['content'][:500]}
"""

def save_to_vectorbrain(messages):
    """保存消息到 VectorBrain"""
    conn = sqlite3.connect(VECBRAIN_DB)
    cursor = conn.cursor()
    
    for i, msg in enumerate(messages, 1):
        if i % 100 == 0:
            print(f"  📊 处理进度：{i}/{len(messages)}")
        
        # 生成向量内容
        vector_content = generate_vector_content(msg)
        
        # 用 bge-m3 生成向量
        result = subprocess.run(
            ['ollama', 'run', 'bge-m3', vector_content],
            capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0:
            vector_str = result.stdout.strip()
            
            # 生成唯一键名
            safe_time = msg['time'].replace(':', '').replace('-', '').replace(' ', '_')
            safe_sender = msg['sender'].replace(' ', '_')
            key = f"spiderman_hist_{safe_sender}_{safe_time}"
            
            value = json.dumps({
                "group": CHAT_NAME,
                "sender": msg['sender'],
                "content": msg['content'],
                "time": msg['time'],
                "source": "历史消息导入"
            }, ensure_ascii=False)
            
            cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, confidence, embedding_vector, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            """, ('spiderman_group_messages', key, value, 'historical_import', 1.0, vector_str))
        else:
            print(f"  ⚠️ 向量生成失败：{msg['sender']} - {msg['content'][:30]}...")
    
    conn.commit()
    conn.close()
    print(f"✅ 向量库更新完成！共存入 {len(messages)} 条历史消息")

def main():
    print("=" * 50)
    print("🕷️ 蜘蛛侠群历史消息向量化开始")
    print("=" * 50)
    
    # 解析消息
    messages = parse_messages_from_markdown(REPORT_FILE)
    
    if not messages:
        print("❌ 没有消息可处理")
        return
    
    # 保存到 VectorBrain
    save_to_vectorbrain(messages)
    
    print("=" * 50)
    print("🎉 历史消息向量化完成！")
    print("=" * 50)

if __name__ == "__main__":
    main()
