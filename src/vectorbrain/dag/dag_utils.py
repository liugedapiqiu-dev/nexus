#!/usr/bin/env python3
"""
VectorBrain DAG 工具函数

提供 DAG 核心算法：
1. 循环依赖检测 (DFS)
2. 拓扑排序 (Kahn 算法)
3. 优先级队列构建
4. DAG 验证工具

作者：[YOUR_AI_NAME] 🧠
版本：v2.0
"""

import sqlite3
import json
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


# ==================== 数据结构 ====================

@dataclass
class Task:
    """任务数据类"""
    task_id: str
    title: str
    description: str
    priority: int
    status: str
    dependencies: List[str]
    dependents: List[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    assigned_worker: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Task':
        """从数据库行创建 Task 对象"""
        # 安全获取字段值（SQLite Row 不支持 .get()）
        def safe_get(row, field, default=None):
            try:
                return row[field] if row[field] is not None else default
            except (IndexError, KeyError):
                return default
        
        # 解析 JSON 字段
        deps_raw = safe_get(row, 'dependencies', '[]')
        deps_parsed = json.loads(deps_raw) if isinstance(deps_raw, str) else (deps_raw or [])
        
        dependents_raw = safe_get(row, 'dependents', '[]')
        dependents_parsed = json.loads(dependents_raw) if isinstance(dependents_raw, str) else (dependents_raw or [])
        
        return cls(
            task_id=row['task_id'],
            title=row['title'],
            description=safe_get(row, 'description', ''),
            priority=safe_get(row, 'priority', 5),
            status=row['status'],
            dependencies=deps_parsed,
            dependents=dependents_parsed,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            completed_at=safe_get(row, 'completed_at'),
            result=safe_get(row, 'result'),
            error_message=safe_get(row, 'error_message'),
            assigned_worker=safe_get(row, 'assigned_worker')
        )


class DAGError(Enum):
    """DAG 错误类型"""
    CYCLE_DETECTED = "检测到循环依赖"
    MISSING_DEPENDENCY = "依赖的任务不存在"
    SELF_DEPENDENCY = "任务不能依赖自己"
    INVALID_TOPOLOGY = "无效的拓扑结构"


# ==================== 循环依赖检测 ====================

def detect_cycle(graph: Dict[str, List[str]]) -> Tuple[bool, Optional[List[str]]]:
    """
    检测 DAG 是否存在循环依赖
    
    使用 DFS + recursion stack 算法
    
    参数:
        graph: 依赖图 {task_id: [dependency_ids]}
    
    返回:
        (has_cycle, cycle_path)
        - has_cycle: True 如果存在循环
        - cycle_path: 循环路径（如果存在），否则 None
    
    算法说明:
        1. 使用 visited 记录已访问节点
        2. 使用 rec_stack 记录当前递归路径
        3. 如果在 rec_stack 中遇到已访问节点 → 发现循环
        4. 回溯时从 rec_stack 移除节点
    
    时间复杂度: O(V + E)
    空间复杂度: O(V + E)
    """
    visited = set()
    rec_stack = set()
    parent_map = {}  # 记录路径用于回溯
    
    def dfs(node: str, path: List[str]) -> Optional[List[str]]:
        """
        DFS 遍历
        
        Args:
            node: 当前节点
            path: 当前路径
        
        Returns:
            循环路径（如果发现），否则 None
        """
        visited.add(node)
        rec_stack.add(node)
        
        # 遍历所有依赖
        for dep in graph.get(node, []):
            if dep not in visited:
                parent_map[dep] = node
                result = dfs(dep, path + [dep])
                if result:
                    return result
            elif dep in rec_stack:
                # 发现循环！回溯路径
                cycle_start = path.index(dep) if dep in path else len(path)
                cycle = path[cycle_start:] + [dep]
                return cycle
        
        # 回溯
        rec_stack.remove(node)
        return None
    
    # 遍历所有节点
    for node in graph:
        if node not in visited:
            result = dfs(node, [node])
            if result:
                return True, result
    
    return False, None


def would_create_cycle(
    task_id: str,
    new_dependencies: List[str],
    existing_graph: Dict[str, List[str]]
) -> Tuple[bool, Optional[List[str]]]:
    """
    检测添加新任务是否会形成循环
    
    参数:
        task_id: 新任务 ID
        new_dependencies: 新任务的依赖列表
        existing_graph: 现有的依赖图
    
    返回:
        (would_cycle, cycle_path)
    
    实现逻辑:
        1. 临时添加新任务到图
        2. 运行 cycle detection
        3. 如果检测到循环 → 拒绝添加
    """
    # 创建临时图
    temp_graph = existing_graph.copy()
    temp_graph[task_id] = new_dependencies
    
    # 检测循环
    has_cycle, cycle_path = detect_cycle(temp_graph)
    
    if has_cycle:
        return True, cycle_path
    
    return False, None


# ==================== 拓扑排序 ====================

def topological_sort(graph: Dict[str, List[str]]) -> Tuple[Optional[List[str]], str]:
    """
    使用 Kahn 算法进行拓扑排序
    
    参数:
        graph: 依赖图 {task_id: [dependency_ids]}
               注意：这里的 dependency 是指该任务依赖谁
    
    返回:
        (sorted_list, error_message)
        - sorted_list: 拓扑排序结果（从根到叶）
        - error_message: 错误信息（如果有）
    
    算法说明:
        1. 计算每个节点的入度（被多少任务依赖）
        2. 将所有入度=0 的节点加入队列
        3. 弹出节点，减少它依赖的节点的入度
        4. 新入度=0 的节点加入队列
        5. 重复直到队列为空
    
    时间复杂度: O(V + E)
    空间复杂度: O(V)
    """
    from collections import deque
    
    # 计算入度（注意：我们的图是正向依赖）
    # 如果 A 依赖 B，那么 B 的出度+1，A 的入度+1
    in_degree = {node: 0 for node in graph}
    
    # 构建反向图：谁被谁依赖
    reverse_graph = {node: [] for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in reverse_graph:
                reverse_graph[dep].append(node)
    
    # 计算入度
    for node in graph:
        for dep in graph[node]:
            if dep in in_degree:
                in_degree[node] += 1
    
    # 初始化队列（入度=0 的节点）
    queue = deque([node for node in graph if in_degree[node] == 0])
    
    # 拓扑排序
    result = []
    
    while queue:
        node = queue.popleft()
        result.append(node)
        
        # 减少依赖此节点的节点的入度
        for dependent in reverse_graph.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    # 检查是否所有节点都被处理
    if len(result) != len(graph):
        # 存在循环，找出未处理的节点
        remaining = set(graph.keys()) - set(result)
        return None, f"检测到循环依赖，未处理节点：{remaining}"
    
    return result, ""


def topological_sort_with_priority(
    tasks: List[Task]
) -> Tuple[List[Task], str]:
    """
    带优先级的拓扑排序
    
    参数:
        tasks: 任务列表
    
    返回:
        (sorted_tasks, error_message)
    
    排序规则:
        1. 必须满足依赖关系（拓扑序）
        2. 同级别中，优先级高的先执行（priority 数字小的优先）
        3. 优先级相同，创建时间早的先执行
    
    实现:
        使用最小堆 (priority, created_at, task)
    """
    import heapq
    
    # 构建图
    graph = {t.task_id: t.dependencies for t in tasks}
    task_map = {t.task_id: t for t in tasks}
    
    # 先进行基础拓扑排序
    topo_order, error = topological_sort(graph)
    
    if error:
        return [], error
    
    # 计算每个任务的层级（距离根节点的距离）
    levels = {}
    for task_id in topo_order:
        deps = graph[task_id]
        if not deps:
            levels[task_id] = 0
        else:
            levels[task_id] = max(levels.get(dep, 0) for dep in deps) + 1
    
    # 按层级分组
    from collections import defaultdict
    level_groups = defaultdict(list)
    for task_id in topo_order:
        level_groups[levels[task_id]].append(task_map[task_id])
    
    # 每组内按优先级排序
    result = []
    for level in sorted(level_groups.keys()):
        group = level_groups[level]
        # 使用堆排序：(priority, created_at, index, task)
        # 添加 index 作为最后的比较项，避免比较 Task 对象
        heap = []
        for idx, t in enumerate(group):
            try:
                priority = int(t.priority) if t.priority is not None else 5
            except (ValueError, TypeError):
                priority = 5
            heap.append((priority, t.created_at, idx, t))
        heapq.heapify(heap)
        
        while heap:
            _, _, _, task = heapq.heappop(heap)
            result.append(task)
    
    return result, ""


# ==================== DAG 验证工具 ====================

def validate_dag(tasks: List[Task]) -> Tuple[bool, List[str]]:
    """
    验证 DAG 的完整性
    
    参数:
        tasks: 任务列表
    
    返回:
        (is_valid, errors)
    
    检查项:
        1. 循环依赖
        2. 依赖的任务是否存在
        3. 自依赖
        4. 状态一致性
    """
    errors = []
    task_ids = {t.task_id for t in tasks}
    graph = {t.task_id: t.dependencies for t in tasks}
    
    # 1. 检查循环依赖
    has_cycle, cycle_path = detect_cycle(graph)
    if has_cycle:
        errors.append(f"{DAGError.CYCLE_DETECTED.value}: {' → '.join(cycle_path)}")
    
    # 2. 检查依赖是否存在
    for task in tasks:
        for dep in task.dependencies:
            if dep not in task_ids:
                errors.append(f"{DAGError.MISSING_DEPENDENCY.value}: "
                            f"任务 {task.task_id} 依赖不存在的任务 {dep}")
    
    # 3. 检查自依赖
    for task in tasks:
        if task.task_id in task.dependencies:
            errors.append(f"{DAGError.SELF_DEPENDENCY.value}: {task.task_id}")
    
    # 4. 检查状态一致性
    for task in tasks:
        if task.status == 'done' or task.status == 'failed':
            if not task.completed_at:
                errors.append(f"任务 {task.task_id} 状态为 {task.status} "
                            f"但没有 completed_at 时间戳")
    
    return len(errors) == 0, errors


def get_ready_tasks(tasks: List[Task]) -> List[Task]:
    """
    获取所有 ready 状态的任务
    
    ready 条件:
        1. 状态为 pending
        2. 所有依赖都已完成 (done)
    
    参数:
        tasks: 任务列表
    
    返回:
        ready 任务列表
    """
    task_map = {t.task_id: t for t in tasks}
    ready = []
    
    for task in tasks:
        if task.status != 'pending':
            continue
        
        # 检查所有依赖是否完成
        all_deps_done = True
        for dep_id in task.dependencies:
            dep_task = task_map.get(dep_id)
            if not dep_task or dep_task.status != 'done':
                all_deps_done = False
                break
        
        if all_deps_done:
            ready.append(task)
    
    return ready


# ==================== 数据库操作工具 ====================

def load_all_tasks(db_path: str) -> List[Task]:
    """
    从数据库加载所有任务
    
    参数:
        db_path: SQLite 数据库路径
    
    返回:
        Task 对象列表
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM tasks ORDER BY priority ASC, created_at ASC
    """)
    
    tasks = [Task.from_row(row) for row in cursor.fetchall()]
    conn.close()
    
    return tasks


def load_task_graph(db_path: str) -> Dict[str, List[str]]:
    """
    从数据库加载依赖图
    
    参数:
        db_path: SQLite 数据库路径
    
    返回:
        {task_id: [dependency_ids]}
    """
    tasks = load_all_tasks(db_path)
    return {t.task_id: t.dependencies for t in tasks}


# ==================== 测试函数 ====================

def run_tests():
    """运行单元测试"""
    print("🧪 运行 DAG 工具函数测试...")
    print("=" * 60)
    
    # 测试 1: 无循环图
    print("\n测试 1: 无循环图检测")
    graph1 = {
        'A': [],
        'B': ['A'],
        'C': ['A'],
        'D': ['B', 'C']
    }
    has_cycle, cycle = detect_cycle(graph1)
    assert not has_cycle, "应该没有循环"
    print("✅ 通过：正确检测无循环图")
    
    # 测试 2: 有循环图
    print("\n测试 2: 有循环图检测")
    graph2 = {
        'A': ['C'],
        'B': ['A'],
        'C': ['B']
    }
    has_cycle, cycle = detect_cycle(graph2)
    assert has_cycle, "应该有循环"
    print(f"✅ 通过：检测到循环 {cycle}")
    
    # 测试 3: 拓扑排序
    print("\n测试 3: 拓扑排序")
    graph3 = {
        'A': [],
        'B': ['A'],
        'C': ['A'],
        'D': ['B', 'C']
    }
    order, error = topological_sort(graph3)
    assert order, f"排序失败：{error}"
    # 验证顺序：A 必须在 B、C 之前，B、C 必须在 D 之前
    assert order.index('A') < order.index('B')
    assert order.index('A') < order.index('C')
    assert order.index('B') < order.index('D')
    assert order.index('C') < order.index('D')
    print(f"✅ 通过：拓扑排序 {order}")
    
    # 测试 4: 优先级排序
    print("\n测试 4: 带优先级的拓扑排序")
    tasks = [
        Task('A', '任务 A', '', 5, 'pending', [], [], '2026-01-01', ''),
        Task('B', '任务 B', '', 3, 'pending', ['A'], [], '2026-01-01', ''),
        Task('C', '任务 C', '', 1, 'pending', ['A'], [], '2026-01-01', ''),
    ]
    sorted_tasks, error = topological_sort_with_priority(tasks)
    assert sorted_tasks, f"排序失败：{error}"
    # A 必须第一，C 优先级高应该在前
    assert sorted_tasks[0].task_id == 'A'
    assert sorted_tasks[1].task_id == 'C'  # priority=1
    assert sorted_tasks[2].task_id == 'B'  # priority=3
    print(f"✅ 通过：优先级排序 {[t.task_id for t in sorted_tasks]}")
    
    # 测试 5: DAG 验证
    print("\n测试 5: DAG 验证")
    is_valid, errors = validate_dag(tasks)
    assert is_valid, f"验证失败：{errors}"
    print("✅ 通过：DAG 验证")
    
    # 测试 6: 获取 ready 任务
    print("\n测试 6: 获取 ready 任务")
    tasks_mixed = [
        Task('A', '任务 A', '', 5, 'done', [], [], '2026-01-01', ''),
        Task('B', '任务 B', '', 3, 'pending', ['A'], [], '2026-01-01', ''),
        Task('C', '任务 C', '', 1, 'pending', ['A'], [], '2026-01-01', ''),
        Task('D', '任务 D', '', 1, 'pending', ['B'], [], '2026-01-01', ''),
    ]
    ready = get_ready_tasks(tasks_mixed)
    assert len(ready) == 2
    assert {t.task_id for t in ready} == {'B', 'C'}
    print(f"✅ 通过：ready 任务 {[t.task_id for t in ready]}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


# ==================== 主函数 ====================

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        run_tests()
    else:
        print("VectorBrain DAG 工具函数库 v2.0")
        print("使用方法：")
        print("  python3 dag_utils.py --test    运行测试")
        print("  from dag_utils import *        导入使用")
        print("")
        print("主要函数：")
        print("  detect_cycle(graph)                  - 检测循环依赖")
        print("  would_create_cycle(task_id, deps, graph) - 检测是否形成循环")
        print("  topological_sort(graph)              - 拓扑排序")
        print("  topological_sort_with_priority(tasks) - 带优先级排序")
        print("  validate_dag(tasks)                  - DAG 验证")
        print("  get_ready_tasks(tasks)               - 获取 ready 任务")
        print("  load_all_tasks(db_path)              - 加载所有任务")
