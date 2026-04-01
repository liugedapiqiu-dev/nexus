#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, sqlite3, subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / '.vectorbrain'
CONFIG_PATH = ROOT / 'maintenance' / 'stability_config.json'


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p))


def now_iso():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def read_json(path: Path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def file_age_minutes(path: Path):
    if not path.exists():
        return None
    return round((datetime.now().timestamp() - path.stat().st_mtime) / 60, 1)


def pgrep(pattern: str):
    try:
        res = subprocess.run(['pgrep', '-fl', pattern], capture_output=True, text=True, timeout=5)
        lines = [x.strip() for x in res.stdout.splitlines() if x.strip()]
        return lines
    except Exception:
        return []


def task_queue_report(db_path: Path, stale_minutes: int):
    if not db_path.exists():
        return {'exists': False, 'error': str(db_path)}
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    status_counts = [dict(r) for r in cur.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status ORDER BY count DESC")]
    stale_running = [dict(r) for r in cur.execute(
        """
        SELECT task_id,title,status,assigned_worker,created_at,updated_at,retry_count,max_retries
        FROM tasks
        WHERE status='running'
          AND COALESCE(datetime(replace(updated_at,'T',' ')), datetime(updated_at), datetime(created_at))
              < datetime('now', ?)
        ORDER BY updated_at ASC
        LIMIT 20
        """,
        (f'-{stale_minutes} minutes',)
    )]
    recent_non_done = [dict(r) for r in cur.execute(
        "SELECT task_id,title,status,priority,assigned_worker,updated_at FROM tasks WHERE status != 'done' ORDER BY updated_at ASC LIMIT 20"
    )]
    return {
        'exists': True,
        'status_counts': status_counts,
        'stale_running': stale_running,
        'recent_non_done': recent_non_done,
    }


def log_report(targets, freshness_minutes):
    rows = []
    for raw in targets:
        p = expand(raw)
        age = file_age_minutes(p)
        rows.append({
            'path': str(p),
            'exists': p.exists(),
            'age_minutes': age,
            'fresh': (age is not None and age <= freshness_minutes),
            'size_bytes': p.stat().st_size if p.exists() else None,
        })
    return rows


def process_report(patterns):
    rows = []
    for pat in patterns:
        matches = pgrep(pat)
        rows.append({'pattern': pat, 'running': len(matches) > 0, 'matches': matches[:10]})
    return rows


def pending_notification_report():
    data = read_json(ROOT / 'state' / 'pending_notifications.json', {}) or {}
    notifs = data.get('notifications') or []
    failed = [n for n in notifs if n.get('status') == 'failed']
    pending = [n for n in notifs if n.get('status') in (None, 'pending', 'failed')]
    return {
        'status': data.get('status'),
        'count': data.get('count'),
        'pending_count': len(pending),
        'failed_count': len(failed),
        'sample': pending[:5],
    }


def derive_findings(task_q, logs, procs, pending):
    findings = []
    if task_q.get('stale_running'):
        findings.append({'severity': 'high', 'kind': 'stale_running_tasks', 'count': len(task_q['stale_running'])})
    stale_logs = [x for x in logs if x['exists'] and x['fresh'] is False]
    if stale_logs:
        findings.append({'severity': 'medium', 'kind': 'stale_logs', 'count': len(stale_logs), 'paths': [x['path'] for x in stale_logs[:5]]})
    down = [x for x in procs if not x['running']]
    if down:
        findings.append({'severity': 'medium', 'kind': 'expected_process_missing', 'count': len(down), 'patterns': [x['pattern'] for x in down]})
    if (pending.get('failed_count') or 0) > 0:
        findings.append({'severity': 'medium', 'kind': 'notification_queue_failed', 'count': pending['failed_count']})
    if not findings:
        findings.append({'severity': 'info', 'kind': 'healthy_enough', 'count': 1})
    return findings


def to_markdown(report):
    lines = []
    lines.append('# VectorBrain Stability Report')
    lines.append('')
    lines.append(f"- Generated: {report['ts']}")
    lines.append('')
    lines.append('## Findings')
    for f in report['findings']:
        lines.append(f"- [{f['severity']}] {f['kind']} x{f.get('count', 1)}")
    lines.append('')
    lines.append('## Task Queue')
    for row in report['task_queue'].get('status_counts', []):
        lines.append(f"- {row['status']}: {row['count']}")
    if report['task_queue'].get('stale_running'):
        lines.append('- stale_running:')
        for item in report['task_queue']['stale_running'][:10]:
            lines.append(f"  - {item['task_id']} | {item.get('title')} | updated_at={item.get('updated_at')}")
    lines.append('')
    lines.append('## Log Freshness')
    for row in report['logs']:
        lines.append(f"- {'OK' if row['fresh'] else 'STALE'} | {row['path']} | age_min={row['age_minutes']}")
    lines.append('')
    lines.append('## Expected Processes')
    for row in report['processes']:
        lines.append(f"- {'RUNNING' if row['running'] else 'MISSING'} | {row['pattern']}")
    lines.append('')
    lines.append('## Pending Notifications')
    pn = report['pending_notifications']
    lines.append(f"- status={pn.get('status')} pending={pn.get('pending_count')} failed={pn.get('failed_count')}")
    return '\n'.join(lines) + '\n'


def main():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    tq = task_queue_report(expand(cfg['task_queue']['db_path']), int(cfg['task_queue']['stale_running_minutes']))
    logs = log_report(cfg['logs']['targets'], int(cfg['logs']['freshness_minutes']))
    procs = process_report(cfg['processes']['expected_patterns'])
    pending = pending_notification_report()
    report = {
        'ts': now_iso(),
        'task_queue': tq,
        'logs': logs,
        'processes': procs,
        'pending_notifications': pending,
    }
    report['findings'] = derive_findings(tq, logs, procs, pending)
    json_path = expand(cfg['outputs']['report_json'])
    md_path = expand(cfg['outputs']['report_md'])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(to_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
