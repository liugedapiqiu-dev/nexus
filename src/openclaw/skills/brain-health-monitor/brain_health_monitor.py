#!/usr/bin/env python3
"""
大脑健康度自动监控系统
每天随机时间点或长时间无消息时自动运行，检查大脑健康状态并保存到 VectorBrain
"""

import os
import json
import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
WORKSPACE = Path.home() / ".openclaw" / "workspace"
REPORT_PATH = WORKSPACE / "memory" / "brain_health_report.md"

# VectorBrain 数据库路径
EPISODIC_DB = VECTORBRAIN_HOME / "memory" / "episodic_memory.db"
KNOWLEDGE_DB = VECTORBRAIN_HOME / "memory" / "knowledge_memory.db"

def get_last_message_time():
    """获取最后收到消息的时间"""
    sessions_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
    if not sessions_dir.exists():
        return datetime.now()
    
    latest_session = max(sessions_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, default=None)
    if latest_session:
        return datetime.fromtimestamp(latest_session.stat().st_mtime)
    return datetime.now()

def get_last_check_time():
    """从 VectorBrain 知识记忆获取上次检查时间"""
    try:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT updated_at FROM knowledge 
            WHERE category='brain_health' AND key='last_check'
            ORDER BY updated_at DESC LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return datetime.fromisoformat(result[0])
    except:
        pass
    
    return datetime.fromisoformat("2024-01-01")

def should_run_check():
    """判断是否应该运行健康检查"""
    last_check = get_last_check_time()
    
    if datetime.now() - last_check < timedelta(hours=12):
        return False, "距离上次检查不足 12 小时"
    
    last_msg_time = get_last_message_time()
    idle_hours = (datetime.now() - last_msg_time).total_seconds() / 3600
    
    if idle_hours > 2:
        return True, f"已空闲 {idle_hours:.1f} 小时"
    
    if idle_hours > 0.5 and random.random() < 0.2:
        return True, f"随机检查（空闲 {idle_hours:.1f} 小时）"
    
    return False, f"活跃中（最后消息：{idle_hours:.1f} 小时前）"

def check_databases():
    """检查数据库完整性"""
    issues = []
    databases = {
        "episodic_memory": VECTORBRAIN_HOME / "memory" / "episodic_memory.db",
        "knowledge_memory": VECTORBRAIN_HOME / "memory" / "knowledge_memory.db",
        "reflections": VECTORBRAIN_HOME / "reflection" / "reflections.db",
        "tasks": VECTORBRAIN_HOME / "tasks" / "task_queue.db",
        "goals": VECTORBRAIN_HOME / "goals" / "goals.db"
    }
    
    for name, db_path in databases.items():
        if not db_path.exists():
            issues.append(f"❌ {name}: 数据库文件缺失")
            continue
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            
            if table_count == 0:
                issues.append(f"⚠️ {name}: 数据库为空")
        except Exception as e:
            issues.append(f"❌ {name}: 数据库损坏 - {str(e)}")
    
    return issues

def check_skills():
    """检查技能配置完整性"""
    skills_dir = Path.home() / ".openclaw" / "skills"
    complete = 0
    incomplete = []
    
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir() or "disabled" in skill_dir.name.lower():
            continue
        
        has_json = (skill_dir / "skill.json").exists()
        has_skillmd = (skill_dir / "SKILL.md").exists()
        
        if has_json and has_skillmd:
            complete += 1
        else:
            incomplete.append(skill_dir.name)
    
    total = complete + len(incomplete)
    rate = (complete / total * 100) if total > 0 else 0
    return rate, incomplete

def check_memory_extraction():
    """检查记忆提炼效率"""
    try:
        conn = sqlite3.connect(EPISODIC_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM episodes WHERE date(timestamp) = date('now')")
        today_episodes = cursor.fetchone()[0]
        conn.close()
        
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM knowledge WHERE date(updated_at) = date('now')")
        today_knowledge = cursor.fetchone()[0]
        conn.close()
        
        valuable_episodes = max(1, int(today_episodes * 0.1))
        extraction_rate = (today_knowledge / valuable_episodes * 100)
        
        return {"today_episodes": today_episodes, "today_knowledge": today_knowledge, "extraction_rate": extraction_rate}
    except:
        return {"today_episodes": 0, "today_knowledge": 0, "extraction_rate": 0}

def check_file_cleanup():
    """检查是否需要清理"""
    issues = []
    backup_files = list(VECTORBRAIN_HOME.glob("**/*.bak")) + list(VECTORBRAIN_HOME.glob("**/*.backup*"))
    
    if len(backup_files) > 3:
        issues.append(f"⚠️ 发现 {len(backup_files)} 个备份文件，建议清理")
    
    dashboard_files = list(VECTORBRAIN_HOME.glob("dashboard*.py"))
    if len(dashboard_files) > 3:
        issues.append(f"⚠️ 发现 {len(dashboard_files)} 个 Dashboard 版本，建议整理")
    
    return issues

def calculate_health_score(db_issues, skill_rate, file_issues):
    """计算健康度分数"""
    score = 100
    score -= len(db_issues) * 10
    if skill_rate < 90:
        score -= (90 - skill_rate) * 0.5
    score -= len(file_issues) * 5
    return max(0, min(100, score))

def generate_report(db_issues, skill_rate, skill_incomplete, memory_stats, file_issues):
    """生成健康报告"""
    health_score = calculate_health_score(db_issues, skill_rate, file_issues)
    
    if health_score >= 95:
        status = "🟢 优秀"
    elif health_score >= 85:
        status = "🟡 良好"
    elif health_score >= 70:
        status = "🟠 需关注"
    else:
        status = "🔴 需立即处理"
    
    report = f"""# 🧠 大脑健康度检查报告

**检查时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**健康度:** {health_score}/100 {status}

---

## 📊 核心指标

| 指标 | 状态 | 详情 |
|------|------|------|
| 数据库完整性 | {"✅" if not db_issues else "⚠️"} | {"正常" if not db_issues else f"{len(db_issues)} 个问题"} |
| 技能配置率 | {"✅" if skill_rate >= 90 else "⚠️"} | {skill_rate:.1f}% |
| 今日记忆提炼 | ✅ | {memory_stats["today_knowledge"]} 条知识 / {memory_stats["today_episodes"]} 条情景 |
| 文件整洁度 | {"✅" if not file_issues else "⚠️"} | {"正常" if not file_issues else f"{len(file_issues)} 个问题"} |

---

## 🔍 详细检查

### 数据库状态
{chr(10).join(db_issues) if db_issues else "✅ 所有数据库正常"}

### 技能配置
**完整率:** {skill_rate:.1f}%
{"✅ 所有技能配置完整" if not skill_incomplete else "⚠️ 配置不完整的技能：" + chr(10) + chr(10).join([f"- {skill}" for skill in skill_incomplete])}

### 记忆提炼
- 今日情景记忆：{memory_stats["today_episodes"]} 条
- 今日知识记忆：{memory_stats["today_knowledge"]} 条
- 提炼效率：{memory_stats["extraction_rate"]:.1f}%

### 文件整洁度
{chr(10).join(file_issues) if file_issues else "✅ 文件系统整洁"}

---

## 🔧 建议操作
"""
    
    if db_issues or skill_incomplete or file_issues:
        report += """
### 自动修复命令
```bash
python3 ~/.openclaw/skills/auto_skill_checker.py --auto-fix
find ~/.vectorbrain/ -name "*.bak" -o -name "*.backup*" -delete
```
"""
    else:
        report += """
**所有系统正常！无需操作！** ✅

继续保持良好习惯：
- 定期回顾知识记忆
- 及时记录重要经验
- 保持技能配置完整
"""
    
    return report, health_score

def save_to_vectorbrain(report, health_score, db_issues, skill_rate, memory_stats, file_issues):
    """将健康检查结果保存到 VectorBrain 向量数据库"""
    timestamp = datetime.now().isoformat()
    
    # 1. 保存到情景记忆（事件记录）
    try:
        conn = sqlite3.connect(EPISODIC_DB)
        cursor = conn.cursor()
        
        event_content = f"""大脑健康度检查报告 - {timestamp}
健康度评分：{health_score}/100
健康等级：{"优秀" if health_score >= 95 else "良好" if health_score >= 85 else "需关注" if health_score >= 70 else "需立即处理"}
核心指标：
- 数据库完整性：{"正常" if not db_issues else f"{len(db_issues)} 个问题"}
- 技能配置率：{skill_rate:.1f}%
- 今日记忆提炼：{memory_stats['today_knowledge']} 条知识 / {memory_stats['today_episodes']} 条情景
- 文件整洁度：{"正常" if not file_issues else f"{len(file_issues)} 个问题"}
详细报告：
{report}
"""
        
        cursor.execute("""
            INSERT INTO episodes (timestamp, worker_id, event_type, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            "brain_health_monitor",
            "health_check",
            event_content,
            json.dumps({
                "health_score": health_score,
                "skill_rate": skill_rate,
                "today_knowledge": memory_stats['today_knowledge'],
                "today_episodes": memory_stats['today_episodes'],
                "db_issues_count": len(db_issues),
                "file_issues_count": len(file_issues)
            })
        ))
        
        conn.commit()
        conn.close()
        print("✅ 已保存健康检查记录到情景记忆 (episodic_memory.db)")
    except Exception as e:
        print(f"⚠️ 保存情景记忆失败：{e}")
    
    # 2. 保存到知识记忆（可检索的知识）
    try:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        
        knowledge_value = f"""# 大脑健康度检查记录

**检查时间:** {timestamp}
**健康度:** {health_score}/100
**等级:** {"🟢 优秀" if health_score >= 95 else "🟡 良好" if health_score >= 85 else "🟠 需关注" if health_score >= 70 else "🔴 需立即处理"}

## 核心指标
| 指标 | 状态 | 数值 |
|------|------|------|
| 数据库完整性 | {"✅" if not db_issues else "⚠️"} | {len(db_issues)} 个问题 |
| 技能配置率 | {"✅" if skill_rate >= 90 else "⚠️"} | {skill_rate:.1f}% |
| 记忆提炼效率 | ✅ | {memory_stats['today_knowledge']}/{memory_stats['today_episodes']} |
| 文件整洁度 | {"✅" if not file_issues else "⚠️"} | {len(file_issues)} 个问题 |

## 问题详情
{"### 数据库问题\n" + chr(10).join(db_issues) if db_issues else "### 数据库问题\n✅ 无"}
{"### 文件整洁度问题\n" + chr(10).join(file_issues) if file_issues else "### 文件整洁度问题\n✅ 无"}

## 建议操作
{"- 修复技能配置\n- 清理备份文件" if db_issues or file_issues else "✅ 所有系统正常，无需操作"}
"""
        
        # 插入最新检查记录
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "brain_health",
            "latest_check",
            knowledge_value,
            "brain_health_monitor",
            timestamp,
            timestamp
        ))
        
        # 保存历史趋势数据
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "brain_health",
            f"check_{timestamp[:10]}",
            json.dumps({
                "timestamp": timestamp,
                "health_score": health_score,
                "skill_rate": skill_rate,
                "db_issues": len(db_issues),
                "file_issues": len(file_issues)
            }),
            "brain_health_monitor",
            timestamp,
            timestamp
        ))
        
        conn.commit()
        conn.close()
        print("✅ 已保存健康检查记录到知识记忆 (knowledge_memory.db)")
    except Exception as e:
        print(f"⚠️ 保存知识记忆失败：{e}")

def save_state():
    """保存检查状态到 VectorBrain"""
    timestamp = datetime.now().isoformat()
    
    try:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        cursor = conn.cursor()
        
        # 获取检查次数
        cursor.execute("SELECT value FROM knowledge WHERE category='brain_health' AND key='check_count'")
        result = cursor.fetchone()
        check_count = int(json.loads(result[0]).get("count", 0)) + 1 if result else 1
        
        # 更新检查次数
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "brain_health",
            "check_count",
            json.dumps({"count": check_count, "last_check": timestamp}),
            "brain_health_monitor",
            timestamp,
            timestamp
        ))
        
        # 更新上次检查时间
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (category, key, value, source_worker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "brain_health",
            "last_check",
            timestamp,
            "brain_health_monitor",
            timestamp,
            timestamp
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ 保存状态失败：{e}")

def send_report(report, health_score, db_issues, skill_rate, memory_stats, file_issues):
    """发送报告并保存到 VectorBrain"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report)
    
    save_to_vectorbrain(report, health_score, db_issues, skill_rate, memory_stats, file_issues)
    
    print(report)
    print(f"\n📄 完整报告已保存至：{REPORT_PATH}")
    print("💾 健康数据已存储到 VectorBrain（支持向量检索）")
    
    if health_score < 85:
        print("\n⚠️ 健康度低于 85，建议立即处理！")

if __name__ == "__main__":
    import sys
    
    should_run, reason = should_run_check()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🔍 强制运行模式")
    elif not should_run:
        print(f"⏭️ 跳过检查：{reason}")
        sys.exit(0)
    else:
        print(f"🔍 触发检查：{reason}")
    
    print("\n开始大脑健康检查...\n")
    
    db_issues = check_databases()
    skill_rate, skill_incomplete = check_skills()
    memory_stats = check_memory_extraction()
    file_issues = check_file_cleanup()
    
    report, health_score = generate_report(db_issues, skill_rate, skill_incomplete, memory_stats, file_issues)
    
    send_report(report, health_score, db_issues, skill_rate, memory_stats, file_issues)
    save_state()
    
    print(f"\n✅ 检查完成！健康度：{health_score}/100")
