#!/usr/bin/env python3
"""
VectorBrain DAG API Server v2.0

提供 REST API 用于：
1. 查询任务列表（支持 DAG 依赖关系）
2. 创建任务（支持指定依赖）
3. 更新任务状态
4. 删除任务
5. 控制 DAG 调度器 (启动/停止/状态)

端口：9000
"""

import json
import sqlite3
import os
import sys
import threading
import time
import uuid
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import List, Dict, Any, Optional

# 导入调度器和工具函数
try:
    from dag_scheduler import DAGScheduler
    from dag_utils import detect_cycle
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  警告：无法导入 DAGScheduler: {e}")
    print("   调度器功能将不可用")
    SCHEDULER_AVAILABLE = False
    DAGScheduler = None
    detect_cycle = None

# ==================== 配置区 ====================
DB_PATH = os.path.expanduser("~/.vectorbrain/tasks/task_queue.db")
API_PORT = 9000
API_HOST = "127.0.0.1"
DAG_DIR = os.path.expanduser("~/.vectorbrain/dag")
SCHEDULER_SCRIPT_PATH = os.path.join(DAG_DIR, "dag_scheduler.py")
SCHEDULER_LOG_PATH = os.path.join(DAG_DIR, "logs", "dag_scheduler.log")
SCHEDULER_HEARTBEAT_TIMEOUT_SECONDS = 15

# ==================== 全局调度器状态 ====================
scheduler_instance: Optional[DAGScheduler] = None
scheduler_thread: Optional[threading.Thread] = None
scheduler_running = False
scheduler_lock = threading.Lock()


# ==================== 调度器控制函数 ====================

def start_scheduler(max_workers: int = 4, poll_interval: float = 1.0):
    """
    启动 DAG 调度器（在后台线程）
    
    Returns:
        (success, message)
    """
    global scheduler_instance, scheduler_thread, scheduler_running
    
    with scheduler_lock:
        if scheduler_running:
            return False, "调度器已在运行中"
        
        if not SCHEDULER_AVAILABLE:
            return False, "DAGScheduler 未导入"
        
        try:
            # 创建调度器实例
            scheduler_instance = DAGScheduler(
                db_path=DB_PATH,
                max_workers=max_workers,
                poll_interval=poll_interval,
                task_timeout=30,
                max_retries=3
            )
            
            # 启动后台线程
            scheduler_thread = threading.Thread(target=scheduler_instance.run, daemon=True)
            scheduler_thread.start()
            
            scheduler_running = True
            
            return True, f"调度器已启动 (Workers={max_workers}, Poll={poll_interval}s)"
        
        except Exception as e:
            return False, f"启动失败：{str(e)}"


def stop_scheduler(wait: bool = True):
    """
    停止 DAG 调度器
    
    Returns:
        (success, message)
    """
    global scheduler_instance, scheduler_thread, scheduler_running
    
    with scheduler_lock:
        if not scheduler_running or scheduler_instance is None:
            return False, "调度器未运行"
        
        try:
            # 触发关闭
            scheduler_instance.shutdown(wait=wait)
            
            # 等待线程结束
            if wait and scheduler_thread:
                scheduler_thread.join(timeout=5)
            
            scheduler_running = False
            scheduler_thread = None
            scheduler_instance = None
            
            return True, "调度器已停止"
        
        except Exception as e:
            return False, f"停止失败：{str(e)}"


def _count_running_tasks_in_db() -> int:
    """从数据库统计当前 running 任务数。"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM tasks WHERE status = 'running'")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def _get_running_tasks_from_db() -> List[Dict[str, Any]]:
    """从数据库读取当前 running 任务，供独立 scheduler 模式展示。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT task_id, title, assigned_worker, updated_at
        FROM tasks
        WHERE status = 'running'
        ORDER BY updated_at DESC, created_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    active = []
    for row in rows:
        active.append({
            'task_id': row['task_id'],
            'title': row['title'],
            'worker_id': row['assigned_worker'],
            'start_time': row['updated_at'],
            'retry_count': None
        })
    return active


def _detect_external_scheduler_process() -> Dict[str, Any]:
    """检测独立运行的 dag_scheduler.py 进程。"""
    try:
        result = subprocess.run(
            ['ps', '-axo', 'pid=,command='],
            capture_output=True,
            text=True,
            check=True
        )
    except Exception as e:
        return {
            'detected': False,
            'pid': None,
            'command': None,
            'error': str(e)
        }

    script_realpath = os.path.realpath(SCHEDULER_SCRIPT_PATH)
    candidates = []

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split(None, 1)
        if len(parts) != 2:
            continue

        pid_text, command = parts

        if str(os.getpid()) == pid_text:
            continue

        if 'dag_scheduler.py' not in command:
            continue

        if 'grep' in command:
            continue

        command_real = os.path.realpath(command.split()[-1]) if command.split() else ''
        if script_realpath not in command and command_real != script_realpath:
            # 保守一点：优先匹配目标脚本本体，避免误把备份脚本/别的同名脚本算进去
            continue

        try:
            pid = int(pid_text)
        except ValueError:
            continue

        candidates.append({
            'pid': pid,
            'command': command
        })

    if not candidates:
        return {
            'detected': False,
            'pid': None,
            'command': None,
            'error': None
        }

    candidates.sort(key=lambda x: x['pid'])
    selected = candidates[0]
    return {
        'detected': True,
        'pid': selected['pid'],
        'command': selected['command'],
        'error': None
    }


def _get_scheduler_log_heartbeat() -> Dict[str, Any]:
    """基于日志 mtime 判断 scheduler 最近是否还在持续活动。"""
    if not os.path.exists(SCHEDULER_LOG_PATH):
        return {
            'log_exists': False,
            'heartbeat_ok': False,
            'last_heartbeat_at': None,
            'heartbeat_age_seconds': None
        }

    mtime = os.path.getmtime(SCHEDULER_LOG_PATH)
    age_seconds = max(0.0, time.time() - mtime)
    return {
        'log_exists': True,
        'heartbeat_ok': age_seconds <= SCHEDULER_HEARTBEAT_TIMEOUT_SECONDS,
        'last_heartbeat_at': datetime.fromtimestamp(mtime).isoformat(),
        'heartbeat_age_seconds': round(age_seconds, 3)
    }


def get_scheduler_status():
    """
    获取调度器状态
    
    Returns:
        dict: 状态信息
    """
    global scheduler_instance, scheduler_thread, scheduler_running

    in_process_running = bool(scheduler_running)
    in_process_thread_alive = scheduler_thread.is_alive() if scheduler_thread else False
    external_process = _detect_external_scheduler_process()
    heartbeat = _get_scheduler_log_heartbeat()

    external_running = external_process['detected'] and heartbeat['heartbeat_ok']
    effective_running = in_process_running or external_running

    status = {
        'running': effective_running,
        'thread_alive': in_process_thread_alive,
        'workers': None,
        'active_tasks': 0,
        'stats': {},
        'mode': 'in_process' if in_process_running else ('external_process' if external_process['detected'] else 'not_running'),
        'in_process': {
            'running': in_process_running,
            'thread_alive': in_process_thread_alive
        },
        'external_process': {
            'detected': external_process['detected'],
            'pid': external_process['pid'],
            'command': external_process['command']
        },
        'heartbeat': heartbeat
    }
    
    if scheduler_instance and in_process_running:
        status['workers'] = scheduler_instance.max_workers
        status['active_tasks'] = len(scheduler_instance.active_tasks)
        status['stats'] = scheduler_instance.stats.copy()
    else:
        status['active_tasks'] = _count_running_tasks_in_db()

    return status


# ==================== 数据库操作 ====================
def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_task_status(tasks: List[Dict]) -> List[Dict]:
    """
    计算每个任务的实际可执行状态
    
    状态优先级: pending → ready → running → done/failed/cancelled
    
    ready 条件：所有 dependencies 都已完成 (done)
    """
    task_map = {t['task_id']: t for t in tasks}
    
    for task in tasks:
        original_status = task['status']
        
        # 只有 pending 状态的任务才需要检查是否变为 ready
        if original_status == 'pending':
            dependencies = json.loads(task.get('dependencies') or '[]')
            
            if not dependencies:
                # 没有依赖，直接 ready
                task['calculated_status'] = 'ready'
            else:
                # 检查所有依赖是否完成
                all_deps_done = True
                for dep_id in dependencies:
                    dep_task = task_map.get(dep_id)
                    if not dep_task or dep_task['status'] != 'done':
                        all_deps_done = False
                        break
                
                task['calculated_status'] = 'ready' if all_deps_done else 'pending'
        else:
            task['calculated_status'] = original_status
    
    return tasks

# ==================== HTTP 请求处理器 ====================
class DAGAPIHandler(BaseHTTPRequestHandler):
    
    def _send_response(self, status_code: int, data: Any):
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        if isinstance(data, dict):
            response = json.dumps(data, ensure_ascii=False, default=str)
        else:
            response = json.dumps(data, ensure_ascii=False, default=str)
        
        self.wfile.write(response.encode('utf-8'))
    
    def do_OPTIONS(self):
        """处理 CORS preflight 请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            # 调度器控制端点
            if path == '/api/v1/scheduler/status':
                self._get_scheduler_status()
            elif path == '/api/v1/scheduler/active':
                self._get_active_tasks()
            # 任务端点
            elif path == '/api/v1/tasks':
                self._get_tasks(query_params)
            elif path.startswith('/api/v1/tasks/'):
                task_id = path.split('/')[-1]
                self._get_task(task_id)
            elif path == '/api/v1/stats':
                self._get_stats()
            elif path == '/health':
                self._health_check()
            else:
                self._send_response(404, {'error': 'Not found', 'path': path})
        
        except Exception as e:
            self._send_response(500, {'error': str(e)})
    
    def do_POST(self):
        """处理 POST 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
            
            # 调度器控制端点
            if path == '/api/v1/scheduler/start':
                self._start_scheduler(data)
            elif path == '/api/v1/scheduler/stop':
                self._stop_scheduler(data)
            # 任务端点
            elif path == '/api/v1/tasks':
                self._create_task(data)
            elif path.startswith('/api/v1/tasks/') and path.endswith('/status'):
                task_id = path.split('/')[4]
                self._update_task_status(task_id, data)
            else:
                self._send_response(404, {'error': 'Not found'})
        
        except json.JSONDecodeError:
            self._send_response(400, {'error': 'Invalid JSON'})
        except Exception as e:
            self._send_response(500, {'error': str(e)})
    
    def do_DELETE(self):
        """处理 DELETE 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            if path.startswith('/api/v1/tasks/'):
                task_id = path.split('/')[-1]
                self._delete_task(task_id)
            else:
                self._send_response(404, {'error': 'Not found'})
        
        except Exception as e:
            self._send_response(500, {'error': str(e)})
    
    # ==================== API 端点实现 ====================
    
    def _get_tasks(self, query_params: Dict):
        """获取任务列表（支持 DAG 依赖关系）"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 可选过滤：status, assigned_worker
        where_clauses = []
        params = []
        
        if 'status' in query_params:
            status = query_params['status'][0]
            where_clauses.append("status = ?")
            params.append(status)
        
        if 'worker' in query_params:
            worker = query_params['worker'][0]
            where_clauses.append("assigned_worker = ?")
            params.append(worker)
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        query = f"""
            SELECT 
                task_id, title, description, priority, status,
                assigned_worker, created_by, created_at, updated_at,
                completed_at, result, error_message,
                dependencies, dependents
            FROM tasks
            {where_sql}
            ORDER BY priority ASC, created_at ASC
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # 转换为字典列表
        tasks = []
        for row in rows:
            task = dict(row)
            # 解析 JSON 字段
            task['dependencies'] = json.loads(task.get('dependencies') or '[]')
            task['dependents'] = json.loads(task.get('dependents') or '[]')
            tasks.append(task)
        
        # 计算每个任务的实际状态（考虑依赖）
        tasks = calculate_task_status(tasks)
        
        self._send_response(200, {
            'success': True,
            'count': len(tasks),
            'data': tasks
        })
    
    def _get_task(self, task_id: str):
        """获取单个任务详情"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            self._send_response(404, {'error': 'Task not found', 'task_id': task_id})
            return
        
        task = dict(row)
        task['dependencies'] = json.loads(task.get('dependencies') or '[]')
        task['dependents'] = json.loads(task.get('dependents') or '[]')
        
        self._send_response(200, {'success': True, 'data': task})
    
    def _get_stats(self):
        """获取任务统计信息"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 按状态统计
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
        """)
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # 总数
        cursor.execute("SELECT COUNT(*) as total FROM tasks")
        total = cursor.fetchone()['total']
        
        # 计算 ready 状态的任务数（pending 且依赖已完成的）
        cursor.execute("SELECT task_id, dependencies FROM tasks WHERE status = 'pending'")
        ready_count = 0
        for row in cursor.fetchall():
            deps = json.loads(row['dependencies'] or '[]')
            if not deps:
                ready_count += 1
            else:
                # 检查依赖是否都完成
                placeholders = ','.join('?' * len(deps))
                cursor.execute(f"""
                    SELECT COUNT(*) as done_count FROM tasks 
                    WHERE task_id IN ({placeholders}) AND status = 'done'
                """, deps)
                if cursor.fetchone()['done_count'] == len(deps):
                    ready_count += 1
        
        conn.close()
        
        self._send_response(200, {
            'success': True,
            'data': {
                'total': total,
                'by_status': status_counts,
                'ready_to_run': ready_count
            }
        })
    
    def _create_task(self, data: Dict):
        """创建新任务（支持 DAG 依赖）"""
        required_fields = ['title']
        for field in required_fields:
            if field not in data:
                self._send_response(400, {'error': f'Missing required field: {field}'})
                return
        
        task_id = data.get('task_id', f"task_{uuid.uuid4().hex[:16]}")
        title = data['title']
        description = data.get('description', '')
        priority = data.get('priority', 5)
        dependencies = data.get('dependencies', [])
        assigned_worker = data.get('assigned_worker', '')
        created_by = data.get('created_by', 'api')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 验证依赖任务是否存在
            if dependencies:
                placeholders = ','.join('?' * len(dependencies))
                cursor.execute(f"SELECT task_id FROM tasks WHERE task_id IN ({placeholders})", dependencies)
                existing_deps = {row['task_id'] for row in cursor.fetchall()}
                
                missing_deps = set(dependencies) - existing_deps
                if missing_deps:
                    self._send_response(400, {
                        'error': 'Dependencies not found',
                        'missing': list(missing_deps)
                    })
                    return
            
            # 计算依赖任务的 dependents
            dependents_of_this = []
            
            # 插入新任务
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, title, description, priority, status,
                    assigned_worker, created_by, dependencies, dependents
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """, (
                task_id, title, description, priority,
                assigned_worker, created_by,
                json.dumps(dependencies), json.dumps(dependents_of_this)
            ))
            
            # 更新依赖任务的 dependents 字段
            for dep_id in dependencies:
                cursor.execute("SELECT dependents FROM tasks WHERE task_id = ?", (dep_id,))
                row = cursor.fetchone()
                current_dependents = json.loads(row['dependents'] or '[]')
                current_dependents.append(task_id)
                cursor.execute("""
                    UPDATE tasks SET dependents = ?, updated_at = ?
                    WHERE task_id = ?
                """, (json.dumps(current_dependents), datetime.now().isoformat(), dep_id))
            
            conn.commit()
            conn.close()
            
            self._send_response(201, {
                'success': True,
                'message': 'Task created',
                'task_id': task_id
            })
        
        except sqlite3.IntegrityError:
            conn.close()
            self._send_response(409, {'error': 'Task ID already exists', 'task_id': task_id})
    
    def _update_task_status(self, task_id: str, data: Dict):
        """更新任务状态"""
        if 'status' not in data:
            self._send_response(400, {'error': 'Missing status field'})
            return
        
        new_status = data['status']
        valid_statuses = ['pending', 'ready', 'running', 'done', 'failed', 'cancelled']
        
        if new_status not in valid_statuses:
            self._send_response(400, {
                'error': 'Invalid status',
                'valid': valid_statuses
            })
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查任务是否存在
        cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,))
        if not cursor.fetchone():
            conn.close()
            self._send_response(404, {'error': 'Task not found', 'task_id': task_id})
            return
        
        # 更新状态
        updates = ["status = ?", "updated_at = ?"]
        params = [new_status, datetime.now().isoformat()]
        
        if new_status in ['done', 'failed', 'cancelled']:
            updates.append("completed_at = ?")
            params.append(datetime.now().isoformat())
        
        if 'result' in data:
            updates.append("result = ?")
            params.append(data['result'])
        
        if 'error_message' in data:
            updates.append("error_message = ?")
            params.append(data['error_message'])
        
        params.append(task_id)
        
        cursor.execute(f"""
            UPDATE tasks SET {', '.join(updates)}
            WHERE task_id = ?
        """, params)
        
        conn.commit()
        conn.close()
        
        self._send_response(200, {
            'success': True,
            'message': f'Task status updated to {new_status}',
            'task_id': task_id
        })
    
    def _delete_task(self, task_id: str):
        """删除任务"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查任务是否存在
        cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,))
        if not cursor.fetchone():
            conn.close()
            self._send_response(404, {'error': 'Task not found', 'task_id': task_id})
            return
        
        # 检查是否有依赖此任务的其他任务
        cursor.execute("SELECT dependents FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        dependents = json.loads(row['dependents'] or '[]')
        
        if dependents:
            conn.close()
            self._send_response(409, {
                'error': 'Cannot delete task with dependents',
                'dependents': dependents
            })
            return
        
        # 删除任务
        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        conn.commit()
        conn.close()
        
        self._send_response(200, {
            'success': True,
            'message': 'Task deleted',
            'task_id': task_id
        })
    
    # ==================== 调度器控制端点 ====================
    
    def _get_scheduler_status(self):
        """获取调度器状态"""
        status = get_scheduler_status()
        self._send_response(200, {
            'success': True,
            'data': status
        })
    
    def _get_active_tasks(self):
        """获取活跃任务列表"""
        global scheduler_instance

        active = []

        if scheduler_running and scheduler_instance is not None:
            for task_id, scheduled in scheduler_instance.active_tasks.items():
                active.append({
                    'task_id': task_id,
                    'title': scheduled.task.title,
                    'worker_id': scheduled.worker_id,
                    'start_time': scheduled.start_time.isoformat(),
                    'retry_count': scheduled.retry_count
                })
        else:
            status = get_scheduler_status()
            if status['external_process']['detected']:
                active = _get_running_tasks_from_db()
        
        self._send_response(200, {
            'success': True,
            'count': len(active),
            'data': active
        })
    
    def _start_scheduler(self, data: Dict):
        """启动调度器"""
        max_workers = data.get('max_workers', 4)
        poll_interval = data.get('poll_interval', 1.0)
        
        success, message = start_scheduler(max_workers, poll_interval)
        
        if success:
            self._send_response(200, {
                'success': True,
                'message': message
            })
        else:
            self._send_response(400, {
                'success': False,
                'error': message
            })
    
    def _stop_scheduler(self, data: Dict):
        """停止调度器"""
        wait = data.get('wait', True)
        
        success, message = stop_scheduler(wait)
        
        if success:
            self._send_response(200, {
                'success': True,
                'message': message
            })
        else:
            self._send_response(400, {
                'success': False,
                'error': message
            })
    
    # ==================== 健康检查 ====================
    
    def _health_check(self):
        """健康检查"""
        """健康检查"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            count = cursor.fetchone()[0]
            conn.close()
            
            self._send_response(200, {
                'status': 'healthy',
                'database': 'connected',
                'task_count': count
            })
        except Exception as e:
            self._send_response(500, {
                'status': 'unhealthy',
                'error': str(e)
            })
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [API] {args[0]}")

# ==================== 主函数 ====================
def main():
    """启动 API 服务器"""
    server_address = (API_HOST, API_PORT)
    httpd = HTTPServer(server_address, DAGAPIHandler)
    
    print("=" * 60)
    print("🚀 VectorBrain DAG API Server")
    print("=" * 60)
    print(f"🌐 监听地址：http://{API_HOST}:{API_PORT}")
    print(f"📊 API 端点:")
    print(f"   === 任务管理 ===")
    print(f"   GET    /api/v1/tasks          - 获取任务列表")
    print(f"   GET    /api/v1/tasks/:id      - 获取任务详情")
    print(f"   POST   /api/v1/tasks          - 创建任务")
    print(f"   POST   /api/v1/tasks/:id/status - 更新任务状态")
    print(f"   DELETE /api/v1/tasks/:id      - 删除任务")
    print(f"   GET    /api/v1/stats          - 获取统计信息")
    print(f"   === 调度器控制 ===")
    print(f"   GET    /api/v1/scheduler/status  - 调度器状态")
    print(f"   GET    /api/v1/scheduler/active  - 活跃任务")
    print(f"   POST   /api/v1/scheduler/start   - 启动调度器")
    print(f"   POST   /api/v1/scheduler/stop    - 停止调度器")
    print(f"   === 其他 ===")
    print(f"   GET    /health                - 健康检查")
    print("=" * 60)
    print(f"🖼️  Dashboard: 打开 ~/.vectorbrain/dag/dag_dashboard.html")
    print("=" * 60)
    print()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        httpd.shutdown()

if __name__ == '__main__':
    main()
