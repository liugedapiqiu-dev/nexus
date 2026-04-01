#!/usr/bin/env python3
"""
VectorBrain 批量向量重新生成脚本（使用 bge-m3）

功能：
强制重新生成所有记录的向量（覆盖旧模型生成的向量）

执行：
python3 ~/.vectorbrain/connector/regenerate_all_embeddings.py
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
    """调用 Ollama bge-m3 生成文本向量"""
    try:
        result = subprocess.run(
            ['ollama', 'run', 'bge-m3', text],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            print(f"⚠️  失败：{result.stderr[:100]}")
            return None
    except Exception as e:
        print(f"⚠️  错误：{e}")
        return None

def get_all_records():
    """获取所有记录"""
    conn = sqlite3.connect(str(KNOWLEDGE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, category, key, value FROM knowledge")
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        'id': row['id'],
        'category': row['category'],
        'key': row['key'],
        'value': row['value']
    } for row in rows]

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
    print("🔄 VectorBrain 批量向量重新生成（bge-m3 多语言模型）")
    print("=" * 70)
    print()
    
    # 获取所有记录
    print("📊 扫描数据库...")
    all_records = get_all_records()
    total_count = len(all_records)
    
    print(f"📌 找到 {total_count} 条记录需要重新生成向量")
    print()
    print("⚠️  注意：这将覆盖所有旧向量（nomic-embed-text 生成的）")
    print()
    
    # 确认
    response = input("继续吗？(y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    # 批量生成
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    for i, record in enumerate(all_records, 1):
        print(f"[{i}/{total_count}] {record['category']} / {record['key'][:40]}...", end=" ")
        
        # 结构化提示词
        input_text = f"[分类]: {record['category']}\n[标题]: {record['key']}\n[内容摘要]: {record['value'][:300]}"
        
        # 生成向量
        vector = get_ollama_embedding(input_text)
        
        if vector:
            save_embedding(record['id'], vector)
            print(f"✅ ({len(vector)}维)")
            success_count += 1
        else:
            print("❌")
            fail_count += 1
        
        time.sleep(0.5)
    
    # 统计
    end_time = time.time()
    elapsed = end_time - start_time
    
    print()
    print("=" * 70)
    print("📊 重新生成完成！")
    print("=" * 70)
    print(f"⏱️  总耗时：{elapsed:.1f} 秒")
    print(f"✅ 成功：{success_count} 条")
    print(f"❌ 失败：{fail_count} 条")
    print(f"⚡ 平均速度：{elapsed/total_count:.2f} 秒/条")
    print()
    print("🎉 所有向量已更新为 bge-m3 模型生成！")

if __name__ == '__main__':
    main()
