#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / '.vectorbrain'
CONFIG_PATH = ROOT / 'maintenance' / 'stability_config.json'


def now_iso():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p))


def append_log(path: Path, line: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(line.rstrip() + '\n')


def main():
    ap = argparse.ArgumentParser(description='Guard and optionally repair stale task queue items')
    ap.add_argument('--apply', action='store_true', help='Apply repairs instead of dry-run')
    args = ap.parse_args()

    cfg = load_config()
    task_cfg = cfg['task_queue']
    out_cfg = cfg['outputs']
    db_path = expand(task_cfg['db_path'])
    log_path = expand(out_cfg['repair_log'])
    stale_m = int(task_cfg.get('stale_running_minutes', 45))
    max_retry = int(task_cfg.get('max_retry_ceiling', 3))
    quarantine_status = task_cfg.get('quarantine_status', 'failed')
    prefix = task_cfg.get('repair_note_prefix', 'stability_guard')

    if not db_path.exists():
        print(json.dumps({'ok': False, 'error': f'missing db: {db_path}'}))
        return 2

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    status_counts = [dict(r) for r in cur.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status ORDER BY count DESC")]
    stale_running = [dict(r) for r in cur.execute(
        """
        SELECT task_id,title,status,assigned_worker,created_at,updated_at,retry_count,max_retries,last_error
        FROM tasks
        WHERE status='running'
          AND COALESCE(datetime(replace(updated_at,'T',' ')), datetime(updated_at), datetime(created_at))
              < datetime('now', ?)
        ORDER BY COALESCE(datetime(replace(updated_at,'T',' ')), datetime(updated_at), datetime(created_at)) ASC
        """,
        (f'-{stale_m} minutes',)
    )]
    exhausted = [dict(r) for r in cur.execute(
        """
        SELECT task_id,title,status,assigned_worker,created_at,updated_at,retry_count,max_retries,last_error
        FROM tasks
        WHERE status IN ('queued','pending','running','failed')
          AND COALESCE(retry_count,0) >= COALESCE(NULLIF(max_retries,0), ?)
        ORDER BY updated_at ASC
        """,
        (max_retry,)
    )]

    actions = []
    if args.apply:
        for row in stale_running:
            task_id = row['task_id']
            note = f"{prefix}: auto-quarantined stale running task at {now_iso()}"
            cur.execute(
                """
                UPDATE tasks
                   SET status=?,
                       error_message=COALESCE(error_message,'') || CASE WHEN COALESCE(error_message,'')='' THEN ? ELSE '\n' || ? END,
                       last_error=?,
                       updated_at=CURRENT_TIMESTAMP
                 WHERE task_id=?
                """,
                (quarantine_status, note, note, note, task_id)
            )
            actions.append({'task_id': task_id, 'action': 'quarantine_stale_running'})
        for row in exhausted:
            if row['status'] == quarantine_status:
                continue
            task_id = row['task_id']
            note = f"{prefix}: retry ceiling reached at {now_iso()}"
            cur.execute(
                """
                UPDATE tasks
                   SET status=?,
                       error_message=COALESCE(error_message,'') || CASE WHEN COALESCE(error_message,'')='' THEN ? ELSE '\n' || ? END,
                       last_error=?,
                       updated_at=CURRENT_TIMESTAMP
                 WHERE task_id=?
                """,
                (quarantine_status, note, note, note, task_id)
            )
            actions.append({'task_id': task_id, 'action': 'quarantine_retry_exhausted'})
        conn.commit()
        for action in actions:
            append_log(log_path, json.dumps({'ts': now_iso(), **action}, ensure_ascii=False))

    result = {
        'ok': True,
        'mode': 'apply' if args.apply else 'dry-run',
        'ts': now_iso(),
        'status_counts': status_counts,
        'stale_running_count': len(stale_running),
        'stale_running': stale_running,
        'retry_exhausted_count': len(exhausted),
        'retry_exhausted': exhausted,
        'actions': actions,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
