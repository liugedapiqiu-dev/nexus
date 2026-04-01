#!/usr/bin/env python3
"""
OpenClaw 启动自检脚本
检查 VectorBrain 状态、记忆系统、网关状态等
"""

import os
import sys
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def check_process(name, pattern):
    """检查进程是否运行"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', pattern],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pid = result.stdout.strip().split('\n')[0]
            return True, pid
        return False, None
    except Exception as e:
        return False, str(e)

def check_port(port):
    """检查端口是否监听"""
    try:
        result = subprocess.run(
            ['lsof', '-i', f':{port}'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def check_database_count(db_path, table):
    """检查数据库记录数"""
    try:
        if not os.path.exists(db_path):
            return 0, "文件不存在"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        conn.close()
        return count, "OK"
    except Exception as e:
        return 0, str(e)

def generate_report():
    """生成自检报告"""
    report = []
    startup_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 1. 检查 OpenClaw 进程
    report.append(f"{Colors.BLUE}🏥 OpenClaw 启动自检报告{Colors.END}")
    report.append(f"\n启动时间：{startup_time}")
    
    oc_running, oc_pid = check_process('openclaw', 'openclaw')
    if oc_running:
        report.append(f"运行进程：{Colors.GREEN}✅ 正常 (PID: {oc_pid}){Colors.END}")
    else:
        report.append(f"运行进程：{Colors.YELLOW}⚠️ 未检测到{Colors.END}")
    
    # 2. 检查 VectorBrain 状态
    report.append(f"\n{Colors.BLUE}🧠 VectorBrain 状态{Colors.END}")
    
    vb_running, vb_pid = check_process('agent_core_loop', 'agent_core_loop.py')
    if vb_running:
        report.append(f"  - 进程状态：{Colors.GREEN}✅ 运行中 (PID: {vb_pid}){Colors.END}")
    else:
        report.append(f"  - 进程状态：{Colors.RED}❌ 未运行{Colors.END}")
    
    # 检查记忆数据库
    episodic_db = Path.home() / '.vectorbrain' / 'memory' / 'episodic_memory.db'
    knowledge_db = Path.home() / '.vectorbrain' / 'memory' / 'knowledge_memory.db'
    
    episodic_count, _ = check_database_count(str(episodic_db), 'episodes')
    knowledge_count, _ = check_database_count(str(knowledge_db), 'knowledge')
    
    report.append(f"  - 情景记忆：{Colors.GREEN}{episodic_count} 条{Colors.END}")
    report.append(f"  - 知识记忆：{Colors.GREEN}{knowledge_count} 条{Colors.END}")
    
    # 3. 检查 OpenClaw 状态
    report.append(f"\n{Colors.BLUE}🦾 OpenClaw 状态{Colors.END}")
    
    # 检查网关端口
    gateway_port = 18789
    if check_port(gateway_port):
        report.append(f"  - 网关端口：{Colors.GREEN}✅ {gateway_port} 正常{Colors.END}")
    else:
        report.append(f"  - 网关端口：{Colors.YELLOW}⚠️ {gateway_port} 未监听{Colors.END}")
    
    # 检查飞书通道（简化检查）
    feishu_config = Path.home() / '.openclaw' / 'openclaw.json'
    if feishu_config.exists():
        report.append(f"  - 飞书通道：{Colors.GREEN}✅ 已配置{Colors.END}")
    else:
        report.append(f"  - 飞书通道：{Colors.YELLOW}⚠️ 未找到配置{Colors.END}")
    
    # 检查技能数量
    skills_dir = Path.home() / '.openclaw' / 'skills'
    if skills_dir.exists():
        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
        report.append(f"  - 技能数量：{Colors.GREEN}{skill_count} 个{Colors.END}")
    else:
        report.append(f"  - 技能数量：{Colors.YELLOW}⚠️ 未找到{Colors.END}")
    
    # 4. 总结
    report.append(f"\n{Colors.GREEN}✅ 系统就绪，等待指令{Colors.END}")
    
    return '\n'.join(report)

def send_report(report):
    """发送报告到当前会话"""
    try:
        # 使用 OpenClaw CLI 发送消息
        subprocess.run(
            ['openclaw', 'send', report],
            capture_output=True,
            text=True
        )
        print("报告已发送")
    except Exception as e:
        print(f"发送失败：{e}")
        # 如果发送失败，至少打印出来
        print("\n自检报告:")
        print(report)

if __name__ == '__main__':
    print("🏥 OpenClaw 启动自检中...")
    
    # 生成报告
    report = generate_report()
    
    # 发送报告
    send_report(report)
    
    print("\n✅ 自检完成")
