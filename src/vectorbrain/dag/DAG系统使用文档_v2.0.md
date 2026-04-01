# 🧠 VectorBrain DAG 任务系统 v2.0 - 完整使用文档

**文档版本**: v2.0  
**更新时间**: 2026-03-15  
**作者**: [YOUR_AI_NAME] 🧠  
**状态**: ✅ 生产就绪

---

## 📋 目录

1. [系统概述](#系统概述)
2. [快速开始](#快速开始)
3. [架构说明](#架构说明)
4. [API 参考](#api-参考)
5. [使用示例](#使用示例)
6. [核心算法](#核心算法)
7. [故障排查](#故障排查)
8. [最佳实践](#最佳实践)

---

## 系统概述

### 什么是 DAG 任务系统？

DAG（Directed Acyclic Graph，有向无环图）任务系统是一个**智能任务调度引擎**，可以：

- ✅ 自动管理任务依赖关系
- ✅ 智能调度执行顺序
- ✅ 并发执行独立任务
- ✅ 失败自动重试
- ✅ 实时监控进度

### 核心特性

| 特性 | 说明 | 状态 |
|------|------|------|
| **循环依赖检测** | DFS 算法，防止死锁 | ✅ |
| **拓扑排序** | Kahn 算法 + 优先级 | ✅ |
| **原子性抢占** | 防止重复执行 | ✅ |
| **并发控制** | 可配置 Worker 池 | ✅ |
| **超时处理** | 自动标记失败 | ✅ |
| **失败重试** | 最多 3 次重试 | ✅ |
| **实时监控** | REST API + Dashboard | ✅ |
| **远程控制** | 启动/停止调度器 | ✅ |

### 应用场景

- 🤖 **AI Agent 工作流** - 多步骤任务自动执行
- 📊 **数据处理管道** - ETL 流程自动化
- 🔄 **自动化测试** - 依赖管理 + 并发执行
- 📦 **构建系统** - 类似 Make/Airflow 的简化版

---

## 快速开始

### 1. 启动系统

```bash
# 进入工作目录
cd ~/.openclaw/workspace

# 启动 DAG API 服务器（端口 9000）
python3 dag_api_server.py &

# 或使用 nohup 后台运行
nohup python3 dag_api_server.py > /tmp/dag_api.log 2>&1 &
```

### 2. 验证系统正常

```bash
# 检查健康状态
curl http://127.0.0.1:9000/health

# 返回:
# {"status": "healthy", "database": "connected", "task_count": 51}
```

### 3. 启动调度器

```bash
# 通过 API 启动调度器
curl -X POST http://127.0.0.1:9000/api/v1/scheduler/start \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 4, "poll_interval": 1.0}'

# 返回:
# {"success": true, "message": "调度器已启动 (Workers=4, Poll=1.0s)"}
```

### 4. 打开 Dashboard

```bash
# 在浏览器打开监控界面
open ~/.vectorbrain/dag/dag_dashboard.html
```

Dashboard 会**每秒自动刷新**，显示：
- 实时任务状态
- DAG 依赖关系图
- 执行统计信息

---

## 架构说明

### 系统架构图

```
┌─────────────────────────────────────────────────┐
│              用户界面层                          │
│  ┌──────────────┐    ┌──────────────────┐      │
│  │  Dashboard   │    │  API 客户端       │      │
│  │  (HTML+JS)   │    │  (curl/Python)   │      │
│  └──────┬───────┘    └────────┬─────────┘      │
│         │                     │                  │
│         └──────────┬──────────┘                  │
│                    │ HTTP :9000                  │
└────────────────────▼─────────────────────────────┘
┌─────────────────────────────────────────────────┐
│              API 服务层                           │
│  ┌─────────────────────────────────────────┐   │
│  │   dag_api_server.py (HTTP Server)        │   │
│  │                                          │   │
│  │  任务管理端点：                          │   │
│  │  - GET/POST /api/v1/tasks               │   │
│  │  - GET/POST/DELETE /api/v1/tasks/:id    │   │
│  │                                          │   │
│  │  调度器控制端点：                        │   │
│  │  - GET /api/v1/scheduler/status         │   │
│  │  - POST /api/v1/scheduler/start         │   │
│  │  - POST /api/v1/scheduler/stop          │   │
│  └─────────────────────────────────────────┘   │
└────────────────────▼─────────────────────────────┘
┌─────────────────────────────────────────────────┐
│              调度器层                            │
│  ┌─────────────────────────────────────────┐   │
│  │   dag_scheduler.py                      │   │
│  │                                          │   │
│  │  - Poll Loop (每秒轮询)                 │   │
│  │  - Ready Queue (优先队列)               │   │
│  │  - Worker Pool (并发执行)               │   │
│  │  - 状态管理                             │   │
│  └─────────────────────────────────────────┘   │
└────────────────────▼─────────────────────────────┘
┌─────────────────────────────────────────────────┐
│              数据持久层                          │
│  ┌─────────────────────────────────────────┐   │
│  │   SQLite task_queue.db                  │   │
│  │                                          │   │
│  │  - 任务表（含依赖关系）                 │   │
│  │  - 状态索引                             │   │
│  │  - WAL 模式（高并发）                   │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 文件结构

```
~/.vectorbrain/dag/
├── dag_api_server.py      # API 服务器 (700 行)
├── dag_scheduler.py       # 调度器核心 (650 行)
├── dag_utils.py           # 核心算法 (450 行)
├── dag_dashboard.html     # 监控界面 (5KB)
└── DAG 系统使用文档.md     # 本文档
```

### 数据流

```
创建任务 → 验证依赖 → 存储数据库
                ↓
调度器轮询 → 发现 ready 任务
                ↓
原子抢占 → 防止重复执行
                ↓
Worker 执行 → 超时监控
                ↓
结果回写 → 状态更新
                ↓
依赖任务 → 变为 ready → 循环
```

---

## API 参考

### 基础信息

- **Base URL**: `http://127.0.0.1:9000`
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

---

### 任务管理 API

#### 1. 获取任务列表

```http
GET /api/v1/tasks
GET /api/v1/tasks?status=pending
GET /api/v1/tasks?worker=worker_1
```

**查询参数**:
- `status` (可选): 过滤状态 (pending/running/done/failed)
- `worker` (可选): 过滤 Worker

**响应示例**:
```json
{
  "success": true,
  "count": 5,
  "data": [
    {
      "task_id": "task_001",
      "title": "数据处理",
      "status": "pending",
      "priority": 5,
      "dependencies": ["task_000"],
      "dependents": ["task_002"],
      "created_at": "2026-03-15T00:00:00",
      "calculated_status": "ready"
    }
  ]
}
```

---

#### 2. 获取任务详情

```http
GET /api/v1/tasks/:task_id
```

**路径参数**:
- `task_id`: 任务 ID

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_001",
    "title": "数据处理",
    "description": "处理输入数据并生成报告",
    "status": "running",
    "priority": 5,
    "dependencies": ["task_000"],
    "dependents": ["task_002"],
    "assigned_worker": "scheduler_12345_0",
    "created_at": "2026-03-15T00:00:00",
    "updated_at": "2026-03-15T00:01:00"
  }
}
```

---

#### 3. 创建任务

```http
POST /api/v1/tasks
Content-Type: application/json

{
  "task_id": "my_task",
  "title": "我的任务",
  "description": "任务描述",
  "priority": 5,
  "dependencies": ["task_001", "task_002"]
}
```

**请求字段**:
- `task_id` (可选): 自定义任务 ID（默认自动生成）
- `title` (**必填**): 任务标题
- `description` (可选): 任务描述
- `priority` (可选): 优先级（1-10，数字越小优先级越高，默认 5）
- `dependencies` (可选): 依赖的任务 ID 列表

**响应示例**:
```json
{
  "success": true,
  "message": "Task created",
  "task_id": "my_task"
}
```

**错误响应**:
```json
{
  "error": "Dependencies not found",
  "missing": ["task_999"]
}
```

---

#### 4. 更新任务状态

```http
POST /api/v1/tasks/:task_id/status
Content-Type: application/json

{
  "status": "done",
  "result": "任务成功完成"
}
```

**路径参数**:
- `task_id`: 任务 ID

**请求字段**:
- `status` (**必填**): 新状态
  - `pending`: 等待中
  - `ready`: 可执行（所有依赖已完成）
  - `running`: 执行中
  - `done`: 已完成
  - `failed`: 失败
  - `cancelled`: 已取消
- `result` (可选): 执行结果
- `error_message` (可选): 错误信息

**响应示例**:
```json
{
  "success": true,
  "message": "Task status updated to done",
  "task_id": "my_task"
}
```

---

#### 5. 删除任务

```http
DELETE /api/v1/tasks/:task_id
```

**路径参数**:
- `task_id`: 任务 ID

**响应示例**:
```json
{
  "success": true,
  "message": "Task deleted",
  "task_id": "my_task"
}
```

**错误响应**:
```json
{
  "error": "Cannot delete task with dependents",
  "dependents": ["task_003", "task_004"]
}
```

---

#### 6. 获取统计信息

```http
GET /api/v1/stats
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total": 51,
    "by_status": {
      "pending": 10,
      "running": 2,
      "done": 37,
      "failed": 2
    },
    "ready_to_run": 5
  }
}
```

---

#### 7. 健康检查

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "database": "connected",
  "task_count": 51
}
```

---

### 调度器控制 API

#### 8. 获取调度器状态

```http
GET /api/v1/scheduler/status
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "running": true,
    "thread_alive": true,
    "workers": 4,
    "active_tasks": 2,
    "stats": {
      "tasks_started": 15,
      "tasks_completed": 13,
      "tasks_failed": 0,
      "tasks_retried": 2,
      "total_execution_time": 45.6
    }
  }
}
```

**字段说明**:
- `running`: 调度器是否运行
- `thread_alive`: 后台线程是否存活
- `workers`: Worker 池大小
- `active_tasks`: 当前活跃任务数
- `stats`: 统计信息

---

#### 9. 获取活跃任务

```http
GET /api/v1/scheduler/active
```

**响应示例**:
```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "task_id": "task_001",
      "title": "数据处理",
      "worker_id": "scheduler_12345_0",
      "start_time": "2026-03-15T00:01:00",
      "retry_count": 0
    }
  ]
}
```

---

#### 10. 启动调度器

```http
POST /api/v1/scheduler/start
Content-Type: application/json

{
  "max_workers": 4,
  "poll_interval": 1.0
}
```

**请求字段**:
- `max_workers` (可选): 最大并发 Worker 数（默认 4）
- `poll_interval` (可选): 轮询间隔秒数（默认 1.0）

**响应示例**:
```json
{
  "success": true,
  "message": "调度器已启动 (Workers=4, Poll=1.0s)"
}
```

**错误响应**:
```json
{
  "success": false,
  "error": "调度器已在运行中"
}
```

---

#### 11. 停止调度器

```http
POST /api/v1/scheduler/stop
Content-Type: application/json

{
  "wait": true
}
```

**请求字段**:
- `wait` (可选): 是否等待活跃任务完成（默认 true）

**响应示例**:
```json
{
  "success": true,
  "message": "调度器已停止"
}
```

---

## 使用示例

### 示例 1: 创建简单任务链

```bash
# 任务 1: 数据收集
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "collect_data",
    "title": "📥 数据收集",
    "priority": 1
  }'

# 任务 2: 数据处理（依赖任务 1）
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "process_data",
    "title": "⚙️ 数据处理",
    "priority": 2,
    "dependencies": ["collect_data"]
  }'

# 任务 3: 生成报告（依赖任务 2）
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "generate_report",
    "title": "📊 生成报告",
    "priority": 3,
    "dependencies": ["process_data"]
  }'
```

**执行流程**:
```
📥 数据收集 (priority=1)
      ↓
⚙️ 数据处理 (priority=2)
      ↓
📊 生成报告 (priority=3)
```

---

### 示例 2: 创建并行任务

```bash
# 基础任务
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "init",
    "title": "🚀 初始化",
    "priority": 1
  }'

# 并行任务 A
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_a",
    "title": "🅰️ 任务 A",
    "priority": 2,
    "dependencies": ["init"]
  }'

# 并行任务 B
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_b",
    "title": "🅱️ 任务 B",
    "priority": 2,
    "dependencies": ["init"]
  }'

# 并行任务 C
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_c",
    "title": "🇨️ 任务 C",
    "priority": 2,
    "dependencies": ["init"]
  }'

# 汇总任务（依赖所有并行任务）
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "finalize",
    "title": "🏁 汇总完成",
    "priority": 3,
    "dependencies": ["task_a", "task_b", "task_c"]
  }'
```

**执行流程**:
```
        🚀 初始化
           │
     ┌─────┼─────┐
     │     │     │
     ▼     ▼     ▼
   🅰️ A   🅱️ B   🇨️ C  (并行执行)
     │     │     │
     └─────┼─────┘
           │
           ▼
      🏁 汇总完成
```

---

### 示例 3: Python 脚本控制

```python
#!/usr/bin/env python3
"""
DAG 任务系统 - Python 客户端示例
"""

import requests
import time

BASE_URL = "http://127.0.0.1:9000"

def create_task(task_id, title, priority=5, dependencies=None):
    """创建任务"""
    url = f"{BASE_URL}/api/v1/tasks"
    data = {
        "task_id": task_id,
        "title": title,
        "priority": priority,
        "dependencies": dependencies or []
    }
    response = requests.post(url, json=data)
    return response.json()

def get_scheduler_status():
    """获取调度器状态"""
    url = f"{BASE_URL}/api/v1/scheduler/status"
    response = requests.get(url)
    return response.json()

def start_scheduler(workers=4):
    """启动调度器"""
    url = f"{BASE_URL}/api/v1/scheduler/start"
    data = {"max_workers": workers}
    response = requests.post(url, json=data)
    return response.json()

# 使用示例
if __name__ == "__main__":
    print("🚀 DAG 任务系统示例")
    print("=" * 60)
    
    # 1. 启动调度器
    print("\n1️⃣ 启动调度器...")
    result = start_scheduler(workers=2)
    print(f"   {result['message']}")
    
    # 2. 创建任务链
    print("\n2️⃣ 创建任务链...")
    create_task("step1", "第一步：数据收集", priority=1)
    create_task("step2", "第二步：数据处理", priority=2, dependencies=["step1"])
    create_task("step3", "第三步：生成报告", priority=3, dependencies=["step2"])
    
    # 3. 监控执行
    print("\n3️⃣ 监控执行...")
    for i in range(10):
        status = get_scheduler_status()
        data = status['data']
        
        print(f"   [{i+1}] 活跃任务：{data['active_tasks']}, "
              f"已完成：{data['stats']['tasks_completed']}")
        
        time.sleep(1)
    
    print("\n✅ 示例完成！")
```

---

## 核心算法

### 1. 循环依赖检测 (DFS)

**问题**: 防止 A → B → C → A 的死循环

**算法**: DFS + Recursion Stack

```python
def detect_cycle(graph):
    """
    检测 DAG 是否存在循环依赖
    
    graph: {task_id: [dependency_ids]}
    返回：(has_cycle, cycle_path)
    """
    visited = set()
    rec_stack = set()
    
    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        
        for dep in graph.get(node, []):
            if dep not in visited:
                cycle = dfs(dep, path + [dep])
                if cycle:
                    return cycle
            elif dep in rec_stack:
                # 发现循环！
                return path + [dep]
        
        rec_stack.remove(node)
        return None
    
    for node in graph:
        if node not in visited:
            cycle = dfs(node, [node])
            if cycle:
                return True, cycle
    
    return False, None
```

**时间复杂度**: O(V + E)  
**空间复杂度**: O(V)

---

### 2. 拓扑排序 (Kahn 算法)

**问题**: 确定任务的正确执行顺序

**算法**: 入度递减

```python
from collections import deque

def topological_sort(graph):
    """
    拓扑排序
    
    graph: {task_id: [dependency_ids]}
    返回：(sorted_list, error_message)
    """
    # 计算入度
    in_degree = {node: 0 for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[node] += 1
    
    # 入度=0 的节点加入队列
    queue = deque([n for n in in_degree if in_degree[n] == 0])
    result = []
    
    while queue:
        node = queue.popleft()
        result.append(node)
        
        # 减少依赖此节点的节点的入度
        for dependent in reverse_graph.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    if len(result) != len(graph):
        return None, "检测到循环依赖"
    
    return result, ""
```

**时间复杂度**: O(V + E)  
**空间复杂度**: O(V)

---

### 3. 带优先级的拓扑排序

**问题**: 在满足依赖的前提下，优先执行高优先级任务

**算法**: 层级 + 优先队列

```python
import heapq

def topological_sort_with_priority(tasks):
    """
    带优先级的拓扑排序
    
    排序规则:
    1. 满足依赖关系（拓扑序）
    2. 同层级按优先级排序
    3. 优先级相同按创建时间排序
    """
    # 1. 基础拓扑排序
    topo_order, error = topological_sort(graph)
    
    # 2. 计算层级
    levels = {}
    for task_id in topo_order:
        deps = graph[task_id]
        levels[task_id] = max(levels.get(dep, 0) for dep in deps) + 1
    
    # 3. 按层级分组
    level_groups = defaultdict(list)
    for task_id in topo_order:
        level_groups[levels[task_id]].append(task)
    
    # 4. 每组内按优先级排序（使用堆）
    result = []
    for level in sorted(level_groups.keys()):
        heap = [(t.priority, t.created_at, t) for t in level_groups[level]]
        heapq.heapify(heap)
        while heap:
            _, _, task = heapq.heappop(heap)
            result.append(task)
    
    return result, ""
```

---

### 4. 原子性任务抢占

**问题**: 防止多个 Worker 重复执行同一任务

**解决方案**: 数据库行级锁

```sql
UPDATE tasks
SET status = 'running',
    assigned_worker = 'worker_123',
    updated_at = NOW()
WHERE task_id = 'task_001' AND status = 'ready'
```

**关键点**:
- `WHERE status = 'ready'` 确保只有 ready 任务可被抢占
- 检查 `rowcount` 确认是否成功抢占
- rowcount=1 → 成功
- rowcount=0 → 被其他 Worker 抢走

---

## 故障排查

### 问题 1: 调度器无法启动

**症状**:
```json
{"success": false, "error": "DAGScheduler 未导入"}
```

**原因**: `dag_scheduler.py` 不存在或导入失败

**解决方案**:
```bash
# 1. 检查文件是否存在
ls -lh ~/.vectorbrain/dag/dag_scheduler.py

# 2. 测试导入
cd ~/.openclaw/workspace
python3 -c "from dag_scheduler import DAGScheduler"

# 3. 查看详细错误
python3 dag_api_server.py  # 前台运行看错误
```

---

### 问题 2: 任务永远处于 pending 状态

**症状**: 任务状态一直是 `pending`，不执行

**可能原因**:
1. 依赖任务未完成
2. 调度器未启动
3. 循环依赖

**排查步骤**:
```bash
# 1. 检查依赖
curl http://127.0.0.1:9000/api/v1/tasks/task_001 | jq '.data.dependencies'

# 2. 检查依赖任务状态
curl http://127.0.0.1:9000/api/v1/tasks/task_000 | jq '.data.status'

# 3. 检查调度器状态
curl http://127.0.0.1:9000/api/v1/scheduler/status

# 4. 检测循环依赖
curl http://127.0.0.1:9000/api/v1/stats | jq '.data.ready_to_run'
```

---

### 问题 3: 端口被占用

**症状**:
```
OSError: [Errno 48] Address already in use
```

**解决方案**:
```bash
# 1. 找到占用端口的进程
lsof -i :9000

# 2. 杀死旧进程
kill -9 <PID>

# 3. 重新启动
python3 dag_api_server.py &
```

---

### 问题 4: Dashboard 无法连接

**症状**: Dashboard 显示 "同步断开"

**解决方案**:
```bash
# 1. 检查 API 服务器
curl http://127.0.0.1:9000/health

# 2. 检查 Dashboard 配置
grep "API_URL" ~/.vectorbrain/dag/dag_dashboard.html

# 3. 应该是:
# const API_URL = "http://127.0.0.1:9000/api/v1/tasks";
```

---

## 最佳实践

### 1. 任务设计原则

✅ **推荐**:
- 任务粒度适中（5-30 分钟）
- 明确定义依赖关系
- 使用有意义的 task_id
- 设置合理优先级

❌ **避免**:
- 任务过大（>1 小时）
- 循环依赖
- 过深的依赖链（>10 层）
- 优先级全部相同

---

### 2. 并发配置

**推荐配置**:
```json
{
  "max_workers": 4,      // CPU 核心数
  "poll_interval": 1.0,  // 1 秒轮询
  "task_timeout": 30,    // 30 分钟超时
  "max_retries": 3       // 最多重试 3 次
}
```

**调整策略**:
- CPU 密集型任务：`workers = CPU 核心数`
- IO 密集型任务：`workers = CPU 核心数 × 2`
- 短任务：减小 `poll_interval` 到 0.5s
- 长任务：增加 `task_timeout` 到 60 分钟

---

### 3. 错误处理

**推荐模式**:
```python
try:
    # 执行任务
    result = execute_task()
    
    # 标记完成
    update_status(task_id, "done", result)
    
except TimeoutError:
    # 超时处理
    update_status(task_id, "failed", "任务超时")
    # 自动重试由调度器处理
    
except Exception as e:
    # 其他错误
    update_status(task_id, "failed", str(e))
    # 记录详细日志
    log_error(task_id, traceback.format_exc())
```

---

### 4. 监控告警

**关键指标**:
- 活跃任务数（突然增加/减少）
- 失败率（>10% 需要关注）
- 平均执行时间（异常增长）
- 队列堆积（ready 任务过多）

**告警阈值**:
```python
if failed_rate > 0.1:  # 失败率 > 10%
    send_alert("任务失败率过高")

if active_tasks == 0 and pending_tasks > 10:  # 队列堆积
    send_alert("调度器可能停止工作")

if avg_execution_time > baseline * 2:  # 执行时间翻倍
    send_alert("任务执行异常缓慢")
```

---

## 附录

### A. 任务状态机

```
                    ┌─────────┐
                    │ pending │
                    └────┬────┘
                         │ 所有依赖完成
                         ▼
                    ┌─────────┐
          调度器发现 │ ready   │
                         └────┬────┘
                              │ Worker 抢占
                              ▼
                         ┌─────────┐
                         │ running │
                         └────┬────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
         ┌────────┐     ┌────────┐     ┌──────────┐
         │  done  │     │ failed │     │cancelled │
         └────────┘     └─┬──────┘     └──────────┘
                          │
                          │ retry_count < max_retries
                          └──────────────┐
                                         ▼
                                    ┌─────────┐
                                    │ pending │ (重试)
                                    └─────────┘
```

---

### B. API 快速参考卡

```bash
# 健康检查
curl http://127.0.0.1:9000/health

# 获取任务列表
curl http://127.0.0.1:9000/api/v1/tasks

# 创建任务
curl -X POST http://127.0.0.1:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_id": "t1", "title": "任务 1", "priority": 5}'

# 启动调度器
curl -X POST http://127.0.0.1:9000/api/v1/scheduler/start \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 4}'

# 查看调度器状态
curl http://127.0.0.1:9000/api/v1/scheduler/status

# 停止调度器
curl -X POST http://127.0.0.1:9000/api/v1/scheduler/stop \
  -H "Content-Type: application/json" \
  -d '{"wait": true}'
```

---

### C. 故障诊断命令

```bash
# 检查进程
ps aux | grep dag_api_server

# 检查端口
lsof -i :9000

# 查看日志
tail -f /tmp/dag_api.log

# 数据库检查
sqlite3 ~/.vectorbrain/tasks/task_queue.db "SELECT COUNT(*) FROM tasks"

# 测试 API
curl http://127.0.0.1:9000/health | python3 -m json.tool
```

---

**文档结束**

---

**最后更新**: 2026-03-15  
**维护者**: [YOUR_AI_NAME] 🧠  
**GitHub**: liugedapiqiu-dev/[YOUR_INITIALS]longxia  
**反馈**: 欢迎提交 Issue 或 Pull Request
