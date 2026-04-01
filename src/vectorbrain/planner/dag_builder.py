#!/usr/bin/env python3
"""
VectorBrain V4 - DAG Builder

将任务计划提交到 Scheduler API
"""

import http.client
import json
from typing import List, Dict
import time


SCHEDULER_HOST = "127.0.0.1"
SCHEDULER_PORT = 9000
SCHEDULER_PATH = "/api/v1/tasks"


def submit_tasks(tasks: List[Dict], goal_id: str = None) -> Dict:
    """
    提交任务列表到 Scheduler
    
    使用 http.client 而不是 requests（避免连接问题）
    """
    print(f"[DAG Builder] 提交 {len(tasks)} 个任务到 {SCHEDULER_HOST}:{SCHEDULER_PORT}...")
    
    result = {
        "success": True,
        "task_ids": [],
        "submitted": 0,
        "failed": 0,
        "errors": []
    }
    
    for i, task in enumerate(tasks, 1):
        try:
            # 构建 API 负载
            payload = {
                "title": task.get("title", f"Task {i}"),
                "description": f"{task.get('task_type', 'shell')}:{task.get('command', '')}",
                "priority": task.get("priority", 5)
            }
            
            # 如果有依赖关系
            if "dependencies" in task and task["dependencies"]:
                payload["dependencies"] = task["dependencies"]
            
            # 发送请求（使用 http.client）
            conn = http.client.HTTPConnection(SCHEDULER_HOST, SCHEDULER_PORT, timeout=10)
            headers = {'Content-Type': 'application/json'}
            conn.request('POST', SCHEDULER_PATH, json.dumps(payload), headers)
            response = conn.getresponse()
            
            status_code = response.status
            body = response.read().decode('utf-8')
            conn.close()
            
            if status_code in [200, 201]:
                response_data = json.loads(body)
                task_id = response_data.get("task_id")
                result["task_ids"].append(task_id)
                result["submitted"] += 1
                print(f"            ✅ 任务 {i}/{len(tasks)}: {task_id}")
            else:
                result["failed"] += 1
                result["errors"].append(f"HTTP {status_code}: {body}")
                print(f"            ❌ 任务 {i}/{len(tasks)}: HTTP {status_code}")
            
            # 小延迟避免 API 过载
            time.sleep(0.1)
        
        except Exception as e:
            result["failed"] += 1
            result["errors"].append(str(e))
            print(f"            ❌ 任务 {i}/{len(tasks)}: {e}")
    
    result["success"] = result["failed"] == 0
    
    print(f"[DAG Builder] ✅ 提交完成：{result['submitted']} 成功，{result['failed']} 失败")
    
    return result


def submit_task(task: Dict, goal_id: str = None) -> Dict:
    """提交单个任务"""
    return submit_tasks([task], goal_id)


def create_dag(tasks: List[Dict], goal_id: str = None) -> Dict:
    """
    创建 DAG 并提交
    
    自动处理依赖关系（顺序执行）
    """
    print(f"[DAG Builder] 创建 DAG...")
    
    # 为任务添加依赖关系（线性 DAG）
    enhanced_tasks = []
    prev_task_id = None
    
    for i, task in enumerate(tasks):
        enhanced_task = task.copy()
        
        # 如果不是第一个任务，添加依赖
        if i > 0 and prev_task_id:
            enhanced_task["dependencies"] = [prev_task_id]
            enhanced_task["title"] = f"{task.get('title', 'Task')} (依赖：{prev_task_id[-8:]})"
        
        enhanced_tasks.append(enhanced_task)
        # 使用临时 ID（实际提交后会更新）
        prev_task_id = f"task_{i}"
    
    # 提交 DAG
    return submit_tasks(enhanced_tasks, goal_id)


if __name__ == "__main__":
    # 测试
    print("🧪 测试 DAG Builder...\n")
    
    # 模拟任务
    test_tasks = [
        {
            "task_type": "shell",
            "command": "echo 'Task 1'",
            "title": "测试任务 1",
            "priority": 5
        },
        {
            "task_type": "shell",
            "command": "echo 'Task 2'",
            "title": "测试任务 2",
            "priority": 5
        }
    ]
    
    print("提交测试任务...")
    result = submit_tasks(test_tasks)
    
    print(f"\n提交结果:")
    print(f"  成功：{result['submitted']}")
    print(f"  失败：{result['failed']}")
    print(f"  任务 IDs: {result['task_ids']}")
