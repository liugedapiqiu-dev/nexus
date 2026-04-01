#!/usr/bin/env python3
"""
FAISS 索引构建管理器

功能：
从 SQLite 数据库抽取所有向量 → 构建 FAISS 索引 → 持久化到磁盘

用法：
python3 ~/.vectorbrain/connector/faiss_manager.py
"""

import sqlite3
import json
import numpy as np
import faiss
from pathlib import Path

DB_PATH = Path.home() / '.vectorbrain/memory/knowledge_memory.db'
INDEX_PATH = Path.home() / '.vectorbrain/memory/knowledge.index'
DIMENSION = 1024  # bge-m3 维度

def build_faiss_index():
    """
    构建 FAISS 索引
    """
    print("🧠 开始构建 FAISS 索引...")
    
    # 连接数据库，抽取所有向量
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT id, embedding_vector FROM knowledge WHERE embedding_vector IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("⚠️ 数据库中没有找到向量！")
        return
    
    print(f"📦 抽取到 {len(rows)} 条向量数据，准备构建空间索引...")
    
    # 转换为 numpy 矩阵
    ids = np.array([row[0] for row in rows], dtype=np.int64)
    vectors = np.array([json.loads(row[1]) for row in rows], dtype=np.float32)
    
    # L2 归一化 (让 Inner Product 等价于余弦相似度)
    faiss.normalize_L2(vectors)
    
    # 创建内积索引 + ID 映射
    index = faiss.IndexIDMap(faiss.IndexFlatIP(DIMENSION))
    index.add_with_ids(vectors, ids)
    
    # 写入磁盘
    faiss.write_index(index, str(INDEX_PATH))
    
    print(f"✅ FAISS 索引构建完毕！已持久化至 {INDEX_PATH}")

if __name__ == "__main__":
    build_faiss_index()
