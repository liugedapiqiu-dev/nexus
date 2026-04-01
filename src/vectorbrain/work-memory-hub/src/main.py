#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path.home() / '.vectorbrain' / 'work-memory-hub'
CONFIG_EXAMPLE = ROOT / 'configs' / 'config.example.json'
SHARED = {
    'memory_root': Path.home() / '.vectorbrain' / 'memory',
    'connector_root': Path.home() / '.vectorbrain' / 'connector',
    'monitor_root': Path.home() / '.vectorbrain' / 'monitor_center',
}


def status() -> int:
    payload = {
        'app': 'work-memory-hub',
        'root': str(ROOT),
        'config_example_exists': CONFIG_EXAMPLE.exists(),
        'shared_paths': {k: {'path': str(v), 'exists': v.exists()} for k, v in SHARED.items()},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='work-memory-hub scaffold entry')
    parser.add_argument('command', nargs='?', default='status', choices=['status'])
    args = parser.parse_args()
    if args.command == 'status':
        return status()
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
