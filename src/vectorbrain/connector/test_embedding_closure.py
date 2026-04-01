#!/usr/bin/env python3
"""
VectorBrain Embedding 闭环测试脚本

测试流程：
1. 从 knowledge_memory.db 读取一条旧数据
2. 调用 Ollama 生成向量
3. 将向量存回数据库的 embedding_vector 字段
4. 验证读取

执行：
python3 ~/.vectorbrain/connector/test_embedding_closure.py
"""

import sqlite3
import json
import subprocess
from pathlib import Path

# VectorBrain 路径
VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
KNOWLEDGE_DB = VECTORBRAIN_ROOT / 'memory' / 'knowledge_memory.db'

def get_ollama_embedding(text: str) -> list:
    """
    调用 Ollama 生成文本向量
    
    Args:
        text: 输入文本
        
    Returns:
        向量列表
    """
    # 使用 curl 调用 Ollama API
    import urllib.request
    import urllib.parse
    
    url = "http://localhost:11434/api/embeddings"
    data = json.dumps({
        "model": "nomic-embed-text",
        "prompt": text
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['embedding']
    except Exception as e:
        print(f"❌ Ollama API 调用失败：{e}")
        # 备用方案：使用 subprocess 调用 ollama run
        print("🔄 尝试使用 ollama run 命令...")
        result = subprocess.run(
            ['ollama', 'run', 'nomic-embed-text', text],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # 输出是纯向量数组
            return json.loads(result.stdout.strip())
        else:
            raise Exception(f"ollama run 也失败了：{result.stderr}")

def add_embedding_column():
    """添加 embedding_vector 字段到 knowledge 表"""
    conn = sqlite3.connect(str(KNOWLEDGE_DB))
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE knowledge ADD COLUMN embedding_vector TEXT")
        print("✅ 已添加 embedding_vector 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️  embedding_vector 字段已存在")
        else:
            raise
    
    conn.commit()
    conn.close()

def read_one_record():
    """读取一条知识记录"""
    conn = sqlite3.connect(str(KNOWLEDGE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, category, key, value 
        FROM knowledge 
        WHERE embedding_vector IS NULL 
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row['id'],
            'category': row['category'],
            'key': row['key'],
            'value': row['value']
        }
    return None

def save_embedding(record_id: int, vector: list):
    """保存向量到数据库"""
    conn = sqlite3.connect(str(KNOWLEDGE_DB))
    cursor = conn.cursor()
    
    # 将向量列表转为 JSON 字符串
    vector_str = json.dumps(vector)
    
    cursor.execute("""
        UPDATE knowledge 
        SET embedding_vector = ? 
        WHERE id = ?
    """, (vector_str, record_id))
    
    conn.commit()
    conn.close()
    print(f"✅ 已保存向量（{len(vector)} 维）到记录 {record_id}")

def verify_embedding(record_id: int):
    """验证向量已正确保存"""
    conn = sqlite3.connect(str(KNOWLEDGE_DB))
    cursor = conn.cursor()
    
    cursor.execute("SELECT embedding_vector FROM knowledge WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    
    if row and row[0]:
        vector = json.loads(row[0])
        print(f"✅ 验证成功：读取到 {len(vector)} 维向量")
        print(f"   前 5 个值：{vector[:5]}")
    else:
        print("❌ 验证失败：未找到向量")
    
    conn.close()

def main():
    """主函数"""
    print("=" * 60)
    print("🧪 VectorBrain Embedding 闭环测试")
    print("=" * 60)
    print()
    
    # 步骤 1：添加字段
    print("步骤 1: 添加 embedding_vector 字段...")
    add_embedding_column()
    print()
    
    # 步骤 2：读取一条记录
    print("步骤 2: 读取一条知识记录...")
    record = read_one_record()
    
    if not record:
        print("❌ 没有找到未生成向量的记录（可能都已生成）")
        return
    
    print(f"✅ 找到记录:")
    print(f"   ID: {record['id']}")
    print(f"   Category: {record['category']}")
    print(f"   Key: {record['key']}")
    print(f"   Value: {record['value'][:100]}...")
    print()
    
    # 步骤 3：生成向量
    print("步骤 3: 调用 Ollama 生成向量...")
    # 使用 key + value 的前 200 字符作为输入
    input_text = f"{record['category']} {record['key']} {record['value'][:200]}"
    
    try:
        vector = get_ollama_embedding(input_text)
        print(f"✅ 向量生成成功！")
        print(f"   维度：{len(vector)}")
        print(f"   前 5 个值：{vector[:5]}")
    except Exception as e:
        print(f"❌ 向量生成失败：{e}")
        return
    
    print()
    
    # 步骤 4：保存向量
    print("步骤 4: 保存向量到数据库...")
    save_embedding(record['id'], vector)
    print()
    
    # 步骤 5：验证
    print("步骤 5: 验证向量已正确保存...")
    verify_embedding(record['id'])
    print()
    
    print("=" * 60)
    print("🎉 闭环测试完成！")
    print("=" * 60)
    print()
    print("下一步:")
    print("1. 如果测试成功，可以运行批量脚本生成所有记录的向量")
    print("2. 修改记忆注入逻辑，使用向量检索替代关键词匹配")

if __name__ == '__main__':
    main()
