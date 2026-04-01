#!/usr/bin/env python3
"""
Layer: ingestion
Status: secondary
Boundary: legacy compatibility submission shim; prefer runtime/service bridge contracts for new callers.
Architecture refs:
- architecture/layer-manifest.md
- architecture/runtime-boundary-rules.md

VectorBrain OpenClaw Connector

OpenClaw Worker 通过此模块向 VectorBrain 提交任务。

注意：该模块保留为 legacy compatibility shim。新调用方应优先走统一 bridge contract，而不是继续新增文件投递旁路。

用法：
from openclaw_connector import push_task

# Worker 提交任务
push_task("scan_amazon", {"url": "https://amazon.com/..."})
push_task("analyse_supplier", {"supplier": "XXX"})
push_task("research_product", {"product": "XXX"})
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# VectorBrain 任务目录
VECTORBRAIN_TASK_PATH = Path.home() / '.vectorbrain' / 'tasks'

# 确保目录存在
VECTORBRAIN_TASK_PATH.mkdir(parents=True, exist_ok=True)


def push_task(task_name: str, payload: dict = None, priority: int = 5) -> str:
    """
    向 VectorBrain 提交任务
    
    Args:
        task_name: 任务名称
        payload: 任务参数
        priority: 优先级 (1-10, 1 最高)
    
    Returns:
        task_id: 任务 ID
    """
    # 生成唯一任务 ID
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    # 创建任务对象
    task = {
        "task_id": task_id,
        "task_name": task_name,
        "title": task_name,  # 兼容 task_manager
        "description": f"由 OpenClaw Worker 提交",
        "payload": payload or {},
        "priority": priority,
        "status": "pending",
        "submitted_by": "openclaw_worker",
        "submitted_at": datetime.utcnow().isoformat()
    }
    
    # 写入任务文件
    task_file = VECTORBRAIN_TASK_PATH / f"{task_id}.json"
    
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 任务已提交：{task_name}")
    print(f"   任务 ID: {task_id}")
    print(f"   文件：{task_file}")
    
    return task_id


def get_pending_tasks():
    """获取所有待处理任务"""
    tasks = []
    
    for task_file in VECTORBRAIN_TASK_PATH.glob("*.json"):
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                tasks.append(task)
        except Exception as e:
            print(f"读取任务失败 {task_file}: {e}")
    
    return tasks


def clear_old_tasks(days: int = 7):
    """清理旧任务文件"""
    import time
    
    current_time = time.time()
    max_age = days * 24 * 60 * 60  # 秒
    
    for task_file in VECTORBRAIN_TASK_PATH.glob("*.json"):
        if current_time - task_file.stat().st_mtime > max_age:
            task_file.unlink()
            print(f"清理旧任务：{task_file.name}")


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("OpenClaw Connector 使用示例")
    print("="*60)
    
    # 示例 1：提交研究任务
    print("\n示例 1：提交研究任务")
    task_id = push_task(
        "research_amazon",
        {
            "url": "https://amazon.com/dp/XXX",
            "keywords": ["wireless", "bluetooth"]
        },
        priority=1
    )
    
    # 示例 2：提交分析任务
    print("\n示例 2：提交分析任务")
    task_id = push_task(
        "analyse_supplier",
        {
            "supplier_name": "XXX Company",
            "products": ["product A", "product B"]
        },
        priority=2
    )
    
    # 示例 3：提交扫描任务
    print("\n示例 3：提交扫描任务")
    task_id = push_task(
        "scan_amazon",
        {
            "search_term": "wireless headphones",
            "min_price": 10,
            "max_price": 50
        },
        priority=3
    )
    
    # 获取所有任务
    print("\n当前待处理任务:")
    tasks = get_pending_tasks()
    for task in tasks:
        print(f"  - {task['task_name']} (priority: {task['priority']})")
    
    print("\n示例完成！")
