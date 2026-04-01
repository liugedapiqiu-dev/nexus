#!/usr/bin/env python3
"""
VectorBrain 向量检索模块

功能：
接收一句话 → 转成向量 → 跟数据库里的所有向量比对相似度 → 返回最相关的 Top-K

用法：
# 作为模块导入
from vector_search import search_memory
results = search_memory("上次那个备份的事", top_k=3)

# 直接运行测试
python3 ~/.vectorbrain/connector/vector_search.py
"""

import sqlite3
import json
import numpy as np
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Optional

# faiss 是可选依赖：在某些 Python/macOS 环境（如 Python 3.14 / arm64）可能没有可用 wheel。
# 支持从独立虚拟环境注入 site-packages（避免污染系统 Python）。
FAISS_VENV = Path.home() / '.vectorbrain' / '.venv-faiss'
faiss_site_candidates = [
    FAISS_VENV / 'lib' / 'python3.14' / 'site-packages',
    FAISS_VENV / 'lib' / 'python3.13' / 'site-packages',
    FAISS_VENV / 'lib' / 'python3.12' / 'site-packages',
    FAISS_VENV / 'lib' / 'python3.11' / 'site-packages',
]
for candidate in faiss_site_candidates:
    if candidate.exists() and str(candidate) not in os.sys.path:
        os.sys.path.insert(0, str(candidate))
        break

try:
    import faiss  # type: ignore
except Exception:  # ImportError 或动态库加载失败等
    faiss = None
    print("⚠️ faiss 不可用，将自动降级为 SQLite 文本检索（无向量索引）")

# VectorBrain 路径
VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
KNOWLEDGE_DB = VECTORBRAIN_ROOT / 'memory' / 'knowledge_memory.db'
INDEX_PATH = VECTORBRAIN_ROOT / 'memory' / 'knowledge.index'
INFORMATION_DB = VECTORBRAIN_ROOT / 'memory' / 'information_memory.db'
HABIT_DB = VECTORBRAIN_ROOT / 'memory' / 'habit_memory.db'


def _get_knowledge_columns(db_path: str) -> set:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(knowledge)")
    cols = {row[1] for row in cursor.fetchall()}
    conn.close()
    return cols

# 全局加载 FAISS 索引到内存（常驻内存，毫秒级检索）
# faiss 不可用时自动降级
memory_index = None
SEARCH_BACKEND = "sqlite_fallback"
if faiss is not None:
    try:
        memory_index = faiss.read_index(str(INDEX_PATH))
        SEARCH_BACKEND = "faiss"
        print(f"✅ 启动自检：当前检索后端 = FAISS（索引已加载）")
        print(f"   索引路径：{INDEX_PATH}")
    except Exception as e:
        print(f"⚠️ 启动自检：当前检索后端 = SQLite fallback（FAISS 索引加载失败）")
        print(f"   原因：{e}")
        print("   如需重建索引：python3 ~/.vectorbrain/connector/faiss_manager.py")
else:
    print("⚠️ 启动自检：当前检索后端 = SQLite fallback（faiss 模块不可用）")
    print(f"   期望虚拟环境：{FAISS_VENV}")

def get_ollama_embedding(text: str) -> np.ndarray:
    """
    调用 Ollama 生成文本向量（使用 bge-m3 多语言模型）
    
    Args:
        text: 输入文本
        
    Returns:
        numpy 向量数组
    """
    try:
        result = subprocess.run(
            ['ollama', 'run', 'bge-m3', text],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            vector = json.loads(result.stdout.strip())
            return np.array(vector)
        else:
            raise Exception(f"ollama run 失败：{result.stderr[:100]}")
            
    except subprocess.TimeoutExpired:
        raise Exception("Ollama 请求超时")

def _fallback_sql_text_search(query: str, db_path: str, top_k: int = 3) -> List[Dict]:
    """当 faiss 不可用时的降级检索：兼容新旧 knowledge schema。"""
    q = query.strip()
    if not q:
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cols = _get_knowledge_columns(db_path)
    tokens = [tok for tok in q.split() if tok]
    like_query = f"%{q}%"

    results = []

    # 新 schema: id, content, metadata, source, importance, created_at
    if {'content', 'metadata', 'source'}.issubset(cols):
        token_conditions = " + ".join(["CASE WHEN content LIKE ? THEN 1 ELSE 0 END" for _ in tokens]) or "0"
        sql = f"""
            SELECT id, content, metadata, source, importance, created_at,
                   CASE WHEN content LIKE ? THEN 10 ELSE 0 END + ({token_conditions}) AS rank
            FROM knowledge
            WHERE content LIKE ?
               OR metadata LIKE ?
               OR source LIKE ?
               {''.join([' OR content LIKE ?' for _ in tokens])}
            ORDER BY rank DESC, importance DESC, created_at DESC
            LIMIT ?
        """
        params = [like_query]
        params.extend([f"%{tok}%" for tok in tokens])
        params.extend([like_query, like_query, like_query])
        params.extend([f"%{tok}%" for tok in tokens])
        params.append(top_k)
        cursor.execute(sql, params)

        for row in cursor.fetchall():
            _id, content, metadata, source, importance, created_at, rank = row
            score = min(0.95, 0.35 + 0.08 * float(rank or 0))
            label = source or "knowledge"
            results.append({
                "id": int(_id),
                "category": "knowledge",
                "key": label,
                "value": (content[:200] + "...") if len(content) > 200 else content,
                "score": float(score),
                "mode": "sql_like",
                "metadata": metadata,
                "created_at": created_at,
                "importance": importance,
            })

    # 旧 schema: id, category, key, value, source_worker, confidence, created_at, updated_at, embedding_vector
    elif {'category', 'key', 'value'}.issubset(cols):
        token_conditions = " + ".join(["CASE WHEN value LIKE ? THEN 1 ELSE 0 END" for _ in tokens]) or "0"
        sql = f"""
            SELECT id, category, key, value, source_worker, confidence, created_at, updated_at,
                   CASE WHEN value LIKE ? OR key LIKE ? THEN 10 ELSE 0 END + ({token_conditions}) AS rank
            FROM knowledge
            WHERE value LIKE ?
               OR key LIKE ?
               OR category LIKE ?
               {''.join([' OR value LIKE ? OR key LIKE ?' for _ in tokens])}
            ORDER BY rank DESC, confidence DESC, updated_at DESC, created_at DESC
            LIMIT ?
        """
        params = [like_query, like_query]
        params.extend([f"%{tok}%" for tok in tokens])
        params.extend([like_query, like_query, like_query])
        for tok in tokens:
            params.extend([f"%{tok}%", f"%{tok}%"])
        params.append(top_k)
        cursor.execute(sql, params)

        for row in cursor.fetchall():
            _id, category, key, value, source_worker, confidence, created_at, updated_at, rank = row
            score = min(0.95, 0.35 + 0.08 * float(rank or 0))
            results.append({
                "id": int(_id),
                "category": category or "knowledge",
                "key": key or (source_worker or 'knowledge'),
                "value": (value[:200] + "...") if len(value) > 200 else value,
                "score": float(score),
                "mode": "sql_like",
                "metadata": source_worker,
                "created_at": created_at,
                "importance": confidence,
            })

    conn.close()
    return results


def search_memory(
    query: str,
    db_path: str = str(KNOWLEDGE_DB),
    top_k: int = 3,
    min_score: float = 0.0
) -> List[Dict]:
    """检索 VectorBrain 记忆。

    优先：FAISS 向量检索（需要 faiss + index）
    降级：SQLite 文本 LIKE 检索（不依赖 faiss）
    """

    # ---- Fallback: faiss 不可用 或 index 未就绪 ----
    if faiss is None or memory_index is None:
        mode = "no_faiss" if faiss is None else "no_index"
        print(f"⚠️  向量检索不可用（{mode}），使用 SQLite 文本检索：'{query}'\n")
        results = _fallback_sql_text_search(query=query, db_path=db_path, top_k=top_k)

        print("=" * 70)
        print(f"📊 检索完成（fallback sql_like）！返回 Top-{len(results)} 结果")
        print("=" * 70)
        for i, res in enumerate(results, 1):
            print()
            print(f"[{i}] 匹配度：{res['score']:.4f} | 标签：{res['category']} / {res['key']}")
            print(f"    内容预览：{res['value'][:100]}...")
        print()
        return results

    # ---- FAISS 向量检索路径 ----
    print(f"⚡ 启动 FAISS 极速检索：'{query}'\n")

    # 1. 生成查询向量
    print("步骤 1: 生成查询向量...")
    query_vector = get_ollama_embedding(query)
    print(f"✅ 查询向量维度：{len(query_vector)}")
    print()

    # 2. 转换矩阵并归一化
    q_vec = np.array([query_vector], dtype=np.float32)
    faiss.normalize_L2(q_vec)

    # 3. FAISS 底层 C++ 检索 (毫秒级)
    print("步骤 2: FAISS 极速检索...")
    scores, ids = memory_index.search(q_vec, top_k)
    print(f"✅ FAISS 检索完成")
    print()

    # 4. 根据命中的 ID 反查 SQLite 提取文本
    print("步骤 3: 从 SQLite 提取文本内容...")
    results = []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cols = _get_knowledge_columns(db_path)

    for i in range(top_k):
        record_id = int(ids[0][i])
        score = float(scores[0][i])

        if record_id == -1 or score < min_score:
            continue

        if {'content', 'metadata', 'source'}.issubset(cols):
            cursor.execute("SELECT id, content, metadata, source, importance, created_at FROM knowledge WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                _id, content, metadata, source, importance, created_at = row
                results.append({
                    "id": int(_id),
                    "category": "knowledge",
                    "key": source or "knowledge",
                    "value": content[:200] + "..." if len(content) > 200 else content,
                    "score": score,
                    "mode": "faiss",
                    "metadata": metadata,
                    "created_at": created_at,
                    "importance": importance,
                })
        elif {'category', 'key', 'value'}.issubset(cols):
            cursor.execute("SELECT id, category, key, value, source_worker, confidence, created_at, updated_at FROM knowledge WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                _id, category, key, value, source_worker, confidence, created_at, updated_at = row
                results.append({
                    "id": int(_id),
                    "category": category or "knowledge",
                    "key": key or (source_worker or 'knowledge'),
                    "value": value[:200] + "..." if len(value) > 200 else value,
                    "score": score,
                    "mode": "faiss",
                    "metadata": source_worker,
                    "created_at": created_at,
                    "importance": confidence,
                })

    conn.close()
    print(f"✅ 提取完成")
    print()

    # 输出结果
    print("=" * 70)
    print(f"📊 检索完成！返回 Top-{len(results)} 结果")
    print("=" * 70)

    for i, res in enumerate(results, 1):
        print()
        print(f"[{i}] 匹配度：{res['score']:.4f} | 标签：{res['category']} / {res['key']}")
        print(f"    内容预览：{res['value'][:100]}...")

    print()

    return results

def search_information_memory(query: str, top_k: int = 3, min_score: float = 0.0) -> List[Dict]:
    """信息记忆检索：和知识记忆走相同 SQLite schema / 相同搜索链路。"""
    if not INFORMATION_DB.exists():
        return []
    results = _fallback_sql_text_search(query=query, db_path=str(INFORMATION_DB), top_k=top_k)
    for item in results:
        item['memory_type'] = 'information'
        if item.get('category') == 'knowledge':
            item['category'] = 'information'
    return results


def search_habit_memory(query: str, top_k: int = 3, min_score: float = 0.0) -> List[Dict]:
    """习惯记忆检索：独立 habit_memory.db，先走 SQLite schema 兼容链路。"""
    if not HABIT_DB.exists():
        return []
    results = _fallback_sql_text_search(query=query, db_path=str(HABIT_DB), top_k=max(top_k, 8))
    for item in results:
        item['memory_type'] = 'habit'
        item['category'] = item.get('category') or 'habit'
    return results

def search_global_memory(query: str, top_k: int = 5) -> List[Dict]:
    """全局主脑检索：知识记忆 + 习惯记忆 + 信息记忆，统一走主链路。"""
    results = []
    seen = set()
    info_priority_keywords = [
        '采购', '下单', '订单', '合同', '供应商', '验厂', '质检', '核价', '报价', '纸箱',
        '产品', '资金申请', '付款', '交期', '物料', '彩盒', '手提袋', '毛巾'
    ]
    habit_priority_keywords = [
        '习惯', '偏好', '风格', '口径', '怎么填', '表格习惯', '填写习惯', '填写', '常用', '喜欢', '记得我怎么'
    ]
    prioritize_info = any(k in query for k in info_priority_keywords)
    prioritize_habit = any(k in query for k in habit_priority_keywords)

    knowledge_results = search_memory(query=query, db_path=str(KNOWLEDGE_DB), top_k=top_k)
    for item in knowledge_results:
        item['memory_type'] = item.get('memory_type', 'knowledge')
        bonus = 0.0 if prioritize_info else 0.08
        if prioritize_habit:
            bonus += 0.05
        item['_rank_score'] = item.get('score', 0) + bonus
        key = (item.get('memory_type'), item.get('id'), item.get('key'))
        if key not in seen:
            seen.add(key)
            results.append(item)

    habit_results = search_habit_memory(query=query, top_k=top_k)
    for item in habit_results:
        bonus = 0.55 if prioritize_habit else 0.12
        extra = 0.0
        joined = f"{item.get('category','')} {item.get('key','')} {item.get('value','')}"
        if prioritize_habit and any(tok in joined for tok in ['habit', '习惯', '偏好', '填写', '口径', '风格']):
            extra += 0.35
        if prioritize_habit and any(tok in joined for tok in ['表格', '采购', '下单', '任务明细']):
            extra += 0.20
        item['_rank_score'] = item.get('score', 0) + bonus + extra
        key = (item.get('memory_type'), item.get('id'), item.get('key'))
        if key not in seen:
            seen.add(key)
            results.append(item)

    info_results = search_information_memory(query=query, top_k=top_k)
    for item in info_results:
        bonus = 0.22 if prioritize_info else 0.02
        item['_rank_score'] = item.get('score', 0) + bonus
        key = (item.get('memory_type'), item.get('id'), item.get('key'))
        if key not in seen:
            seen.add(key)
            results.append(item)

    results.sort(key=lambda x: x.get('_rank_score', x.get('score', 0)), reverse=True)
    for item in results:
        item.pop('_rank_score', None)
    return results[:top_k]


def quick_search(query: str, top_k: int = 3) -> List[Dict]:
    """
    快速搜索（简化版，无详细输出）
    
    Args:
        query: 查询文本
        top_k: 返回结果数量
        
    Returns:
        匹配结果列表
    """
    return search_global_memory(query, top_k=top_k)

# ===== 测试入口 =====
if __name__ == "__main__":
    import sys
    
    # 如果命令行传入参数，只搜索该查询
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"🔍 搜索：'{query}'\n")
        results = search_global_memory(query, top_k=3)
        
        if results:
            print(f"\n✅ 找到 {len(results)} 条相关记忆")
            for i, res in enumerate(results, 1):
                print(f"\n[{i}] 匹配度：{res['score']:.4f} | {res['category']} / {res['key']}")
                print(f"    {res['value'][:200]}...")
        else:
            print("\n⚠️  未找到相关记忆")
        
        sys.exit(0)
    
    # 否则运行默认测试
    print("=" * 70)
    print("🧪 VectorBrain 向量检索测试")
    print("=" * 70)
    print()
    
    # 测试查询（使用模糊的、口语化的提问）
    test_queries = [
        "上次那个系统备份的经验是什么？",  # 应该匹配 backup_procedure
        "帮我看看股票",  # 应该匹配 Stock 002599
        "健豪平时的习惯有哪些？",  # 应该匹配 学习健豪的习惯记录
        "怎么修改配置文件",  # 应该匹配 openclaw.json 修改规则
        "有机会提醒吗",  # 应该匹配 opportunity_scan_log
    ]
    
    print(f"准备测试 {len(test_queries)} 个查询...")
    print()
    
    for i, query in enumerate(test_queries, 1):
        print()
        print(f"{'='*70}")
        print(f"测试 [{i}/{len(test_queries)}]: '{query}'")
        print(f"{'='*70}")
        print()
        
        try:
            top_results = search_global_memory(query, top_k=2)
            
            if top_results:
                print(f"✅ 最佳匹配：{top_results[0]['key']} (分数：{top_results[0]['score']:.4f})")
            else:
                print("⚠️  未找到匹配结果")
                
        except Exception as e:
            print(f"❌ 错误：{e}")
        
        print()
    
    print()
    print("=" * 70)
    print("🎉 全部测试完成！")
    print("=" * 70)
    print()
    print("下一步：")
    print("1. 检查匹配结果是否符合预期")
    print("2. 如果效果好，修改 boot.md 的记忆注入逻辑")
    print("3. 将成功经验写入 VectorBrain")


# ============================================================================
# 🔄 情景记忆混合检索（FAISS + SQL）
# ============================================================================

EPISODIC_DB = VECTORBRAIN_ROOT / 'memory' / 'episodic_memory.db'
EPISODIC_INDEX_PATH = VECTORBRAIN_ROOT / 'memory' / 'episodic.index'
EPISODIC_METADATA_PATH = VECTORBRAIN_ROOT / 'memory' / 'episodic_metadata.json'

# 情景记忆主库（恢复后覆盖回 memory/ 同名文件）
BIG_EPISODIC_DB = VECTORBRAIN_ROOT / 'memory' / 'episodic_memory.db'

# 全局加载情景记忆 FAISS 索引
episodic_index = None
if faiss is not None:
    try:
        if os.path.exists(str(EPISODIC_INDEX_PATH)):
            episodic_index = faiss.read_index(str(EPISODIC_INDEX_PATH))
            print(f"✅ 情景记忆 FAISS 索引已加载 ({EPISODIC_INDEX_PATH})")
        else:
            print(f"⚠️ 情景记忆 FAISS 索引不存在，将降级到 SQL 检索")
    except Exception as e:
        print(f"⚠️ 情景记忆 FAISS 索引加载失败：{e}")

def search_episodic_memory(query: str, top_k: int = 5, recent_hours: int = 24) -> List[Dict]:
    """
    情景记忆混合检索：
    - 大脑主库：FAISS + 大历史库回表
    - 小脑在线库：SQL 增量补充（覆盖最近新增、未入索引内容）
    """
    results = []
    seen_ids = set()

    # ========== 1. FAISS 向量检索（主检索：大脑历史库）==========
    if faiss is not None and episodic_index is not None:
        try:
            print(f"⚡ 情景记忆 FAISS 检索（大脑主库）：'{query}'")
            query_vector = get_ollama_embedding(query)
            q_vec = np.array([query_vector], dtype=np.float32)
            faiss.normalize_L2(q_vec)
            scores, ids = episodic_index.search(q_vec, top_k * 3)

            metadata = []
            if os.path.exists(str(EPISODIC_METADATA_PATH)):
                metadata = json.load(open(str(EPISODIC_METADATA_PATH), 'r'))

            brain_conn = sqlite3.connect(str(BIG_EPISODIC_DB)) if BIG_EPISODIC_DB.exists() else None
            brain_cursor = brain_conn.cursor() if brain_conn else None

            for i in range(min(top_k * 3, len(ids[0]))):
                idx = int(ids[0][i])
                score = float(scores[0][i])

                if idx < 0 or idx >= len(metadata) or score < 0.45:
                    continue

                meta = metadata[idx]
                db_id = meta.get('db_id')
                record_type = meta.get('type')
                content = meta.get('content', '')
                timestamp = meta.get('timestamp')

                if not db_id or not record_type:
                    continue

                item_id = f"{record_type}_{db_id}"
                if item_id in seen_ids:
                    continue

                # 大脑历史库 schema：只有 episodes(id, timestamp, worker_id, event_type, content, metadata, created_at)
                if brain_cursor and record_type == 'episode':
                    brain_cursor.execute("SELECT id, content, timestamp, worker_id, event_type FROM episodes WHERE id = ?", (db_id,))
                    row = brain_cursor.fetchone()
                    if row:
                        _, content, timestamp, worker_id, event_type = row
                        results.append({
                            'id': item_id,
                            'type': record_type,
                            'content': content,
                            'timestamp': timestamp,
                            'score': score,
                            'source': 'faiss_brain',
                            'worker_id': worker_id,
                            'event_type': event_type,
                        })
                        seen_ids.add(item_id)
                        continue

                # 回表失败时，退化到 metadata 内容
                results.append({
                    'id': item_id,
                    'type': record_type,
                    'content': content,
                    'timestamp': timestamp,
                    'score': score,
                    'source': 'faiss_meta'
                })
                seen_ids.add(item_id)

            if brain_conn:
                brain_conn.close()
            print(f"✅ FAISS 找到 {len(results)} 条相关结果")

        except Exception as e:
            print(f"⚠️ FAISS 检索失败：{e}")

    # ========== 2. SQL 增量补充（小脑在线库）==========
    try:
        print(f"📊 情景记忆 SQL 检索（小脑增量，最近 {recent_hours} 小时）...")
        conn = sqlite3.connect(str(EPISODIC_DB))
        cursor = conn.cursor()

        from datetime import datetime, timedelta
        cutoff_time = (datetime.now() - timedelta(hours=recent_hours)).isoformat()
        sql_results = []

        # 在线小脑 episodes（新 schema）
        cursor.execute(
            """
            SELECT episode_id, task_input, task_output, timestamp, task_type
            FROM episodes
            WHERE timestamp > ? AND (task_input LIKE ? OR task_output LIKE ? OR task_type LIKE ?)
            ORDER BY timestamp DESC LIMIT ?
            """,
            (datetime.now().timestamp() - recent_hours * 3600, f'%{query}%', f'%{query}%', f'%{query}%', top_k)
        )
        for row in cursor.fetchall():
            episode_id, task_input, task_output, timestamp, task_type = row
            record_id = f"live_episode_{episode_id}"
            if record_id not in seen_ids:
                sql_results.append({
                    'id': record_id,
                    'type': 'episode',
                    'content': (task_input or '') + '\n' + (task_output or ''),
                    'timestamp': timestamp,
                    'score': 0.62,
                    'source': 'sql_live',
                    'event_type': task_type,
                })
                seen_ids.add(record_id)

        # 在线 conversations
        cursor.execute(
            "SELECT id, content, timestamp, sender_name FROM conversations WHERE timestamp > ? AND content LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (cutoff_time, f'%{query}%', top_k)
        )
        for row in cursor.fetchall():
            conv_id, content, timestamp, sender_name = row
            record_id = f"conversation_{conv_id}"
            if record_id not in seen_ids:
                sql_results.append({
                    'id': record_id,
                    'type': 'conversation',
                    'content': content,
                    'timestamp': timestamp,
                    'score': 0.6,
                    'source': 'sql_live',
                    'sender_name': sender_name,
                })
                seen_ids.add(record_id)

        conn.close()
        results.extend(sql_results)
        print(f"✅ SQL 找到 {len(sql_results)} 条增量结果")

    except Exception as e:
        print(f"⚠️ SQL 检索失败：{e}")

    results.sort(key=lambda x: x['score'], reverse=True)
    final_results = results[:top_k]

    print(f"\n📊 混合检索完成：返回 {len(final_results)} 条结果 (FAISS主脑: {sum(1 for r in final_results if r['source'].startswith('faiss'))}, SQL增量: {sum(1 for r in final_results if r['source']=='sql_live')})")
    return final_results


def quick_episodic_search(query: str, top_k: int = 3) -> List[Dict]:
    """
    情景记忆快速搜索（无详细输出）
    
    Args:
        query: 查询文本
        top_k: 返回结果数量
    
    Returns:
        检索结果列表
    """
    return search_episodic_memory(query, top_k=top_k, recent_hours=12)
