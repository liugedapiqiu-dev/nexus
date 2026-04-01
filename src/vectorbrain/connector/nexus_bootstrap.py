#!/usr/bin/env python3
"""
Nexus Bootstrap - 首次启动自动初始化
自动检测路径、创建数据库、配置定时任务
"""

import os
import sys
import json
import subprocess
import socket
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from nexus_config import (
    HOME, VECTORBRAIN_DIR, OPENCLAW_DIR,
    load_nexus_config, create_nexus_config, get_path
)


def check_ollama_service():
    """检查 Ollama 服务是否运行"""
    try:
        with socket.create_connection(('127.0.0.1', 11434), timeout=3):
            return True
    except:
        return False


def get_ollama_models():
    """获取已安装的 Ollama 模型列表"""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        models = []
        for line in result.stdout.split("\n")[1:]:
            if line.strip() and "NAME" not in line:
                parts = line.split()
                if parts:
                    models.append(parts[0])
        return models
    except:
        return []


def ensure_ollama_running():
    """确保 Ollama 服务运行"""
    if check_ollama_service():
        return True

    print("  Ollama 服务未运行，正在启动...")
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time
        for _ in range(10):
            time.sleep(1)
            if check_ollama_service():
                print("  Ollama 服务已启动")
                return True
    except Exception as e:
        print(f"  启动 Ollama 失败: {e}")
    return False


def ensure_ollama_models():
    """确保必要的 Ollama 模型已下载"""
    print("\n[0/6] 检查 Ollama 模型...")

    # 确保 Ollama 服务运行
    if not ensure_ollama_running():
        print("  无法启动 Ollama 服务，请手动运行 'ollama serve'")
        return False

    installed_models = get_ollama_models()
    print(f"  已安装模型: {', '.join(installed_models) or '无'}")

    required_models = {
        "nomic-embed-text": "向量模型 (必须)",
    }

    missing = []
    for model, desc in required_models.items():
        if model not in installed_models:
            missing.append((model, desc))

    if not missing:
        print("  所有必需模型已安装")
        return True

    print("\n  缺少以下模型:")
    for model, desc in missing:
        print(f"    - {model}: {desc}")

    print("\n  是否自动下载? (Y/n)", end=" ")
    response = input().strip().lower()
    if response and response != 'y':
        print("  跳过模型下载")
        return True

    for model, desc in missing:
        print(f"\n  下载 {model} ({desc})...")
        print(f"  这可能需要几分钟到十几分钟，请耐心等待...")

        try:
            proc = subprocess.Popen(["ollama", "pull", model], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                line = line.strip()
                if line:
                    print(f"  {line}")
            proc.wait()
            if proc.returncode == 0:
                print(f"  ✅ {model} 下载完成")
            else:
                print(f"  ❌ {model} 下载失败")
        except Exception as e:
            print(f"  ❌ 下载出错: {e}")

    return True


def ensure_directory(path):
    """确保目录存在"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def init_memory_databases():
    """初始化记忆数据库"""
    print("\n[1/6] 初始化记忆数据库...")

    memory_dir = get_path("vectorbrain", "memory")
    tasks_dir = get_path("vectorbrain", "tasks")

    ensure_directory(memory_dir)
    ensure_directory(tasks_dir)

    db_files = [
        "episodic_memory.db",
        "knowledge_memory.db",
        "information_memory.db",
        "habit_memory.db",
        "heart_memory.db",
        "work_memory_hub.db",
        "lessons_memory.db",
    ]

    for db in db_files:
        db_path = memory_dir / db
        if not db_path.exists():
            db_path.touch()
            print(f"  Created: {db}")

    task_db = tasks_dir / "task_queue.db"
    if not task_db.exists():
        task_db.touch()
        print(f"  Created: task_queue.db")

    print("  记忆数据库初始化完成")
    return True


def init_openclaw_integration():
    """初始化 OpenClaw 集成"""
    print("\n[2/6] 初始化 OpenClaw 集成...")

    # 检测 OpenClaw 是否存在
    if not OPENCLAW_DIR.exists():
        print("  OpenClaw 未安装，跳过集成")
        return False

    # 检测 VectorBrain MCP 扩展
    vb_ext = OPENCLAW_DIR / "extensions" / "vectorbrain"
    if vb_ext.exists():
        print(f"  VectorBrain MCP 扩展已就绪: {vb_ext}")
    else:
        print(f"  警告: VectorBrain MCP 扩展未找到")

    # 创建 OpenClaw hooks 目录的符号链接或引用
    hooks_dir = get_path("openclaw", "hooks")
    ensure_directory(hooks_dir)

    # 检测 session 目录
    sessions_dir = get_path("openclaw", "sessions")
    print(f"  OpenClaw sessions: {sessions_dir}")

    print("  OpenClaw 集成初始化完成")
    return True


def setup_session_archiver():
    """配置会话归档器 - 自动发现 sessions 目录"""
    print("\n[3/6] 配置会话归档器...")

    sessions_dir = get_path("openclaw", "sessions")
    vb_connector = get_path("vectorbrain", "connector")

    archiver_script = vb_connector / "session_archiver.py"
    if not archiver_script.exists():
        print(f"  警告: session_archiver.py 未找到")
        return False

    # 创建会话归档配置
    archiver_config = {
        "sessions_dir": str(sessions_dir),
        "archiver_script": str(archiver_script),
        "last_archive": None,
        "auto_archive": True,
        "archive_interval_hours": 1,
    }

    config_path = VECTORBRAIN_DIR / "session_archiver_config.json"
    with open(config_path, "w") as f:
        json.dump(archiver_config, f, indent=2, ensure_ascii=False)

    print(f"  会话目录: {sessions_dir}")
    print(f"  归档配置: {config_path}")
    print("  会话归档器配置完成")
    return True


def setup_chat_scraper():
    """配置飞书聊天抓取 - 自动检测配置"""
    print("\n[4/6] 配置聊天抓取器...")

    oc_config = get_path("openclaw") / "openclaw.json"

    if oc_config.exists():
        try:
            with open(oc_config) as f:
                config = json.load(f)

            feishu_config = config.get("channels", {}).get("feishu", {})
            if feishu_config.get("enabled"):
                print(f"  飞书集成已启用")
            else:
                print(f"  飞书集成未启用")
        except Exception as e:
            print(f"  无法读取 OpenClaw 配置: {e}")
    else:
        print(f"  OpenClaw 配置文件未找到，跳过飞书配置")

    print("  聊天抓取器配置完成")
    return True


def setup_cron_jobs():
    """配置定时任务 - 使用正确的动态路径"""
    print("\n[5/6] 配置定时任务...")

    cron_dir = get_path("openclaw", "cron")
    ensure_directory(cron_dir)

    vb_connector = get_path("vectorbrain", "connector")
    chat_scraper = vb_connector / "chat_scraper_v2.py"

    if not chat_scraper.exists():
        print(f"  警告: chat_scraper_v2.py 未找到，跳过定时任务")
        return False

    # 创建定时任务配置
    cron_config = {
        "jobs": [
            {
                "id": "nexus-session-archive",
                "name": "Nexus Session Archive",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3600000},  # 每小时
                "script": str(archiver_script if (archiver_script := vb_connector / "session_archiver.py").exists() else ""),
                "action": "archive_sessions",
            },
            {
                "id": "nexus-chat-scrap",
                "name": "Nexus Chat Scrap",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 10800000},  # 每3小时
                "script": str(chat_scraper),
                "action": "--mode incremental",
            }
        ]
    }

    # 保存到 VectorBrain 目录（方便管理）
    cron_config_path = VECTORBRAIN_DIR / "cron_config.json"
    with open(cron_config_path, "w") as f:
        json.dump(cron_config, f, indent=2, ensure_ascii=False)

    # 也复制到 OpenClaw cron 目录
    oc_cron_path = cron_dir / "nexus_jobs.json"
    with open(oc_cron_path, "w") as f:
        json.dump(cron_config, f, indent=2, ensure_ascii=False)

    print(f"  定时任务配置: {cron_config_path}")
    print(f"  OpenClaw 定时任务: {oc_cron_path}")
    print("  定时任务配置完成")
    return True


def create_startup_marker():
    """创建启动标记"""
    marker = {
        "first_run_at": datetime.now().isoformat(),
        "nexus_version": "1.0.0",
        "status": "initialized",
    }

    marker_path = VECTORBRAIN_DIR / ".nexus_initialized"
    with open(marker_path, "w") as f:
        json.dump(marker, f, indent=2)

    print(f"\n启动标记: {marker_path}")


def main():
    print("=" * 50)
    print("  Nexus Brain - 首次启动初始化")
    print("=" * 50)
    print(f"\nVectorBrain: {VECTORBRAIN_DIR}")
    print(f"OpenClaw:    {OPENCLAW_DIR}")

    # 确保配置存在
    config = load_nexus_config()
    if not config:
        print("\n创建 Nexus 配置...")
        config = create_nexus_config()

    # 初始化步骤
    success = True
    success &= ensure_ollama_models()
    success &= init_memory_databases()
    success &= init_openclaw_integration()
    success &= setup_session_archiver()
    success &= setup_chat_scraper()
    success &= setup_cron_jobs()

    if success:
        create_startup_marker()
        print("\n" + "=" * 50)
        print("  Nexus 初始化完成!")
        print("=" * 50)
        print("\n下一步:")
        print("  1. 配置 API Keys (复制 .env.template 为 .env)")
        print("  2. 启动 Ollama: ollama serve")
        print("  3. 启动 Nexus: python nexus_bootstrap.py")
    else:
        print("\n" + "=" * 50)
        print("  Nexus 初始化完成 (部分功能可能不可用)")
        print("=" * 50)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
