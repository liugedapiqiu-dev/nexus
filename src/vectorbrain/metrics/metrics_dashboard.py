#!/usr/bin/env python3
"""
VectorBrain Metrics Dashboard CLI
快速查看系统性能指标
"""

import sys
import os
sys.path.insert(0, os.path.expanduser("~/.vectorbrain/metrics"))

from metrics_collector import get_collector
from datetime import datetime

def print_dashboard():
    """打印 Metrics Dashboard"""
    collector = get_collector()
    
    print("=" * 60)
    print("📊 VectorBrain Metrics Dashboard")
    print("=" * 60)
    print(f"⏰ 时间：{datetime.now().isoformat()}")
    print()
    
    # 核心指标
    throughput = collector.get_throughput(60)
    avg_time = collector.get_avg_execution_time(300)
    queue_depth = collector.get_queue_depth()
    recent_ticks = collector.get_recent_ticks(60)
    
    print("🚀 性能指标")
    print(f"  吞吐量：{throughput:.3f} tasks/sec")
    print(f"  平均执行时间：{avg_time:.2f} sec")
    print(f"  队列深度：{queue_depth} tasks")
    print()
    
    # Scheduler 状态
    if recent_ticks:
        last_tick = recent_ticks[0]
        print("📡 Scheduler 状态")
        print(f"  最近轮询：{last_tick['timestamp']}")
        print(f"  Ready 任务：{last_tick['ready_count']}")
        print(f"  Running 任务：{last_tick['running_count']}")
        print(f"  Dispatch 任务：{last_tick['dispatch_count']}")
        print()
        
        # 计算平均 ready 任务数
        avg_ready = sum(t['ready_count'] for t in recent_ticks) / len(recent_ticks)
        avg_running = sum(t['running_count'] for t in recent_ticks) / len(recent_ticks)
        
        print("📈 平均值 (最近 60 次轮询)")
        print(f"  平均 Ready: {avg_ready:.2f}")
        print(f"  平均 Running: {avg_running:.2f}")
    else:
        print("⚠️  暂无 Scheduler 数据")
    
    print()
    print("=" * 60)

if __name__ == '__main__':
    print_dashboard()
