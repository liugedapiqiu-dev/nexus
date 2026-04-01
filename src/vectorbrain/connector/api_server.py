#!/usr/bin/env python3
"""
VectorBrain Gateway API Server v2
为 OpenClaw 提供常驻记忆存取服务 + DAG 任务调度

v2.0 (2026-03-13): 添加 DAG 任务调度端点

状态标记（2026-03-19）：
- 当前归类：旧旁路 / 非主链
- 排查原则：不要作为主框架健康状态的第一观察对象
- 处理原则：若要继续整顿，先确认真实调用方，再决定保留/停用/归档
- 参考清单：~/.vectorbrain/SCRIPT_REGISTRY.md
"""

from pathlib import Path
import sys
# 提前注入 ~/.vectorbrain，确保下面的 runtime.* 导入可解析
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from runtime.bridge_http import (
    OpenClawIngressRequest,
    OpenClawPostprocessRequest,
    openclaw_bridge,
)
from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime
import uvicorn
import os
import time

from runtime.unified_bridge import unified_bridge

app = FastAPI(title="VectorBrain Gateway")

# ===== 添加 CORS 中间件（允许前端跨域访问）=====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议替换为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保数据库路径正确
VECBRAIN_HOME = Path.home() / ".vectorbrain"
EPISODIC_DB = str(VECBRAIN_HOME / "memory" / "episodic_memory.db")
KNOWLEDGE_DB = str(VECBRAIN_HOME / "memory" / "knowledge_memory.db")
TASKS_DB = str(VECBRAIN_HOME / "tasks" / "task_queue.db")

# 添加 DAG 模块路径
sys.path.insert(0, str(VECBRAIN_HOME / 'src'))


# ===== 数据模型 =====

class MemoryEvent(BaseModel):
    role: str
    content: str
    metadata: dict = {}


class OpenClawPreprocessRequest(BaseModel):
    session_id: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    message_id: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    text: str = ""
    raw: Dict[str, Any] = {}
    context: Dict[str, Any] = {}


class OpenClawPostprocessRequest(BaseModel):
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    channel: Optional[str] = None
    user_text: Optional[str] = None
    assistant_text: Optional[str] = None
    mode: Optional[str] = None
    latency_ms: Optional[int] = None
    success: bool = True
    metadata: Dict[str, Any] = {}


class TaskModel(BaseModel):
    task_id: str
    title: str
    description: Optional[str] = ""
    depends_on: Optional[List[str]] = []
    priority: Optional[int] = 5


class DAGSubmitRequest(BaseModel):
    tasks: List[TaskModel]
    run_group: Optional[str] = None


class DAGSubmitResponse(BaseModel):
    status: str
    msg: str
    run_id: str
    task_count: int
    topology: List[str]


@app.post("/v1/openclaw/preprocess")
async def openclaw_preprocess(request: OpenClawIngressRequest):
    """Unified OpenClaw ingress bridge. Legacy connector now only hosts this contract for compatibility."""
    return openclaw_bridge.preprocess(request)


@app.post("/v1/openclaw/postprocess")
async def openclaw_postprocess(request: OpenClawPostprocessRequest):
    """Unified OpenClaw postprocess contract (minimal ack in compatibility host)."""
    return openclaw_bridge.postprocess(request)


@app.get("/v1/ready")
async def ready_check():
    return openclaw_bridge.ready()


@app.get("/v1/health")
async def unified_health_check():
    return openclaw_bridge.health()


@app.post("/memory/save")
async def save_memory(event: MemoryEvent):
    """保存事件到情景记忆（legacy compatibility path，不再推荐作为主入口）"""
    try:
        conn = sqlite3.connect(EPISODIC_DB)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        # 插入事件记录
        cursor.execute("""
            INSERT INTO episodes (timestamp, worker_id, event_type, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            "global_gateway",
            f"message_{event.role}",
            event.content,
            json.dumps(event.metadata, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "msg": "记忆已写入海绵体",
            "timestamp": timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/load")
async def load_memory(limit: int = 5):
    """获取最近的记忆上下文（legacy compatibility path）"""
    try:
        conn = sqlite3.connect(EPISODIC_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT event_type, content, metadata, timestamp
            FROM episodes
            WHERE worker_id = 'global_gateway'
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        context = [
            {
                "type": r[0],
                "content": r[1],
                "metadata": json.loads(r[2] if r[2] else "{}"),
                "timestamp": r[3]
            }
            for r in reversed(rows)
        ]
        
        return {
            "status": "success",
            "data": context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """旧 connector 自身健康检查；主桥健康请看 /v1/health"""
    return {
        "status": "healthy",
        "service": "VectorBrain Gateway",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/v1/openclaw/preprocess")
async def openclaw_preprocess(request: OpenClawPreprocessRequest):
    """Unified Bridge preprocess 主入口（OpenClaw 默认消息优先走这里）"""
    try:
        return unified_bridge.preprocess(request.model_dump())
    except Exception as e:
        return {
            "ok": False,
            "mode": "fail_open",
            "trace_id": f"vb_fail_{int(time.time())}",
            "reason": f"api_preprocess_exception: {e}",
            "degraded": True,
            "prepend_prompt": "",
            "append_prompt": "",
            "memory_context": [],
            "response_guidance": {},
            "direct_response": None,
        }


@app.post("/v1/openclaw/postprocess")
async def openclaw_postprocess(request: OpenClawPostprocessRequest):
    """最小 postprocess：把最终回复落回 episodic memory，供后续检索/追踪"""
    try:
        conn = sqlite3.connect(EPISODIC_DB)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO episodes (timestamp, worker_id, event_type, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            "openclaw_unified_bridge",
            "openclaw_postprocess",
            request.assistant_text or "",
            json.dumps(request.model_dump(), ensure_ascii=False),
        ))
        conn.commit()
        conn.close()
        return {"ok": True, "status": "recorded", "timestamp": timestamp, "trace_id": request.trace_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/ready")
async def ready_check():
    return {"status": "ready", "service": "VectorBrain Unified Bridge", "timestamp": datetime.now().isoformat()}


# ===== DAG 任务调度端点 =====

@app.post("/api/v1/tasks/dag", response_model=DAGSubmitResponse)
async def submit_dag_endpoint(request: DAGSubmitRequest):
    """
    提交 DAG 任务组
    
    示例请求体：
    ```json
    {
        "tasks": [
            {"task_id": "build", "title": "构建项目"},
            {"task_id": "test", "title": "运行测试", "depends_on": ["build"]},
            {"task_id": "deploy", "title": "部署", "depends_on": ["test"]}
        ]
    }
    ```
    """
    try:
        # 导入 DAG 模块
        from dag_task_manager import init_db, submit_dag, cleanup_zombie_tasks
        
        # 初始化数据库
        init_db(TASKS_DB)
        cleanup_zombie_tasks(TASKS_DB)
        
        # 转换请求模型为任务列表
        tasks_list = [
            {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "depends_on": task.depends_on or [],
                "priority": task.priority or 5
            }
            for task in request.tasks
        ]
        
        # 生成 run_group
        run_id = request.run_group or f"dag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 提交 DAG
        success = submit_dag(tasks_list, TASKS_DB)
        
        if not success:
            raise HTTPException(status_code=400, detail="DAG 提交失败：检测到循环依赖")
        
        # 🆕 自动启动 Worker（后台运行）
        import subprocess
        import sys
        from pathlib import Path
        
        # 使用后台进程启动 Worker
        venv_python = str(Path.home() / '.vectorbrain' / 'connector' / 'venv' / 'bin' / 'python3')
        worker_script = str(Path.home() / '.vectorbrain' / 'src' / 'dag_task_manager.py')
        
        # 启动 Worker（不阻塞）
        subprocess.Popen(
            [venv_python, worker_script, 'worker', '--auto-exit'],
            stdout=open('/tmp/dag_worker.log', 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        
        print(f"🚀 Worker 已自动启动！")
        
        # 🆕 自动打开 Dashboard
        try:
            dashboard_path = Path.home() / '.openclaw' / 'workspace' / 'dag_dashboard.html'
            if dashboard_path.exists():
                import webbrowser
                webbrowser.open(f'file://{dashboard_path}')
                print(f"📺 Dashboard 已自动打开！")
        except Exception as e:
            print(f"⚠️ 无法自动打开 Dashboard: {e}")
        
        # 获取拓扑排序
        from graphlib import TopologicalSorter
        graph = {t["task_id"]: t["depends_on"] for t in tasks_list}
        ts = TopologicalSorter(graph)
        topology = list(ts.static_order())
        
        return DAGSubmitResponse(
            status="success",
            msg=f"DAG 任务组已提交，共 {len(tasks_list)} 个任务，Worker 已自动启动！",
            run_id=run_id,
            task_count=len(tasks_list),
            topology=topology
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取单个任务状态"""
    try:
        conn = sqlite3.connect(TASKS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, title, description, status, priority, 
                   dependencies, dependents, created_at, updated_at, 
                   completed_at, result, error_message
            FROM tasks
            WHERE task_id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        return {
            "status": "success",
            "data": {
                "task_id": row["task_id"],
                "title": row["title"],
                "description": row["description"],
                "status": row["status"],
                "priority": row["priority"],
                "dependencies": json.loads(row["dependencies"] or "[]"),
                "dependents": json.loads(row["dependents"] or "[]"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "completed_at": row["completed_at"],
                "result": row["result"],
                "error_message": row["error_message"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 20):
    """获取任务列表（可选按状态过滤）"""
    try:
        conn = sqlite3.connect(TASKS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT task_id, title, status, priority, created_at, updated_at
                FROM tasks
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT task_id, title, status, priority, created_at, updated_at
                FROM tasks
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "status": "success",
            "data": [
                {
                    "task_id": row["task_id"],
                    "title": row["title"],
                    "status": row["status"],
                    "priority": row["priority"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
                for row in rows
            ],
            "count": len(rows)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务（仅对 pending/ready 状态有效）"""
    try:
        conn = sqlite3.connect(TASKS_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ? AND status IN ('pending', 'ready')
        """, (task_id,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected == 0:
            raise HTTPException(status_code=400, detail="任务无法取消（可能已在运行或已完成）")
        
        return {
            "status": "success",
            "msg": f"任务 {task_id} 已取消"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "service": "VectorBrain Gateway",
        "version": "1.1.0",
        "role": "legacy_compatibility_host",
        "primary_contract": "/v1/openclaw/preprocess",
        "legacy_routes": ["/memory/save", "/memory/load", "/health"],
        "endpoints": [
            "POST /v1/openclaw/preprocess",
            "POST /v1/openclaw/postprocess",
            "GET /v1/ready",
            "GET /v1/health",
            "POST /memory/save",
            "GET /memory/load",
            "GET /health"
        ]
    }


if __name__ == "__main__":
    # 启动服务，监听 8999 端口
    print("=" * 60)
    print("🧠 VectorBrain Gateway API Server")
    print("=" * 60)
    print(f"  🌐 监听地址：http://127.0.0.1:8999")
    print(f"  📚 数据库：{EPISODIC_DB}")
    print(f"  🚀 启动中...")
    print("=" * 60)
    
    uvicorn.run(app, host="127.0.0.1", port=8999)
