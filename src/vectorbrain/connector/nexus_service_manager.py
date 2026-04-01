#!/usr/bin/env python3
"""
[YOUR_AI_NAME]系统服务管理脚本 - 启动/停止所有核心服务

用法:
    python3 ~/.vectorbrain/connector/nexus_service_manager.py start    # 启动所有
    python3 ~/.vectorbrain/connector/nexus_service_manager.py stop     # 停止所有
    python3 ~/.vectorbrain/connector/nexus_service_manager.py restart  # 重启所有
    python3 ~/.vectorbrain/connector/nexus_service_manager.py status   # 查看状态
"""

import subprocess
import os
import sys
import time
from pathlib import Path

CONNECTOR_DIR = Path.home() / ".vectorbrain" / "connector"
STATE_DIR = Path.home() / ".vectorbrain" / "state"

SERVICES = {
    "network_monitor": {
        "script": "network_monitor.py",
        "log": "network_monitor.log",
        "loop": False,  # 自己带循环
        "args": ""
    },
    "task_manager": {
        "script": "task_manager.py",
        "log": "task_manager.log",
        "loop": True,  # 需要包装成循环
        "interval": 60,  # 1 分钟检查一次
        "code": """
import time
from task_manager import task_manager_loop
while True:
    task_manager_loop()
    time.sleep(60)
"""
    },
    "task_monitor": {
        "script": "task_monitor.py",
        "log": "task_monitor.log",
        "loop": True,
        "interval": 300,  # 5 分钟检查一次
        "code": """
import time
from task_monitor import check_task_execution_counts, save_alerts
while True:
    anomalies = check_task_execution_counts()
    if anomalies:
        save_alerts(anomalies)
    time.sleep(300)
"""
    },
    "opportunity_poller": {
        "script": "opportunity_poller.py",
        "log": "opportunity_poller.log",
        "loop": True,
        "interval": 600,  # 10 分钟检查一次
        "code": """
import time
from opportunity_poller import check_opportunities, update_status, format_message, write_pending_queue
while True:
    opps = check_opportunities()
    if opps:
        for o in opps:
            update_status(o['opportunity_id'])
        write_pending_queue(opps, format_message(opps))
    time.sleep(600)
"""
    },
}

def get_pid(name):
    """获取进程 PID"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", name],
            capture_output=True,
            text=True
        )
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except:
        return []

def start_service(name, config):
    """启动单个服务"""
    print(f"🚀 启动 {name}...")
    
    # 检查是否已在运行
    pids = get_pid(name)
    if pids:
        print(f"   ⚠️  已在运行 (PID: {', '.join(pids)})")
        return
    
    # 确保日志目录存在
    log_path = CONNECTOR_DIR / config["log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 启动服务
    if config["loop"]:
        # 需要包装成循环的服务
        cmd = f"cd {CONNECTOR_DIR} && nohup python3 -c \"{config['code']}\" >> {log_path} 2>&1 &"
    else:
        # 自带循环的服务
        script_path = CONNECTOR_DIR / config["script"]
        cmd = f"cd {CONNECTOR_DIR} && nohup python3 {config['script']} >> {log_path} 2>&1 &"
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        time.sleep(1)
        
        # 验证是否启动成功
        pids = get_pid(name)
        if pids:
            print(f"   ✅ 启动成功 (PID: {pids[0]})")
            return True
        else:
            print(f"   ❌ 启动失败 (未找到进程)")
            return False
    except Exception as e:
        print(f"   ❌ 启动异常：{e}")
        return False

def stop_service(name):
    """停止单个服务"""
    print(f"🛑 停止 {name}...")
    
    pids = get_pid(name)
    if not pids:
        print(f"   ℹ️  未运行")
        return
    
    for pid in pids:
        try:
            subprocess.run(["kill", pid], check=True)
            print(f"   ✅ 已停止 (PID: {pid})")
        except Exception as e:
            print(f"   ❌ 停止失败：{e}")

def cmd_start():
    """启动所有服务"""
    print("=" * 60)
    print("🧠 [YOUR_AI_NAME]服务管理器 - 启动所有服务")
    print("=" * 60)
    
    success = 0
    for name, config in SERVICES.items():
        if start_service(name, config):
            success += 1
    
    print("")
    print(f"完成：{success}/{len(SERVICES)} 服务启动成功")
    print("=" * 60)

def cmd_stop():
    """停止所有服务"""
    print("=" * 60)
    print("🧠 [YOUR_AI_NAME]服务管理器 - 停止所有服务")
    print("=" * 60)
    
    for name in SERVICES.keys():
        stop_service(name)
    
    print("")
    print("完成")
    print("=" * 60)

def cmd_restart():
    """重启所有服务"""
    cmd_stop()
    time.sleep(2)
    cmd_start()

def cmd_status():
    """查看状态"""
    os.system(f"python3 {CONNECTOR_DIR}/nexus_health_check.py")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  {sys.argv[0]} start   # 启动所有")
        print(f"  {sys.argv[0]} stop    # 停止所有")
        print(f"  {sys.argv[0]} restart # 重启所有")
        print(f"  {sys.argv[0]} status  # 查看状态")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        cmd_start()
    elif command == "stop":
        cmd_stop()
    elif command == "restart":
        cmd_restart()
    elif command == "status":
        cmd_status()
    else:
        print(f"未知命令：{command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
