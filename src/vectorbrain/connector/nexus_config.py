#!/usr/bin/env python3
"""
Nexus Auto-Configuration System
自动检测并配置所有路径，首次运行时自动初始化
"""

import os
import json
import sys
import socket
import uuid
from pathlib import Path
from datetime import datetime

HOME = Path.home()
VECTORBRAIN_DIR = HOME / ".vectorbrain"
OPENCLAW_DIR = HOME / ".openclaw"


def get_openclaw_sessions_dir():
    """自动检测 OpenClaw sessions 目录"""
    candidates = [
        OPENCLAW_DIR / "agents" / "main" / "sessions",
        OPENCLAW_DIR / "sessions",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    # 默认路径
    default = OPENCLAW_DIR / "agents" / "main" / "sessions"
    default.mkdir(parents=True, exist_ok=True)
    return str(default)


def get_openclaw_config():
    """检测 OpenClaw 配置中的 feishu 等配置"""
    config_path = OPENCLAW_DIR / "openclaw.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                return str(config_path)
        except:
            pass
    return ""


def detect_ollama_models():
    """检测已安装的 Ollama 模型"""
    import subprocess
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


def check_python_packages():
    """检测已安装的 Python 包"""
    import subprocess
    required = ["faiss", "pyautogui", "pandas", "numpy", "pillow", "requests"]
    installed = {}
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True, timeout=30)
        for pkg in required:
            installed[pkg] = pkg.lower() in result.stdout.lower()
    except:
        pass
    return installed


def check_node_packages():
    """检测已安装的 Node 包"""
    import subprocess
    required = ["@vercel/agent-browser"]
    installed = {}
    try:
        result = subprocess.run(["npm", "list", "-g", "--depth=0"], capture_output=True, text=True, timeout=30)
        for pkg in required:
            installed[pkg] = pkg in result.stdout
    except:
        pass
    return installed


def generate_device_id():
    """生成新的设备 ID"""
    return uuid.uuid4().hex


def create_nexus_config():
    """创建 Nexus 配置"""

    config = {
        "version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
        "hostname": socket.gethostname(),

        "paths": {
            "vectorbrain": {
                "root": str(VECTORBRAIN_DIR),
                "memory": str(VECTORBRAIN_DIR / "memory"),
                "tasks": str(VECTORBRAIN_DIR / "tasks"),
                "logs": str(VECTORBRAIN_DIR / "logs"),
                "connector": str(VECTORBRAIN_DIR / "connector"),
                "skills": str(VECTORBRAIN_DIR / "skills"),
                "heart": str(VECTORBRAIN_DIR / "heart"),
                "planner": str(VECTORBRAIN_DIR / "planner"),
                "intelligence": str(VECTORBRAIN_DIR / "intelligence"),
                "dag": str(VECTORBRAIN_DIR / "dag"),
            },
            "openclaw": {
                "root": str(OPENCLAW_DIR),
                "workspace": str(OPENCLAW_DIR / "workspace"),
                "sessions": get_openclaw_sessions_dir(),
                "skills": str(OPENCLAW_DIR / "skills"),
                "extensions": str(OPENCLAW_DIR / "extensions"),
                "hooks": str(OPENCLAW_DIR / "hooks"),
                "cron": str(OPENCLAW_DIR / "cron"),
            }
        },

        "device": {
            "id": generate_device_id(),
            "name": socket.gethostname(),
        },

        "ollama": {
            "host": "127.0.0.1:11434",
            "models": detect_ollama_models(),
        },

        "python_packages": check_python_packages(),
        "node_packages": check_node_packages(),

        "environment": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        },

        "status": {
            "initialized": False,
            "first_run": True,
        }
    }

    config_path = VECTORBRAIN_DIR / ".nexus_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"Nexus configuration created: {config_path}")
    return config


def load_nexus_config():
    """加载 Nexus 配置"""
    config_path = VECTORBRAIN_DIR / ".nexus_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return None


def resolve_path(path_template, config=None):
    """动态解析路径模板
    支持: {VB}, {OC}, {HOME}
    """
    if config is None:
        config = load_nexus_config()

    if config and "paths" in config:
        vb = config["paths"]["vectorbrain"]["root"]
        oc = config["paths"]["openclaw"]["root"]
    else:
        vb = str(VECTORBRAIN_DIR)
        oc = str(OPENCLAW_DIR)

    result = path_template.replace("{VB}", vb)
    result = result.replace("{OC}", oc)
    result = result.replace("{HOME}", str(HOME))
    result = result.replace("~", str(HOME))

    return Path(result)


def get_path(key, subkey=None):
    """获取配置路径
    用法:
        get_path("vectorbrain", "memory")  -> ~/.vectorbrain/memory
        get_path("openclaw", "sessions")    -> ~/.openclaw/agents/main/sessions
    """
    config = load_nexus_config()
    if config and "paths" in config:
        if subkey:
            return Path(config["paths"][key][subkey])
        return Path(config["paths"][key]["root"])
    # Fallback
    if key == "vectorbrain":
        return VECTORBRAIN_DIR
    elif key == "openclaw":
        return OPENCLAW_DIR
    return Path.home()


if __name__ == "__main__":
    print("Nexus Auto-Configuration System")
    print("=" * 40)

    config = create_nexus_config()

    print(f"\nDetected paths:")
    print(f"  VectorBrain: {config['paths']['vectorbrain']['root']}")
    print(f"  OpenClaw: {config['paths']['openclaw']['root']}")
    print(f"  Sessions: {config['paths']['openclaw']['sessions']}")

    print(f"\nOllama models: {', '.join(config['ollama']['models']) or 'none'}")

    print(f"\nPython packages:")
    for pkg, installed in config["python_packages"].items():
        status = "OK" if installed else "MISSING"
        print(f"  {pkg}: {status}")

    print(f"\nDevice ID: {config['device']['id']}")
    print(f"\nNexus is ready! Run nexus_bootstrap.py to initialize.")
