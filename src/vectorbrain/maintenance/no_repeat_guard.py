#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List

HOME = Path.home()
WORKSPACE = HOME / '.openclaw' / 'workspace'
VECTORBRAIN = HOME / '.vectorbrain'
PENDING_QUEUE = VECTORBRAIN / 'state' / 'pending_notifications.json'
LAUNCH_AGENT_DIR = HOME / 'Library' / 'LaunchAgents'
DEFAULT_LABEL = 'ai.openclaw.gateway'


def sh(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def load_json(path: Path) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_pending_queue() -> Dict[str, Any]:
    out: Dict[str, Any] = {'check': 'pending_queue', 'ok': True, 'issues': [], 'facts': {}}
    if not PENDING_QUEUE.exists():
        out['ok'] = False
        out['issues'].append(f'missing file: {PENDING_QUEUE}')
        return out

    data = load_json(PENDING_QUEUE)
    notifications = data.get('notifications') if isinstance(data, dict) else None
    if not isinstance(notifications, list):
        out['ok'] = False
        out['issues'].append('notifications is not a list')
        return out

    pending = [n for n in notifications if n.get('status') in (None, 'pending', 'failed')]
    sent = [n for n in notifications if n.get('status') == 'sent']
    total = len(notifications)
    top_count = data.get('count')
    top_status = data.get('status')
    expected_count = len(pending)
    expected_status = 'pending' if pending else 'idle'
    top_level_legacy_fields = [k for k in ('type', 'title', 'description', 'reflections') if k in data]

    out['facts'] = {
        'file': str(PENDING_QUEUE),
        'total_count': total,
        'pending_count': len(pending),
        'sent_count': len(sent),
        'top_level_count': top_count,
        'expected_count': expected_count,
        'top_level_status': top_status,
        'expected_status': expected_status,
        'top_level_legacy_fields': top_level_legacy_fields,
    }

    if top_count != expected_count:
        out['ok'] = False
        out['issues'].append(f'count mismatch: top-level={top_count} expected={expected_count}')
    if top_status != expected_status:
        out['ok'] = False
        out['issues'].append(f'status mismatch: top-level={top_status} expected={expected_status}')
    if top_level_legacy_fields:
        out['issues'].append('top-level legacy payload fields still present; treat notifications[] as source of truth')

    return out


def check_launchagent(label: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {'check': 'launchagent', 'label': label, 'ok': True, 'issues': [], 'facts': {}}
    plist_path = LAUNCH_AGENT_DIR / f'{label}.plist'
    uid = os.getuid()
    facts: Dict[str, Any] = {'uid': uid, 'plist_path': str(plist_path), 'plist_exists': plist_path.exists()}

    plist_label = None
    if plist_path.exists():
        try:
            with open(plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
            plist_label = plist_data.get('Label')
            facts['plist_label'] = plist_label
            facts['program_arguments'] = plist_data.get('ProgramArguments')
        except Exception as e:
            out['ok'] = False
            out['issues'].append(f'plist parse failed: {e}')

    proc = sh(['launchctl', 'print', f'gui/{uid}/{label}'])
    facts['launchctl_print_rc'] = proc.returncode
    facts['launchctl_print_snippet'] = (proc.stdout or proc.stderr or '').splitlines()[:10]
    facts['loaded_in_gui_domain'] = proc.returncode == 0

    if plist_path.exists() and plist_label and plist_label != label:
        out['ok'] = False
        out['issues'].append(f'plist label mismatch: file implies {label}, plist has {plist_label}')
    if not facts['loaded_in_gui_domain']:
        out['issues'].append('service not found in launchctl gui domain; do not describe it as loaded/running')

    out['facts'] = facts
    return out


def check_path_rules() -> Dict[str, Any]:
    out: Dict[str, Any] = {'check': 'path_rules', 'ok': True, 'issues': [], 'facts': {}}
    out['facts'] = {
        'workspace_root': str(WORKSPACE),
        'vectorbrain_root': str(VECTORBRAIN),
        'direct_read_safe_root': str(WORKSPACE),
        'rules': [
            'read only workspace paths directly',
            'workspace-external files should be accessed via exec/tool, not read',
            'vectorbrain memory lives under ~/.vectorbrain, not ~/.openclaw/memory',
        ],
    }
    return out


def run_all(label: str) -> Dict[str, Any]:
    checks = [check_path_rules(), check_pending_queue(), check_launchagent(label)]
    ok = all(c.get('ok', False) for c in checks)
    return {'ok': ok, 'checks': checks}


def main() -> int:
    parser = argparse.ArgumentParser(description='No-repeat guard checks for recurring OpenClaw/VectorBrain failure modes.')
    parser.add_argument('--label', default=DEFAULT_LABEL, help='LaunchAgent label to inspect')
    parser.add_argument('--json', action='store_true', help='Output JSON only')
    args = parser.parse_args()

    result = run_all(args.label)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.json:
        print('\n判定口径：')
        print('- 路径：只有 workspace 内适合 direct read；workspace 外一律先想 exec/技能/一等工具。')
        print('- 队列：notifications[] 才是真相源；top-level count/status 必须和重算结果一致。')
        print('- LaunchAgent：plist 存在 ≠ 已加载；只有 launchctl print gui/$UID/<label> 成功，才可称 loaded。')
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
