#!/usr/bin/env python3
"""
版本自动归档系统
自动检测并归档旧版本文件（如 Dashboard、脚本等），保持工作区整洁
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
WORKSPACE = Path.home() / ".openclaw" / "workspace"
ARCHIVE_DIR = VECTORBRAIN_HOME / "archive"

# 需要监控的文件模式
FILE_PATTERNS = {
    "dashboard": {
        "pattern": "dashboard*.py",
        "keep_latest": 2,  # 保留最新 2 个版本
        "description": "Dashboard 版本"
    },
    "skill_backup": {
        "pattern": "*.bak",
        "keep_latest": 0,  # 全部归档
        "description": "技能备份文件"
    },
    "old_reports": {
        "pattern": "*_report_*.md",
        "keep_days": 30,  # 保留 30 天
        "description": "旧报告文件"
    }
}

def find_versioned_files(directory, pattern):
    """查找带版本号的文件"""
    files = list(directory.glob(pattern))
    
    # 按修改时间排序（最新的在前）
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    return files

def archive_old_files(files_to_archive, reason=""):
    """归档旧文件"""
    if not files_to_archive:
        return 0
    
    # 创建归档目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_subdir = ARCHIVE_DIR / f"auto_archive_{timestamp}"
    archive_subdir.mkdir(parents=True, exist_ok=True)
    
    archived_count = 0
    for file in files_to_archive:
        try:
            # 移动文件到归档目录
            dest = archive_subdir / file.name
            shutil.move(str(file), str(dest))
            archived_count += 1
            print(f"  📦 归档：{file.name}")
        except Exception as e:
            print(f"  ⚠️ 归档失败 {file.name}: {e}")
    
    return archived_count

def cleanup_dashboards():
    """清理 Dashboard 版本"""
    print("\n📊 检查 Dashboard 版本...")
    
    dashboard_files = find_versioned_files(VECTORBRAIN_HOME, "dashboard*.py")
    
    if len(dashboard_files) <= 2:
        print(f"  ✅ 当前 {len(dashboard_files)} 个版本，无需清理")
        return 0
    
    # 保留最新 2 个，归档其他的
    files_to_archive = dashboard_files[2:]
    
    if files_to_archive:
        print(f"  📦 发现 {len(files_to_archive)} 个旧版本需要归档")
        archived = archive_old_files(files_to_archive, "Dashboard 旧版本")
        return archived
    
    return 0

def cleanup_backup_files():
    """清理备份文件"""
    print("\n🗑️ 检查备份文件...")
    
    backup_files = list(VECTORBRAIN_HOME.glob("**/*.bak")) + \
                   list(VECTORBRAIN_HOME.glob("**/*.backup")) + \
                   list(VECTORBRAIN_HOME.glob("**/*.backup.*"))
    
    if not backup_files:
        print(f"  ✅ 没有备份文件需要清理")
        return 0
    
    print(f"  📦 发现 {len(backup_files)} 个备份文件需要归档")
    archived = archive_old_files(backup_files, "备份文件")
    return archived

def cleanup_old_reports():
    """清理旧报告文件"""
    print("\n📄 检查旧报告文件...")
    
    report_files = list(WORKSPACE.glob("memory/*_report_*.md"))
    
    if not report_files:
        print(f"  ✅ 没有旧报告需要清理")
        return 0
    
    # 检查文件年龄
    cutoff_time = datetime.now().timestamp() - (30 * 24 * 60 * 60)  # 30 天前
    old_files = [f for f in report_files if f.stat().st_mtime < cutoff_time]
    
    if old_files:
        print(f"  📦 发现 {len(old_files)} 个 30 天前的旧报告")
        archived = archive_old_files(old_files, "旧报告")
        return archived
    
    print(f"  ✅ 所有报告都在 30 天内，无需清理")
    return 0

def generate_cleanup_report(dashboard_count, backup_count, report_count):
    """生成清理报告"""
    total = dashboard_count + backup_count + report_count
    
    report = f"""# 文件归档清理报告

**执行时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 归档统计

| 类型 | 归档数量 |
|------|----------|
| Dashboard 旧版本 | {dashboard_count} 个 |
| 备份文件 | {backup_count} 个 |
| 旧报告文件 | {report_count} 个 |
| **总计** | **{total} 个** |

## 归档位置

所有归档文件已保存至：`~/.vectorbrain/archive/autoArchive_{datetime.now().strftime("%Y%m%d_%H%M%S")}/`

## 建议

- 定期（每月）清理归档目录
- 保留重要文件的备份
- 使用 Git 进行版本控制
"""
    
    return report, total

def save_report_to_vectorbrain(report, total_archived):
    """保存报告到 VectorBrain"""
    import sqlite3
    import json
    
    try:
        KNOWLEDGE_DB = VECTORBRAIN_HOME / "memory" / "knowledge_memory.db"
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "file_cleanup",
            f"cleanup_report_{datetime.now().strftime('%Y-%m-%d')}",
            report,
            "auto_archive_system",
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        print("\n✅ 清理报告已保存到 VectorBrain")
    except Exception as e:
        print(f"\n⚠️ 保存报告失败：{e}")

def run_auto_archive():
    """运行自动归档"""
    print("🔍 开始文件归档清理...\n")
    
    # 执行清理
    dashboard_archived = cleanup_dashboards()
    backup_archived = cleanup_backup_files()
    report_archived = cleanup_old_reports()
    
    # 生成报告
    report, total = generate_cleanup_report(dashboard_archived, backup_archived, report_archived)
    
    print("\n" + report)
    
    # 保存到 VectorBrain
    save_report_to_vectorbrain(report, total)
    
    if total > 0:
        print(f"\n✅ 归档完成！共归档 {total} 个文件")
    else:
        print(f"\n✅ 无需归档，文件系统整洁")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🔍 强制运行模式")
        run_auto_archive()
    else:
        run_auto_archive()
