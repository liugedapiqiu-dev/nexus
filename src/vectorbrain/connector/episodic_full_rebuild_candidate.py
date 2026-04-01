#!/usr/bin/env python3
"""
最小侵入式 episodic 全量重建：
- 只读取 episodic_memory.db
- 仅输出到候选目录，不覆盖现网
- 固定 faiss/ollama 环境
- 并发调用 ollama run（默认 4 路）提升重建速度
- 生成 index / metadata / validation_report
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

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

import numpy as np  # type: ignore
import faiss  # type: ignore

VECTORBRAIN_HOME = Path.home() / '.vectorbrain'
MEMORY_DIR = VECTORBRAIN_HOME / 'memory'
DB_PATH = MEMORY_DIR / 'episodic_memory.db'
OLLAMA_BIN = '/opt/homebrew/bin/ollama'
MODEL = 'bge-m3'
DIM = 1024
BATCH_SIZE = 100
MAX_WORKERS = 4


def atomic_write_text(path: Path, content: str, encoding: str = 'utf-8'):
    tmp = path.with_name(f'.{path.name}.{uuid4().hex}.tmp')
    tmp.write_text(content, encoding=encoding)
    os.replace(tmp, path)


def log(msg: str, log_file: Path):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def get_embedding(text: str) -> np.ndarray:
    result = subprocess.run(
        [OLLAMA_BIN, 'run', MODEL, text],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(f'ollama failed: {result.stderr[:200]}')
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError('ollama returned empty output')
    try:
        vec = np.array(json.loads(stdout), dtype=np.float32)
    except Exception as e:
        raise RuntimeError(f'invalid vector json: {e}; out={stdout[:200]}') from e
    if vec.ndim != 1 or vec.shape[0] != DIM:
        raise RuntimeError(f'bad vector shape: {getattr(vec, "shape", None)}')
    return vec


def embed_job(args: Tuple[int, dict]) -> Tuple[int, np.ndarray, dict]:
    idx, record = args
    vec = get_embedding(record['text_for_embedding'])
    item = {k: v for k, v in record.items() if k != 'text_for_embedding'}
    return idx, vec, item


def sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not DB_PATH.exists():
        raise RuntimeError(f'db missing: {DB_PATH}')
    if not Path(OLLAMA_BIN).exists():
        raise RuntimeError(f'ollama missing: {OLLAMA_BIN}')

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    out_dir = MEMORY_DIR / f'episodic-rebuild-candidate-{stamp}'
    out_dir.mkdir(parents=True, exist_ok=False)
    log_file = out_dir / 'rebuild.log'
    progress_file = out_dir / 'progress.json'
    index_path = out_dir / 'episodic.index'
    metadata_path = out_dir / 'episodic_metadata.json'
    report_path = out_dir / 'validation_report.json'

    log(f'candidate dir: {out_dir}', log_file)
    log('preflight: checking ollama version', log_file)
    ver = subprocess.run([OLLAMA_BIN, '--version'], capture_output=True, text=True, timeout=15)
    if ver.returncode != 0:
        raise RuntimeError(f'ollama --version failed: {ver.stderr[:200]}')
    log(f'ollama version: {ver.stdout.strip()}', log_file)

    probe = get_embedding('healthcheck')
    log(f'embedding probe ok, dim={probe.shape[0]}', log_file)

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    db_episodes = cur.execute('select count(*) from episodes').fetchone()[0]
    db_conversations = cur.execute('select count(*) from conversations').fetchone()[0]
    log(f'db counts: episodes={db_episodes}, conversations={db_conversations}', log_file)

    cur.execute('SELECT id, timestamp, worker_id, event_type, content FROM episodes ORDER BY id')
    episodes = cur.fetchall()
    cur.execute('SELECT id, chat_id, sender_name, content, timestamp FROM conversations ORDER BY id')
    conversations = cur.fetchall()
    conn.close()

    all_records = []
    for ep_id, timestamp, worker_id, event_type, content in episodes:
        all_records.append({
            'id': f'ep_{ep_id}',
            'db_id': ep_id,
            'type': 'episode',
            'timestamp': timestamp,
            'worker_id': worker_id,
            'event_type': event_type,
            'content': (content or '')[:500],
            'text_for_embedding': f'[Episode] {worker_id} @ {timestamp}: {content}',
        })
    for conv_id, chat_id, sender_name, content, timestamp in conversations:
        all_records.append({
            'id': f'conv_{conv_id}',
            'db_id': conv_id,
            'type': 'conversation',
            'timestamp': timestamp,
            'chat_id': chat_id,
            'sender_name': sender_name or 'Unknown',
            'content': (content or '')[:500],
            'text_for_embedding': f'[Conversation] {sender_name or "Unknown"} @ {chat_id}: {content}',
        })

    total = len(all_records)
    log(f'total records to vectorize: {total}, workers={MAX_WORKERS}', log_file)

    vectors: List[np.ndarray] = [None] * total  # type: ignore
    metadata: List[dict] = [None] * total  # type: ignore
    start = time.time()
    processed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for batch_start in range(0, total, BATCH_SIZE):
            batch = list(enumerate(all_records[batch_start: batch_start + BATCH_SIZE], start=batch_start))
            for idx, vec, item in ex.map(embed_job, batch):
                vectors[idx] = vec
                metadata[idx] = item
                processed += 1

            elapsed = time.time() - start
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else None
            atomic_write_text(progress_file, json.dumps({
                'processed': processed,
                'total': total,
                'rate_rps': rate,
                'eta_seconds': eta,
                'updated_at': datetime.now().isoformat(),
                'workers': MAX_WORKERS,
                'batch_size': BATCH_SIZE,
            }, ensure_ascii=False, indent=2))
            log(f'progress {processed}/{total} ({processed/total*100:.2f}%), rate={rate:.2f}/s, eta_s={eta if eta is not None else "n/a"}', log_file)

    vectors_np = np.array(vectors, dtype=np.float32)
    if vectors_np.ndim != 2 or vectors_np.shape[1] != DIM:
        raise RuntimeError(f'bad vectors array shape: {vectors_np.shape}')

    index = faiss.IndexFlatL2(DIM)
    index.add(vectors_np)

    tmp_index = index_path.with_name(f'.{index_path.name}.{uuid4().hex}.tmp')
    faiss.write_index(index, str(tmp_index))
    os.replace(tmp_index, index_path)
    atomic_write_text(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2))

    ids = [m['id'] for m in metadata]
    unique_ids = len(set(ids))
    duplicates = len(ids) - unique_ids
    type_counter = Counter(m['type'] for m in metadata)

    report = {
        'generated_at': datetime.now().isoformat(),
        'candidate_dir': str(out_dir),
        'db_path': str(DB_PATH),
        'index_path': str(index_path),
        'metadata_path': str(metadata_path),
        'db_episodes': db_episodes,
        'db_conversations': db_conversations,
        'metadata_total': len(metadata),
        'metadata_type_counts': dict(type_counter),
        'unique_ids': unique_ids,
        'duplicates': duplicates,
        'index_ntotal': int(index.ntotal),
        'index_dim': int(index.d),
        'index_size_bytes': index_path.stat().st_size,
        'metadata_size_bytes': metadata_path.stat().st_size,
        'index_sha256': sha256(index_path),
        'metadata_sha256': sha256(metadata_path),
        'checks': {
            'metadata_equals_db_total': len(metadata) == (db_episodes + db_conversations),
            'index_ntotal_equals_metadata_total': int(index.ntotal) == len(metadata),
            'index_dim_expected_1024': int(index.d) == DIM,
            'duplicate_ids_zero': duplicates == 0,
            'episode_count_match': type_counter.get('episode', 0) == db_episodes,
            'conversation_count_match': type_counter.get('conversation', 0) == db_conversations,
        },
        'not_replaced_live_files': True,
        'rebuild_mode': 'parallel_ollama_run',
        'workers': MAX_WORKERS,
    }
    atomic_write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2))
    log(f'validation report written: {report_path}', log_file)
    log('done', log_file)


if __name__ == '__main__':
    main()
