#!/usr/bin/env python3
"""
记忆自动提炼引擎
自动分析情景记忆，识别高价值对话和经验，提炼为知识记忆
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
EPISODIC_DB = VECTORBRAIN_HOME / "memory" / "episodic_memory.db"
KNOWLEDGE_DB = VECTORBRAIN_HOME / "memory" / "knowledge_memory.db"

# 提炼规则配置
EXTRACTION_RULES = {
    "architecture_decision": {
        "keywords": ["架构决策", "decision", "选择", "方案", "规范", "协议", "标准"],
        "event_types": ["chat_user", "chat_assistant"],
        "min_content_length": 200,
        "description": "架构决策、规范制定、标准定义"
    },
    "workflow": {
        "keywords": ["工作流程", "流程", "workflow", "步骤", "操作", "执行", "自动"],
        "event_types": ["chat_user", "chat_assistant"],
        "min_content_length": 150,
        "description": "工作流程、操作方法、执行步骤"
    },
    "skill_configuration": {
        "keywords": ["技能配置", "skill", "skill.json", "SKILL.md", "function calling"],
        "event_types": ["chat_user", "chat_assistant", "memory_rule"],
        "min_content_length": 100,
        "description": "技能配置、Function Calling 相关"
    },
    "experience": {
        "keywords": ["经验", "教训", "learn", "error", "错误", "修复", "解决", "问题"],
        "event_types": ["chat_user", "chat_assistant"],
        "min_content_length": 100,
        "description": "经验教训、问题解决、错误修复"
    },
    "system_standard": {
        "keywords": ["标准", "standard", "必定执行", "协议", "protocol", "规范"],
        "event_types": ["memory_rule", "chat_user", "chat_assistant"],
        "min_content_length": 200,
        "description": "系统标准、必定执行的规范"
    }
}

def get_recent_episodes(hours=24, limit=100):
    """获取最近 N 小时的情景记忆"""
    try:
        conn = sqlite3.connect(EPISODIC_DB)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT id, timestamp, worker_id, event_type, content, metadata
            FROM episodes
            WHERE timestamp > ?
            AND event_type NOT LIKE 'task_%'
            ORDER BY timestamp DESC
            LIMIT ?
        """, (cutoff_time, limit))
        
        episodes = cursor.fetchall()
        conn.close()
        
        return episodes
    except Exception as e:
        print(f"⚠️ 读取情景记忆失败：{e}")
        return []

def classify_episode(content, event_type):
    """分类情景记忆，判断属于哪种知识类型"""
    classifications = []
    
    for category, rule in EXTRACTION_RULES.items():
        score = 0
        
        # 关键词匹配
        for keyword in rule["keywords"]:
            if keyword.lower() in content.lower():
                score += 1
        
        # 事件类型匹配
        if event_type in rule["event_types"]:
            score += 1
        
        # 内容长度检查
        if len(content) >= rule["min_content_length"]:
            score += 1
        
        # 如果达到阈值，认为属于该类别
        if score >= 2:
            classifications.append((category, score))
    
    # 返回得分最高的分类
    if classifications:
        return max(classifications, key=lambda x: x[1])[0]
    
    return None

def extract_knowledge(episodes):
    """从情景记忆中提炼知识"""
    extracted = []
    
    for episode in episodes:
        id, timestamp, worker_id, event_type, content, metadata = episode
        
        # 跳过已提炼的内容（通过元数据标记）
        if metadata:
            try:
                meta = json.loads(metadata)
                if meta.get("extracted", False):
                    continue
            except:
                pass
        
        # 分类
        category = classify_episode(content, event_type)
        
        if category:
            # 提炼知识
            knowledge = {
                "episode_id": id,
                "timestamp": timestamp,
                "category": category,
                "content": content,
                "worker_id": worker_id,
                "event_type": event_type
            }
            extracted.append(knowledge)
    
    return extracted

def save_to_knowledge(extracted_episodes):
    """将提炼的知识保存到知识记忆"""
    saved_count = 0
    
    for ep in extracted_episodes:
        try:
            conn = sqlite3.connect(KNOWLEDGE_DB)
            cursor = conn.cursor()
            
            # 生成知识记录 key
            knowledge_key = f"auto_extracted_{ep['episode_id']}_{datetime.now().strftime('%Y%m%d')}"
            
            # 创建知识记录
            knowledge_value = f"""# 自动提炼知识记录

**来源:** 情景记忆 ID {ep['episode_id']}
**提炼时间:** {datetime.now().isoformat()}
**原始时间:** {ep['timestamp']}
**类别:** {ep['category']}
**工作者:** {ep['worker_id']}
**事件类型:** {ep['event_type']}

---

## 内容

{ep['content'][:5000]}

---

## 元数据

- 自动提炼：是
- 需要人工审核：建议检查
- 相关记录：情景记忆 ID {ep['episode_id']}
"""
            
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ep['category'],
                knowledge_key,
                knowledge_value,
                "memory_extraction_engine",
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            # 更新情景记忆的元数据（标记为已提炼）
            cursor_ep = sqlite3.connect(EPISODIC_DB).cursor()
            try:
                cursor_ep.execute("SELECT metadata FROM episodes WHERE id = ?", (ep['episode_id'],))
                result = cursor_ep.fetchone()
                if result:
                    try:
                        meta = json.loads(result[0])
                    except:
                        meta = {}
                    meta['extracted'] = True
                    meta['extracted_at'] = datetime.now().isoformat()
                    meta['knowledge_key'] = knowledge_key
                    
                    cursor_ep.execute("""
                        UPDATE episodes SET metadata = ? WHERE id = ?
                    """, (json.dumps(meta), ep['episode_id']))
                    cursor_ep.connection.commit()
            except Exception as e:
                print(f"⚠️ 更新情景记忆元数据失败：{e}")
            finally:
                cursor_ep.connection.close()
            
            conn.commit()
            conn.close()
            
            saved_count += 1
            print(f"✅ 提炼：情景记忆 #{ep['episode_id']} → {ep['category']}")
            
        except Exception as e:
            print(f"⚠️ 保存知识失败：{e}")
    
    return saved_count

def generate_extraction_report(extracted_count, saved_count, categories):
    """生成提炼报告"""
    report = f"""# 记忆自动提炼报告

**提炼时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 提炼统计

| 指标 | 数值 |
|------|------|
| 分析情景记忆 | {extracted_count} 条 |
| 成功提炼知识 | {saved_count} 条 |
| 提炼率 | {saved_count/extracted_count*100 if extracted_count > 0 else 0:.1f}% |

## 知识分类

"""
    
    for category, count in categories.items():
        report += f"- **{category}**: {count} 条\n"
    
    report += f"""
## 建议

- 检查提炼的知识记录质量
- 合并重复或相似的知识
- 将重要知识提升为系统标准
"""
    
    return report

def run_extraction():
    """运行记忆提炼"""
    print("🔍 开始分析情景记忆...\n")
    
    # 获取最近 24 小时的情景记忆（排除系统日志）
    episodes = get_recent_episodes(hours=24, limit=200)
    
    if not episodes:
        print("⏭️ 没有新的情景记忆需要分析")
        return
    
    print(f"📊 找到 {len(episodes)} 条情景记忆\n")
    
    # 提炼知识
    extracted = extract_knowledge(episodes)
    
    if not extracted:
        print("⏭️ 没有发现需要提炼的知识")
        return
    
    print(f"💡 识别出 {len(extracted)} 条潜在知识\n")
    
    # 保存到知识记忆
    saved_count = save_to_knowledge(extracted)
    
    # 统计分类
    categories = {}
    for ep in extracted:
        cat = ep['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    # 生成报告
    report = generate_extraction_report(len(extracted), saved_count, categories)
    
    print("\n" + report)
    
    # 保存报告到 VectorBrain
    try:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "memory_extraction",
            f"extraction_report_{datetime.now().strftime('%Y-%m-%d')}",
            report,
            "memory_extraction_engine",
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        print("✅ 提炼报告已保存到知识记忆")
    except Exception as e:
        print(f"⚠️ 保存报告失败：{e}")
    
    print(f"\n✅ 提炼完成！成功提炼 {saved_count} 条知识")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🔍 强制运行模式（忽略时间范围）")
        run_extraction()
    else:
        run_extraction()
