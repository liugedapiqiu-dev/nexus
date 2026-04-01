#!/usr/bin/env python3
"""
VectorBrain V4 - Pattern Reasoner

根据知识模式推理，生成规划提示
"""

from typing import List, Dict, Tuple


def reason_from_patterns(goal, patterns: List[Tuple]) -> List[Dict]:
    """
    根据知识模式推理，生成规划提示
    
    Args:
        goal: Goal 对象
        patterns: 知识模式列表
    
    Returns:
        提示列表
    """
    print(f"[Pattern Reasoner] 开始推理...")
    
    hints = []
    
    for pattern in patterns:
        pattern_id = pattern[0]
        pattern_type = pattern[1]
        description = pattern[2]
        confidence = pattern[3]
        
        # 根据不同模式类型生成提示
        if pattern_type == "slow_task":
            hints.append({
                "type": "avoid_long_tasks",
                "description": "检测到慢任务模式，建议将长任务拆分为更小的子任务",
                "confidence": confidence,
                "action": "split_tasks",
                "max_duration": 5.0  # 秒
            })
        
        elif pattern_type == "high_failure_rate":
            hints.append({
                "type": "add_retry_logic",
                "description": "检测到高失败率，建议增加重试机制",
                "confidence": confidence,
                "action": "increase_retries",
                "retry_count": 3
            })
        
        elif pattern_type == "task_type_distribution":
            hints.append({
                "type": "optimize_task_type",
                "description": "检测到任务类型分布不均，建议优化任务类型选择",
                "confidence": confidence,
                "action": "balance_types"
            })
        
        elif pattern_type == "frequent_failure":
            hints.append({
                "type": "error_handling",
                "description": "检测到频繁失败，建议增强错误处理",
                "confidence": confidence,
                "action": "add_error_handling"
            })
        
        else:
            # 通用提示
            hints.append({
                "type": "general_optimization",
                "description": f"基于模式 '{pattern_type}' 的优化建议",
                "confidence": confidence,
                "action": "optimize"
            })
    
    print(f"[Pattern Reasoner] ✅ 生成 {len(hints)} 个提示")
    for hint in hints:
        print(f"            - {hint['type']}: {hint['description'][:50]}...")
    
    return hints


def apply_hints_to_plan(hints: List[Dict], tasks: List[Dict]) -> List[Dict]:
    """
    将提示应用到任务计划
    
    Args:
        hints: 提示列表
        tasks: 任务列表
    
    Returns:
        优化后的任务列表
    """
    optimized_tasks = tasks.copy()
    
    for hint in hints:
        if hint['type'] == 'avoid_long_tasks':
            # 标记可能需要拆分的任务
            for task in optimized_tasks:
                if 'timeout' not in task:
                    task['timeout'] = int(hint.get('max_duration', 5.0) * 60)
        
        elif hint['type'] == 'add_retry_logic':
            # 增加重试次数
            retry_count = hint.get('retry_count', 3)
            for task in optimized_tasks:
                task['retries'] = max(task.get('retries', 2), retry_count)
        
        elif hint['type'] == 'error_handling':
            # 添加错误处理标记
            for task in optimized_tasks:
                task['error_handling'] = True
    
    return optimized_tasks


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Pattern Reasoner...\n")
    
    # 模拟模式数据
    test_patterns = [
        ("pattern_001", "slow_task", "Tasks > 5s frequently appear", 0.7),
        ("pattern_002", "high_failure_rate", "High failure rate detected (25%)", 0.8),
        ("pattern_003", "task_type_distribution", "Shell tasks dominate", 0.6)
    ]
    
    # 模拟目标
    from goal_engine import parse_goal
    goal = parse_goal("分析数据并生成报告")
    
    hints = reason_from_patterns(goal, test_patterns)
    
    print(f"\n生成的提示:")
    for hint in hints:
        print(f"  - {hint['type']}: {hint['action']}")
