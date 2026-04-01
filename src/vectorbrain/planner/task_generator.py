#!/usr/bin/env python3
"""
VectorBrain V4 - Task Generator

根据目标和提示生成具体任务
"""

import sys
from pathlib import Path
from typing import List, Dict

# 添加路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from planner.task_dsl import TaskDSL, TaskDSLBuilder


def generate_tasks(goal, hints: List[Dict] = None) -> List[Dict]:
    """
    根据目标生成任务列表
    
    Args:
        goal: Goal 对象
        hints: 规划提示列表
    
    Returns:
        任务列表（字典格式）
    """
    print(f"[Task Generator] 生成任务...")
    
    tasks = []
    text = goal.description.lower()
    tags = goal.tags
    context = goal.context
    
    # 根据标签和关键词生成任务
    if 'file_operation' in tags:
        tasks.extend(_generate_file_tasks(text))
    
    if 'data_analysis' in tags:
        tasks.extend(_generate_data_tasks(text))
    
    if 'coding' in tags:
        tasks.extend(_generate_code_tasks(text))
    
    if 'web_operation' in tags:
        tasks.extend(_generate_web_tasks(text))
    
    if 'system_query' in tags:
        tasks.extend(_generate_system_tasks(text))
    
    # 如果没有匹配到特定模式，生成通用任务
    if not tasks:
        tasks.append(
            TaskDSL(
                task_type="shell",
                command=f"echo '执行目标：{goal.description}'",
                title="执行通用任务",
                priority=goal.priority
            ).to_dict()
        )
    
    # 应用提示优化任务
    if hints:
        from pattern_reasoner import apply_hints_to_plan
        tasks = apply_hints_to_plan(hints, tasks)
    
    print(f"[Task Generator] ✅ 生成 {len(tasks)} 个任务")
    for i, task in enumerate(tasks, 1):
        print(f"            {i}. {task.get('title', 'Task')} ({task.get('task_type', 'unknown')})")
    
    return tasks


def _generate_file_tasks(text: str) -> List[Dict]:
    """生成文件操作任务"""
    tasks = []
    
    if any(word in text for word in ['list', 'ls', 'dir']):
        tasks.append(
            TaskDSL(
                task_type="shell",
                command="ls -la",
                title="列出当前目录文件",
                priority=5
            ).to_dict()
        )
    
    if any(word in text for word in ['check', 'find', 'search']):
        tasks.append(
            TaskDSL(
                task_type="shell",
                command="find . -type f -name '*.txt'",
                title="查找文件",
                priority=5
            ).to_dict()
        )
    
    return tasks


def _generate_data_tasks(text: str) -> List[Dict]:
    """生成数据分析任务"""
    tasks = []
    
    # 基础数据分析流程
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 1: 加载数据'",
            title="加载数据",
            priority=1
        ).to_dict()
    )
    
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 2: 清洗数据'",
            title="清洗数据",
            priority=2
        ).to_dict()
    )
    
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 3: 分析数据'",
            title="分析数据",
            priority=3
        ).to_dict()
    )
    
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 4: 生成报告'",
            title="生成报告",
            priority=4
        ).to_dict()
    )
    
    return tasks


def _generate_code_tasks(text: str) -> List[Dict]:
    """生成编程任务"""
    tasks = []
    
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 1: 创建项目结构'",
            title="创建项目结构",
            priority=1
        ).to_dict()
    )
    
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 2: 编写代码'",
            title="编写代码",
            priority=2
        ).to_dict()
    )
    
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 3: 运行测试'",
            title="运行测试",
            priority=3
        ).to_dict()
    )
    
    return tasks


def _generate_web_tasks(text: str) -> List[Dict]:
    """生成网页操作任务"""
    tasks = []
    
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 1: 发送 HTTP 请求'",
            title="发送 HTTP 请求",
            priority=1
        ).to_dict()
    )
    
    tasks.append(
        TaskDSL(
            task_type="shell",
            command="echo 'Step 2: 解析响应'",
            title="解析响应",
            priority=2
        ).to_dict()
    )
    
    return tasks


def _generate_system_tasks(text: str) -> List[Dict]:
    """生成系统查询任务"""
    tasks = []
    
    if any(word in text for word in ['info', 'system', 'uname']):
        tasks.append(
            TaskDSL(
                task_type="shell",
                command="uname -a",
                title="获取系统信息",
                priority=5
            ).to_dict()
        )
    
    if any(word in text for word in ['check', 'status', 'health']):
        tasks.append(
            TaskDSL(
                task_type="shell",
                command="uptime",
                title="检查系统状态",
                priority=5
            ).to_dict()
        )
    
    return tasks


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Task Generator...\n")
    
    from goal_engine import parse_goal
    
    test_goals = [
        "列出当前目录的文件",
        "分析销售数据",
        "检查系统信息"
    ]
    
    for goal_text in test_goals:
        goal = parse_goal(goal_text)
        tasks = generate_tasks(goal)
        print(f"  生成 {len(tasks)} 个任务\n")
