#!/usr/bin/env python3
import json
import pathlib
import sqlite3
import subprocess
from typing import Any, Dict

HOME = pathlib.Path.home()
TASK_DB = HOME / '.vectorbrain' / 'tasks' / 'task_queue.db'
SESSIONS_FILE = HOME / '.openclaw' / 'agents' / 'main' / 'sessions' / 'sessions.json'


def run_json(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if p.returncode != 0:
            return {"ok": False, "error": (p.stderr or p.stdout).strip(), "cmd": cmd}
        text = (p.stdout or '').strip()
        start = text.find('{')
        if start < 0:
            return {"ok": False, "error": "no-json-object-found", "raw": text[:4000], "cmd": cmd}
        return {"ok": True, "data": json.loads(text[start:])}
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": cmd}


def gateway_truth() -> Dict[str, Any]:
    gw = run_json(['openclaw', 'gateway', 'status', '--json'])
    st = run_json(['openclaw', 'status', '--json'])
    out: Dict[str, Any] = {
        'source': '~/.vectorbrain/bin/openclaw_state_truth.py + openclaw gateway/status --json',
        'gatewayStatus': 'unknown',
        'serviceStatus': 'unknown',
        'serviceLoaded': None,
        'serviceRuntime': None,
        'rpcOk': None,
        'listening': [],
        'pid': None,
        'explanation': '',
        'raw': {}
    }
    if gw.get('ok'):
        data = gw['data']
        out['raw']['gatewayStatus'] = data
        svc = data.get('service', {})
        runtime = svc.get('runtime', {})
        port = data.get('port', {})
        listeners = port.get('listeners', []) or []
        out['serviceLoaded'] = svc.get('loaded')
        out['serviceRuntime'] = runtime.get('status')
        out['serviceStatus'] = f"{'loaded' if svc.get('loaded') else 'not_loaded'}/{runtime.get('status', 'unknown')}"
        out['rpcOk'] = data.get('rpc', {}).get('ok')
        out['listening'] = [x.get('address') for x in listeners if x.get('address')]
        if listeners:
            out['pid'] = listeners[0].get('pid')
    if st.get('ok'):
        data = st['data']
        out['raw']['status'] = data
        gw2 = data.get('gateway', {})
        gws = data.get('gatewayService', {})
        if gw2.get('reachable'):
            out['gatewayStatus'] = 'online'
        elif gw2.get('reachable') is False:
            out['gatewayStatus'] = 'offline'
        if out['serviceLoaded'] is None:
            out['serviceLoaded'] = gws.get('installed')
        if out['serviceRuntime'] is None:
            out['serviceRuntime'] = gws.get('runtimeShort')
    if out['gatewayStatus'] == 'online' and out['serviceRuntime'] == 'stopped' and out['listening']:
        out['explanation'] = 'Gateway 真在监听且 RPC 可达，但当前不是由 LaunchAgent 真托管；属于“手动进程在线 / LaunchAgent 显示 stopped”的分叉状态。'
    elif out['gatewayStatus'] == 'online':
        out['explanation'] = 'Gateway 在线。'
    elif out['gatewayStatus'] == 'offline':
        out['explanation'] = 'Gateway 不可达。'
    else:
        out['explanation'] = 'Gateway 状态未能可靠判定。'
    return out


def queue_truth() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        'source': str(TASK_DB),
        'exists': TASK_DB.exists(),
        'waiting': 0,
        'running': 0,
        'completed': 0,
        'failed': 0,
        'total': 0,
        'anomalies': [],
        'blocking': False,
    }
    if not TASK_DB.exists():
        out['anomalies'].append({'type': 'missing-db', 'detail': str(TASK_DB)})
        return out
    conn = sqlite3.connect(TASK_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("select status, count(*) c from tasks group by status order by status").fetchall()
        raw = {r['status']: r['c'] for r in rows}
        out['rawByStatus'] = raw
        out['waiting'] = conn.execute("select count(*) from tasks where status='pending'").fetchone()[0]
        out['running'] = conn.execute("select count(*) from tasks where status='running' and completed_at is null").fetchone()[0]
        out['completed'] = conn.execute("select count(*) from tasks where status='done' or (completed_at is not null and ifnull(status,'') not in ('failed'))").fetchone()[0]
        out['failed'] = conn.execute("select count(*) from tasks where status='failed'").fetchone()[0]
        out['total'] = conn.execute("select count(*) from tasks").fetchone()[0]
        stale = conn.execute("select task_id,title,status,assigned_worker,updated_at,completed_at,result from tasks where status='running' and completed_at is not null limit 20").fetchall()
        if stale:
            out['anomalies'].append({
                'type': 'stale-running-completed',
                'count': len(stale),
                'examples': [dict(r) for r in stale[:3]],
                'explanation': '这些记录 status 仍是 running，但 completed_at/result 已表明其实际上已完成；显示层不应直接把它们计为执行中。'
            })
        out['blocking'] = out['running'] > 0 and out['waiting'] > 0
        return out
    finally:
        conn.close()


def sessions_truth() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        'source': str(SESSIONS_FILE),
        'exists': SESSIONS_FILE.exists(),
        'count': 0,
        'recent': [],
        'anomalies': []
    }
    if not SESSIONS_FILE.exists():
        return out
    try:
        data = json.loads(SESSIONS_FILE.read_text())
        out['count'] = len(data)
        items = sorted(data.items(), key=lambda kv: kv[1].get('updatedAt', 0), reverse=True)
        for key, meta in items[:8]:
            delivery = meta.get('deliveryContext') or {}
            channel = meta.get('channel') or meta.get('lastChannel') or delivery.get('channel') or 'unknown'
            display = meta.get('displayName') or meta.get('subject') or meta.get('lastTo') or key
            out['recent'].append({
                'key': key,
                'sessionId': meta.get('sessionId'),
                'updatedAt': meta.get('updatedAt'),
                'channel': channel,
                'displayName': display,
                'deliveryContext': delivery,
                'abortedLastRun': bool(meta.get('abortedLastRun')),
            })
        missing_delivery = [k for k, v in items[:20] if not (v.get('deliveryContext') or {}).get('channel') and not v.get('channel') and not v.get('lastChannel')]
        if missing_delivery:
            out['anomalies'].append({
                'type': 'missing-delivery-channel',
                'count': len(missing_delivery),
                'examples': missing_delivery[:5],
                'explanation': '部分 session 元数据没有明确 channel，只能回退推断。显示层应优先读 deliveryContext.channel，再回退 lastChannel/channel。'
            })
    except Exception as e:
        out['anomalies'].append({'type': 'read-error', 'detail': str(e)})
    return out


if __name__ == '__main__':
    print(json.dumps({
        'gateway': gateway_truth(),
        'queue': queue_truth(),
        'sessions': sessions_truth(),
    }, ensure_ascii=False, indent=2, default=str))
