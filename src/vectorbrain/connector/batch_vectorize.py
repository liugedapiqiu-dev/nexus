#!/usr/bin/env python3
"""
批量向量化工具 - 为无向量的知识记忆生成 embedding

用法：
python3 ~/.vectorbrain/connector/batch_vectorize.py
"""

import sqlite3
import json
import subprocess
import numpy as np
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / '.vectorbrain/memory/knowledge_memory.db'

def get_ollama_embedding(text: str) -> list:
    """
    调用 Ollama 生成文本向量（bge-m3 模型）
    """
    try:
        # 截取前 2000 字符（bge-m3 最大长度限制）
        text = text[:2000]
        
        result = subprocess.run(
            ['ollama', 'run', 'bge-m3', text],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            return None
            
    except Exception as e:
        print(f"⚠️ 生成向量失败：{e}")
        return None

def batch_vectorize():
    """
    批量为无向量的记录生成向量
    """
    print("=" * 70)
    print("🚀 开始批量向量化")
    print("=" * 70)
    print()
    
    # 连接数据库
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 查询所有无向量的记录
    cursor.execute("""
        SELECT id, category, key, value 
        FROM knowledge 
        WHERE embedding_vector IS NULL
        ORDER BY id ASC
    """)
    
    rows = cursor.fetchall()
    total = len(rows)
    
    print(f"📦 找到 {total} 条需要向量化的记录")
    print()
    
    if total == 0:
        print("✅ 所有记录已有向量！")
        conn.close()
        return
    
    # 统计
    success = 0
    failed = 0
    skipped = 0
    
    for i, (record_id, category, key, value) in enumerate(rows, 1):
        # 进度显示
        print(f"[{i}/{total}] 处理 ID {record_id}: {category} / {key[:30]}...")
        
        # 如果 value 为空或太短，跳过
        if not value or len(value.strip()) < 10:
            print(f"  ⚠️ 跳过：内容为空或太短")
            skipped += 1
            continue
        
        # 生成向量
        vector = get_ollama_embedding(value)
        
        if vector:
            # 更新数据库
            cursor.execute("""
                UPDATE knowledge 
                SET embedding_vector = ?
                WHERE id = ?
            """, (json.dumps(vector), record_id))
            conn.commit()
            
            print(f"  ✅ 成功 (维度：{len(vector)})")
            success += 1
        else:
            print(f"  ❌ 失败")
            failed += 1
        
        # 每 50 条显示统计
        if i % 50 == 0:
            print()
            print(f"  📊 进度：{i}/{total} | 成功：{success} | 失败：{failed} | 跳过：{skipped}")
            print()
    
    conn.close()
    
    print()
    print("=" * 70)
    print("✅ 批量向量化完成！")
    print("=" * 70)
    print()
    print(f"📊 统计结果:")
    print(f"  - 总记录数：{total}")
    print(f"  - ✅ 成功：{success} ({success/total*100:.1f}%)")
    print(f"  - ❌ 失败：{failed} ({failed/total*100:.1f}%)")
    print(f"  - ⚠️ 跳过：{skipped} ({skipped/total*100:.1f}%)")
    print()
    
    # 建议重建 FAISS 索引
    if success > 0:
        print("📝 下一步：重建 FAISS 索引以包含新向量")
        print("   运行：python3 ~/.vectorbrain/connector/faiss_manager.py")
        print()

if __name__ == "__main__":
    batch_vectorize()
