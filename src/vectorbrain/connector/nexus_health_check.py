#!/usr/bin/env python3
"""
[YOUR_AI_NAME]系统健康监控脚本 - 一键查看所有核心脚本运行状态

用法:
    python3 ~/.vectorbrain/connector/nexus_health_check.py

或者添加到 alias:
    alias nexus-status='python3 ~/.vectorbrain/connector/nexus_health_check.py'
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
COMMON_DIR = VECTORBRAIN_HOME / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from notify_helper import log_event

# 配置
CORE_SERVICES = [
    {"name": "OpenClaw Gateway", "pattern": "openclaw", "critical": True},
    {"name": "Ollama Serve", "pattern": "ollama serve", "critical": True},
    {"name": "Agent Core Loop", "pattern": "agent_core_loop.py", "critical": True},
]

MONITOR_SERVICES = [
    {"name": "Network Monitor", "pattern": "network_monitor.py", "critical": True},
    {"name": "Task Manager", "pattern": "task_manager.py", "critical": False},
    {"name": "Task Monitor", "pattern": "task_monitor", "critical": False},
    {"name": "Opportunity Poller", "pattern": "opportunity_poller", "critical": False},
    {"name": "Dashboard V3", "pattern": "dashboard_v3.py", "critical": False},
]

def get_pid(pattern):
    """获取进程的 PID"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True
        )
        pids = result.stdout.strip().split('\n')
        return [p for p in pids if p] if pids else []
    except Exception as e:
        log_event("nexus_health_check", "get_pid_failed", {"pattern": pattern, "error": str(e)}, level="warning")
        return []

def get_process_info(pid):
    """获取进程详细信息"""
    try:
        result = subprocess.run(
            ["ps", "-p", pid, "-o", "pid,etimes,command"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split(None, 2)
            uptime = int(parts[1]) if len(parts) > 1 else 0
            return {
                "pid": pid,
                "uptime": uptime,
                "uptime_str": format_uptime(uptime),
                "command": parts[2] if len(parts) > 2 else ""
            }
        return None
    except Exception as e:
        log_event("nexus_health_check", "get_process_info_failed", {"pid": pid, "error": str(e)}, level="warning")
        return None

def format_uptime(seconds):
    """格式化运行时间"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds // 60}分钟"
    elif seconds < 86400:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}小时{mins}分钟"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}天{hours}小时"

def check_network():
    """检查网络状态"""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
            capture_output=True,
            timeout=3
        )
        return result.returncode == 0
    except Exception as e:
        log_event("nexus_health_check", "check_network_failed", {"error": str(e)}, level="warning")
        return False

def check_ollama_models():
    """检查 Ollama 模型"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            return len(lines) - 1  # 减去标题行
        return 0
    except Exception as e:
        log_event("nexus_health_check", "check_ollama_models_failed", {"error": str(e)}, level="warning")
        return 0

def get_log_tail(log_path, lines=3):
    """读取日志文件最后几行"""
    try:
        path = Path(log_path)
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return [l.strip() for l in all_lines[-lines:]]
    except Exception as e:
        log_event("nexus_health_check", "get_log_tail_failed", {"log_path": str(log_path), "error": str(e)}, level="warning")
        return None

def print_status():
    """打印状态报告"""
    print("=" * 80)
    print("🧠 [YOUR_AI_NAME]系统健康检查")
    print("=" * 80)
    print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # 网络状态
    network_ok = check_network()
    print(f"🌐 网络状态：{'✅ 正常' if network_ok else '❌ 断开'}")
    
    # Ollama 模型
    model_count = check_ollama_models()
    print(f"📦 Ollama 模型：{model_count} 个")
    
    print("")
    print("-" * 80)
    print("🔧 核心服务 (必须运行)")
    print("-" * 80)
    
    core_running = 0
    for service in CORE_SERVICES:
        pids = get_pid(service["pattern"])
        status = "✅" if pids else "❌"
        critical = "🔴" if service["critical"] and not pids else ""
        
        if pids:
            core_running += 1
            info = get_process_info(pids[0])
            uptime = info["uptime_str"] if info else "未知"
            print(f"{status} {service['name']:<25} PID: {pids[0]:<8} 运行：{uptime} {critical}")
        else:
            print(f"{status} {service['name']:<25} 未运行 {critical}")
    
    print("")
    print("-" * 80)
    print("📊 监控服务 (建议运行)")
    print("-" * 80)
    
    monitor_running = 0
    for service in MONITOR_SERVICES:
        pids = get_pid(service["pattern"])
        status = "✅" if pids else "❌"
        
        if pids:
            monitor_running += 1
            info = get_process_info(pids[0])
            uptime = info["uptime_str"] if info else "未知"
            print(f"{status} {service['name']:<25} PID: {pids[0]:<8} 运行：{uptime}")
        else:
            print(f"{status} {service['name']:<25} 未运行")
    
    print("")
    print("-" * 80)
    print("📝 最近日志摘要")
    print("-" * 80)
    
    log_files = [
        ("Network Monitor", "~/.vectorbrain/connector/network_monitor.log"),
        ("Task Manager", "~/.vectorbrain/connector/task_manager.log"),
    ]
    
    for name, path in log_files:
        lines = get_log_tail(os.path.expanduser(path))
        if lines:
            print(f"\n{name}:")
            for line in lines:
                print(f"  {line[:100]}")
    
    print("")
    print("=" * 80)
    
    # 总结
    total_core = len(CORE_SERVICES)
    total_monitor = len(MONITOR_SERVICES)
    total = total_core + total_monitor
    running = core_running + monitor_running
    
    health_score = int((running / total) * 100)
    
    if health_score >= 90:
        score_emoji = "🟢"
        status_text = "优秀"
    elif health_score >= 70:
        score_emoji = "🟡"
        status_text = "良好"
    else:
        score_emoji = "🔴"
        status_text = "需关注"
    
    print(f"健康评分：{score_emoji} {health_score}/100 ({status_text})")
    print(f"运行中：{running}/{total} 服务")
    print(f"  核心：{core_running}/{total_core}")
    print(f"  监控：{monitor_running}/{total_monitor}")
    print("=" * 80)
    
    # 告警
    missing_critical = [s for s in CORE_SERVICES if not get_pid(s["pattern"]) and s["critical"]]
    if missing_critical:
        print("\n🚨 严重告警：以下核心服务未运行！")
        for s in missing_critical:
            print(f"   - {s['name']}")
        print("\n建议立即启动或检查配置")
    
    return health_score

if __name__ == "__main__":
    health_score = print_status()
    sys.exit(0 if health_score >= 80 else 1)
