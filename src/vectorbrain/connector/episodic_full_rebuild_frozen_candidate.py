#!/usr/bin/env python3
"""
冻结边界的 episodic 全量候选重建（可续跑 / 持续写进度 / 最终校验）

特性：
- 先固化 freeze manifest（episodes/conversations max id + count）
- 后续恢复时严格只处理冻结边界内的数据，不追实时增长
- batch shard 落盘，可中断后继续
- 最终在 candidate 目录内写出 episodic.index / episodic_metadata.json / validation_report.json
- 不覆盖现网文件

用法：
  python3 episodic_full_rebuild_frozen_candidate.py --candidate-dir <dir>
  python3 episodic_full_rebuild_frozen_candidate.py --candidate-dir <dir> --freeze-episodes-max-id 123 --freeze-conversations-max-id 45
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

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
DEFAULT_BATCH_SIZE = 100
DEFAULT_MAX_WORKERS = 4


def atomic_write_text(path: Path, content: str, encoding: str = 'utf-8'):
    tmp = path.with_name(f'.{path.name}.{uuid4().hex}.tmp')
    tmp.write_text(content, encoding=encoding)
    os.replace(tmp, path)


def atomic_write_json(path: Path, data):
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


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


def sanitize_embedding_text(text: str) -> str:
    if text is None:
        return ''
    # 防止 subprocess argv 因 NUL 直接崩溃；同时尽量保留可读上下文
    text = text.replace('\x00', ' ')
    # 清理其他控制字符，避免二进制污染文本导致模型调用异常变慢
    text = ''.join(ch if (ch == '\n' or ch == '\t' or ord(ch) >= 32) else ' ' for ch in text)
    # 稳定优先：限制单条送入模型的文本长度，避免极端长文本卡住单次推理
    max_len = 4000
    if len(text) > max_len:
        text = text[:max_len]
    return text


def get_embedding(text: str) -> np.ndarray:
    safe_text = sanitize_embedding_text(text)
    result = subprocess.run(
        [OLLAMA_BIN, 'run', MODEL],
        input=safe_text,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(f'ollama failed: {result.stderr[:300]}')
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError('ollama returned empty output')
    try:
        vec = np.array(json.loads(stdout), dtype=np.float32)
    except Exception as e:
        raise RuntimeError(f'invalid vector json: {e}; out={stdout[:300]}') from e
    if vec.ndim != 1 or vec.shape[0] != DIM:
        raise RuntimeError(f'bad vector shape: {getattr(vec, "shape", None)}')
    return vec


def embed_job(args: Tuple[int, dict]) -> Tuple[int, np.ndarray, dict]:
    idx, record = args
    vec = get_embedding(record['text_for_embedding'])
    item = {k: v for k, v in record.items() if k != 'text_for_embedding'}
    return idx, vec, item


def preflight():
    if not DB_PATH.exists():
        raise RuntimeError(f'db missing: {DB_PATH}')
    if not Path(OLLAMA_BIN).exists():
        raise RuntimeError(f'ollama missing: {OLLAMA_BIN}')
    ver = subprocess.run([OLLAMA_BIN, '--version'], capture_output=True, text=True, timeout=15)
    if ver.returncode != 0:
        raise RuntimeError(f'ollama --version failed: {ver.stderr[:200]}')
    probe = get_embedding('healthcheck')
    if int(probe.shape[0]) != DIM:
        raise RuntimeError(f'embedding probe dim mismatch: {probe.shape}')
    return ver.stdout.strip()


def db_connect():
    return sqlite3.connect(str(DB_PATH))


def get_live_db_snapshot() -> Dict[str, int]:
    conn = db_connect()
    cur = conn.cursor()
    out = {
        'episodes_max_id': cur.execute('select coalesce(max(id), 0) from episodes').fetchone()[0],
        'episodes_count': cur.execute('select count(*) from episodes').fetchone()[0],
        'conversations_max_id': cur.execute('select coalesce(max(id), 0) from conversations').fetchone()[0],
        'conversations_count': cur.execute('select count(*) from conversations').fetchone()[0],
    }
    conn.close()
    return {k: int(v or 0) for k, v in out.items()}


def count_within_freeze(cur, table: str, max_id: int) -> int:
    return int(cur.execute(f'select count(*) from {table} where id <= ?', (max_id,)).fetchone()[0])


def create_or_load_freeze_manifest(candidate_dir: Path, ep_max_arg: Optional[int], conv_max_arg: Optional[int], log_file: Path) -> Dict:
    manifest_path = candidate_dir / 'freeze_manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        log(f'loaded existing freeze manifest: {manifest_path}', log_file)
        return manifest

    live = get_live_db_snapshot()
    episodes_max_id = int(ep_max_arg if ep_max_arg is not None else live['episodes_max_id'])
    conversations_max_id = int(conv_max_arg if conv_max_arg is not None else live['conversations_max_id'])

    conn = db_connect()
    cur = conn.cursor()
    episodes_count_frozen = count_within_freeze(cur, 'episodes', episodes_max_id)
    conversations_count_frozen = count_within_freeze(cur, 'conversations', conversations_max_id)
    conn.close()

    manifest = {
        'created_at': datetime.now().isoformat(),
        'db_path': str(DB_PATH),
        'freeze': {
            'episodes_max_id': episodes_max_id,
            'conversations_max_id': conversations_max_id,
        },
        'db_counts_at_freeze': {
            'episodes_count_frozen': episodes_count_frozen,
            'conversations_count_frozen': conversations_count_frozen,
            'total_frozen': episodes_count_frozen + conversations_count_frozen,
        },
        'live_db_snapshot_at_freeze_time': live,
        'policy': {
            'strict_id_boundary': True,
            'do_not_replace_live_files': True,
            'resume_only_with_same_manifest': True,
        },
        'rebuild_config': {
            'model': MODEL,
            'dim': DIM,
            'batch_size': DEFAULT_BATCH_SIZE,
            'max_workers': DEFAULT_MAX_WORKERS,
            'ollama_bin': OLLAMA_BIN,
        },
    }
    atomic_write_json(manifest_path, manifest)
    log(f'created freeze manifest: {manifest_path}', log_file)
    return manifest


def build_records_from_freeze(manifest: Dict) -> Tuple[List[dict], int, int]:
    ep_max = int(manifest['freeze']['episodes_max_id'])
    conv_max = int(manifest['freeze']['conversations_max_id'])

    conn = db_connect()
    cur = conn.cursor()

    db_episodes = count_within_freeze(cur, 'episodes', ep_max)
    db_conversations = count_within_freeze(cur, 'conversations', conv_max)

    cur.execute(
        'SELECT id, timestamp, worker_id, event_type, content FROM episodes WHERE id <= ? ORDER BY id',
        (ep_max,),
    )
    episodes = cur.fetchall()
    cur.execute(
        'SELECT id, chat_id, sender_name, content, timestamp FROM conversations WHERE id <= ? ORDER BY id',
        (conv_max,),
    )
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


def load_existing_shard_count(shards_dir: Path, total: int, batch_size: int) -> int:
    done = 0
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size - 1, total - 1)
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


def write_progress(progress_file: Path, manifest: Dict, processed: int, total: int, start_ts: float, max_workers: int, batch_size: int, note: str = ''):
    elapsed = time.time() - start_ts
    rate = processed / elapsed if elapsed > 0 else 0.0
    eta = (total - processed) / rate if rate > 0 else None
    atomic_write_json(progress_file, {
        'updated_at': datetime.now().isoformat(),
        'candidate_dir': str(progress_file.parent),
        'freeze': manifest['freeze'],
        'db_counts_at_freeze': manifest['db_counts_at_freeze'],
        'processed': processed,
        'total': total,
        'remaining': max(total - processed, 0),
        'rate_rps': rate,
        'eta_seconds': eta,
        'workers': max_workers,
        'batch_size': batch_size,
        'mode': 'frozen_resume_sharded',
        'note': note,
    })


def assemble_final_outputs(out_dir: Path, shards_dir: Path, total: int, db_episodes: int, db_conversations: int, manifest: Dict, log_file: Path, max_workers: int, batch_size: int):
    index_path = out_dir / 'episodic.index'
    metadata_path = out_dir / 'episodic_metadata.json'
    report_path = out_dir / 'validation_report.json'

    index = faiss.IndexFlatL2(DIM)
    all_meta: List[dict] = []
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size - 1, total - 1)
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
    atomic_write_json(metadata_path, all_meta)

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
        'freeze': manifest['freeze'],
        'db_counts_at_freeze': manifest['db_counts_at_freeze'],
        'db_path': str(DB_PATH),
        'index_path': str(index_path),
        'metadata_path': str(metadata_path),
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
        'rebuild_mode': 'frozen_resume_sharded_ollama_run',
        'workers': max_workers,
        'batch_size': batch_size,
        'shards_dir': str(shards_dir),
        'shard_file_count': len(list(shards_dir.glob('*.npy'))),
    }
    atomic_write_json(report_path, report)
    log(f'validation report written: {report_path}', log_file)
    log(f'passed={passed}', log_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate-dir', required=True)
    parser.add_argument('--freeze-episodes-max-id', type=int, default=None)
    parser.add_argument('--freeze-conversations-max-id', type=int, default=None)
    parser.add_argument('--max-workers', type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    max_workers = max(1, int(args.max_workers))
    batch_size = max(1, int(args.batch_size))

    out_dir = Path(args.candidate_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    shards_dir = out_dir / 'shards'
    shards_dir.mkdir(parents=True, exist_ok=True)

    log_file = out_dir / 'rebuild.log'
    progress_file = out_dir / 'progress.json'

    log(f'frozen rebuild candidate dir: {out_dir}', log_file)
    ollama_ver = preflight()
    log(f'preflight ok; ollama={ollama_ver}', log_file)

    manifest = create_or_load_freeze_manifest(
        out_dir,
        args.freeze_episodes_max_id,
        args.freeze_conversations_max_id,
        log_file,
    )
    log(f"freeze boundary: episodes_max_id={manifest['freeze']['episodes_max_id']}, conversations_max_id={manifest['freeze']['conversations_max_id']}", log_file)
    log(f"frozen db counts: episodes={manifest['db_counts_at_freeze']['episodes_count_frozen']}, conversations={manifest['db_counts_at_freeze']['conversations_count_frozen']}, total={manifest['db_counts_at_freeze']['total_frozen']}", log_file)

    all_records, db_episodes, db_conversations = build_records_from_freeze(manifest)
    total = len(all_records)
    if total != int(manifest['db_counts_at_freeze']['total_frozen']):
        raise RuntimeError(f'freeze count mismatch: built={total} manifest={manifest["db_counts_at_freeze"]["total_frozen"]}')

    already_done = load_existing_shard_count(shards_dir, total, batch_size)
    if already_done > 0:
        log(f'found resumable shards: {already_done}/{total}', log_file)
    else:
        log('no valid existing shards found; starting from batch 0', log_file)

    start = time.time()
    write_progress(progress_file, manifest, already_done, total, start, max_workers, batch_size, note='starting/resuming from shard cache')

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size - 1, total - 1)
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
            atomic_write_json(json_path, batch_meta)

            processed = batch_end + 1
            write_progress(progress_file, manifest, processed, total, start, max_workers, batch_size, note=f'sharded up to {batch_end}')
            elapsed = time.time() - start
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else None
            log(f'progress {processed}/{total} ({processed/total*100:.2f}%), rate={rate:.2f}/s, eta_s={eta if eta is not None else "n/a"}', log_file)

    log('all shards ready; assembling final metadata and index', log_file)
    assemble_final_outputs(out_dir, shards_dir, total, db_episodes, db_conversations, manifest, log_file, max_workers, batch_size)
    write_progress(progress_file, manifest, total, total, start, max_workers, batch_size, note='completed')
    log('done', log_file)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('interrupted', file=sys.stderr)
        sys.exit(130)
