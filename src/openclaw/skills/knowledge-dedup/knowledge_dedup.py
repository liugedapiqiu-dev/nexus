#!/usr/bin/env python3
"""
知识记忆去重机制
检测 VectorBrain 知识记忆中的重复内容，提供合并建议
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
KNOWLEDGE_DB = VECTORBRAIN_HOME / "memory" / "knowledge_memory.db"

def get_all_knowledge(limit=500):
    """获取所有知识记录"""
    try:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, category, key, value, updated_at
            FROM knowledge
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        
        records = cursor.fetchall()
        conn.close()
        
        return records
    except Exception as e:
        print(f"⚠️ 读取知识记忆失败：{e}")
        return []

def calculate_similarity(text1, text2):
    """计算两个文本的相似度"""
    # 简化文本（去除格式）
    simple1 = ' '.join(text1.split())[:1000]  # 取前 1000 字符
    simple2 = ' '.join(text2.split())[:1000]
    
    return SequenceMatcher(None, simple1, simple2).ratio()

def find_duplicates(records, threshold=0.85):
    """查找重复的知识记录"""
    duplicates = []
    
    # 按类别分组
    by_category = {}
    for record in records:
        id, category, key, value, updated_at = record
        if category not in by_category:
            by_category[category] = []
        by_category[category].append({
            "id": id,
            "category": category,
            "key": key,
            "value": value,
            "updated_at": updated_at
        })
    
    # 在每个类别内查找重复
    for category, items in by_category.items():
        if len(items) < 2:
            continue
        
        # 两两比较
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item1 = items[i]
                item2 = items[j]
                
                # 计算相似度
                similarity = calculate_similarity(item1["value"], item2["value"])
                
                if similarity >= threshold:
                    duplicates.append({
                        "category": category,
                        "item1": item1,
                        "item2": item2,
                        "similarity": similarity
                    })
    
    return duplicates

def suggest_merge(duplicate_group):
    """提供合并建议"""
    item1 = duplicate_group["item1"]
    item2 = duplicate_group["item2"]
    similarity = duplicate_group["similarity"]
    
    # 判断哪个更新
    if item1["updated_at"] > item2["updated_at"]:
        keep = item1
        remove = item2
    else:
        keep = item2
        remove = item1
    
    suggestion = {
        "action": "merge",
        "keep": {
            "key": keep["key"],
            "id": keep["id"],
            "reason": "更新" if keep["updated_at"] > remove["updated_at"] else "较完整"
        },
        "remove": {
            "key": remove["key"],
            "id": remove["id"]
        },
        "similarity": similarity,
        "confidence": "high" if similarity > 0.95 else "medium"
    }
    
    return suggestion

def generate_dedup_report(duplicates):
    """生成去重报告"""
    if not duplicates:
        return "✅ 未发现重复知识记录", 0
    
    report = f"""# 知识记忆去重报告

**执行时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**分析记录数:** {len(set([d['item1']['id'] for d in duplicates] + [d['item2']['id'] for d in duplicates]))}
**发现重复组数:** {len(duplicates)}

---

## 重复详情

"""
    
    merge_actions = []
    
    for i, dup in enumerate(duplicates, 1):
        suggestion = suggest_merge(dup)
        
        report += f"""### 重复组 {i}

**类别:** {dup['category']}
**相似度:** {dup['similarity']*100:.1f}%
**置信度:** {suggestion['confidence']}

**建议操作:**
- ✅ 保留：`{suggestion['keep']['key']}` ({suggestion['keep']['reason']})
- ❌ 删除/合并：`{suggestion['remove']['key']}`

---

"""
        
        merge_actions.append(suggestion)
    
    report += f"""## 执行建议

### 自动合并（推荐）

```bash
python3 ~/.openclaw/skills/knowledge-dedup/knowledge_dedup.py --auto-merge
```

### 手动审核

检查上述重复组，确认合并建议是否合理。

### 注意事项

- 高置信度（>95%）可以直接合并
- 中等置信度（85-95%）建议人工审核
- 合并前建议备份知识记忆数据库
"""
    
    return report, len(merge_actions)

def save_report_to_vectorbrain(report, duplicate_count):
    """保存报告到 VectorBrain"""
    try:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "system_maintenance",
            f"dedup_report_{datetime.now().strftime('%Y-%m-%d')}",
            report,
            "knowledge_dedup_system",
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        print("\n✅ 去重报告已保存到 VectorBrain")
    except Exception as e:
        print(f"\n⚠️ 保存报告失败：{e}")

def auto_merge_high_confidence(duplicates, dry_run=True):
    """自动合并高置信度的重复记录"""
    merged_count = 0
    skipped_count = 0
    
    try:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        
        for dup in duplicates:
            suggestion = suggest_merge(dup)
            
            # 只处理高置信度的重复
            if suggestion['confidence'] != 'high':
                skipped_count += 1
                continue
            
            if dry_run:
                print(f"  📋 [模拟] 合并：{suggestion['remove']['key']} → {suggestion['keep']['key']}")
                merged_count += 1
            else:
                try:
                    # 备份要删除的记录
                    remove_item = suggestion['remove']
                    cursor.execute("""
                        SELECT category, key, value FROM knowledge WHERE id = ?
                    """, (remove_item['id'],))
                    result = cursor.fetchone()
                    
                    if result:
                        category, key, value = result
                        
                        # 创建合并记录
                        merged_key = f"merged_{key}_{datetime.now().strftime('%Y%m%d')}"
                        merged_value = f"""# 已合并的重复记录

**原始 Key:** {key}
**合并时间:** {datetime.now().isoformat()}
**合并到:** {suggestion['keep']['key']}
**相似度:** {dup['similarity']*100:.1f}%

---

## 原始内容

{value[:3000]}
"""
                        
                        # 插入合并记录（存档）
                        cursor.execute("""
                            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            "merged_records",
                            merged_key,
                            merged_value,
                            "knowledge_dedup_system",
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))
                        
                        # 删除重复记录
                        cursor.execute("DELETE FROM knowledge WHERE id = ?", (remove_item['id'],))
                        
                        merged_count += 1
                        print(f"  ✅ 合并：{remove_item['key']} → {suggestion['keep']['key']}")
                        
                except Exception as e:
                    print(f"  ⚠️ 合并失败 {suggestion['remove']['key']}: {e}")
                    continue
        
        if not dry_run:
            conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"⚠️ 自动合并失败：{e}")
    
    return merged_count, skipped_count

def run_dedup_analysis():
    """运行去重分析"""
    print("🔍 开始分析知识记忆...\n")
    
    # 获取知识记录
    records = get_all_knowledge(limit=500)
    
    if not records:
        print("⏭️ 没有知识记录需要分析")
        return
    
    print(f"📊 分析了 {len(records)} 条知识记录\n")
    
    # 查找重复
    print("🔍 正在查找重复记录...")
    duplicates = find_duplicates(records, threshold=0.85)
    
    # 生成报告
    report, action_count = generate_dedup_report(duplicates)
    
    print("\n" + report)
    
    # 保存到 VectorBrain
    save_report_to_vectorbrain(report, action_count)
    
    if action_count > 0:
        print(f"\n⚠️ 发现 {action_count} 组重复，建议审核并合并")
    else:
        print(f"\n✅ 未发现重复记录")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🔍 强制运行模式")
        run_dedup_analysis()
    elif len(sys.argv) > 1 and sys.argv[1] == "--auto-merge":
        print("🔧 自动合并高置信度重复记录\n")
        
        # 先获取重复记录
        records = get_all_knowledge(limit=500)
        duplicates = find_duplicates(records, threshold=0.85)
        
        # 过滤出高置信度的
        high_conf_dups = [d for d in duplicates if calculate_similarity(d['item1']['value'], d['item2']['value']) > 0.95]
        
        print(f"📊 发现 {len(high_conf_dups)} 组高置信度重复\n")
        
        # 模拟运行
        print("=== 模拟合并（dry run）===")
        merged, skipped = auto_merge_high_confidence(high_conf_dups, dry_run=True)
        print(f"\n模拟完成：可合并 {merged} 组，跳过 {skipped} 组\n")
        
        # 询问是否执行
        response = input("是否执行实际合并？(yes/no): ")
        if response.lower() in ['yes', 'y']:
            print("\n=== 执行合并 ===")
            merged, skipped = auto_merge_high_confidence(high_conf_dups, dry_run=False)
            print(f"\n✅ 合并完成！已合并 {merged} 组记录")
        else:
            print("\n⏭️ 已取消合并操作")
    else:
        run_dedup_analysis()
