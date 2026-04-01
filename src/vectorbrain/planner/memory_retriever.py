#!/usr/bin/env python3
"""
Layer: intelligence
Status: secondary
Boundary: Intelligence -> Memory read path for planning/retrieval; should consume memory via stable adapters/contracts.
Architecture refs:
- architecture/layer-manifest.md
- architecture/runtime-boundary-rules.md

VectorBrain V4 - Memory Retriever

从知识库中检索相关知识模式
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 添加路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from memory.knowledge_db import load_patterns


def retrieve_relevant_patterns(goal) -> List[Tuple]:
    """
    检索与目标相关的知识模式
    
    Args:
        goal: Goal 对象
    
    Returns:
        相关知识模式列表
    """
    print(f"[Memory Retriever] 检索相关知识...")
    
    # 加载所有模式
    all_patterns = load_patterns()
    
    if not all_patterns:
        print(f"[Memory Retriever] ⚠️  知识库为空")
        return []
    
    relevant = []
    goal_text = goal.description.lower()
    goal_tags = goal.tags
    
    for pattern in all_patterns:
        pattern_id = pattern[0]
        pattern_type = pattern[1]
        description = pattern[2]
        confidence = pattern[3]
        
        # 计算相关性分数
        score = 0.0
        
        # 1. 关键词匹配
        desc_words = description.lower().split()
        for word in goal_text.split():
            if len(word) > 3 and any(word in dw for dw in desc_words):
                score += 0.2
        
        # 2. 标签匹配
        if pattern_type in goal_tags:
            score += 0.5
        
        # 3. 类型匹配
        if 'slow' in pattern_type and any(t in goal_tags for t in ['data_analysis', 'coding']):
            score += 0.3
        if 'failure' in pattern_type:
            score += 0.2  # 失败模式总是相关的
        
        # 4. 置信度加权
        score *= confidence
        
        # 阈值过滤
        if score > 0.1:
            relevant.append((pattern, score))
    
    # 按分数排序
    relevant.sort(key=lambda x: x[1], reverse=True)
    
    print(f"[Memory Retriever] ✅ 找到 {len(relevant)} 个相关模式")
    for p, score in relevant[:3]:  # 只显示前 3 个
        print(f"            - {p[1]}: {p[2][:50]}... (score: {score:.2f})")
    
    # 只返回模式本身（不带分数）
    return [p for p, _ in relevant]


def retrieve_patterns_by_type(pattern_type: str) -> List[Tuple]:
    """按类型检索模式"""
    from memory.knowledge_db import load_patterns_by_type
    return load_patterns_by_type(pattern_type)


def get_all_patterns() -> List[Tuple]:
    """获取所有模式"""
    return load_patterns()


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Memory Retriever...\n")
    
    # 先创建测试目标
    from goal_engine import parse_goal
    
    test_goals = [
        "列出文件",
        "分析数据",
        "检查系统"
    ]
    
    for goal_text in test_goals:
        goal = parse_goal(goal_text)
        patterns = retrieve_relevant_patterns(goal)
        print(f"  找到 {len(patterns)} 个相关模式\n")
