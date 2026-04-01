#!/usr/bin/env python3
"""
VectorBrain Metrics System v1.0

采集:
- 任务执行指标 (execution time, status, worker)
- Scheduler 轮询指标 (tick, ready_count, dispatch_count)
- Worker 利用率 (busy/idle, current_task)

数据库：~/.vectorbrain/metrics/metrics.db
"""

import sqlite3
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

# ==================== 配置 ====================
METRICS_DB = os.path.expanduser("~/.vectorbrain/metrics/metrics.db")

# ==================== 数据库初始化 ====================

def init_metrics_db():
    """初始化 Metrics 数据库"""
    os.makedirs(os.path.dirname(METRICS_DB), exist_ok=True)
    
    conn = sqlite3.connect(METRICS_DB)
    cursor = conn.cursor()
    
    # 任务执行指标
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_metrics (
            task_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            execution_time REAL,
            status TEXT,
            worker_id TEXT,
            title TEXT
        )
    """)
    
    # Scheduler 轮询指标
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_ticks (
            tick_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ready_count INTEGER DEFAULT 0,
            running_count INTEGER DEFAULT 0,
            dispatch_count INTEGER DEFAULT 0
        )
    """)
    
    # Worker 状态快照
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS worker_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            worker_id TEXT,
            busy BOOLEAN DEFAULT 0,
            current_task TEXT
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON task_metrics(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_time ON task_metrics(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tick_time ON scheduler_ticks(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_time ON worker_stats(timestamp)")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Metrics 数据库已初始化：{METRICS_DB}")
    return METRICS_DB


# ==================== Metrics 采集 API ====================

class MetricsCollector:
    """Metrics 采集器"""
    
    def __init__(self, db_path: str = METRICS_DB):
        self.db_path = db_path
        init_metrics_db()
    
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
    
    # --- 任务指标 ---
    
    def record_task_created(self, task_id: str, title: str = ""):
        """记录任务创建"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO task_metrics (task_id, created_at, title)
            VALUES (?, ?, ?)
        """, (task_id, datetime.now().isoformat(), title))
        conn.commit()
        conn.close()
    
    def record_task_started(self, task_id: str, worker_id: str = ""):
        """记录任务开始执行"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE task_metrics
            SET started_at = ?, worker_id = ?
            WHERE task_id = ?
        """, (datetime.now().isoformat(), worker_id, task_id))
        conn.commit()
        conn.close()
    
    def record_task_completed(self, task_id: str, status: str):
        """记录任务完成"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 计算执行时间
        cursor.execute("""
            UPDATE task_metrics
            SET completed_at = ?, status = ?,
                execution_time = (julianday() - julianday(started_at)) * 86400
            WHERE task_id = ?
        """, (datetime.now().isoformat(), status, task_id))
        
        conn.commit()
        conn.close()
    
    # --- Scheduler 指标 ---
    
    def record_tick(self, ready_count: int, running_count: int, dispatch_count: int = 0):
        """记录 Scheduler 轮询"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scheduler_ticks (ready_count, running_count, dispatch_count)
            VALUES (?, ?, ?)
        """, (ready_count, running_count, dispatch_count))
        conn.commit()
        conn.close()
    
    # --- Worker 指标 ---
    
    def record_worker_state(self, worker_id: str, busy: bool, current_task: str = ""):
        """记录 Worker 状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO worker_stats (worker_id, busy, current_task)
            VALUES (?, ?, ?)
        """, (worker_id, 1 if busy else 0, current_task))
        conn.commit()
        conn.close()
    
    # --- 查询 API ---
    
    def get_throughput(self, window_seconds: int = 60) -> float:
        """获取吞吐量 (tasks/sec)"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM task_metrics
            WHERE status IN ('done', 'success', 'failed')
            AND completed_at > datetime('now', '-' || ? || ' seconds')
        """, (window_seconds,))
        count = cursor.fetchone()[0]
        conn.close()
        return count / window_seconds if window_seconds > 0 else 0
    
    def get_avg_execution_time(self, window_seconds: int = 300) -> float:
        """获取平均执行时间 (秒)"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT AVG(execution_time) FROM task_metrics
            WHERE status IN ('done', 'success')
            AND execution_time IS NOT NULL
            AND completed_at > datetime('now', '-' || ? || ' seconds')
        """, (window_seconds,))
        result = cursor.fetchone()[0]
        conn.close()
        return result if result else 0
    
    def get_queue_depth(self) -> int:
        """获取当前队列深度 (pending 任务数)"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM task_metrics
            WHERE status = 'pending' OR status IS NULL
        """)
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_recent_ticks(self, limit: int = 60) -> List[Dict]:
        """获取最近 Scheduler 轮询记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tick_id, timestamp, ready_count, running_count, dispatch_count
            FROM scheduler_ticks
            ORDER BY tick_id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'tick_id': r[0],
                'timestamp': r[1],
                'ready_count': r[2],
                'running_count': r[3],
                'dispatch_count': r[4]
            }
            for r in rows
        ]


# ==================== 单例 ====================

_collector: Optional[MetricsCollector] = None

def get_collector() -> MetricsCollector:
    """获取 Metrics 采集器单例"""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


# ==================== 测试 ====================

if __name__ == '__main__':
    print("🧪 测试 Metrics 系统...")
    
    collector = get_collector()
    
    # 模拟数据
    for i in range(5):
        task_id = f"test_task_{i}"
        collector.record_task_created(task_id, f"Test Task {i}")
        collector.record_task_started(task_id, f"worker_{i % 2}")
        time.sleep(0.1)
        collector.record_task_completed(task_id, "done")
        collector.record_tick(ready_count=3-i, running_count=i, dispatch_count=1)
    
    # 查询指标
    print(f"\n📊 Metrics 报告:")
    print(f"  吞吐量：{collector.get_throughput(60):.3f} tasks/sec")
    print(f"  平均执行时间：{collector.get_avg_execution_time(300):.2f} sec")
    print(f"  队列深度：{collector.get_queue_depth()}")
    print(f"  最近轮询：{len(collector.get_recent_ticks(10))} 条")
    
    print("\n✅ Metrics 系统测试完成")
