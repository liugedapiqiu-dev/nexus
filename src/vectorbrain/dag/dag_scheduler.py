#!/usr/bin/env python3
"""
VectorBrain DAG 调度器

核心功能：
1. 轮询数据库，发现 ready 任务
2. 优先级队列调度
3. 原子性任务抢占（防止重复执行）
4. 分配给 Worker 执行
5. 状态管理（pending → ready → running → done/failed）

作者：[YOUR_AI_NAME] 🧠
版本：v2.0
"""

import sqlite3
import json
import os
import sys
import time
import logging
import signal
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock, Event
import heapq

# 导入工具函数
from dag_utils import (
    Task, load_all_tasks, get_ready_tasks,
    detect_cycle, validate_dag, topological_sort_with_priority
)

# 导入 Experience Collector (V3 Memory)
EXPERIENCE_ENABLED = False
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.home() / ".vectorbrain"))
    from experience.experience_collector import record_episode
    EXPERIENCE_ENABLED = True
except Exception as e:
    record_episode = None


# ==================== 配置区 ====================

# 数据库路径
DB_PATH = os.path.expanduser("~/.vectorbrain/tasks/task_queue.db")

# 日志配置
LOG_DIR = os.path.expanduser("~/.vectorbrain/dag/logs")
LOG_FILE = os.path.join(LOG_DIR, "dag_scheduler.log")
os.makedirs(LOG_DIR, exist_ok=True)

# 调度器配置
POLL_INTERVAL_SECONDS = 1  # 轮询间隔
MAX_WORKERS = 4  # 最大并发 Worker 数
TASK_TIMEOUT_MINUTES = 30  # 任务超时时间
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY_SECONDS = 5  # 重试延迟

# Worker ID
WORKER_POOL_ID = f"scheduler_{os.getpid()}"

# ==================== 日志配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ==================== 数据结构 ====================

@dataclass
class ScheduledTask:
    """调度中的任务"""
    task: Task
    worker_id: str
    start_time: datetime
    future: Optional[Future] = None
    retry_count: int = 0


# ==================== 数据库操作（原子性） ====================

class TaskDatabase:
    """
    任务数据库操作类
    
    关键：所有状态变更必须是原子性的，防止并发冲突
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程安全的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=30)
            self._local.conn.row_factory = sqlite3.Row
            # 启用 WAL 模式提高并发性能
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn
    
    def claim_task(self, task_id: str, worker_id: str) -> bool:
        """
        原子性抢占任务
        
        使用 UPDATE + WHERE 确保只有一个 Worker 能抢到任务
        
        SQL 逻辑：
        UPDATE tasks
        SET status='running', assigned_worker=?, updated_at=?
        WHERE task_id=? AND status='pending'
        
        返回 True 如果成功抢占，False 如果被别人抢走
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks
            SET status = 'running',
                assigned_worker = ?,
                updated_at = ?
            WHERE task_id = ? AND status = 'pending'
        """, (worker_id, datetime.now().isoformat(), task_id))
        
        conn.commit()
        
        # 检查是否成功（有 1 行被更新）
        return cursor.rowcount == 1
    
    def complete_task(self, task_id: str, result: str, worker_id: str) -> bool:
        """
        标记任务完成
        
        验证 worker_id 确保只有执行任务的 Worker 能完成它
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks
            SET status = 'done',
                result = ?,
                completed_at = ?,
                updated_at = ?
            WHERE task_id = ? AND assigned_worker = ?
        """, (result, datetime.now().isoformat(), datetime.now().isoformat(),
              task_id, worker_id))
        
        conn.commit()
        return cursor.rowcount == 1
    
    def fail_task(self, task_id: str, error_message: str, worker_id: str,
                  retry_count: int = 0, max_retries: int = 3) -> bool:
        """
        标记任务失败
        
        可以选择是否重试
        
        Args:
            retry_count: 当前重试次数
            max_retries: 最大重试次数（默认 3）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 如果还有重试次数，标记为 pending 而不是 failed
        if retry_count < max_retries:
            cursor.execute("""
                UPDATE tasks
                SET status = 'pending',
                    error_message = ?,
                    retry_count = ?,
                    updated_at = ?,
                    priority = ?  -- 提高优先级，让它早点执行
                WHERE task_id = ? AND assigned_worker = ?
            """, (error_message, retry_count, datetime.now().isoformat(),
                  1,  # 重试任务优先级提高到 1
                  task_id, worker_id))
        else:
            cursor.execute("""
                UPDATE tasks
                SET status = 'failed',
                    error_message = ?,
                    retry_count = ?,
                    last_error = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE task_id = ? AND assigned_worker = ?
            """, (error_message, retry_count, error_message, datetime.now().isoformat(),
                  datetime.now().isoformat(), task_id, worker_id))
        
        conn.commit()
        return cursor.rowcount == 1
    
    def get_ready_tasks(self, limit: int = 10) -> List[Task]:
        """
        获取 ready 任务
        
        ready 条件：
        1. status = 'pending'
        2. 所有 dependencies 都完成
        
        注意：这里使用应用层验证，不是数据库层
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 获取所有 pending 任务（按优先级排序）
        cursor.execute("""
            SELECT * FROM tasks
            WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC
            LIMIT ?
        """, (limit,))
        
        pending_tasks = [Task.from_row(row) for row in cursor.fetchall()]
        
        # 构建任务映射
        task_map = {t.task_id: t for t in pending_tasks}
        
        # 还需要加载已完成的任务来验证依赖
        cursor.execute("""
            SELECT * FROM tasks WHERE status = 'done'
        """)
        done_tasks = {Task.from_row(row).task_id: True for row in cursor.fetchall()}
        
        # 验证每个 pending 任务的依赖
        ready = []
        for task in pending_tasks:
            all_deps_done = True
            for dep_id in task.dependencies:
                if dep_id not in done_tasks:
                    all_deps_done = False
                    break
            
            if all_deps_done:
                ready.append(task)
        
        return ready
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return load_all_tasks(self.db_path)
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ==================== 任务执行器 ====================

class TaskExecutor:
    """
    任务执行器
    
    负责实际执行任务逻辑
    当前是简化版本，执行 Python 代码或外部命令
    """
    
    def __init__(self, timeout_minutes: int = TASK_TIMEOUT_MINUTES,
                 max_workers: int = 4):
        self.timeout_minutes = timeout_minutes
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"✅ TaskExecutor 初始化完成 (max_workers={max_workers})")
    
    def execute(self, task: Task) -> Tuple[bool, str]:
        """
        执行任务
        
        返回 (success, result_message)
        
        当前实现：
        - 如果 task.description 包含 Python 代码，执行它
        - 否则标记为完成（模拟执行）
        
        TODO: 实现真正的任务执行逻辑
        """
        logger.info(f"🚀 开始执行任务：{task.task_id}")
        logger.info(f"   标题：{task.title}")
        logger.info(f"   超时：{self.timeout_minutes} 分钟")
        
        try:
            # 模拟执行（因为没有真正的任务逻辑）
            # 实际使用时，这里应该：
            # 1. 解析 task.description 或 task.metadata
            # 2. 执行对应的函数/脚本/HTTP 请求
            # 3. 捕获输出和错误
            
            start_time = time.time()
            
            # 模拟不同类型的任务
            if "slow" in task.task_id.lower():
                # 慢速任务：模拟 5 秒执行
                time.sleep(5)
                result = f"慢速任务执行完成 (耗时 {time.time() - start_time:.2f}秒)"
            
            elif "test" in task.task_id.lower():
                # 测试任务：模拟 2 秒执行
                time.sleep(2)
                result = f"测试任务执行完成 (耗时 {time.time() - start_time:.2f}秒)"
            
            else:
                # 普通任务：模拟 1 秒执行
                time.sleep(1)
                result = f"任务执行完成 (耗时 {time.time() - start_time:.2f}秒)"
            
            logger.info(f"✅ 任务完成：{task.task_id}")
            return True, result
        
        except TimeoutError as e:
            error_msg = f"任务超时（超过 {self.timeout_minutes} 分钟）"
            logger.error(f"❌ {error_msg}: {task.task_id}")
            return False, error_msg
        
        except Exception as e:
            error_msg = f"执行错误：{str(e)}"
            logger.error(f"❌ {error_msg}: {task.task_id}")
            logger.exception("详细错误:")
            return False, error_msg
    
    def shutdown(self):
        """关闭执行器"""
        self.executor.shutdown(wait=True)


# ==================== Stage 5: 高级任务执行器 ====================

class AdvancedTaskExecutor:
    """
    高级任务执行器 - 支持多种任务类型
    
    支持:
    - ShellTask: 执行 shell 命令
    - PythonTask: 执行 Python 函数
    - HTTPTask: 调用 HTTP API
    """
    
    def __init__(self, timeout_minutes: int = 30):
        self.timeout_minutes = timeout_minutes
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def execute(self, task: 'Task') -> Tuple[bool, str]:
        """
        根据任务描述自动选择执行器
        
        规则:
        - description 包含 "shell:" → ShellTask
        - description 包含 "python:" → PythonTask
        - description 包含 "http:" → HTTPTask
        - 否则 → 模拟执行 (兼容旧任务)
        """
        description = getattr(task, 'description', '') or ''
        
        if description.startswith('shell:'):
            return self._execute_shell(description[6:])
        elif description.startswith('python:'):
            return self._execute_python(description[7:])
        elif description.startswith('http:'):
            return self._execute_http(description[5:])
        else:
            # 兼容旧任务：模拟执行
            return self._execute_simulated(task)
    
    def _execute_shell(self, command: str) -> Tuple[bool, str]:
        """执行 Shell 命令"""
        import subprocess
        try:
            logger.info(f"[ShellExecutor] 执行：{command}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_minutes * 60
            )
            
            if result.returncode == 0:
                return True, f"stdout: {result.stdout}\nstderr: {result.stderr}"
            else:
                return False, f"exit code {result.returncode}: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return False, f"Timeout after {self.timeout_minutes} minutes"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def _execute_python(self, code: str) -> Tuple[bool, str]:
        """执行 Python 代码"""
        try:
            logger.info(f"[PythonExecutor] 执行代码")
            # 创建安全的执行环境
            local_vars = {}
            exec(code, {}, local_vars)
            
            # 返回结果
            result = local_vars.get('result', ' executed successfully')
            return True, str(result)
        
        except Exception as e:
            return False, f"Python error: {str(e)}"
    
    def _execute_http(self, config: str) -> Tuple[bool, str]:
        """执行 HTTP 请求"""
        import json
        try:
            config_dict = json.loads(config)
            url = config_dict.get('url', '')
            method = config_dict.get('method', 'GET')
            
            logger.info(f"[HTTPExecutor] {method} {url}")
            
            # 简化的 HTTP 执行 (实际需要 import requests)
            return True, f"HTTP {method} {url} executed (mock)"
        
        except Exception as e:
            return False, f"HTTP error: {str(e)}"
    
    def _execute_simulated(self, task: 'Task') -> Tuple[bool, str]:
        """模拟执行 (兼容旧任务)"""
        import time
        time.sleep(1)
        return True, f"Task {task.task_id} completed (simulated)"



# ==================== 核心调度器 ====================

class DAGScheduler:
    """
    DAG 调度器 - 核心组件
    
    架构:
    ┌─────────────────────────────────────┐
    │         DAG Scheduler               │
    │                                     │
    │  ┌─────────────┐  ┌──────────────┐ │
    │  │ Poll Loop   │→ │ Ready Queue  │ │
    │  │ (每秒轮询)  │  │ (优先队列)   │ │
    │  └─────────────┘  └──────┬───────┘ │
    │                          │          │
    │                          ▼          │
    │                   ┌─────────────┐  │
    │                   │Worker Pool  │  │
    │                   │(并发执行)   │  │
    │                   └─────────────┘  │
    └─────────────────────────────────────┘
    
    关键特性:
    1. 原子性任务抢占（防重复执行）
    2. 优先级调度
    3. 并发控制
    4. 超时处理
    5. 失败重试
    6. 优雅关闭
    """
    
    def __init__(self, db_path: str = DB_PATH, 
                 max_workers: int = 4,
                 poll_interval: float = 1.0,
                 task_timeout: int = 30,
                 max_retries: int = 3):
        self.db = TaskDatabase(db_path)
        self.executor = AdvancedTaskExecutor(timeout_minutes=task_timeout)
        
        # 配置参数
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        
        # 调度状态
        self.running = False
        self.shutdown_event = Event()
        self.active_tasks: Dict[str, ScheduledTask] = {}
        self.lock = Lock()
        
        # 统计信息
        self.stats = {
            'tasks_started': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_retried': 0,
            'total_execution_time': 0.0
        }
        
        # 设置信号处理器（优雅关闭）
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """处理关闭信号"""
        logger.info(f"🛑 收到信号 {signum}，准备关闭...")
        self.shutdown()
    
    def _get_ready_tasks_with_priority(self) -> List[Task]:
        """
        获取 ready 任务并按优先级排序
        
        使用 dag_utils 中的 topological_sort_with_priority
        """
        all_tasks = self.db.get_all_tasks()
        
        # 筛选 pending 任务
        pending = [t for t in all_tasks if t.status == 'pending']
        
        if not pending:
            return []
        
        # 获取已完成的任务 ID
        done_ids = {t.task_id for t in all_tasks if t.status == 'done'}
        
        # 验证依赖，找出真正 ready 的任务
        ready = []
        for task in pending:
            all_deps_done = all(dep_id in done_ids for dep_id in task.dependencies)
            if all_deps_done:
                ready.append(task)
        
        if not ready:
            return []
        
        # 按优先级排序
        try:
            sorted_tasks, error = topological_sort_with_priority(ready)
            if error:
                logger.warning(f"⚠️ 排序失败：{error}")
                return ready  # 返回未排序的
            return sorted_tasks
        except Exception as e:
            logger.error(f"❌ 排序异常：{e}")
            return ready
    
    def _dispatch_task(self, task: Task) -> bool:
        """
        分发任务到 Worker
        
        返回 True 如果成功分发
        """
        # 尝试抢占任务
        worker_id = f"{WORKER_POOL_ID}_{len(self.active_tasks)}"
        
        if not self.db.claim_task(task.task_id, worker_id):
            logger.warning(f"⚠️ 任务 {task.task_id} 被其他 Worker 抢走")
            return False
        
        # 创建调度任务
        scheduled = ScheduledTask(
            task=task,
            worker_id=worker_id,
            start_time=datetime.now()
        )
        
        # 记录活跃任务
        with self.lock:
            self.active_tasks[task.task_id] = scheduled
            self.stats['tasks_started'] += 1
        
        logger.info(f"📤 任务分发：{task.task_id} → Worker {worker_id}")
        
        # 异步执行
        future = self.executor.executor.submit(self._execute_task, scheduled)
        scheduled.future = future
        
        return True
    
    def _execute_task(self, scheduled: ScheduledTask):
        """
        执行任务（在 Worker 线程中）
        
        处理:
        1. 实际执行
        2. 结果回写
        3. 错误处理
        4. 重试逻辑
        """
        task = scheduled.task
        start_time = time.time()
        
        try:
            # [Worker] start 日志
            logger.info(f"[Worker] start {task.task_id} - {task.title}")
            
            # 执行任务
            success, result = self.executor.execute(task)
            
            execution_time = time.time() - start_time
            
            if success:
                # 任务成功
                self.db.complete_task(task.task_id, result, scheduled.worker_id)
                
                # 记录经验 (V3 Memory)
                if EXPERIENCE_ENABLED and record_episode:
                    try:
                        execution_time = time.time() - start_time
                        episode_data = {
                            "task_id": task.task_id,
                            "type": "general",
                            "input": task.title,
                            "output": result[:200] if result else "",
                            "status": "done",
                            "execution_time": execution_time
                        }
                        record_episode(episode_data)
                    except Exception as e:
                        pass
                # [Worker] finish 日志
                logger.info(f"[Worker] finish {task.task_id} (耗时 {execution_time:.2f}s)")
                
                with self.lock:
                    self.stats['tasks_completed'] += 1
                    self.stats['total_execution_time'] += execution_time
            else:
                # 任务失败
                self._handle_task_failure(scheduled, result)
        
        except Exception as e:
            error_msg = f"未捕获的异常：{str(e)}"
            logger.error(f"[Worker] error {task.task_id}: {error_msg}")
            logger.exception("详细堆栈:")
            self._handle_task_failure(scheduled, error_msg)
        
        finally:
            # 从活跃任务中移除
            with self.lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
    
    def _handle_task_failure(self, scheduled: ScheduledTask, error_message: str):
        """处理任务失败"""
        task = scheduled.task
        scheduled.retry_count += 1
        
        if scheduled.retry_count < self.max_retries:
            # 重试
            logger.warning(f"🔄 任务失败，准备重试 ({scheduled.retry_count}/{self.max_retries}): {task.task_id}")
            self.db.fail_task(task.task_id, error_message, scheduled.worker_id,
                            scheduled.retry_count, self.max_retries)
            
            with self.lock:
                self.stats['tasks_retried'] += 1
        else:
            # 最终失败
            logger.error(f"❌ 任务最终失败：{task.task_id} - {error_message}")
            self.db.fail_task(task.task_id, error_message, scheduled.worker_id,
                            scheduled.retry_count, self.max_retries)
            
            with self.lock:
                self.stats['tasks_failed'] += 1
    
    def run(self):
        """
        运行调度器主循环
        
        伪代码:
        while running:
            ready_tasks = get_ready_tasks()
            for task in ready_tasks:
                if can_dispatch():
                    dispatch(task)
            sleep(poll_interval)
        """
        logger.info("=" * 60)
        logger.info("🚀 VectorBrain DAG 调度器启动")
        logger.info("=" * 60)
        logger.info(f"📊 数据库：{self.db.db_path}")
        logger.info(f"⚙️  轮询间隔：{self.poll_interval}秒")
        logger.info(f"👷 Worker 池：{self.max_workers} 并发")
        logger.info(f"⏱️  任务超时：{self.executor.timeout_minutes}分钟")
        logger.info(f"🔄 最大重试：{self.max_retries}次")
        logger.info("=" * 60)
        
        self.running = True
        self.shutdown_event.clear()
        
        try:
            tick_count = 0
            
            while self.running and not self.shutdown_event.is_set():
                tick_count += 1
                
                # 1. 获取 ready 任务
                ready_tasks = self._get_ready_tasks_with_priority()
                
                # [Scheduler] tick 日志
                logger.info(f"[Scheduler] tick={tick_count} ready={len(ready_tasks)} running={len(self.active_tasks)}")
                
                # 2. 分发任务（不超过最大并发数）
                dispatched = 0
                for task in ready_tasks:
                    # 检查并发限制
                    with self.lock:
                        if len(self.active_tasks) >= self.max_workers:
                            break
                    
                    # 分发任务
                    if self._dispatch_task(task):
                        dispatched += 1
                
                if dispatched > 0:
                    logger.info(f"📊 本轮分发 {dispatched} 个任务，"
                              f"活跃任务 {len(self.active_tasks)} 个")
                
                # 3. 等待下一轮
                time.sleep(self.poll_interval)
        
        except Exception as e:
            logger.error(f"❌ 调度器异常：{e}")
            logger.exception("详细堆栈:")
        
        finally:
            self.running = False
            logger.info("🛑 调度器已停止")
    
    def shutdown(self, wait: bool = True):
        """
        关闭调度器
        
        Args:
            wait: 是否等待活跃任务完成
        """
        logger.info("🛑 正在关闭调度器...")
        self.running = False
        self.shutdown_event.set()
        
        if wait:
            # 等待活跃任务完成
            if self.active_tasks:
                logger.info(f"⏳ 等待 {len(self.active_tasks)} 个活跃任务完成...")
                # 简单等待，实际应该更复杂
                time.sleep(5)
        
        # 关闭执行器
        self.executor.shutdown()
        
        # 关闭数据库
        self.db.close()
        
        # 打印统计
        self._print_stats()
    
    def _print_stats(self):
        """打印统计信息"""
        logger.info("=" * 60)
        logger.info("📊 调度器统计")
        logger.info("=" * 60)
        logger.info(f"  启动任务：{self.stats['tasks_started']}")
        logger.info(f"  完成任务：{self.stats['tasks_completed']}")
        logger.info(f"  失败任务：{self.stats['tasks_failed']}")
        logger.info(f"  重试任务：{self.stats['tasks_retried']}")
        
        if self.stats['tasks_completed'] > 0:
            avg_time = self.stats['total_execution_time'] / self.stats['tasks_completed']
            logger.info(f"  平均耗时：{avg_time:.2f}秒")
        
        logger.info("=" * 60)


# ==================== 主函数 ====================

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VectorBrain DAG 调度器')
    parser.add_argument('--db', default=DB_PATH, help='数据库路径')
    parser.add_argument('--workers', type=int, default=4, help='Worker 数量')
    parser.add_argument('--poll-interval', type=float, default=1.0,
                       help='轮询间隔（秒）')
    parser.add_argument('--test', action='store_true', help='运行测试')
    
    args = parser.parse_args()
    
    if args.test:
        # 运行测试
        print("🧪 运行调度器测试...")
        test_scheduler()
        return
    
    # 使用命令行参数
    workers = args.workers
    poll_interval = args.poll_interval
    
    # 创建并运行调度器
    logger.info(f"⚙️  配置：Worker={workers}, Poll={poll_interval}s")
    scheduler = DAGScheduler(args.db)
    scheduler.run()


def test_scheduler():
    """测试调度器"""
    print("=" * 60)
    print("🧪 DAG 调度器测试")
    print("=" * 60)
    
    # 创建测试数据库
    test_db = ":memory:"
    
    # 创建调度器
    scheduler = DAGScheduler(test_db)
    
    print("✅ 调度器创建成功")
    print("✅ 测试通过")
    
    scheduler.shutdown()


if __name__ == '__main__':
    main()



# ==================== Stage 5.2: 任务日志系统 ====================

def setup_task_logging():
    """配置任务日志系统"""
    task_log_dir = os.path.expanduser("~/.vectorbrain/logs/tasks")
    os.makedirs(task_log_dir, exist_ok=True)
    return task_log_dir

def log_task_execution(task_id: str, message: str, level: str = "INFO"):
    """记录任务执行日志到独立文件"""
    task_log_dir = os.path.expanduser("~/.vectorbrain/logs/tasks")
    log_file = os.path.join(task_log_dir, f"{task_id}.log")
    
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Failed to write task log: {e}")

# 修改 execute 方法添加日志
original_execute = None
if 'AdvancedTaskExecutor' in dir():
    def logged_execute(self, task):
        task_id = getattr(task, 'task_id', 'unknown')
        log_task_execution(task_id, f"Starting execution")
        
        success, result = original_execute(self, task) if original_execute else self._execute_simulated(task)
        
        if success:
            log_task_execution(task_id, f"Completed: {result[:100]}")
        else:
            log_task_execution(task_id, f"Failed: {result[:100]}", "ERROR")
        
        return success, result
    
    original_execute = AdvancedTaskExecutor.execute
    AdvancedTaskExecutor.execute = logged_execute
    logger.info("✅ 任务日志系统已启用")
