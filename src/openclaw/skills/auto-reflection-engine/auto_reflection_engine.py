#!/usr/bin/env python3
"""
任务完成后自动反思系统
分析已完成任务，提取经验教训，自动记录到 VectorBrain
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
TASKS_DB = VECTORBRAIN_HOME / "tasks" / "task_queue.db"
KNOWLEDGE_DB = VECTORBRAIN_HOME / "memory" / "knowledge_memory.db"
EPISODIC_DB = VECTORBRAIN_HOME / "memory" / "episodic_memory.db"

def get_recent_completed_tasks(hours=24, limit=20):
    """获取最近完成的 N 个任务"""
    try:
        conn = sqlite3.connect(TASKS_DB)
        cursor = conn.cursor()
        
        # 获取最近完成的任务（status='done' 或 'completed'）
        cursor.execute("""
            SELECT task_id, title, description, status, result, error_message, 
                   created_at, completed_at, assigned_worker
            FROM tasks
            WHERE status IN ('done', 'completed')
            AND completed_at > datetime('now', ?)
            ORDER BY completed_at DESC
            LIMIT ?
        """, (f'-{hours} hours', limit))
        
        tasks = cursor.fetchall()
        conn.close()
        
        return tasks
    except Exception as e:
        print(f"⚠️ 读取任务失败：{e}")
        return []

def analyze_task(task):
    """分析任务，提取经验教训"""
    task_id, title, description, status, result, error_message, created_at, completed_at, worker = task
    
    reflections = {
        "task_id": task_id,
        "title": title,
        "success": status in ['done', 'completed'] and not error_message,
        "lessons": [],
        "action_items": [],
        "patterns": []
    }
    
    # 分析成功经验
    if reflections["success"] and result:
        # 提取成功因素
        if "成功" in result or "完成" in result or "✅" in result:
            reflections["lessons"].append("✅ 任务成功完成")
        
        # 提取有效方法
        if "自动" in result or "批量" in result:
            reflections["patterns"].append("自动化/批处理方法有效")
        
        if "VectorBrain" in result or "记忆" in result:
            reflections["patterns"].append("VectorBrain 集成成功")
    
    # 分析失败教训
    if error_message or not reflections["success"]:
        reflections["lessons"].append(f"❌ 失败原因：{error_message or '任务未完成'}")
        reflections["action_items"].append("需要分析失败原因并修复")
    
    # 分析任务类型
    task_type = "unknown"
    if "技能" in title or "skill" in title.lower():
        task_type = "skill_configuration"
    elif "记忆" in title or "memory" in title.lower():
        task_type = "memory_operation"
    elif "健康" in title or "health" in title.lower():
        task_type = "health_check"
    elif "清理" in title or "cleanup" in title.lower():
        task_type = "cleanup"
    elif "升级" in title or "upgrade" in title.lower():
        task_type = "system_upgrade"
    
    reflections["task_type"] = task_type
    
    return reflections

def generate_reflection_content(reflection):
    """生成反思内容"""
    content = f"""# 任务反思记录

**任务 ID:** {reflection['task_id']}
**任务标题:** {reflection['title']}
**反思时间:** {datetime.now().isoformat()}
**任务状态:** {"✅ 成功" if reflection['success'] else "❌ 失败"}
**任务类型:** {reflection.get('task_type', 'unknown')}

---

## 经验教训

"""
    
    if reflection['lessons']:
        for lesson in reflection['lessons']:
            content += f"- {lesson}\n"
    else:
        content += "- 无明显经验教训\n"
    
    content += "\n## 发现的模式\n\n"
    
    if reflection['patterns']:
        for pattern in reflection['patterns']:
            content += f"- {pattern}\n"
    else:
        content += "- 无明显模式\n"
    
    content += "\n## 后续行动\n\n"
    
    if reflection['action_items']:
        for item in reflection['action_items']:
            content += f"- {item}\n"
    else:
        content += "- 无需后续行动\n"
    
    content += f"""
---

## 元数据

- 自动反思：是
- 任务 ID: {reflection['task_id']}
- 需要人工审核：{not reflection['success']}
"""
    
    return content

def save_reflection(reflection):
    """保存反思到知识记忆"""
    try:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        
        # 生成反思记录 key
        reflection_key = f"task_reflection_{reflection['task_id']}_{datetime.now().strftime('%Y%m%d')}"
        
        content = generate_reflection_content(reflection)
        
        # 确定分类
        category = reflection.get('task_type', 'experience')
        if category == 'unknown':
            category = 'experience'
        
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            category,
            reflection_key,
            content,
            "auto_reflection_engine",
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"⚠️ 保存反思失败：{e}")
        return False

def mark_task_reflected(task_id):
    """标记任务已反思"""
    try:
        conn = sqlite3.connect(TASKS_DB)
        cursor = conn.cursor()
        
        # 尝试更新任务元数据（如果 tasks 表有 metadata 字段）
        try:
            cursor.execute("""
                UPDATE tasks SET result = json_set(result, '$.reflected', true)
                WHERE task_id = ?
            """, (task_id,))
            conn.commit()
        except:
            pass  # 如果失败，忽略
        
        conn.close()
    except:
        pass

def run_auto_reflection():
    """运行自动反思"""
    print("🔍 开始分析已完成任务...\n")
    
    # 获取最近完成的任务
    tasks = get_recent_completed_tasks(hours=24, limit=20)
    
    if not tasks:
        print("⏭️ 没有新完成的任务需要反思")
        return
    
    print(f"📊 找到 {len(tasks)} 个已完成任务\n")
    
    # 分析和反思
    reflected_count = 0
    success_count = 0
    fail_count = 0
    lessons_count = 0
    
    for task in tasks:
        reflection = analyze_task(task)
        
        # 只反思有经验的任務
        if reflection['lessons'] or reflection['patterns']:
            if save_reflection(reflection):
                mark_task_reflected(task[0])
                reflected_count += 1
                
                if reflection['success']:
                    success_count += 1
                else:
                    fail_count += 1
                
                if reflection['lessons']:
                    lessons_count += len(reflection['lessons'])
                
                status = "✅" if reflection['success'] else "❌"
                print(f"{status} 反思：任务 {task[0]} - {task[1][:30]}...")
    
    # 生成报告
    print(f"\n📊 反思统计:")
    print(f"  - 分析任务：{len(tasks)} 个")
    print(f"  - 完成反思：{reflected_count} 个")
    print(f"  - 成功经验：{success_count} 个")
    print(f"  - 失败教训：{fail_count} 个")
    print(f"  - 提取教训：{lessons_count} 条")
    
    if reflected_count > 0:
        print(f"\n✅ 反思完成！{reflected_count} 个任务已记录到 VectorBrain")
    else:
        print(f"\n⏭️ 没有需要反思的任务")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🔍 强制运行模式")
        run_auto_reflection()
    else:
        run_auto_reflection()
