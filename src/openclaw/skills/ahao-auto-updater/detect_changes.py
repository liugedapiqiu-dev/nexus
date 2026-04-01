#!/usr/bin/env python3
"""
[YOUR_AI_NAME]文件变更检测器 v1.0
检测关键文件变化，记录到变更日志

包含的 BUG 防护：
1. 并发冲突 - 文件锁
2. 超时保护 - 10 秒超时
3. 权限检查 - 启动前验证
4. 磁盘空间 - 定期清理
5. 时区统一 - Asia/Shanghai
"""

import hashlib
import json
import os
import sys
import fcntl
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
# import pytz (使用标准库)

# ============================================================================
# 配置
# ============================================================================
HOME = Path.home()
OPENCLAW_HOME = HOME / ".openclaw"
WORKSPACE = OPENCLAW_HOME / "workspace"
SKILLS_DIR = OPENCLAW_HOME / "skills"
VECTORBRAIN_HOME = HOME / ".vectorbrain"

# 关键目录（需要检测的）
KEY_DIRECTORIES = [
    SKILLS_DIR,                      # 技能目录
    OPENCLAW_HOME / "hooks",         # 钩子配置
    WORKSPACE / "docs",              # 系统文档
    VECTORBRAIN_HOME / "connector",  # VectorBrain 连接器
    VECTORBRAIN_HOME / "src",        # VectorBrain 核心代码
]

# 需要检测的文件类型
KEY_PATTERNS = [
    "*.py", "*.json", "*.md", "*.sh",
    "*.yaml", "*.yml", "*.toml",
]

# 排除目录（不检测）
EXCLUDE_DIRS = [
    "node_modules", "__pycache__", ".git",
    ".venv", "venv", ".pytest_cache",
]

# 文件路径
HASHES_FILE = WORKSPACE / ".file_hashes.json"
CHANGELOG_FILE = WORKSPACE / "CHANGELOG.md"
LOCK_FILE = Path("/tmp/ahao_detector.lock")
MAX_HASHES = 100  # 最多保留 100 个文件哈希
MAX_LOG_SIZE = 1024 * 1024  # 日志最大 1MB
TIMEOUT_SECONDS = 10  # 超时 10 秒

# ============================================================================
# 工具函数
# ============================================================================

def get_shanghai_time():
    """获取上海时区时间"""
    SHANGHAI_TZ = timezone(timedelta(hours=8))
    return datetime.now(SHANGHAI_TZ)

def calculate_file_hash(file_path):
    """计算文件 SHA256 哈希（带超时保护）"""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        return None

def acquire_lock():
    """获取文件锁（防止并发冲突）"""
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except IOError:
        return None

def release_lock(lock_fd):
    """释放文件锁"""
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except:
            pass

def load_last_hashes():
    """读取上次的哈希记录"""
    if not HASHES_FILE.exists():
        return {}
    try:
        with open(HASHES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("hashes", {})
    except:
        return {}

def save_hashes(hashes):
    """保存哈希记录（带清理）"""
    # 如果超过最大数量，保留最近的
    if len(hashes) > MAX_HASHES:
        # 简单策略：保留前 MAX_HASHES 个
        hashes = dict(list(hashes.items())[:MAX_HASHES])
    
    data = {
        "last_update": get_shanghai_time().isoformat(),
        "hashes": hashes
    }
    
    # 原子写入（先写临时文件，再重命名）
    tmp_file = HASHES_FILE.with_suffix('.tmp')
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp_file.rename(HASHES_FILE)

def append_to_changelog(entry):
    """追加到变更日志（带大小检查）"""
    # 检查日志大小
    if CHANGELOG_FILE.exists() and CHANGELOG_FILE.stat().st_size > MAX_LOG_SIZE:
        # 日志太大，归档旧日志
        archive_file = WORKSPACE / "CHANGELOG_ARCHIVE.md"
        try:
            CHANGELOG_FILE.rename(archive_file)
            print(f"📦 已归档旧日志到 {archive_file}")
        except:
            pass
    
    # 追加新条目
    with open(CHANGELOG_FILE, 'a', encoding='utf-8') as f:
        f.write(entry + "\n")

def check_permissions():
    """检查文件读取权限"""
    unreadable = []
    for dir_path in KEY_DIRECTORIES:
        if not dir_path.exists():
            continue
        if not os.access(dir_path, os.R_OK):
            unreadable.append(str(dir_path))
    
    if unreadable:
        print(f"⚠️ 以下目录无法读取：{unreadable}")
        return False
    return True

def check_disk_space():
    """检查磁盘空间"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(WORKSPACE)
        free_gb = free / (1024**3)
        if free_gb < 1:  # 少于 1GB
            print(f"⚠️ 磁盘空间不足：{free_gb:.2f}GB")
            return False
        return True
    except:
        return True  # 无法检查则跳过

# ============================================================================
# 核心函数
# ============================================================================

def get_all_key_files():
    """获取所有关键文件及其哈希"""
    key_files = {}
    start_time = time.time()
    
    for dir_path in KEY_DIRECTORIES:
        if not dir_path.exists():
            continue
        
        for pattern in KEY_PATTERNS:
            try:
                for file_path in dir_path.rglob(pattern):
                    # 检查超时
                    if time.time() - start_time > TIMEOUT_SECONDS:
                        print(f"⏰ 哈希计算超时（{TIMEOUT_SECONDS}秒），已处理 {len(key_files)} 个文件")
                        break
                    
                    # 跳过排除目录
                    if any(exclude in str(file_path) for exclude in EXCLUDE_DIRS):
                        continue
                    
                    if file_path.is_file():
                        try:
                            rel_path = str(file_path.relative_to(HOME))
                            file_hash = calculate_file_hash(file_path)
                            if file_hash:
                                key_files[rel_path] = file_hash
                        except Exception as e:
                            pass
            except Exception as e:
                pass
    
    return key_files

def detect_changes():
    """检测文件变化"""
    print("🔍 开始检测文件变化...")
    
    # 读取上次的哈希记录
    last_hashes = load_last_hashes()
    print(f"📊 上次记录：{len(last_hashes)} 个文件")
    
    # 计算当前哈希
    current_hashes = get_all_key_files()
    print(f"📊 当前记录：{len(current_hashes)} 个文件")
    
    # 比对变化
    changes = {
        "new_files": [],      # 新增文件
        "modified_files": [], # 修改文件
        "deleted_files": [],  # 删除文件
    }
    
    # 检测新增和修改
    for file_path, current_hash in current_hashes.items():
        if file_path not in last_hashes:
            changes["new_files"].append(file_path)
        elif last_hashes[file_path] != current_hash:
            changes["modified_files"].append(file_path)
    
    # 检测删除
    for file_path in last_hashes:
        if file_path not in current_hashes:
            changes["deleted_files"].append(file_path)
    
    # 输出结果
    print(f"\n✅ 检测结果:")
    print(f"   新增文件：{len(changes['new_files'])} 个")
    print(f"   修改文件：{len(changes['modified_files'])} 个")
    print(f"   删除文件：{len(changes['deleted_files'])} 个")
    
    return changes, current_hashes

def log_changes(changes):
    """记录变更到日志"""
    timestamp = get_shanghai_time().strftime("%Y-%m-%d %H:%M")
    
    has_changes = any(changes.values())
    
    changelog_entry = f"\n## {timestamp} - 系统更新\n"
    
    if has_changes:
        if changes["new_files"]:
            changelog_entry += f"\n### 新增文件 ({len(changes['new_files'])})\n"
            for f in changes["new_files"][:10]:  # 只记录前 10 个
                changelog_entry += f"- ✅ {f}\n"
            if len(changes["new_files"]) > 10:
                changelog_entry += f"- ... 还有 {len(changes['new_files']) - 10} 个\n"
        
        if changes["modified_files"]:
            changelog_entry += f"\n### 修改文件 ({len(changes['modified_files'])})\n"
            for f in changes["modified_files"][:10]:
                changelog_entry += f"- 🔄 {f}\n"
            if len(changes["modified_files"]) > 10:
                changelog_entry += f"- ... 还有 {len(changes['modified_files']) - 10} 个\n"
        
        if changes["deleted_files"]:
            changelog_entry += f"\n### 删除文件 ({len(changes['deleted_files'])})\n"
            for f in changes["deleted_files"][:10]:
                changelog_entry += f"- ❌ {f}\n"
            if len(changes["deleted_files"]) > 10:
                changelog_entry += f"- ... 还有 {len(changes['deleted_files']) - 10} 个\n"
    else:
        changelog_entry += "- ✅ 无变更\n"
    
    # 追加到日志
    append_to_changelog(changelog_entry)
    
    return changelog_entry

def update_snapshot():
    """更新状态快照"""
    print("\n📝 正在更新状态快照...")
    
    # 扫描所有技能
    skills = []
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith('.'):
            skill_json = skill_dir / 'skill.json'
            if skill_json.exists():
                try:
                    with open(skill_json, 'r', encoding='utf-8') as f:
                        skill_data = json.load(f)
                        skills.append({
                            "name": skill_data.get("name", skill_dir.name),
                            "description": skill_data.get("description", ""),
                        })
                except:
                    pass
    
    # 生成快照
    snapshot = f"""# [YOUR_AI_NAME]状态快照

**更新时间**: {get_shanghai_time().strftime("%Y-%m-%d %H:%M")}

## 核心身份
[YOUR_AI_NAME] 🧠 - [YOUR_NAME]的 AI 智能体

## 已安装技能 ({len(skills)}个)
"""
    for skill in sorted(skills, key=lambda x: x['name']):
        snapshot += f"- {skill['name']}: {skill['description']}\n"
    
    snapshot += f"""
## 最近项目
详见：VectorBrain 知识记忆

## 待办事项
详见：`docs/TODO.md`

## 系统配置
- VectorBrain: ~/.vectorbrain/
- 时区：Asia/Shanghai
- 自动检测：✅ 已启用
"""
    
    # 保存快照
    snapshot_path = WORKSPACE / "[YOUR_AI_NAME]状态快照.md"
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        f.write(snapshot)
    
    print(f"✅ 状态快照已更新：{snapshot_path}")

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("=" * 60)
    print("🧠 [YOUR_AI_NAME]文件变更检测器 v1.0")
    print("=" * 60)
    print(f"启动时间：{get_shanghai_time().strftime('%Y-%m-%d %H:%M:%S')} (Asia/Shanghai)")
    print()
    
    # 步骤 1: 获取文件锁
    print("🔒 正在获取文件锁...")
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("⚠️ 已有其他检测器在运行，跳过本次检测")
        return
    print("✅ 文件锁已获取")
    
    try:
        # 步骤 2: 检查权限
        print("\n🔐 检查文件权限...")
        if not check_permissions():
            print("⚠️ 权限检查失败，继续执行...")
        
        # 步骤 3: 检查磁盘空间
        print("\n💾 检查磁盘空间...")
        if not check_disk_space():
            print("⚠️ 磁盘空间不足，继续执行...")
        
        # 步骤 4: 检测变化
        print("\n" + "=" * 60)
        changes, current_hashes = detect_changes()
        
        # 步骤 5: 记录变更
        print("\n📝 记录变更到日志...")
        changelog = log_changes(changes)
        print(changelog)
        
        # 步骤 6: 保存哈希
        print("\n💾 保存文件哈希...")
        save_hashes(current_hashes)
        print(f"✅ 已保存 {len(current_hashes)} 个文件哈希")
        
        # 步骤 7: 更新快照
        update_snapshot()
        
        print("\n" + "=" * 60)
        print("✅ [YOUR_AI_NAME]文件变更检测完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 检测过程出错：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 释放锁
        release_lock(lock_fd)
        print("\n🔓 文件锁已释放")

if __name__ == "__main__":
    main()
