#!/usr/bin/env python3
"""
VectorBrain V3 - Task DSL (Domain Specific Language)

定义任务的标准格式，供 Planner 使用
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import uuid


@dataclass
class TaskDSL:
    """
    任务 DSL 定义
    
    用于 Planner 生成标准化的任务描述
    """
    task_type: str  # shell, python, http, general
    command: str    # 具体命令/代码/URL
    title: str      # 任务标题
    priority: int = 5       # 优先级 1-10 (1 最高)
    retries: int = 2        # 最大重试次数
    timeout: int = 30       # 超时时间（分钟）
    dependencies: List[str] = None  # 依赖的任务 ID
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 API 请求）"""
        return {
            "title": self.title,
            "description": f"{self.task_type}:{self.command}",
            "priority": self.priority,
            "task_type": self.task_type,
            "command": self.command,
            "retries": self.retries,
            "timeout": self.timeout,
            "dependencies": self.dependencies
        }
    
    def to_api_payload(self) -> Dict[str, Any]:
        """转换为 API 请求负载"""
        return {
            "title": self.title,
            "description": f"{self.task_type}:{self.command}",
            "priority": self.priority
        }


@dataclass
class Plan:
    """
    计划定义
    
    由 Planner 生成，包含多个任务
    """
    goal: str
    tasks: List[TaskDSL]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks]
        }
    
    def generate_task_ids(self) -> List[str]:
        """为所有任务生成 ID"""
        task_ids = []
        for task in self.tasks:
            task_id = f"task_{uuid.uuid4().hex[:16]}"
            task_ids.append(task_id)
        return task_ids


class TaskDSLBuilder:
    """
    Task DSL 构建器
    
    方便链式创建任务
    """
    
    def __init__(self):
        self.task_type = "general"
        self.command = ""
        self.title = ""
        self.priority = 5
        self.retries = 2
        self.timeout = 30
        self.dependencies = []
    
    def set_type(self, task_type: str) -> 'TaskDSLBuilder':
        """设置任务类型"""
        self.task_type = task_type
        return self
    
    def set_command(self, command: str) -> 'TaskDSLBuilder':
        """设置命令"""
        self.command = command
        return self
    
    def set_title(self, title: str) -> 'TaskDSLBuilder':
        """设置标题"""
        self.title = title
        return self
    
    def set_priority(self, priority: int) -> 'TaskDSLBuilder':
        """设置优先级"""
        self.priority = priority
        return self
    
    def set_retries(self, retries: int) -> 'TaskDSLBuilder':
        """设置重试次数"""
        self.retries = retries
        return self
    
    def set_timeout(self, timeout: int) -> 'TaskDSLBuilder':
        """设置超时时间"""
        self.timeout = timeout
        return self
    
    def add_dependency(self, task_id: str) -> 'TaskDSLBuilder':
        """添加依赖"""
        self.dependencies.append(task_id)
        return self
    
    def build(self) -> TaskDSL:
        """构建任务"""
        return TaskDSL(
            task_type=self.task_type,
            command=self.command,
            title=self.title,
            priority=self.priority,
            retries=self.retries,
            timeout=self.timeout,
            dependencies=self.dependencies
        )


# 便捷函数

def shell_task(command: str, title: str = "", priority: int = 5) -> TaskDSL:
    """创建 Shell 任务"""
    if not title:
        title = f"Shell: {command[:30]}..."
    
    return TaskDSL(
        task_type="shell",
        command=command,
        title=title,
        priority=priority
    )


def python_task(code: str, title: str = "", priority: int = 5) -> TaskDSL:
    """创建 Python 任务"""
    if not title:
        title = f"Python: {code[:30]}..."
    
    return TaskDSL(
        task_type="python",
        command=code,
        title=title,
        priority=priority
    )


def http_task(url: str, method: str = "GET", title: str = "", priority: int = 5) -> TaskDSL:
    """创建 HTTP 任务"""
    if not title:
        title = f"HTTP: {method} {url[:30]}..."
    
    command = f"{method} {url}"
    
    return TaskDSL(
        task_type="http",
        command=command,
        title=title,
        priority=priority
    )


if __name__ == "__main__":
    # 测试
    print("🧪 测试 Task DSL...")
    
    # 方法 1: 直接创建
    task1 = shell_task("ls -la", "列出文件", priority=1)
    print(f"\n任务 1: {task1.to_dict()}")
    
    # 方法 2: 使用构建器
    task2 = (TaskDSLBuilder()
        .set_type("shell")
        .set_command("echo hello")
        .set_title("问候测试")
        .set_priority(3)
        .set_retries(1)
        .build())
    
    print(f"任务 2: {task2.to_dict()}")
    
    # 方法 3: 创建计划
    plan = Plan(
        goal="数据分析流程",
        tasks=[
            shell_task("python load_data.py", "加载数据", priority=1),
            shell_task("python clean_data.py", "清洗数据", priority=2),
            shell_task("python analyze.py", "分析数据", priority=3),
            shell_task("python report.py", "生成报告", priority=4)
        ]
    )
    
    print(f"\n计划：{plan.goal}")
    for i, task in enumerate(plan.tasks, 1):
        print(f"  {i}. {task.title} (priority: {task.priority})")
