#!/usr/bin/env python3
"""
Nexus Path Resolution - 集中式路径解析
所有脚本都应该从这儿导入路径，而不是硬编码

用法:
    from nexus_paths import VB, OC, get_path

    # VectorBrain 路径
    VB.memory_dir       # ~/.vectorbrain/memory
    VB.tasks_dir       # ~/.vectorbrain/tasks
    VB.connector_dir    # ~/.vectorbrain/connector

    # OpenClaw 路径
    OC.workspace_dir    # ~/.openclaw/workspace
    OC.sessions_dir     # ~/.openclaw/agents/main/sessions
    OC.skills_dir       # ~/.openclaw/skills

    # 动态解析
    get_path("vectorbrain", "memory")
    get_path("openclaw", "sessions")
"""

import os
import json
from pathlib import Path
from typing import Optional

HOME = Path.home()
VECTORBRAIN_HOME = HOME / ".vectorbrain"
OPENCLAW_HOME = HOME / ".openclaw"

# 缓存配置
_config_cache = None


def _load_config():
    """加载 Nexus 配置"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_path = VECTORBRAIN_HOME / ".nexus_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                _config_cache = json.load(f)
                return _config_cache
        except:
            pass
    return None


def _get_default_paths():
    """获取默认路径"""
    return {
        "vectorbrain": {
            "root": str(VECTORBRAIN_HOME),
            "memory": str(VECTORBRAIN_HOME / "memory"),
            "tasks": str(VECTORBRAIN_HOME / "tasks"),
            "logs": str(VECTORBRAIN_HOME / "logs"),
            "connector": str(VECTORBRAIN_HOME / "connector"),
            "skills": str(VECTORBRAIN_HOME / "skills"),
            "heart": str(VECTORBRAIN_HOME / "heart"),
            "planner": str(VECTORBRAIN_HOME / "planner"),
            "intelligence": str(VECTORBRAIN_HOME / "intelligence"),
            "dag": str(VECTORBRAIN_HOME / "dag"),
            "experience": str(VECTORBRAIN_HOME / "experience"),
            "reflection": str(VECTORBRAIN_HOME / "reflection"),
            "runtime": str(VECTORBRAIN_HOME / "runtime"),
            "state": str(VECTORBRAIN_HOME / "state"),
        },
        "openclaw": {
            "root": str(OPENCLAW_HOME),
            "workspace": str(OPENCLAW_HOME / "workspace"),
            "sessions": str(OPENCLAW_HOME / "agents" / "main" / "sessions"),
            "skills": str(OPENCLAW_HOME / "skills"),
            "extensions": str(OPENCLAW_HOME / "extensions"),
            "hooks": str(OPENCLAW_HOME / "hooks"),
            "cron": str(OPENCLAW_HOME / "cron"),
            "identity": str(OPENCLAW_HOME / "identity"),
        }
    }


def get_paths():
    """获取所有路径（从配置或默认）"""
    config = _load_config()
    if config and "paths" in config:
        return config["paths"]
    return _get_default_paths()


def get_path(system: str, key: str = None) -> Path:
    """
    获取路径

    用法:
        get_path("vectorbrain")       -> Path ~/.vectorbrain
        get_path("vectorbrain", "memory") -> Path ~/.vectorbrain/memory
        get_path("openclaw", "sessions")  -> Path ~/.openclaw/agents/main/sessions
    """
    paths = get_paths()
    if key:
        return Path(paths[system][key])
    return Path(paths[system]["root"])


def get_path_str(system: str, key: str = None) -> str:
    """获取路径字符串"""
    return str(get_path(system, key))


# ============================================================
# 便捷访问器
# ============================================================

class PathBundle:
    """路径Bundle，方便访问"""

    def __init__(self, system: str):
        self._system = system
        self._paths = get_paths()[system]

    def __getattr__(self, name: str) -> Path:
        if name.startswith("_"):
            return super().__getAttribute__(name)
        if name in self._paths:
            return Path(self._paths[name])
        # 尝试转换为 snake_case
        snake = self._to_snake(name)
        if snake in self._paths:
            return Path(self._paths[snake])
        raise AttributeError(f"Unknown path: {name}")

    def _to_snake(self, name: str) -> str:
        """转换为 snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def __repr__(self):
        return f"PathBundle({self._system})"


# 全局访问器
VB = PathBundle("vectorbrain")
OC = PathBundle("openclaw")


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_sessions_dirs():
    """查找所有可能的 sessions 目录"""
    candidates = [
        OC.sessions_dir,
        OPENCLAW_HOME / "sessions",
        OPENCLAW_HOME / "agents" / "main" / "sessions",
    ]
    found = []
    for d in candidates:
        if d.exists() and d.is_dir():
            found.append(d)
    return found


def find_openclaw_config():
    """查找 OpenClaw 配置文件"""
    candidates = [
        OPENCLAW_HOME / "openclaw.json",
        OPENCLAW_HOME / "config.json",
    ]
    for f in candidates:
        if f.exists():
            return f
    return None


if __name__ == "__main__":
    print("Nexus Paths")
    print("=" * 40)
    print(f"VectorBrain root: {VB.root}")
    print(f"  memory: {VB.memory}")
    print(f"  tasks: {VB.tasks}")
    print(f"  connector: {VB.connector}")
    print()
    print(f"OpenClaw root: {OC.root}")
    print(f"  workspace: {OC.workspace}")
    print(f"  sessions: {OC.sessions}")
    print(f"  skills: {OC.skills}")
    print()
    print(f"Available sessions dirs: {find_sessions_dirs()}")
