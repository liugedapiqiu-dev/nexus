#!/usr/bin/env python3
"""
VectorBrain V4 - Planner Core

核心编排器：协调各个模块完成从 Goal 到 DAG 的转换
"""

import sys
from pathlib import Path
from typing import List, Dict

# 添加路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from planner.goal_engine import parse_goal
from planner.memory_retriever import retrieve_relevant_patterns
from planner.pattern_reasoner import reason_from_patterns
from planner.task_generator import generate_tasks
from planner.dag_builder import submit_tasks


def run_planner(goal_text: str, priority: int = 5) -> Dict:
    """
    运行完整的 Planner 流程
    
    Args:
        goal_text: 目标描述
        priority: 优先级 1-10
    
    Returns:
        结果字典：{
            "goal_id": str,
            "task_ids": List[str],
            "tasks_count": int,
            "success": bool
        }
    """
    print("\n" + "=" * 60)
    print("🧠 VectorBrain V4 Planner")
    print("=" * 60)
    
    result = {
        "goal_id": None,
        "task_ids": [],
        "tasks_count": 0,
        "success": False,
        "patterns_found": 0,
        "hints_count": 0
    }
    
    try:
        # Step 1: 解析目标
        print("\n[1/5] 解析目标...")
        goal = parse_goal(goal_text, priority)
        result["goal_id"] = goal.goal_id
        
        # Step 2: 检索相关知识
        print("\n[2/5] 检索知识库...")
        patterns = retrieve_relevant_patterns(goal)
        result["patterns_found"] = len(patterns)
        
        # Step 3: 基于模式推理
        print("\n[3/5] 模式推理...")
        hints = reason_from_patterns(goal, patterns)
        result["hints_count"] = len(hints)
        
        # Step 4: 生成任务
        print("\n[4/5] 生成任务...")
        tasks = generate_tasks(goal, hints)
        result["tasks_count"] = len(tasks)
        
        # Step 5: 提交到 Scheduler
        print("\n[5/5] 提交任务...")
        submit_result = submit_tasks(tasks, goal.goal_id)
        result["task_ids"] = submit_result.get("task_ids", [])
        result["success"] = submit_result.get("success", False)
        
        # 总结
        print("\n" + "=" * 60)
        print("✅ Planner 执行完成")
        print("=" * 60)
        print(f"目标 ID: {result['goal_id']}")
        print(f"找到模式：{result['patterns_found']} 个")
        print(f"生成提示：{result['hints_count']} 个")
        print(f"生成任务：{result['tasks_count']} 个")
        print(f"提交成功：{result['success']}")
        print(f"任务 IDs: {result['task_ids']}")
        
    except Exception as e:
        print(f"\n❌ Planner 执行失败：{e}")
        import traceback
        traceback.print_exc()
        result["success"] = False
    
    return result


def quick_plan(goal_text: str) -> List[str]:
    """
    快速规划（简化版）
    
    Args:
        goal_text: 目标描述
    
    Returns:
        任务 ID 列表
    """
    result = run_planner(goal_text)
    return result.get("task_ids", [])


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Planner Core...\n")
    
    test_goals = [
        "列出当前目录的文件",
        "检查系统信息"
    ]
    
    for goal in test_goals:
        print(f"\n测试目标：{goal}")
        result = run_planner(goal)
        
        if result["success"]:
            print(f"✅ 成功创建 {result['tasks_count']} 个任务")
        else:
            print(f"❌ 失败")
        print("-" * 60)
