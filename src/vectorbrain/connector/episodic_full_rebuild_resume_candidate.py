#!/usr/bin/env python3
"""
在既有 candidate 目录内进行可恢复的 episodic 全量重建。
特点：
- 不覆盖现网 index / metadata
- 仅读取 episodic_memory.db
- 以 batch shard 落盘，支持中断后继续
- 最终在 candidate 目录写出 episodic.index / episodic_metadata.json / validation_report.json
"""

import json
import os
import shutil
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


def sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


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


def build_records() -> Tuple[List[dict], int, int]:
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    db_episodes = cur.execute('select count(*) from episodes').fetchone()[0]
    db_conversations = cur.execute('select count(*) from conversations').fetchone()[0]

    cur.execute('SELECT id, timestamp, worker_id, event_type, content FROM episodes ORDER BY id')
    episodes = cur.fetchall()
    cur.execute('SELECT id, chat_id, sender_name, content, timestamp FROM conversations ORDER BY id')
    conversations = cur.fetchall()
    conn.close()

    all_records = []
    for ep_id, timestamp, worker_id, event_type, content in episodes:
        content = content or ''
        all_records.append({
            'id': f'ep_{ep_id}',
            'db_id': ep_id,
            'type': 'episode',
            'timestamp': timestamp,
            'worker_id': worker_id,
            'event_type': event_type,
            'content': content[:500],
            'text_for_embedding': f'[Episode] {worker_id} @ {timestamp}: {content}',
        })
    for conv_id, chat_id, sender_name, content, timestamp in conversations:
        content = content or ''
        all_records.append({
            'id': f'conv_{conv_id}',
            'db_id': conv_id,
            'type': 'conversation',
            'timestamp': timestamp,
            'chat_id': chat_id,
            'sender_name': sender_name or 'Unknown',
            'content': content[:500],
            'text_for_embedding': f'[Conversation] {sender_name or "Unknown"} @ {chat_id}: {content}',
        })
    return all_records, db_episodes, db_conversations


def shard_paths(shards_dir: Path, batch_start: int, batch_end: int) -> Tuple[Path, Path]:
    stem = f'{batch_start:06d}-{batch_end:06d}'
    return shards_dir / f'{stem}.npy', shards_dir / f'{stem}.json'


def load_existing_shard_count(shards_dir: Path, total: int) -> int:
    done = 0
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE - 1, total - 1)
        npy_path, json_path = shard_paths(shards_dir, batch_start, batch_end)
        if npy_path.exists() and json_path.exists():
            try:
                arr = np.load(npy_path)
                meta = json.loads(json_path.read_text(encoding='utf-8'))
                expected = batch_end - batch_start + 1
                if arr.shape == (expected, DIM) and isinstance(meta, list) and len(meta) == expected:
                    done += expected
                    continue
            except Exception:
                pass
        break
    return done


def write_progress(progress_file: Path, processed: int, total: int, start_ts: float, note: str = ''):
    elapsed = time.time() - start_ts
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
        'mode': 'resume_sharded',
        'note': note,
    }, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: episodic_full_rebuild_resume_candidate.py <candidate_dir>')

    out_dir = Path(sys.argv[1]).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = out_dir / 'rebuild.log'
    progress_file = out_dir / 'progress.json'
    index_path = out_dir / 'episodic.index'
    metadata_path = out_dir / 'episodic_metadata.json'
    report_path = out_dir / 'validation_report.json'
    shards_dir = out_dir / 'shards'
    shards_dir.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        raise RuntimeError(f'db missing: {DB_PATH}')
    if not Path(OLLAMA_BIN).exists():
        raise RuntimeError(f'ollama missing: {OLLAMA_BIN}')

    log(f'resume rebuild in candidate dir: {out_dir}', log_file)
    ver = subprocess.run([OLLAMA_BIN, '--version'], capture_output=True, text=True, timeout=15)
    if ver.returncode != 0:
        raise RuntimeError(f'ollama --version failed: {ver.stderr[:200]}')
    log(f'ollama version: {ver.stdout.strip()}', log_file)

    probe = get_embedding('healthcheck')
    log(f'embedding probe ok, dim={probe.shape[0]}', log_file)

    all_records, db_episodes, db_conversations = build_records()
    total = len(all_records)
    log(f'db counts: episodes={db_episodes}, conversations={db_conversations}', log_file)
    log(f'total records to vectorize: {total}, workers={MAX_WORKERS}, batch_size={BATCH_SIZE}', log_file)

    already_done = load_existing_shard_count(shards_dir, total)
    if already_done > 0:
        log(f'found resumable shards: {already_done}/{total}', log_file)
    else:
        prior_progress = None
        if progress_file.exists():
            try:
                prior_progress = json.loads(progress_file.read_text(encoding='utf-8')).get('processed')
            except Exception:
                prior_progress = None
        if prior_progress:
            log(f'found prior progress.json processed={prior_progress}, but no valid persisted shards/vectors exist; recomputing from start is required', log_file)
        else:
            log('no existing shards found; starting shard generation from start', log_file)

    # remove stale final outputs before regeneration in candidate dir only
    for p in [index_path, metadata_path, report_path]:
        if p.exists():
            bak = p.with_suffix(p.suffix + '.stale')
            if bak.exists():
                bak.unlink()
            p.rename(bak)
            log(f'moved stale output aside: {p.name} -> {bak.name}', log_file)

    start = time.time()
    processed = already_done
    write_progress(progress_file, processed, total, start, note='resuming from shard cache')

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE - 1, total - 1)
            expected = batch_end - batch_start + 1
            npy_path, json_path = shard_paths(shards_dir, batch_start, batch_end)

            if npy_path.exists() and json_path.exists():
                try:
                    arr = np.load(npy_path)
                    meta = json.loads(json_path.read_text(encoding='utf-8'))
                    if arr.shape == (expected, DIM) and isinstance(meta, list) and len(meta) == expected:
                        continue
                except Exception:
                    log(f'stale/corrupt shard detected, rebuilding batch {batch_start}-{batch_end}', log_file)

            batch = list(enumerate(all_records[batch_start: batch_end + 1], start=batch_start))
            batch_vectors: List[np.ndarray] = [None] * expected  # type: ignore
            batch_meta: List[dict] = [None] * expected  # type: ignore
            for idx, vec, item in ex.map(embed_job, batch):
                pos = idx - batch_start
                batch_vectors[pos] = vec
                batch_meta[pos] = item

            arr = np.array(batch_vectors, dtype=np.float32)
            if arr.shape != (expected, DIM):
                raise RuntimeError(f'batch array shape mismatch for {batch_start}-{batch_end}: {arr.shape}')

            tmp_npy = npy_path.with_name(f'.{npy_path.name}.{uuid4().hex}.tmp')
            with open(tmp_npy, 'wb') as f:
                np.save(f, arr)
            os.replace(tmp_npy, npy_path)
            atomic_write_text(json_path, json.dumps(batch_meta, ensure_ascii=False, indent=2))

            processed = batch_end + 1
            write_progress(progress_file, processed, total, start, note=f'sharded up to {batch_end}')
            elapsed = time.time() - start
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else None
            log(f'progress {processed}/{total} ({processed/total*100:.2f}%), rate={rate:.2f}/s, eta_s={eta if eta is not None else "n/a"}', log_file)

    log('all shards ready; assembling final metadata and index', log_file)
    index = faiss.IndexFlatL2(DIM)
    all_meta: List[dict] = []
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE - 1, total - 1)
        npy_path, json_path = shard_paths(shards_dir, batch_start, batch_end)
        if not (npy_path.exists() and json_path.exists()):
            raise RuntimeError(f'missing shard during assembly: {npy_path.name}')
        arr = np.load(npy_path)
        meta = json.loads(json_path.read_text(encoding='utf-8'))
        if arr.ndim != 2 or arr.shape[1] != DIM:
            raise RuntimeError(f'bad shard vector shape: {npy_path.name} -> {arr.shape}')
        if arr.shape[0] != len(meta):
            raise RuntimeError(f'shard vector/meta size mismatch: {npy_path.name} -> {arr.shape[0]} vs {len(meta)}')
        index.add(arr)
        all_meta.extend(meta)

    tmp_index = index_path.with_name(f'.{index_path.name}.{uuid4().hex}.tmp')
    faiss.write_index(index, str(tmp_index))
    os.replace(tmp_index, index_path)
    atomic_write_text(metadata_path, json.dumps(all_meta, ensure_ascii=False, indent=2))

    ids = [m['id'] for m in all_meta]
    unique_ids = len(set(ids))
    duplicates = len(ids) - unique_ids
    type_counter = Counter(m['type'] for m in all_meta)
    checks = {
        'metadata_equals_db_total': len(all_meta) == (db_episodes + db_conversations),
        'index_ntotal_equals_metadata_total': int(index.ntotal) == len(all_meta),
        'index_dim_expected_1024': int(index.d) == DIM,
        'duplicate_ids_zero': duplicates == 0,
        'episode_count_match': type_counter.get('episode', 0) == db_episodes,
        'conversation_count_match': type_counter.get('conversation', 0) == db_conversations,
    }
    passed = all(checks.values())

    report = {
        'generated_at': datetime.now().isoformat(),
        'candidate_dir': str(out_dir),
        'db_path': str(DB_PATH),
        'index_path': str(index_path),
        'metadata_path': str(metadata_path),
        'db_episodes': db_episodes,
        'db_conversations': db_conversations,
        'metadata_total': len(all_meta),
        'metadata_type_counts': dict(type_counter),
        'unique_ids': unique_ids,
        'duplicates': duplicates,
        'index_ntotal': int(index.ntotal),
        'index_dim': int(index.d),
        'index_size_bytes': index_path.stat().st_size,
        'metadata_size_bytes': metadata_path.stat().st_size,
        'index_sha256': sha256(index_path),
        'metadata_sha256': sha256(metadata_path),
        'checks': checks,
        'passed': passed,
        'not_replaced_live_files': True,
        'rebuild_mode': 'resume_sharded_ollama_run',
        'workers': MAX_WORKERS,
        'batch_size': BATCH_SIZE,
        'shards_dir': str(shards_dir),
        'shard_file_count': len(list(shards_dir.glob('*.npy'))),
    }
    atomic_write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2))
    write_progress(progress_file, total, total, start, note='completed')
    log(f'validation report written: {report_path}', log_file)
    log(f'passed={passed}', log_file)
    log('done', log_file)


if __name__ == '__main__':
    main()
