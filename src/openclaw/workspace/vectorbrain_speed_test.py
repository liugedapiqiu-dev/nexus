#!/usr/bin/env python3
"""VectorBrain 检索速度测试（兼容当前 schema）"""

import sqlite3
import time
import os
import subprocess
from datetime import datetime

EPISODIC_DB_PATH = os.path.expanduser("~/.vectorbrain/memory/episodic_memory.db")
KNOWLEDGE_DB_PATH = os.path.expanduser("~/.vectorbrain/memory/knowledge_memory.db")
VECTOR_SEARCH_SCRIPT = os.path.expanduser("~/.vectorbrain/connector/vector_search.py")


def get_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def timed_query(cursor, sql, params=()):
    start = time.perf_counter()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return rows, elapsed_ms


def test_vector_search_speed():
    keywords = ["向量检索", "测试", "speed test", "检索速度", "增强", "upgrade"]
    query = "蜘蛛侠书包 项目"

    print("=" * 70)
    print("VectorBrain 检索速度测试")
    print("=" * 70)
    print(f"情景库：{EPISODIC_DB_PATH}")
    print(f"知识库：{KNOWLEDGE_DB_PATH}")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"向量检索查询：{query}")
    print("=" * 70)

    epi_conn = sqlite3.connect(EPISODIC_DB_PATH)
    epi_conn.row_factory = sqlite3.Row
    epi = epi_conn.cursor()

    know_conn = sqlite3.connect(KNOWLEDGE_DB_PATH)
    know_conn.row_factory = sqlite3.Row
    know = know_conn.cursor()

    episodes_count = epi.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    conv_count = epi.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    knowledge_count = know.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]

    print(f"\n情景记忆 episodes：{episodes_count:,}")
    print(f"情景对话 conversations：{conv_count:,}")
    print(f"知识记忆 knowledge：{knowledge_count:,}")

    print("\n[测试 1] 情景记忆 LIKE 搜索（episodes）...")
    rows, t1 = timed_query(
        epi,
        """
        SELECT episode_id, timestamp, task_type, substr(task_input, 1, 120) AS preview
        FROM episodes
        WHERE task_input LIKE ? OR task_output LIKE ? OR task_type LIKE ?
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        (f"%{keywords[0]}%", f"%{keywords[0]}%", f"%{keywords[0]}%"),
    )
    print(f"  检索耗时：{t1:.2f} ms")
    print(f"  检索结果：{len(rows)} 条")

    print("\n[测试 2] 情景对话 LIKE 搜索（conversations，多关键词）...")
    rows, t2 = timed_query(
        epi,
        """
        SELECT id, timestamp, sender_name, substr(content, 1, 120) AS preview
        FROM conversations
        WHERE content LIKE ? OR content LIKE ? OR content LIKE ?
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        tuple(f"%{kw}%" for kw in keywords[:3]),
    )
    print(f"  检索耗时：{t2:.2f} ms")
    print(f"  检索结果：{len(rows)} 条")

    print("\n[测试 3] 知识库 LIKE 搜索（knowledge）...")
    know_cols = get_columns(know, 'knowledge')
    if {'content', 'metadata', 'source'}.issubset(know_cols):
        rows, t3 = timed_query(
            know,
            """
            SELECT id, source, importance, substr(content, 1, 120) AS preview
            FROM knowledge
            WHERE content LIKE ? OR metadata LIKE ? OR source LIKE ?
            ORDER BY importance DESC, created_at DESC
            LIMIT 10
            """,
            ("%项目%", "%项目%", "%项目%"),
        )
    else:
        rows, t3 = timed_query(
            know,
            """
            SELECT id, key, confidence, substr(value, 1, 120) AS preview
            FROM knowledge
            WHERE value LIKE ? OR key LIKE ? OR category LIKE ?
            ORDER BY confidence DESC, updated_at DESC
            LIMIT 10
            """,
            ("%项目%", "%项目%", "%项目%"),
        )
    print(f"  检索耗时：{t3:.2f} ms")
    print(f"  检索结果：{len(rows)} 条")

    print("\n[测试 4] 调用真实向量检索脚本（FAISS/Ollama 路径）...")
    start = time.perf_counter()
    result = subprocess.run(
        ["python3", VECTOR_SEARCH_SCRIPT, query],
        capture_output=True,
        text=True,
        timeout=120,
    )
    t4 = (time.perf_counter() - start) * 1000
    print(f"  端到端耗时：{t4:.2f} ms")
    print(f"  退出码：{result.returncode}")

    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    found = "✅ 找到" in output or "📊 检索完成" in output
    print(f"  是否成功返回结果：{'是' if (result.returncode == 0 and found) else '否'}")

    print("\n" + "=" * 70)
    print("结果摘要")
    print("=" * 70)
    preview_lines = [line for line in output.splitlines() if line.strip()][:20]
    for line in preview_lines:
        print(line)

    epi_conn.close()
    know_conn.close()

    print("\n" + "=" * 70)
    print("性能结论")
    print("=" * 70)
    print(f"✓ SQL 情景检索（episodes）: {t1:.2f} ms")
    print(f"✓ SQL 对话检索（conversations）: {t2:.2f} ms")
    print(f"✓ SQL 知识检索（knowledge）: {t3:.2f} ms")
    print(f"✓ 真实向量检索端到端: {t4:.2f} ms")
    print("✓ 当前测试脚本已兼容现有 schema")
    print("✓ 若端到端耗时偏高，主要成本通常在 Ollama embedding，而不是 FAISS 本身")
    print("=" * 70)


if __name__ == "__main__":
    test_vector_search_speed()
