#!/usr/bin/env python3
"""
🧠 情景记忆向量化脚本

为 episodic_memory.db 中的所有 episodes 和 conversations 生成向量嵌入
并创建 FAISS 索引

预计时间：2-3 小时（41,000+ 条记录）
"""

import sqlite3
import faiss
import numpy as np
import json
import os
import time
from pathlib import Path
from datetime import datetime

# VectorBrain 路径
VECTORBRAIN_HOME = Path.home() / '.vectorbrain'
MEMORY_DIR = VECTORBRAIN_HOME / 'memory'

# 数据库路径
EPISODIC_DB = MEMORY_DIR / 'episodic_memory.db'

# 输出路径
EPISODIC_INDEX = MEMORY_DIR / 'episodic.index'
EPISODIC_METADATA = MEMORY_DIR / 'episodic_metadata.json'

# 批次大小（内存控制）
BATCH_SIZE = 100


def get_ollama_embedding(text: str) -> np.ndarray:
    """使用 Ollama 生成长文本嵌入（bge-m3）- 使用 ollama run 命令"""
    import subprocess
    
    try:
        # 使用 ollama run 命令（和 vector_search.py 一致）
        result = subprocess.run(
            ['ollama', 'run', 'bge-m3', text],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            vector = json.loads(result.stdout.strip())
            return np.array(vector, dtype=np.float32)
        else:
            print(f"⚠️ Ollama 错误：{result.stderr[:200]}")
            return np.zeros(1024, dtype=np.float32)
    except Exception as e:
        print(f"⚠️ 嵌入生成失败：{e}")
        return np.zeros(1024, dtype=np.float32)


def load_existing_metadata():
    """加载已有的元数据（用于增量更新）"""
    if EPISODIC_METADATA.exists():
        with open(str(EPISODIC_METADATA), 'r') as f:
            return json.load(f)
    return []


def save_progress(vectors, metadata, processed_count):
    """保存进度（防止中断后重头开始）"""
    # 保存临时索引
    if vectors:
        vectors_np = np.array(vectors, dtype=np.float32)
        index = faiss.IndexFlatL2(1024)
        index.add(vectors_np)
        faiss.write_index(index, str(EPISODIC_INDEX) + '.tmp')
    
    # 保存元数据（修复 Path 拼接问题）
    with open(str(EPISODIC_METADATA) + '.tmp', 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 保存进度
    progress_file = VECTORBRAIN_HOME / 'episodic_backfill_progress.json'
    with open(str(progress_file), 'w') as f:
        json.dump({
            'processed': processed_count,
            'timestamp': datetime.now().isoformat()
        }, f)
    
    print(f"💾 进度已保存：{processed_count} 条")


def backfill_episodic_vectors():
    """为主数据库中的所有记录生成向量"""
    
    print("=" * 70)
    print("🧠 情景记忆向量化脚本")
    print("=" * 70)
    print(f"📂 数据库：{EPISODIC_DB}")
    print(f"📊 批次大小：{BATCH_SIZE}")
    print("=" * 70)
    
    # 检查是否已有进度
    progress_file = VECTORBRAIN_HOME / 'episodic_backfill_progress.json'
    start_from = 0
    existing_vectors = []
    existing_metadata = []
    
    if progress_file.exists():
        progress = json.load(open(progress_file))
        start_from = progress.get('processed', 0)
        print(f"⏩ 发现进度记录，从第 {start_from} 条继续")
        
        # 加载已有数据
        tmp_metadata_path = str(MEMORY_DIR) + '/episodic_metadata.json.tmp'
        if os.path.exists(tmp_metadata_path):
            existing_metadata = json.load(open(tmp_metadata_path))
            print(f"📦 已加载 {len(existing_metadata)} 条现有元数据")
    
    # 连接数据库
    conn = sqlite3.connect(str(EPISODIC_DB))
    cursor = conn.cursor()
    
    # 获取所有 episodes
    print("\n📊 扫描 episodes...")
    cursor.execute("SELECT id, timestamp, worker_id, event_type, content FROM episodes ORDER BY id")
    episodes = cursor.fetchall()
    print(f"✅ 发现 {len(episodes)} 条 episodes")
    
    # 获取所有 conversations
    print("📊 扫描 conversations...")
    cursor.execute("SELECT id, chat_id, sender_name, content, timestamp FROM conversations ORDER BY id")
    conversations = cursor.fetchall()
    print(f"✅ 发现 {len(conversations)} 条 conversations")
    
    # 合并所有记录
    all_records = []
    
    for ep in episodes:
        ep_id, timestamp, worker_id, event_type, content = ep
        all_records.append({
            'id': f'ep_{ep_id}',
            'db_id': ep_id,
            'type': 'episode',
            'timestamp': timestamp,
            'worker_id': worker_id,
            'event_type': event_type,
            'content': content,
            'text_for_embedding': f"[Episode] {worker_id} @ {timestamp}: {content}"
        })
    
    for conv in conversations:
        conv_id, chat_id, sender_name, content, timestamp = conv
        all_records.append({
            'id': f'conv_{conv_id}',
            'db_id': conv_id,
            'type': 'conversation',
            'timestamp': timestamp,
            'chat_id': chat_id,
            'sender_name': sender_name or 'Unknown',
            'content': content,
            'text_for_embedding': f"[Conversation] {sender_name or 'Unknown'} @ {chat_id}: {content}"
        })
    
    total = len(all_records)
    print(f"\n📊 总计：{total} 条记录需要向量化")
    
    if start_from > 0:
        print(f"⏩ 跳过前 {start_from} 条已有记录")
        all_records = all_records[start_from:]
    
    # 开始向量化
    print("\n🚀 开始向量化...")
    print("=" * 70)
    
    vectors = existing_vectors
    metadata = existing_metadata
    
    start_time = time.time()
    
    for i, record in enumerate(all_records):
        if i % BATCH_SIZE == 0 and i > 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total - start_from - i) / rate if rate > 0 else 0
            print(f"⚡ 进度：{start_from + i}/{total} ({(start_from + i) / total * 100:.1f}%) | "
                  f"速度：{rate:.1f} 条/秒 | 剩余：{eta / 60:.1f} 分钟")
            
            # 每批次保存进度
            save_progress(vectors, metadata, start_from + i)
        
        # 生成向量
        embedding = get_ollama_embedding(record['text_for_embedding'])
        vectors.append(embedding)
        
        # 存储元数据（不存储向量以节省内存）
        metadata.append({
            'id': record['id'],
            'db_id': record['db_id'],
            'type': record['type'],
            'timestamp': record['timestamp'],
            'content': record['content'][:500]  # 限制长度
        })
    
    # 最终保存
    print("\n📦 保存最终索引...")
    vectors_np = np.array(vectors, dtype=np.float32)
    
    print(f"🔧 创建 FAISS 索引（{len(vectors_np)} 条向量，{vectors_np.shape[1]} 维）...")
    index = faiss.IndexFlatL2(1024)
    index.add(vectors_np)
    
    print(f"💾 写入索引文件：{EPISODIC_INDEX}...")
    faiss.write_index(index, str(EPISODIC_INDEX))
    
    print(f"💾 写入元数据文件：{EPISODIC_METADATA}...")
    with open(str(EPISODIC_METADATA), 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 清理临时文件
    tmp_files = [
        str(EPISODIC_INDEX) + '.tmp',
        str(EPISODIC_METADATA) + '.tmp',
        str(VECTORBRAIN_HOME / 'episodic_backfill_progress.json')
    ]
    for tmp_file in tmp_files:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
    
    # 统计信息
    total_time = time.time() - start_time
    index_size = os.path.getsize(EPISODIC_INDEX) / 1024 / 1024
    
    print("\n" + "=" * 70)
    print("✅ 向量化完成！")
    print("=" * 70)
    print(f"📊 处理记录数：{total}")
    print(f"⏱️  总耗时：{total_time / 60:.1f} 分钟")
    print(f"⚡ 平均速度：{total / total_time:.1f} 条/秒")
    print(f"💾 索引大小：{index_size:.1f}MB")
    print(f"📍 索引位置：{EPISODIC_INDEX}")
    print(f"📄 元数据：{EPISODIC_METADATA}")
    print("=" * 70)


if __name__ == '__main__':
    try:
        backfill_episodic_vectors()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断，进度已保存")
        print("💡 下次运行会自动从断点继续")
    except Exception as e:
        print(f"\n\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
