#!/usr/bin/env python3
"""
🔄 情景记忆增量向量化脚本（稳健版）

目标：
- 固定 faiss / ollama 运行环境
- 启动前自检（faiss / ollama / DB / 表结构）
- embedding 失败时整次失败，不再“假成功”写入索引
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

# ========== faiss 环境注入 ==========
FAISS_VENV = Path.home() / '.vectorbrain' / '.venv-faiss'
faiss_site_candidates = [
    FAISS_VENV / 'lib' / 'python3.14' / 'site-packages',
    FAISS_VENV / 'lib' / 'python3.13' / 'site-packages',
    FAISS_VENV / 'lib' / 'python3.12' / 'site-packages',
    FAISS_VENV / 'lib' / 'python3.11' / 'site-packages',
]
for candidate in faiss_site_candidates:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
        break

try:
    import faiss  # type: ignore
    import numpy as np
except Exception as e:
    print(f"⚠️ faiss 不可用，增量向量化无法执行：{e}")
    sys.exit(1)

# ========== 路径 ==========
VECTORBRAIN_HOME = Path.home() / '.vectorbrain'
MEMORY_DIR = VECTORBRAIN_HOME / 'memory'
EPISODIC_DB = MEMORY_DIR / 'episodic_memory.db'
EPISODIC_INDEX = MEMORY_DIR / 'episodic.index'
EPISODIC_METADATA = MEMORY_DIR / 'episodic_metadata.json'
PROGRESS_FILE = VECTORBRAIN_HOME / 'episodic_last_vectorized.json'
LOG_FILE = VECTORBRAIN_HOME / 'episodic_incremental.log'

OLLAMA_BIN = '/opt/homebrew/bin/ollama'


# ========== 基础工具 ==========
def log(message: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def resolve_ollama_bin() -> str:
    if Path(OLLAMA_BIN).exists():
        return OLLAMA_BIN
    raise RuntimeError(f'未找到固定 ollama 路径：{OLLAMA_BIN}')


def get_columns(cursor, table: str) -> set:
    cursor.execute(f'PRAGMA table_info({table})')
    return {row[1] for row in cursor.fetchall()}


def preflight_check() -> str:
    if not EPISODIC_DB.exists():
        raise RuntimeError(f'情景记忆数据库不存在：{EPISODIC_DB}')

    ollama_bin = resolve_ollama_bin()

    try:
        version_result = subprocess.run(
            [ollama_bin, '--version'],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f'ollama --version 超时：{e}') from e
    except Exception as e:
        raise RuntimeError(f'ollama 启动检查失败：{e}') from e

    if version_result.returncode != 0:
        raise RuntimeError(f'ollama --version 返回非 0：{version_result.stderr[:200]}')

    conn = sqlite3.connect(str(EPISODIC_DB))
    cursor = conn.cursor()
    episode_cols = get_columns(cursor, 'episodes')
    conv_cols = get_columns(cursor, 'conversations')

    required_episode_cols = {'id', 'timestamp', 'worker_id', 'event_type', 'content'}
    required_conv_cols = {'id', 'chat_id', 'sender_name', 'content', 'timestamp'}

    missing_ep = required_episode_cols - episode_cols
    missing_conv = required_conv_cols - conv_cols
    if missing_ep:
        conn.close()
        raise RuntimeError(f'episodes 表缺少字段：{sorted(missing_ep)}；当前字段：{sorted(episode_cols)}')
    if missing_conv:
        conn.close()
        raise RuntimeError(f'conversations 表缺少字段：{sorted(missing_conv)}；当前字段：{sorted(conv_cols)}')

    # 模型可用性快速探测：只要 embedding 不能拿到合法向量，就整次退出
    try:
        probe = get_ollama_embedding('healthcheck', ollama_bin)
    except Exception as e:
        conn.close()
        raise RuntimeError(f'embedding 启动自检失败：{e}') from e

    if int(probe.shape[0]) != 1024:
        conn.close()
        raise RuntimeError(f'embedding 维度异常：期望 1024，实际 {int(probe.shape[0])}')

    # 现有索引/元数据一致性检查
    if EPISODIC_INDEX.exists() != EPISODIC_METADATA.exists():
        conn.close()
        raise RuntimeError('episodic.index 与 episodic_metadata.json 只存在其一，需先人工处理或干净重建')

    if EPISODIC_INDEX.exists() and EPISODIC_METADATA.exists():
        idx = faiss.read_index(str(EPISODIC_INDEX))
        try:
            metadata = json.loads(EPISODIC_METADATA.read_text(encoding='utf-8'))
        except Exception as e:
            conn.close()
            raise RuntimeError(f'元数据读取失败：{e}') from e
        if not isinstance(metadata, list):
            conn.close()
            raise RuntimeError(f'元数据格式异常：期望 list，实际 {type(metadata).__name__}')
        if idx.ntotal != len(metadata):
            conn.close()
            raise RuntimeError(f'索引/元数据数量不一致：index={idx.ntotal}, metadata={len(metadata)}，建议干净重建')
        if idx.d != 1024:
            conn.close()
            raise RuntimeError(f'现有索引维度异常：期望 1024，实际 {idx.d}')

    conn.close()
    return ollama_bin


def get_last_vectorized_id() -> Tuple[int, int]:
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding='utf-8'))
            return int(data.get('last_ep_id', 0)), int(data.get('last_conv_id', 0))
        except Exception:
            log('⚠️ 进度文件读取失败，从头开始')
    return 0, 0


def atomic_write_text(path: Path, content: str, encoding: str = 'utf-8'):
    tmp = path.with_name(f'.{path.name}.{uuid4().hex}.tmp')
    tmp.write_text(content, encoding=encoding)
    os.replace(tmp, path)


def save_last_vectorized_id(ep_id: int, conv_id: int):
    data = {
        'last_ep_id': ep_id,
        'last_conv_id': conv_id,
        'updated': datetime.now().isoformat(),
    }
    atomic_write_text(PROGRESS_FILE, json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    log(f'💾 进度已保存：ep_id={ep_id}, conv_id={conv_id}')


def load_or_create_index():
    if EPISODIC_INDEX.exists():
        log(f'📂 加载现有索引：{EPISODIC_INDEX}')
        return faiss.read_index(str(EPISODIC_INDEX))
    log('🆕 创建新索引')
    return faiss.IndexFlatL2(1024)


def append_metadata(new_metadata: List[dict]):
    if EPISODIC_METADATA.exists():
        existing = json.loads(EPISODIC_METADATA.read_text(encoding='utf-8'))
    else:
        existing = []
    existing.extend(new_metadata)
    atomic_write_text(EPISODIC_METADATA, json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
    log(f'💾 元数据已更新，新增 {len(new_metadata)} 条')


def get_ollama_embedding(text: str, ollama_bin: str) -> np.ndarray:
    try:
        result = subprocess.run(
            [ollama_bin, 'run', 'bge-m3', text],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f'Ollama 请求超时：{e}') from e
    except Exception as e:
        raise RuntimeError(f'调用 Ollama 失败：{e}') from e

    if result.returncode != 0:
        raise RuntimeError(f'Ollama 返回非 0：{result.stderr[:200]}')

    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError('Ollama 返回空输出')

    try:
        vector = json.loads(stdout)
        arr = np.array(vector, dtype=np.float32)
    except Exception as e:
        raise RuntimeError(f'Ollama 输出不是合法向量 JSON：{e}; output={stdout[:200]}') from e

    if arr.ndim != 1 or arr.size == 0:
        raise RuntimeError(f'Ollama 向量格式异常：shape={getattr(arr, "shape", None)}')

    if arr.shape[0] != 1024:
        raise RuntimeError(f'Ollama 向量维度异常：期望 1024，实际 {arr.shape[0]}')

    return arr


def incremental_vectorize():
    log('=' * 60)
    log('🔄 开始增量向量化')
    log('=' * 60)

    ollama_bin = preflight_check()
    log(f'✅ 自检通过：ollama={ollama_bin}')

    last_ep_id, last_conv_id = get_last_vectorized_id()
    log(f'📍 上次进度：ep_id={last_ep_id}, conv_id={last_conv_id}')

    conn = sqlite3.connect(str(EPISODIC_DB))
    cursor = conn.cursor()

    new_vectors: List[np.ndarray] = []
    new_metadata: List[dict] = []
    total_ep = 0
    total_conv = 0

    log('📊 扫描新增 episodes...')
    cursor.execute(
        'SELECT id, timestamp, worker_id, event_type, content FROM episodes WHERE id > ? ORDER BY id',
        (last_ep_id,),
    )
    new_episodes = cursor.fetchall()
    if new_episodes:
        log(f'✅ 发现 {len(new_episodes)} 条新增 episodes')
        for i, ep in enumerate(new_episodes):
            ep_id, timestamp, worker_id, event_type, content = ep
            text = f'[Episode] {worker_id} @ {timestamp}: {content}'
            vector = get_ollama_embedding(text, ollama_bin)
            new_vectors.append(vector)
            new_metadata.append({
                'id': f'ep_{ep_id}',
                'db_id': ep_id,
                'type': 'episode',
                'timestamp': timestamp,
                'worker_id': worker_id,
                'event_type': event_type,
                'content': content[:500],
            })
            last_ep_id = ep_id
            total_ep += 1
            if (i + 1) % 50 == 0:
                log(f'⚡ 进度：{i + 1}/{len(new_episodes)} episodes')
    else:
        log('ℹ️ 无新增 episodes')

    log('📊 扫描新增 conversations...')
    cursor.execute(
        'SELECT id, chat_id, sender_name, content, timestamp FROM conversations WHERE id > ? ORDER BY id',
        (last_conv_id,),
    )
    new_conversations = cursor.fetchall()
    if new_conversations:
        log(f'✅ 发现 {len(new_conversations)} 条新增 conversations')
        for i, conv in enumerate(new_conversations):
            conv_id, chat_id, sender_name, content, timestamp = conv
            text = f'[Conversation] {sender_name or "Unknown"} @ {chat_id}: {content}'
            vector = get_ollama_embedding(text, ollama_bin)
            new_vectors.append(vector)
            new_metadata.append({
                'id': f'conv_{conv_id}',
                'db_id': conv_id,
                'type': 'conversation',
                'timestamp': timestamp,
                'chat_id': chat_id,
                'content': content[:500],
            })
            last_conv_id = conv_id
            total_conv += 1
            if (i + 1) % 50 == 0:
                log(f'⚡ 进度：{i + 1}/{len(new_conversations)} conversations')
    else:
        log('ℹ️ 无新增 conversations')

    conn.close()

    if not new_vectors:
        log('\nℹ️ 无新数据需要向量化')
        save_last_vectorized_id(last_ep_id, last_conv_id)
        log('=' * 60)
        return

    dims = {int(v.shape[0]) for v in new_vectors}
    if len(dims) != 1:
        raise RuntimeError(f'本批次向量维度不一致：{sorted(dims)}')

    log(f'\n📦 准备更新索引：{len(new_vectors)} 条新向量')
    index = load_or_create_index()
    vectors_array = np.array(new_vectors, dtype=np.float32)
    if vectors_array.ndim != 2 or vectors_array.shape[1] != 1024:
        raise RuntimeError(f'待写入向量数组形状异常：{vectors_array.shape}')
    index.add(vectors_array)

    log(f'💾 原子保存索引：{EPISODIC_INDEX}')
    tmp_index = EPISODIC_INDEX.with_name(f'.{EPISODIC_INDEX.name}.{uuid4().hex}.tmp')
    faiss.write_index(index, str(tmp_index))
    os.replace(tmp_index, EPISODIC_INDEX)
    append_metadata(new_metadata)
    save_last_vectorized_id(last_ep_id, last_conv_id)

    index_size = EPISODIC_INDEX.stat().st_size / 1024 / 1024 if EPISODIC_INDEX.exists() else 0
    log('\n✅ 增量向量化完成！')
    log(f'   新增 episodes: {total_ep}')
    log(f'   新增 conversations: {total_conv}')
    log(f'   总计：{total_ep + total_conv} 条')
    log(f'   索引大小：{index_size:.1f}MB')
    log('=' * 60)


if __name__ == '__main__':
    try:
        incremental_vectorize()
    except KeyboardInterrupt:
        log('\n⚠️ 用户中断')
        sys.exit(130)
    except Exception as e:
        log(f'\n❌ 错误：{e}')
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
