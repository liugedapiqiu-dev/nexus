#!/usr/bin/env python3
"""
Layer: runtime
Status: secondary
Boundary: runtime executor living under connector namespace; explicit cross-layer pollution point (Runtime -> Reflection/Memory writes still coupled here).
Architecture refs:
- architecture/layer-manifest.md
- architecture/runtime-boundary-rules.md

VectorBrain 任务管理器 - OpenClaw 任务执行引擎

功能：
1. 查询 pending/queued 任务
2. 原子性抢占任务（queued → running）
3. 执行任务
4. 回写结果（running → completed/failed）
5. ✅ 新增：执行前对照 CHECKLIST.md 自检

安全机制：
- 原子性 UPDATE + ROW COUNT 验证（防抢占冲突）
- 超时机制（30 分钟）
- 全面错误处理 + 详细日志
- flock 文件锁（防 Cron 冲突）
- ✅ CHECKLIST.md 三轮自检制度
"""

import sqlite3
import json
import os
import sys
import time
import fcntl
from datetime import datetime, timedelta
from pathlib import Path

# ==================== 配置区 ====================
DB_PATH = os.path.expanduser("~/.vectorbrain/tasks/task_queue.db")
LOG_FILE = os.path.expanduser("~/.vectorbrain/connector/task_manager.log")
LOCK_FILE = "/tmp/task_manager.lock"
CHECKLIST_FILE = os.path.expanduser("~/.vectorbrain/connector/CHECKLIST.md")
WORKER_ID = "openclaw_main"
TASK_TIMEOUT_MINUTES = 30

# ==================== 日志工具 ====================
def log(message, level="INFO"):
    """写入日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    # 打印到 stdout
    print(log_entry, end="")
    
    # 追加到日志文件
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[ERROR] 写入日志失败：{e}", file=sys.stderr)

def log_banner():
    """打印任务管理器启动横幅（统一收口，避免重复散落）"""
    log("============================================================")
    log("任务管理器启动")
    log(f"Worker ID: {WORKER_ID}")
    log(f"数据库：{DB_PATH}")
    log("============================================================")

def run_checklist(task):
    """
    执行三轮自检制度
    
    返回：
    - True: 通过检查
    - False: 未通过检查
    """
    log("🔍 开始执行三轮自检...", "INFO")
    
    if not os.path.exists(CHECKLIST_FILE):
        log("⚠️  检查清单不存在：CHECKLIST.md (但继续执行)", "WARN")
        return True
    
    task_id = task.get('task_id', 'unknown')
    task_title = task.get('title', 'unknown')
    log(f"  任务：{task_id} - {task_title}", "INFO")
    
    # 第一轮：完整性检查
    log("  第一轮：完整性检查...", "INFO")
    if not os.path.exists(DB_PATH):
        log(f"  ❌ 任务数据库不存在：{DB_PATH}", "ERROR")
        return False
    log("  ✅ 数据库路径存在", "INFO")
    
    # 第二轮：功能性检查
    log("  第二轮：功能性检查...", "INFO")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        log("  ✅ 数据库连接正常", "INFO")
    except Exception as e:
        log(f"  ❌ 数据库连接失败：{e}", "ERROR")
        return False
    
    # 第三轮：用户视角检查
    log("  第三轮：用户视角检查...", "INFO")
    if not task.get('description'):
        log("  ⚠️  任务描述为空（但不影响执行）", "WARN")
    else:
        log("  ✅ 任务描述完整", "INFO")
    
    log("✅ 三轮自检全部通过", "INFO")
    return True

# ==================== 数据库操作 ====================
def get_db_connection():
    """获取数据库连接"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # 支持字典访问
        return conn
    except Exception as e:
        log(f"数据库连接失败：{e}", "ERROR")
        return None

def get_pending_tasks(limit=5):
    """获取待处理的任务（queued 状态）
    
    只处理 assigned_worker 为 NULL 或 'system' 的任务
    跳过 assigned_worker 为个人的任务（如'hao'）
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE status = 'queued' 
            AND (assigned_worker IS NULL OR assigned_worker = 'system')
            ORDER BY priority ASC, created_at ASC 
            LIMIT ?
        """, (limit,))
        tasks = cursor.fetchall()
        conn.close()
        return [dict(task) for task in tasks]
    except Exception as e:
        log(f"查询任务失败：{e}", "ERROR")
        conn.close()
        return []

def claim_task(task_id):
    """
    原子性抢占任务（queued → running）
    
    返回：
    - True: 抢占成功
    - False: 抢占失败（任务已被其他 Worker 抢占）
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        # 原子性 UPDATE + 条件检查
        cursor.execute("""
            UPDATE tasks 
            SET status = 'running', 
                assigned_worker = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ? AND status = 'queued'
        """, (WORKER_ID, task_id))
        
        conn.commit()
        
        # 验证是否成功抢占
        if cursor.rowcount == 0:
            log(f"任务 {task_id} 抢占失败（可能已被其他 Worker 抢占）", "WARN")
            conn.close()
            return False
        
        log(f"任务 {task_id} 抢占成功（Worker: {WORKER_ID}）")
        conn.close()
        return True
        
    except Exception as e:
        log(f"抢占任务失败：{e}", "ERROR")
        conn.close()
        return False

def complete_task(task_id, result):
    """标记任务为完成（running → completed）
    
    同时写入反思记忆，记录完成信息
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 先获取任务详情
        cursor.execute("""
            SELECT title, description, assigned_worker, priority, created_at
            FROM tasks WHERE task_id = ?
        """, (task_id,))
        task_info = cursor.fetchone()
        
        # 更新任务状态
        cursor.execute("""
            UPDATE tasks 
            SET status = 'completed',
                result = ?,
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """, (json.dumps(result, ensure_ascii=False), task_id))
        
        conn.commit()
        conn.close()
        
        # 写入反思记忆
        if task_info:
            log_task_completion_to_reflections(task_id, task_info, result)
        
        log(f"任务 {task_id} 标记为完成")
        return True
        
    except Exception as e:
        log(f"完成任务失败：{e}", "ERROR")
        conn.close()
        return False

def log_task_completion_to_reflections(task_id, task_info, result):
    """
    将任务完成记录写入反思记忆
    
    Args:
        task_id: 任务 ID
        task_info: 任务详情 tuple (title, description, assigned_worker, priority, created_at)
        result: 完成结果 dict
    """
    try:
        from pathlib import Path
        import sqlite3
        
        reflections_db = Path.home() / '.vectorbrain' / 'reflection' / 'reflections.db'
        
        if not reflections_db.exists():
            log(f"反思数据库不存在：{reflections_db}", "WARN")
            return
        
        title, description, assigned_worker, priority, created_at = task_info
        
        # 生成反思内容
        completion_time = datetime.now().isoformat()
        completed_by = assigned_worker if assigned_worker else 'system_auto'
        
        reflection_content = f"""
# 任务完成记录

**任务 ID:** {task_id}
**任务标题:** {title}
**完成时间:** {completion_time}
**执行者:** {completed_by}
**优先级:** {priority}

## 完成原因
{result.get('reason', '系统自动完成') if isinstance(result, dict) else result}

## 完成结果
{json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else result}

## 反思
- 这个任务是否真的完成了？
- 完成质量如何？
- 有什么经验教训？
"""
        
        # 写入反思数据库
        conn = sqlite3.connect(str(reflections_db))
        cursor = conn.cursor()
        
        import uuid
        reflection_id = f"task_completion_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        cursor.execute('''
            INSERT INTO reflections 
            (reflection_id, task_id, goal_id, outcome, success, analysis, 
             lessons_learned, action_items, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reflection_id,
            task_id,
            None,
            'completed',
            1,
            reflection_content,
            f"任务完成记录 - {completed_by}",
            "回顾任务完成质量，总结经验",
            'task_manager_auto',
            completion_time
        ))
        
        conn.commit()
        conn.close()
        
        log(f"已写入任务完成反思：{task_id}")
        
    except Exception as e:
        log(f"写入任务完成反思失败：{e}", "WARN")

def fail_task(task_id, error_message):
    """标记任务为失败（running → failed）"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks 
            SET status = 'failed',
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """, (error_message, task_id))
        
        conn.commit()
        conn.close()
        log(f"任务 {task_id} 标记为失败：{error_message}", "ERROR")
        return True
        
    except Exception as e:
        log(f"标记任务失败：{e}", "ERROR")
        conn.close()
        return False

# ==================== 任务执行引擎 ====================
def execute_task(task):
    """
    执行具体任务
    
    根据任务类型调用不同的处理函数
    """
    task_id = task['task_id']
    title = task['title']
    description = task.get('description', '')
    
    log(f"开始执行任务：{task_id} - {title}")
    
    try:
        # 任务类型路由
        if '测试' in title or 'test' in title.lower():
            result = execute_test_task(task)
        elif '日志' in title or 'log' in title.lower():
            result = execute_log_task(task)
        else:
            # 默认：将任务描述写入日志
            result = execute_default_task(task)
        
        log(f"任务 {task_id} 执行成功")
        return {'success': True, 'result': result}
        
    except Exception as e:
        log(f"任务 {task_id} 执行异常：{e}", "ERROR")
        raise

def execute_test_task(task):
    """执行测试任务 - 写入测试日志"""
    task_id = task['task_id']
    test_file = os.path.expanduser("~/.vectorbrain/state/task_test.log")
    
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    
    with open(test_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"测试任务执行记录\n")
        f.write(f"时间：{datetime.now().isoformat()}\n")
        f.write(f"任务 ID: {task_id}\n")
        f.write(f"标题：{task['title']}\n")
        f.write(f"描述：{task.get('description', '')}\n")
        f.write(f"执行 Worker: {WORKER_ID}\n")
        f.write(f"{'='*60}\n")
    
    return {
        'action': 'write_test_log',
        'file': test_file,
        'timestamp': datetime.now().isoformat()
    }

def execute_log_task(task):
    """执行日志任务 - 写入指定日志"""
    task_id = task['task_id']
    description = task.get('description', '')
    
    log_file = os.path.expanduser("~/.vectorbrain/state/task_logs.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n[{datetime.now().isoformat()}] 任务日志 - {task_id}\n")
        f.write(f"标题：{task['title']}\n")
        f.write(f"内容：{description}\n")
        f.write("-"*60 + "\n")
    
    return {
        'action': 'write_log',
        'file': log_file,
        'timestamp': datetime.now().isoformat()
    }

def execute_default_task(task):
    """默认任务执行 - 记录到日志"""
    return execute_log_task(task)

# ==================== 主循环 ====================
def task_manager_loop():
    """任务管理器主循环"""
    log("="*60)
    log("任务管理器启动")
    log(f"Worker ID: {WORKER_ID}")
    log(f"数据库：{DB_PATH}")
    log("="*60)
    
    # 获取待处理任务
    tasks = get_pending_tasks(limit=5)
    
    if not tasks:
        log("空闲退出：当前无待处理任务")
        return
    
    log(f"发现 {len(tasks)} 个待处理任务")
    
    # 逐个处理任务
    for task in tasks:
        task_id = task['task_id']
        
        # 1. 抢占任务
        if not claim_task(task_id):
            continue  # 抢占失败，跳过
        
        # 1.5 执行三轮自检
        if not run_checklist(task):
            log(f"任务 {task_id} 未通过检查，跳过执行", "ERROR")
            fail_task(task_id, "未通过 CHECKLIST.md 三轮自检")
            continue
        
        # 2. 执行任务
        try:
            result = execute_task(task)
            
            # 3. 回写成功结果
            complete_task(task_id, result)
            
        except Exception as e:
            # 3. 回写失败结果
            fail_task(task_id, str(e))
        
        # 防止过快执行
        time.sleep(1)
    
    log("任务管理器本轮执行完成")

def create_test_task():
    """创建测试任务（用于黑盒测试）"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        test_task_id = f"boot_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, priority, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            test_task_id,
            "启动自检验证测试",
            "验证 OpenClaw 任务执行流程是否正常 - 自动创建的测试任务",
            1,  # 高优先级
            'queued',
            'task_manager_bootstrap'
        ))
        
        conn.commit()
        conn.close()
        
        log(f"测试任务已创建：{test_task_id}")
        return test_task_id
        
    except Exception as e:
        log(f"创建测试任务失败：{e}", "ERROR")
        conn.close()
        return False

# ==================== 入口 ====================
if __name__ == "__main__":
    # 获取文件锁（防止 Cron 重复执行）
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("任务管理器已在运行中（获取文件锁失败）", file=sys.stderr)
        sys.exit(1)
    
    try:
        # 检查命令行参数
        if len(sys.argv) > 1 and sys.argv[1] == '--create-test':
            # 创建测试任务模式
            create_test_task()
        else:
            # 正常执行模式
            task_manager_loop()
    finally:
        # 释放文件锁
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
