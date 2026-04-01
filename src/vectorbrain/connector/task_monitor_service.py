#!/usr/bin/env python3
"""
定时任务监控器 - 统计所有定时任务的运行状态
每 30 秒更新一次统计数据

状态标记（2026-03-19）：
- 当前归类：旧旁路 / 低优先级辅助层
- 排查原则：不要作为主框架运行状态的第一判据
- 处理原则：如需整顿，优先先确认是否仍有 dashboard/脚本真实依赖
- 参考清单：~/.vectorbrain/SCRIPT_REGISTRY.md
"""

import json
import os
import re
import time
import sys
from datetime import datetime
from pathlib import Path

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
COMMON_DIR = VECTORBRAIN_HOME / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from notify_helper import atomic_write_json, log_event

# 配置
TASKS_CONFIG = [
    {
        "name": "opportunity_poller",
        "display_name": "机会扫描器",
        "log_path": "~/.vectorbrain/connector/opportunity_poller.log",
        "pattern": r"开始轮询机会|发现 \d+ 条高优先级机会|状态更新为 'addressed'",
        "success_pattern": r"✅ 已更新状态|✅ 队列写入完成",
        "error_pattern": r"❌ |Error|Traceback|Exception"
    },
    {
        "name": "task_manager",
        "display_name": "任务执行器",
        "log_path": "~/.vectorbrain/connector/task_manager.log",
        "pattern": r"任务管理器启动|发现 \d+ 个待处理任务",
        "success_pattern": r"任务 .* 执行成功|标记为完成",
        "error_pattern": r"抢占失败|标记为失败|Error|Traceback"
    },
    {
        "name": "network_monitor",
        "display_name": "网络监控",
        "log_path": "~/.vectorbrain/connector/network_monitor.log",
        "pattern": r"网络监控启动|网络检测失败|网络恢复",
        "success_pattern": r"✅ 网络正常|网络已恢复",
        "error_pattern": r"❌ |切换模型失败|判定为断网"
    },
    {
        "name": "session_archiver",
        "display_name": "会话归档",
        "log_path": "~/.vectorbrain/session_archiver.log",
        "pattern": r"归档|Archiv",
        "success_pattern": r"✅ |成功|Success",
        "error_pattern": r"❌ |Error|Traceback|失败"
    }
]

STATS_FILE = Path.home() / ".vectorbrain/state/task_monitor_stats.json"

def parse_log_file(log_path, pattern, success_pattern, error_pattern):
    """解析日志文件，统计运行次数"""
    try:
        log_path = Path(log_path).expanduser()
        if not log_path.exists():
            return 0, 0, 0
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 统计总运行次数
        runs = len(re.findall(pattern, content, re.IGNORECASE))
        # 统计成功次数
        successes = len(re.findall(success_pattern, content, re.IGNORECASE))
        # 统计失败次数
        errors = len(re.findall(error_pattern, content, re.IGNORECASE))
        
        return runs, successes, errors
    except Exception as e:
        print(f"解析 {log_path} 失败：{e}")
        return 0, 0, 0

def get_process_status(task_name):
    """检查进程是否在运行"""
    try:
        import subprocess
        result = subprocess.run(["pgrep", "-f", task_name], capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        pids = [p for p in pids if p]
        return len(pids) > 0, pids
    except Exception as e:
        log_event("task_monitor_service", "get_process_status_failed", {"task_name": task_name, "error": str(e)}, level="warning")
        return False, []

def collect_stats():
    """收集所有任务统计数据"""
    stats = {
        "last_update": datetime.now().isoformat(),
        "tasks": []
    }
    
    for task in TASKS_CONFIG:
        runs, successes, errors = parse_log_file(
            task["log_path"],
            task["pattern"],
            task["success_pattern"],
            task["error_pattern"]
        )
        
        running, pids = get_process_status(task["name"])
        
        task_stats = {
            "name": task["name"],
            "display_name": task["display_name"],
            "status": "running" if running else "stopped",
            "pid": pids[0] if pids else None,
            "total_runs": runs,
            "successes": successes,
            "errors": errors,
            "last_log_time": get_last_log_time(task["log_path"])
        }
        
        stats["tasks"].append(task_stats)
    
    # 保存统计数据
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(STATS_FILE, stats)
    
    return stats

def get_last_log_time(log_path):
    """获取日志文件最后修改时间"""
    try:
        log_path = Path(log_path).expanduser()
        if log_path.exists():
            mtime = log_path.stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        log_event("task_monitor_service", "get_last_log_time_failed", {"log_path": str(log_path), "error": str(e)}, level="warning")
    return None

def main():
    """主循环"""
    print("=" * 60)
    print("📊 定时任务监控器启动")
    print("=" * 60)
    print(f"统计文件：{STATS_FILE}")
    print("更新间隔：30 秒")
    print("=" * 60)
    
    while True:
        try:
            stats = collect_stats()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 已更新统计数据")
            print(f"  任务总数：{len(stats['tasks'])}")
            print(f"  运行中：{sum(1 for t in stats['tasks'] if t['status'] == 'running')}")
            print(f"  已停止：{sum(1 for t in stats['tasks'] if t['status'] == 'stopped')}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 收集统计失败：{e}")
        
        time.sleep(30)

if __name__ == "__main__":
    main()
