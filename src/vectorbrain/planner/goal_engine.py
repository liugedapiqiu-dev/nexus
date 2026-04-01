#!/usr/bin/env python3
"""
VectorBrain V4 - Goal Engine

解析用户目标，提取关键信息
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Goal:
    """目标定义"""
    goal_id: str
    description: str
    created_at: float
    priority: int = 5
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, description: str, priority: int = 5) -> 'Goal':
        """创建新目标"""
        return cls(
            goal_id=f"goal_{uuid.uuid4().hex[:12]}",
            description=description,
            created_at=time.time(),
            priority=priority,
            tags=cls._extract_tags(description),
            context=cls._extract_context(description)
        )
    
    @staticmethod
    def _extract_tags(description: str) -> List[str]:
        """从描述中提取标签"""
        text = description.lower()
        tags = []
        
        if any(word in text for word in ['file', 'list', 'dir', 'folder']):
            tags.append('file_operation')
        if any(word in text for word in ['data', 'analyze', 'report']):
            tags.append('data_analysis')
        if any(word in text for word in ['code', 'program', 'script']):
            tags.append('coding')
        if any(word in text for word in ['web', 'http', 'url', 'scrape']):
            tags.append('web_operation')
        if any(word in text for word in ['system', 'info', 'check']):
            tags.append('system_query')
        
        return tags
    
    @staticmethod
    def _extract_context(description: str) -> Dict[str, Any]:
        """提取上下文信息"""
        context = {
            'estimated_tasks': 1,
            'requires_shell': False,
            'requires_python': False,
            'requires_http': False
        }
        
        text = description.lower()
        
        if any(word in text for word in ['shell', 'command', 'bash', 'ls', 'cat']):
            context['requires_shell'] = True
            context['estimated_tasks'] = max(context['estimated_tasks'], 1)
        
        if any(word in text for word in ['python', 'script', 'code', 'run']):
            context['requires_python'] = True
            context['estimated_tasks'] = max(context['estimated_tasks'], 2)
        
        if any(word in text for word in ['web', 'http', 'url', 'api']):
            context['requires_http'] = True
            context['estimated_tasks'] = max(context['estimated_tasks'], 2)
        
        return context
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'goal_id': self.goal_id,
            'description': self.description,
            'priority': self.priority,
            'tags': self.tags,
            'context': self.context,
            'created_at': self.created_at
        }


def parse_goal(goal_text: str, priority: int = 5) -> Goal:
    """
    解析目标文本
    
    Args:
        goal_text: 目标描述
        priority: 优先级 1-10
    
    Returns:
        Goal 对象
    """
    print(f"[Goal Engine] 解析目标：{goal_text[:50]}...")
    goal = Goal.create(goal_text, priority)
    print(f"[Goal Engine] ✅ 目标解析完成：{goal.goal_id}")
    print(f"            标签：{goal.tags}")
    print(f"            预估任务数：{goal.context.get('estimated_tasks', 1)}")
    return goal


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Goal Engine...\n")
    
    test_goals = [
        "列出当前目录的文件",
        "分析销售数据并生成报告",
        "检查系统信息",
        "爬取网页数据"
    ]
    
    for goal_text in test_goals:
        goal = parse_goal(goal_text)
        print(f"  目标 ID: {goal.goal_id}")
        print(f"  标签：{goal.tags}")
        print()
