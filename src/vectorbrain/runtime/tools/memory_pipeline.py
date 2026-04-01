#!/usr/bin/env python3
"""
Layer: runtime
Status: secondary
Boundary: controlled Runtime -> Memory bridge. This file is a cross-layer writer and should not redefine memory truth.
Architecture refs:
- architecture/layer-manifest.md
- architecture/runtime-boundary-rules.md

VectorBrain Memory Pipeline - Stage 5

将执行结果自动写入记忆系统
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import sqlite3

# 添加 VectorBrain 到路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from runtime.tools.executor import ExecutionResult, Plan


# ============================================================================
# Memory Pipeline 类
# ============================================================================

class MemoryPipeline:
    """
    记忆流水线
    
    将执行结果处理并写入记忆系统
    """
    
    def __init__(self, memory_dir: str = None):
        """
        初始化记忆流水线
        
        Args:
            memory_dir: 记忆数据库目录
        """
        self.memory_dir = Path(memory_dir) if memory_dir else Path.home() / ".vectorbrain" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self.knowledge_db = self.memory_dir / "knowledge_memory.db"
        self.episodic_db = self.memory_dir / "episodic_memory.db"
        
        self._init_databases()
    
    def _init_databases(self):
        """初始化数据库"""
        # 知识记忆数据库
        conn = sqlite3.connect(str(self.knowledge_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source_task TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_category_key ON knowledge(category, key)")
        conn.commit()
        conn.close()
        
        # 情景记忆数据库
        conn = sqlite3.connect(str(self.episodic_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task ON episodes(task_id)")
        conn.commit()
        conn.close()
        
        print(f"[Memory] Databases initialized")
    
    def process(self, task_id: str, plan: Plan, result: ExecutionResult):
        """
        处理执行结果并写入记忆
        
        Args:
            task_id: 任务 ID
            plan: 执行计划
            result: 执行结果
        """
        print(f"\n{'='*60}")
        print(f"Processing Memory: {task_id}")
        print(f"{'='*60}\n")
        
        # 1. 写入情景记忆（执行历史）
        self._save_episodic_memory(task_id, plan, result)
        
        # 2. 提取知识并写入知识记忆
        self._extract_and_save_knowledge(task_id, plan, result)
        
        print(f"\nMemory processing completed\n")
    
    def _save_episodic_memory(self, task_id: str, plan: Plan, result: ExecutionResult):
        """
        保存情景记忆（执行历史）
        
        Args:
            task_id: 任务 ID
            plan: 执行计划
            result: 执行结果
        """
        conn = sqlite3.connect(str(self.episodic_db))
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        # 保存任务执行记录
        cursor.execute("""
            INSERT INTO episodes (timestamp, task_id, event_type, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            task_id,
            "task_executed",
            f"Task {task_id} executed with {len(plan.steps)} steps",
            json.dumps({
                "success": result.success,
                "steps": len(plan.steps),
                "step_results": [
                    {
                        "tool": r.get("tool"),
                        "success": r.get("success")
                    }
                    for r in result.step_results
                ]
            }, ensure_ascii=False)
        ))
        
        # 保存每个步骤的执行记录
        for i, step_result in enumerate(result.step_results):
            cursor.execute("""
                INSERT INTO episodes (timestamp, task_id, event_type, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                timestamp,
                task_id,
                "step_executed",
                f"Step {i+1}: {step_result.get('tool')} - {'Success' if step_result.get('success') else 'Failed'}",
                json.dumps(step_result, ensure_ascii=False)
            ))
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ Episodic memory saved ({len(result.step_results) + 1} records)")
    
    def _extract_and_save_knowledge(self, task_id: str, plan: Plan, result: ExecutionResult):
        """
        提取知识并保存
        
        Args:
            task_id: 任务 ID
            plan: 执行计划
            result: 执行结果
        """
        knowledge_entries = []
        
        # 从执行结果中提取知识
        for i, step_result in enumerate(result.step_results):
            tool_name = step_result.get("tool")
            step_data = step_result.get("result", {})
            
            if step_data.get("success"):
                # 根据工具类型提取知识
                if tool_name == "web_search":
                    knowledge = self._extract_search_knowledge(task_id, step_data)
                    if knowledge:
                        knowledge_entries.append(knowledge)
                
                elif tool_name == "web_fetch":
                    knowledge = self._extract_fetch_knowledge(task_id, step_data)
                    if knowledge:
                        knowledge_entries.append(knowledge)
                
                elif tool_name == "read_file":
                    knowledge = self._extract_file_knowledge(task_id, step_data, "read")
                    if knowledge:
                        knowledge_entries.append(knowledge)
                
                elif tool_name == "write_file":
                    knowledge = self._extract_file_knowledge(task_id, step_data, "write")
                    if knowledge:
                        knowledge_entries.append(knowledge)
        
        # 保存知识
        for knowledge in knowledge_entries:
            self._save_knowledge_entry(knowledge)
        
        print(f"  ✅ Knowledge extracted: {len(knowledge_entries)} entries")
    
    def _extract_search_knowledge(self, task_id: str, step_data: Dict) -> Optional[Dict]:
        """从搜索结果提取知识"""
        data = step_data.get("data", {})
        query = data.get("query", task_id)
        results = data.get("results", [])
        
        if results:
            return {
                "category": "search_result",
                "key": f"search_{task_id}_{datetime.now().strftime('%Y%m%d')}",
                "value": json.dumps({
                    "query": query,
                    "results_count": len(results),
                    "top_result": results[0] if results else None
                }, ensure_ascii=False),
                "source_task": task_id,
                "confidence": 0.9
            }
        
        return None
    
    def _extract_fetch_knowledge(self, task_id: str, step_data: Dict) -> Optional[Dict]:
        """从抓取结果提取知识"""
        data = step_data.get("data", {})
        url = data.get("url", "")
        content = data.get("content", "")
        
        if url and content:
            return {
                "category": "web_content",
                "key": f"url_{url.replace('/', '_')}",
                "value": json.dumps({
                    "url": url,
                    "content_preview": content[:500] if len(content) > 500 else content,
                    "content_length": len(content)
                }, ensure_ascii=False),
                "source_task": task_id,
                "confidence": 0.8
            }
        
        return None
    
    def _extract_file_knowledge(self, task_id: str, step_data: Dict, operation: str) -> Optional[Dict]:
        """从文件操作提取知识"""
        data = step_data.get("data", {})
        path = data.get("path", "")
        
        if path:
            return {
                "category": "file_operation",
                "key": f"{operation}_{path.replace('/', '_')}",
                "value": json.dumps({
                    "path": path,
                    "operation": operation,
                    "task_id": task_id
                }, ensure_ascii=False),
                "source_task": task_id,
                "confidence": 1.0
            }
        
        return None
    
    def _save_knowledge_entry(self, knowledge: Dict):
        """
        保存知识条目
        
        Args:
            knowledge: 知识字典
        """
        conn = sqlite3.connect(str(self.knowledge_db))
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge 
                (category, key, value, source_task, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                knowledge["category"],
                knowledge["key"],
                knowledge["value"],
                knowledge["source_task"],
                knowledge["confidence"]
            ))
            
            conn.commit()
            print(f"    Saved: {knowledge['category']} - {knowledge['key']}")
        except Exception as e:
            print(f"    ⚠️ Failed to save knowledge: {e}")
        finally:
            conn.close()
    
    def query_knowledge(self, category: str = None, key: str = None, limit: int = 10) -> List[Dict]:
        """
        查询知识记忆
        
        Args:
            category: 分类
            key: 键名
            limit: 限制数量
            
        Returns:
            知识列表
        """
        conn = sqlite3.connect(str(self.knowledge_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM knowledge"
        params = []
        
        conditions = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if key:
            conditions.append("key = ?")
            params.append(key)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        conn.close()
        
        return results
    
    def get_stats(self) -> Dict:
        """获取记忆统计"""
        conn = sqlite3.connect(str(self.knowledge_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        knowledge_count = cursor.fetchone()[0]
        conn.close()
        
        conn = sqlite3.connect(str(self.episodic_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM episodes")
        episodic_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "knowledge_entries": knowledge_count,
            "episodic_entries": episodic_count
        }


# ============================================================================
# 全局记忆流水线实例
# ============================================================================

memory_pipeline = MemoryPipeline()


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    from runtime.tools.executor import Plan, PlanStep, ExecutionResult
    
    # 创建测试数据
    plan = Plan(
        task_id="test_memory_001",
        steps=[
            PlanStep(tool="web_search", input={"query": "test"}),
            PlanStep(tool="write_file", input={"path": "~/test.txt", "content": "test content"})
        ]
    )
    
    result = ExecutionResult(
        success=True,
        step_results=[
            {
                "step": 0,
                "tool": "web_search",
                "result": {
                    "success": True,
                    "data": {
                        "query": "test",
                        "results": [{"title": "Test Result", "url": "https://example.com"}]
                    }
                },
                "success": True
            },
            {
                "step": 1,
                "tool": "write_file",
                "result": {
                    "success": True,
                    "data": {"path": "~/test.txt", "bytes": 12}
                },
                "success": True
            }
        ]
    )
    
    # 处理记忆
    memory_pipeline.process("test_memory_001", plan, result)
    
    # 查询统计
    stats = memory_pipeline.get_stats()
    print(f"\nMemory Stats: {stats}")
    
    # 查询知识
    knowledge = memory_pipeline.query_knowledge(limit=5)
    print(f"\nRecent Knowledge: {len(knowledge)} entries")
    
    print("\n✅ Memory Pipeline 测试完成！")
