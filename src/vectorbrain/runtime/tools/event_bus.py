#!/usr/bin/env python3
"""
VectorBrain Event Bus - Stage 6

系统事件总线，模块解耦
"""

import sys
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import asyncio

# 添加 VectorBrain 到路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))


# ============================================================================
# 事件数据类
# ============================================================================

@dataclass
class Event:
    """
    系统事件
    
    Attributes:
        name: 事件名称
        data: 事件数据
        timestamp: 时间戳
    """
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# Event Bus 类
# ============================================================================

class EventBus:
    """
    事件总线
    
    发布/订阅模式，实现模块解耦
    """
    
    _instance: Optional['EventBus'] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化事件总线"""
        if self._initialized:
            return
        
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 100  # 最多保留 100 个历史事件
        self._initialized = True
        
        print("[EventBus] Initialized")
    
    def subscribe(self, event_name: str, callback: Callable):
        """
        订阅事件
        
        Args:
            event_name: 事件名称
            callback: 回调函数 async def handler(event: Event)
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        
        self._subscribers[event_name].append(callback)
        print(f"[EventBus] Subscribed to {event_name}")
    
    def unsubscribe(self, event_name: str, callback: Callable):
        """
        取消订阅
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name in self._subscribers:
            if callback in self._subscribers[event_name]:
                self._subscribers[event_name].remove(callback)
                print(f"[EventBus] Unsubscribed from {event_name}")
    
    async def emit(self, event_name: str, data: Dict[str, Any] = None):
        """
        发布事件
        
        Args:
            event_name: 事件名称
            data: 事件数据
        """
        event = Event(name=event_name, data=data or {})
        
        # 记录历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # 通知订阅者
        subscribers = self._subscribers.get(event_name, [])
        
        if subscribers:
            print(f"[EventBus] Emitting {event_name} to {len(subscribers)} subscribers")
            
            # 异步调用所有订阅者
            tasks = [callback(event) for callback in subscribers]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            print(f"[EventBus] No subscribers for {event_name}")
    
    def get_history(self, event_name: str = None, limit: int = 10) -> List[Event]:
        """
        获取历史事件
        
        Args:
            event_name: 事件名称（可选）
            limit: 限制数量
            
        Returns:
            事件列表
        """
        events = self._event_history
        
        if event_name:
            events = [e for e in events if e.name == event_name]
        
        return events[-limit:]
    
    def clear_history(self):
        """清空历史事件"""
        self._event_history.clear()
        print("[EventBus] History cleared")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        subscriber_count = sum(len(subs) for subs in self._subscribers.values())
        
        return {
            "event_types": len(self._subscribers),
            "total_subscribers": subscriber_count,
            "history_size": len(self._event_history)
        }
    
    def summary(self):
        """打印事件总线摘要"""
        print("\n" + "="*60)
        print("VectorBrain Event Bus")
        print("="*60)
        
        stats = self.get_stats()
        print(f"Event Types: {stats['event_types']}")
        print(f"Total Subscribers: {stats['total_subscribers']}")
        print(f"History Size: {stats['history_size']}")
        print()
        
        print("Subscriptions:")
        for event_name, subscribers in self._subscribers.items():
            print(f"  {event_name}: {len(subscribers)} subscribers")
        
        print("="*60 + "\n")


# ============================================================================
# 全局事件总线实例
# ============================================================================

event_bus = EventBus()


# ============================================================================
# 预定义事件助手函数
# ============================================================================

async def emit_task_created(task_id: str, task_title: str):
    """发布任务创建事件"""
    await event_bus.emit("task.created", {
        "task_id": task_id,
        "task_title": task_title
    })


async def emit_task_started(task_id: str):
    """发布任务开始事件"""
    await event_bus.emit("task.started", {
        "task_id": task_id
    })


async def emit_task_completed(task_id: str, success: bool):
    """发布任务完成事件"""
    await event_bus.emit("task.completed", {
        "task_id": task_id,
        "success": success
    })


async def emit_step_executed(task_id: str, step_index: int, tool: str, success: bool):
    """发布步骤执行事件"""
    await event_bus.emit("step.executed", {
        "task_id": task_id,
        "step_index": step_index,
        "tool": tool,
        "success": success
    })


async def emit_tool_called(tool_name: str, input_data: Dict):
    """发布工具调用事件"""
    await event_bus.emit("tool.called", {
        "tool_name": tool_name,
        "input": input_data
    })


async def emit_memory_saved(category: str, key: str):
    """发布记忆保存事件"""
    await event_bus.emit("memory.saved", {
        "category": category,
        "key": key
    })


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    async def test_subscriber(event: Event):
        """测试订阅者"""
        print(f"[Test Subscriber] Received event: {event.name}")
        print(f"  Data: {event.data}")
    
    async def main():
        print("=== 测试 1: 订阅事件 ===")
        event_bus.subscribe("task.created", test_subscriber)
        event_bus.subscribe("task.completed", test_subscriber)
        
        print("\n=== 测试 2: 发布事件 ===")
        await emit_task_created("test_001", "Test Task")
        await emit_task_completed("test_001", True)
        
        print("\n=== 测试 3: 获取历史 ===")
        history = event_bus.get_history(limit=5)
        print(f"History: {len(history)} events")
        for event in history:
            print(f"  - {event.name} at {event.timestamp}")
        
        print("\n=== 测试 4: 统计信息 ===")
        event_bus.summary()
        
        print("\n=== 测试 5: 取消订阅 ===")
        event_bus.unsubscribe("task.created", test_subscriber)
        await emit_task_created("test_002", "Another Task")
        
        print("\n✅ Event Bus 测试完成！")
    
    asyncio.run(main())
