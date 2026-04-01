#!/usr/bin/env python3
"""
状态标记（2026-03-19）：
- 当前归类：辅助观察层
- 主判据替代：任务执行事实优先看 `tasks/task_queue.db` 与 `connector/task_manager.py`
- 处理原则：可用于异常告警补充，但不要作为任务状态第一事实源


任务执行监控告警脚本

功能：
1. 检测同一个任务执行次数超过阈值的异常情况
2. 写入告警日志文件
3. 可选：发送飞书通知

用法：
python3 ~/.vectorbrain/connector/task_monitor.py
"""

import sqlite3
import json
import os
import time
from datetime import datetime

# 配置区
DB_PATH = os.path.expanduser("~/.vectorbrain/reflection/reflections.db")
TASK_DB_PATH = os.path.expanduser("~/.vectorbrain/tasks/task_queue.db")
ALERT_LOG_PATH = os.path.expanduser("~/.vectorbrain/state/task_execution_alerts.json")
EXECUTION_THRESHOLD = 10  # 同一个任务执行超过 N 次触发告警

def check_task_execution_counts():
    """检查任务执行次数，返回异常任务列表"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 按 task_id 分组统计执行次数
        cursor.execute("""
            SELECT task_id, COUNT(*) as exec_count, 
                   MIN(created_at) as first_exec, 
                   MAX(created_at) as last_exec
            FROM reflections 
            WHERE task_id IS NOT NULL AND task_id != ''
            GROUP BY task_id
            HAVING COUNT(*) > ?
            ORDER BY exec_count DESC
        """, (EXECUTION_THRESHOLD,))
        
        anomalies = cursor.fetchall()
        conn.close()
        
        return anomalies
    except Exception as e:
        print(f"❌ 检查任务执行次数失败：{e}")
        return []

def get_task_details(task_id):
    """从任务数据库获取任务详情"""
    try:
        conn = sqlite3.connect(TASK_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT title, description, status FROM tasks WHERE task_id = ?", (task_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "title": result[0],
                "description": result[1],
                "status": result[2]
            }
        return None
    except Exception as e:
        return None

def save_alerts(anomalies):
    """保存告警到日志文件"""
    try:
        alerts = []
        for task_id, exec_count, first_exec, last_exec in anomalies:
            task_details = get_task_details(task_id)
            alert = {
                "alert_time": datetime.now().isoformat(),
                "task_id": task_id,
                "task_title": task_details["title"] if task_details else "未知",
                "task_status": task_details["status"] if task_details else "未知",
                "execution_count": exec_count,
                "first_execution": first_exec,
                "last_execution": last_exec,
                "severity": "critical" if exec_count > 100 else "warning"
            }
            alerts.append(alert)
        
        # 读取现有告警
        existing_alerts = []
        if os.path.exists(ALERT_LOG_PATH):
            with open(ALERT_LOG_PATH, 'r', encoding='utf-8') as f:
                existing_alerts = json.load(f)
        
        # 添加新告警（去重）
        existing_task_ids = {a["task_id"] for a in existing_alerts}
        new_alerts = [a for a in alerts if a["task_id"] not in existing_task_ids]
        
        if new_alerts:
            existing_alerts.extend(new_alerts)
            os.makedirs(os.path.dirname(ALERT_LOG_PATH), exist_ok=True)
            with open(ALERT_LOG_PATH, 'w', encoding='utf-8') as f:
                json.dump(existing_alerts, f, ensure_ascii=False, indent=2)
            
            print(f"🚨 发现 {len(new_alerts)} 个异常任务，已写入告警日志")
            for alert in new_alerts:
                print(f"   - {alert['task_id']}: {alert['task_title']} (执行 {alert['execution_count']} 次)")
        else:
            print("✅ 没有新的异常任务")
        
        return alerts
    except Exception as e:
        print(f"❌ 保存告警失败：{e}")
        return []

def cleanup_excessive_reflections(task_id, keep_latest=10):
    """清理某个任务的过多反思记录，只保留最新的 N 条"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取要删除的记录 ID
        cursor.execute("""
            SELECT reflection_id FROM reflections 
            WHERE task_id = ?
            ORDER BY created_at DESC
            LIMIT -1 OFFSET ?
        """, (task_id, keep_latest))
        
        to_delete = [row[0] for row in cursor.fetchall()]
        
        if to_delete:
            # 删除旧记录
            placeholders = ','.join('?' * len(to_delete))
            cursor.execute(f"DELETE FROM reflections WHERE reflection_id IN ({placeholders})", to_delete)
            conn.commit()
            print(f"🧹 已清理 {len(to_delete)} 条旧反思记录（保留最新 {keep_latest} 条）")
        else:
            print(f"✅ 任务 {task_id} 无需清理")
        
        conn.close()
        return len(to_delete)
    except Exception as e:
        print(f"❌ 清理反思记录失败：{e}")
        return 0

if __name__ == "__main__":
    print("📊 任务执行监控检查")
    print("=" * 60)
    
    # 1. 检查异常任务
    anomalies = check_task_execution_counts()
    
    if anomalies:
        print(f"⚠️  发现 {len(anomalies)} 个任务执行次数超过阈值 ({EXECUTION_THRESHOLD} 次)")
        print()
        
        # 2. 保存告警
        save_alerts(anomalies)
        print()
        
        # 3. 显示详情
        print("📋 异常任务详情:")
        print(f"{'任务 ID':<25} {'标题':<30} {'执行次数':>10} {'首次执行':<25} {'最后执行':<25}")
        print("-" * 120)
        for task_id, exec_count, first_exec, last_exec in anomalies:
            details = get_task_details(task_id)
            title = details["title"][:28] if details else "未知"
            print(f"{task_id:<25} {title:<30} {exec_count:>10} {first_exec:<25} {last_exec:<25}")
    else:
        print(f"✅ 所有任务执行次数正常（阈值：{EXECUTION_THRESHOLD} 次）")
    
    print()
    print("=" * 60)
    print("监控检查完成")
