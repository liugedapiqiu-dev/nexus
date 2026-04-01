#!/usr/bin/env python3
"""
VectorBrain V3 - Reflection Engine

从经验中提炼知识模式（episodes → patterns）
"""

import uuid
import time
from typing import List, Dict, Tuple
from pathlib import Path

# 导入数据库模块
import sys
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from memory.episodic_db import load_recent_episodes, get_episode_count
from memory.knowledge_db import insert_pattern, load_patterns, get_pattern_count


def run_reflection(episodes_limit: int = 200, min_episodes: int = 20):
    """
    运行反思引擎，从经验中发现模式
    
    Args:
        episodes_limit: 加载最近 N 条经验
        min_episodes: 最少需要 N 条经验才开始反思
    """
    episodes = load_recent_episodes(episodes_limit)
    
    if len(episodes) < min_episodes:
        print(f"[Reflection] ⏳ 经验数量不足 ({len(episodes)}/{min_episodes})，跳过反思")
        return []
    
    print(f"[Reflection] 🧠 开始反思 {len(episodes)} 条经验...")
    
    patterns = []
    
    # 模式 1: 慢任务检测
    slow_pattern = _discover_slow_tasks(episodes)
    if slow_pattern:
        patterns.append(slow_pattern)
    
    # 模式 2: 失败率检测
    failure_pattern = _discover_high_failure_rate(episodes)
    if failure_pattern:
        patterns.append(failure_pattern)
    
    # 模式 3: 任务类型分布
    type_pattern = _discover_task_type_patterns(episodes)
    if type_pattern:
        patterns.append(type_pattern)
    
    # 存储发现的模式
    for pattern in patterns:
        insert_pattern(pattern)
        print(f"[Reflection] ✅ 发现模式：{pattern['pattern_type']} - {pattern['description']} (confidence: {pattern['confidence']:.2f})")
    
    print(f"[Reflection] 📊 本次发现 {len(patterns)} 个模式，总计 {get_pattern_count()} 个模式")
    
    return patterns


def _discover_slow_tasks(episodes: List[Tuple]) -> Dict:
    """
    发现慢任务模式
    
    规则：执行时间 > 5 秒的任务超过 10 个
    """
    slow_tasks = [e for e in episodes if e[7] > 5.0]  # execution_time > 5s
    
    if len(slow_tasks) > 10:
        confidence = min(0.95, 0.7 + (len(slow_tasks) / 100))
        
        return {
            "pattern_id": f"pattern_{uuid.uuid4().hex[:8]}",
            "pattern_type": "slow_task",
            "description": f"Tasks with execution_time > 5s frequently appear ({len(slow_tasks)} cases)",
            "confidence": confidence
        }
    
    return None


def _discover_high_failure_rate(episodes: List[Tuple]) -> Dict:
    """
    发现高失败率模式
    
    规则：失败率 > 20%
    """
    total = len(episodes)
    failed = sum(1 for e in episodes if e[8] == 0)  # success = 0
    
    if total > 0:
        failure_rate = failed / total
        
        if failure_rate > 0.2:
            confidence = min(0.95, failure_rate + 0.3)
            
            return {
                "pattern_id": f"pattern_{uuid.uuid4().hex[:8]}",
                "pattern_type": "high_failure_rate",
                "description": f"High failure rate detected ({failure_rate*100:.1f}%, {failed}/{total} tasks)",
                "confidence": confidence
            }
    
    return None


def _discover_task_type_patterns(episodes: List[Tuple]) -> Dict:
    """
    发现任务类型模式
    
    规则：某种任务类型占比 > 50%
    """
    type_counts = {}
    for e in episodes:
        task_type = e[3]
        type_counts[task_type] = type_counts.get(task_type, 0) + 1
    
    total = len(episodes)
    
    for task_type, count in type_counts.items():
        ratio = count / total
        
        if ratio > 0.5 and count > 20:
            return {
                "pattern_id": f"pattern_{uuid.uuid4().hex[:8]}",
                "pattern_type": "task_type_distribution",
                "description": f"Task type '{task_type}' dominates ({ratio*100:.1f}%, {count}/{total} tasks)",
                "confidence": 0.6 + (ratio * 0.3)
            }
    
    return None


def get_reflection_summary() -> Dict:
    """获取反思摘要"""
    episodes = load_recent_episodes(100)
    patterns = load_patterns()
    
    summary = {
        "total_episodes": get_episode_count(),
        "total_patterns": len(patterns),
        "pattern_types": {},
        "avg_confidence": 0
    }
    
    # 统计模式类型
    for p in patterns:
        p_type = p[1]
        summary["pattern_types"][p_type] = summary["pattern_types"].get(p_type, 0) + 1
    
    # 计算平均置信度
    if patterns:
        summary["avg_confidence"] = sum(p[3] for p in patterns) / len(patterns)
    
    return summary


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Reflection Engine...")
    
    # 运行反思
    patterns = run_reflection()
    
    # 获取摘要
    summary = get_reflection_summary()
    print(f"\n📊 反思摘要:")
    print(f"  总经验数：{summary['total_episodes']}")
    print(f"  总模式数：{summary['total_patterns']}")
    print(f"  平均置信度：{summary['avg_confidence']:.2f}")
    print(f"  模式类型：{summary['pattern_types']}")
