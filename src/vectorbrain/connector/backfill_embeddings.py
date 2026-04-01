#!/usr/bin/env python3
"""
VectorBrain 批量向量生成脚本

功能：
遍历 knowledge_memory.db 中所有 embedding_vector IS NULL 的记录
调用 Ollama 生成向量并回填到数据库

执行：
python3 ~/.vectorbrain/connector/backfill_embeddings.py
"""

import sqlite3
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

# VectorBrain 路径
VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
KNOWLEDGE_DB = VECTORBRAIN_ROOT / 'memory' / 'knowledge_memory.db'

def get_ollama_embedding(text: str) -> list:
    """
    调用 Ollama 生成文本向量（使用 bge-m3 多语言模型）
    
    Args:
        text: 输入文本
        
    Returns:
        向量列表
    """
    try:
        result = subprocess.run(
            ['ollama', 'run', 'bge-m3', text],
            capture_output=True,
            text=True,
            timeout=60  # bge-m3 更大，给更多时间
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            print(f"⚠️  ollama run 失败：{result.stderr[:100]}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"⚠️  请求超时")
        return None
    except Exception as e:
        print(f"⚠️  错误：{e}")
        return None

def get_null_records(limit: int = None):
    """获取所有未生成向量的记录"""
    conn = sqlite3.connect(str(KNOWLEDGE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT id, category, key, value FROM knowledge WHERE embedding_vector IS NULL"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    records = []
    for row in rows:
        records.append({
            'id': row['id'],
            'category': row['category'],
            'key': row['key'],
            'value': row['value']
        })
    
    return records

def save_embedding(record_id: int, vector: list):
    """保存向量到数据库"""
    conn = sqlite3.connect(str(KNOWLEDGE_DB))
    cursor = conn.cursor()
    
    vector_str = json.dumps(vector)
    
    cursor.execute("""
        UPDATE knowledge 
        SET embedding_vector = ?, updated_at = ?
        WHERE id = ?
    """, (vector_str, datetime.now().isoformat(), record_id))
    
    conn.commit()
    conn.close()

def main():
    """主函数"""
    print("=" * 70)
    print("🔄 VectorBrain 批量向量生成（历史数据回填）")
    print("=" * 70)
    print()
    
    # 获取所有未生成向量的记录
    print("📊 扫描数据库...")
    null_records = get_null_records()
    total_count = len(null_records)
    
    if total_count == 0:
        print("✅ 所有记录都已生成向量！")
        return
    
    print(f"📌 找到 {total_count} 条记录需要生成向量")
    print()
    
    # 批量生成
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    for i, record in enumerate(null_records, 1):
        # 进度显示
        print(f"[{i}/{total_count}] 处理：{record['category']} / {record['key'][:40]}...", end=" ")
        
        # 生成输入文本（结构化提示词）
        # 格式：[分类]: xxx\n[标题]: xxx\n[内容摘要]: xxx
        input_text = f"[分类]: {record['category']}\n[标题]: {record['key']}\n[内容摘要]: {record['value'][:300]}"
        
        # 生成向量
        vector = get_ollama_embedding(input_text)
        
        if vector:
            # 保存向量
            save_embedding(record['id'], vector)
            print(f"✅ 成功 ({len(vector)}维)")
            success_count += 1
        else:
            print("❌ 失败")
            fail_count += 1
        
        # 短暂等待，避免 Ollama 过载
        time.sleep(0.5)
    
    # 统计
    end_time = time.time()
    elapsed = end_time - start_time
    
    print()
    print("=" * 70)
    print("📊 批量生成完成！")
    print("=" * 70)
    print(f"⏱️  总耗时：{elapsed:.1f} 秒")
    print(f"✅ 成功：{success_count} 条")
    print(f"❌ 失败：{fail_count} 条")
    print(f"📈 成功率：{success_count/total_count*100:.1f}%")
    print(f"⚡ 平均速度：{elapsed/total_count:.2f} 秒/条")
    print()
    
    if fail_count > 0:
        print("⚠️  失败的记录可以重新运行此脚本重试")
    
    print("🎉 历史数据回填完成！")
    print()
    print("下一步：编写 vector_search.py 模块")

if __name__ == '__main__':
    main()
