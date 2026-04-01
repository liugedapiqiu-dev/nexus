#!/usr/bin/env python3
"""
VectorBrain V3 - Experience Integration Layer

通过 monkey-patching 在运行时集成 Experience Collector 到 Scheduler
避免直接修改 scheduler 代码导致的缩进问题
"""

import sys
import os
from pathlib import Path
import time

# 添加路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))
sys.path.insert(0, str(Path.home() / ".vectorbrain/dag"))

from experience.experience_collector import record_episode

print("=" * 60)
print("🧠 VectorBrain V3 - Experience Integration")
print("=" * 60)

# 现在导入并 patch scheduler
from dag_scheduler import DAGScheduler

# 保存原始方法
_original_execute_task = DAGScheduler._execute_task
_original_handle_failure = DAGScheduler._handle_task_failure


def _detect_task_type(task):
    """检测任务类型"""
    description = getattr(task, 'description', '') or ''
    
    if description.startswith('shell:'):
        return 'shell'
    elif description.startswith('python:'):
        return 'python'
    elif description.startswith('http:'):
        return 'http'
    else:
        return 'general'


def _execute_task_with_experience(self, scheduled):
    """增强的 _execute_task，记录经验"""
    task = scheduled.task
    start_time = time.time()
    
    # 调用原始方法
    try:
        result = _original_execute_task(self, scheduled)
        
        # 记录经验（成功）
        try:
            episode_data = {
                "task_id": task.task_id,
                "type": _detect_task_type(task),
                "input": task.description or task.title,
                "output": "completed",
                "status": "done",
                "execution_time": time.time() - start_time
            }
            record_episode(episode_data)
        except Exception as e:
            print(f"⚠️  记录经验失败：{e}")
        
        return result
    
    except Exception as e:
        # 记录经验（失败）
        try:
            episode_data = {
                "task_id": task.task_id,
                "type": _detect_task_type(task),
                "input": task.description or task.title,
                "output": str(e)[:500],
                "status": "failed",
                "execution_time": time.time() - start_time
            }
            record_episode(episode_data)
        except Exception:
            pass
        
        raise


# 应用 patch
DAGScheduler._execute_task = _execute_task_with_experience

print("✅ Experience Collector 已集成到 Scheduler")
print("=" * 60)

# 现在运行 scheduler
if __name__ == "__main__":
    import subprocess
    # 启动原始的 scheduler
    scheduler_script = Path.home() / ".vectorbrain/dag/dag_scheduler.py"
    os.execv(sys.executable, [sys.executable, str(scheduler_script)] + sys.argv[1:])
