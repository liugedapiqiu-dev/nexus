#!/usr/bin/env python3
"""
[YOUR_AI_NAME]后台加载器 v1.0
独立进程运行，不依赖会话生命周期
"""

import json
import os
import sys
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 配置
HOME = Path.home()
WORKSPACE = HOME / ".openclaw" / "workspace"
VECTORBRAIN_HOME = HOME / ".vectorbrain"
STATUS_FILE = WORKSPACE / ".ahao_loading_status.json"
PID_FILE = Path("/tmp/ahao_loader.pid")

# 上海时区 (UTC+8)
SHANGHAI_TZ = timezone(timedelta(hours=8))

def get_shanghai_time():
    return datetime.now(SHANGHAI_TZ)

def update_status(level, status, progress="100%", message=""):
    """更新加载状态"""
    status_data = {
        "session_id": str(os.getpid()),
        "start_time": get_shanghai_time().isoformat(),
        "status": status,
        "progress": {
            f"level_{level}": {
                "status": status,
                "progress": progress,
                "timestamp": get_shanghai_time().isoformat()
            }
        },
        "message": message,
        "last_heartbeat": get_shanghai_time().isoformat()
    }
    
    tmp_file = STATUS_FILE.with_suffix('.tmp')
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        tmp_file.rename(STATUS_FILE)
    except Exception as e:
        print(f"⚠️ 更新状态失败：{e}")

def load_vectorbrain():
    """第二级：加载 VectorBrain"""
    print("\n🧠 第二级：加载 VectorBrain 上下文...")
    update_status("2", "loading", "0%", "正在检索 VectorBrain...")
    
    try:
        knowledge_db = VECTORBRAIN_HOME / "memory" / "knowledge_memory.db"
        tasks_db = VECTORBRAIN_HOME / "tasks" / "task_queue.db"
        
        # 检索知识记忆
        recent_context = []
        if knowledge_db.exists():
            conn = sqlite3.connect(knowledge_db, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT category, key, substr(value, 1, 100) FROM knowledge ORDER BY updated_at DESC LIMIT 5")
            recent_context = cursor.fetchall()
            conn.close()
        
        # 检查待办任务
        pending_tasks = []
        if tasks_db.exists():
            conn = sqlite3.connect(tasks_db, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, title FROM tasks WHERE status NOT IN ('done','completed') LIMIT 5")
            pending_tasks = cursor.fetchall()
            conn.close()
        
        print(f"✅ VectorBrain 检索完成：{len(recent_context)} 条记忆，{len(pending_tasks)} 个待办")
        update_status("2", "completed", "100%", f"{len(recent_context)} 条记忆，{len(pending_tasks)} 个待办")
        return True
    except Exception as e:
        print(f"❌ VectorBrain 加载失败：{e}")
        update_status("2", "failed", "0%", str(e))
        return False

def detect_changes():
    """第三级：检测文件变更"""
    print("\n🔍 第三级：检测文件变更...")
    update_status("3", "loading", "0%", "正在检测...")
    
    try:
        detector_script = HOME / ".openclaw" / "skills" / "ahao-auto-updater" / "detect_changes.py"
        if detector_script.exists():
            import subprocess
            result = subprocess.run([sys.executable, str(detector_script)], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ 文件检测完成")
                update_status("3", "completed", "100%", "检测完成")
                return True
        print("⚠️ 检测器不存在，跳过")
        update_status("3", "skipped", "100%", "检测器不存在")
        return True
    except Exception as e:
        print(f"❌ 文件检测失败：{e}")
        update_status("3", "failed", "0%", str(e))
        return False

def main():
    print("=" * 60)
    print("🧠 [YOUR_AI_NAME]后台加载器 v1.0")
    print(f"启动时间：{get_shanghai_time().strftime('%Y-%m-%d %H:%M:%S')} (Asia/Shanghai)")
    print("=" * 60)
    
    # 写入 PID
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    try:
        # 第二级
        load_vectorbrain()
        
        # 第三级
        detect_changes()
        
        # 完成
        update_status("ready", "ready", "100%", "[YOUR_AI_NAME] 100% 就绪")
        print("\n" + "=" * 60)
        print("✅ [YOUR_AI_NAME]后台加载完成！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 加载过程出错：{e}")
        update_status("failed", "failed", "0%", str(e))
    finally:
        # 清理 PID
        if PID_FILE.exists():
            PID_FILE.unlink()

if __name__ == "__main__":
    main()
