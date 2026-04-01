#!/usr/bin/env python3
"""
VectorBrain V3 - Experience Collector

任务执行完成后自动记录经验到 Episodic Memory
"""

import uuid
import time
from typing import Dict, Any
from pathlib import Path

# 导入数据库模块
import sys
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from memory.episodic_db import insert_episode, get_episode_count


def record_episode(task: Dict[str, Any]) -> str:
    """
    记录任务执行经验
    
    Args:
        task: {
            "task_id": str,
            "type": str (shell/python/http),
            "input": str (command/code/url),
            "output": str (result),
            "status": str (done/failed/pending),
            "execution_time": float (seconds)
        }
    
    Returns:
        episode_id: 记录 ID
    """
    episode_id = f"ep_{uuid.uuid4().hex[:16]}"
    
    data = (
        episode_id,
        task.get("task_id", "unknown"),
        time.time(),
        task.get("type", "unknown"),
        str(task.get("input", "")),
        str(task.get("output", "")),
        task.get("status", "unknown"),
        float(task.get("execution_time", 0)),
        1 if task.get("status") == "done" else 0
    )
    
    insert_episode(data)
    
    print(f"[Memory] ✅ Episode recorded: {episode_id}")
    print(f"         Task: {task.get('task_id')} | Status: {task.get('status')} | Time: {task.get('execution_time', 0):.2f}s")
    
    return episode_id


def record_task_completion(scheduler, task, success: bool, result: str, execution_time: float):
    """
    在 Scheduler 中调用，记录任务完成
    
    Args:
        scheduler: DAGScheduler 实例
        task: Task 对象
        success: 是否成功
        result: 执行结果
        execution_time: 执行时间（秒）
    """
    episode_data = {
        "task_id": task.task_id,
        "type": _detect_task_type(task),
        "input": task.description or task.title,
        "output": result[:500] if result else "",  # 限制长度
        "status": "done" if success else "failed",
        "execution_time": execution_time
    }
    
    return record_episode(episode_data)


def _detect_task_type(task) -> str:
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


def get_experience_stats() -> Dict:
    """获取经验统计信息"""
    from memory.episodic_db import load_recent_episodes
    
    episodes = load_recent_episodes(1000)
    
    stats = {
        "total_episodes": len(episodes),
        "success_count": sum(1 for e in episodes if e[8] == 1),
        "failed_count": sum(1 for e in episodes if e[8] == 0),
        "avg_execution_time": sum(e[7] for e in episodes) / len(episodes) if episodes else 0,
        "task_types": {}
    }
    
    # 统计任务类型分布
    for e in episodes:
        task_type = e[3]
        stats["task_types"][task_type] = stats["task_types"].get(task_type, 0) + 1
    
    return stats


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Experience Collector...")
    
    # 模拟任务数据
    test_task = {
        "task_id": "task_test_001",
        "type": "shell",
        "input": "echo hello_vectorbrain",
        "output": "hello_vectorbrain",
        "status": "done",
        "execution_time": 0.5
    }
    
    episode_id = record_episode(test_task)
    print(f"✅ 记录成功：{episode_id}")
    
    # 获取统计
    stats = get_experience_stats()
    print(f"\n📊 经验统计:")
    print(f"  总记录数：{stats['total_episodes']}")
    print(f"  成功：{stats['success_count']}")
    print(f"  失败：{stats['failed_count']}")
    print(f"  平均执行时间：{stats['avg_execution_time']:.2f}s")
    print(f"  任务类型：{stats['task_types']}")
