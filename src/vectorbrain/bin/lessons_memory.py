#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.vectorbrain'))
from memory.lessons_adapter import get_lesson, get_recent_lessons, search_lessons, write_lesson


def main() -> int:
    parser = argparse.ArgumentParser(description='Minimal CLI for lessons_memory.db')
    sub = parser.add_subparsers(dest='cmd', required=True)

    w = sub.add_parser('write', help='write/upsert a lesson into lessons_memory.db')
    w.add_argument('--title', required=True)
    w.add_argument('--scenario', required=True)
    w.add_argument('--root-cause', required=True, dest='root_cause')
    w.add_argument('--correct-action', required=True, dest='correct_action')
    w.add_argument('--prevention-rule', required=True, dest='prevention_rule')
    w.add_argument('--source-system', required=True, dest='source_system')
    w.add_argument('--symptom', default='')
    w.add_argument('--keywords', default='')
    w.add_argument('--severity', default='medium')
    w.add_argument('--source-path', default='', dest='source_path')
    w.add_argument('--lesson-key', default='', dest='lesson_key')

    g = sub.add_parser('get', help='get one lesson by lesson_key')
    g.add_argument('lesson_key')

    s = sub.add_parser('search', help='search lessons db only')
    s.add_argument('query', nargs='?', default='')
    s.add_argument('--limit', type=int, default=10)
    s.add_argument('--source-system', default='', dest='source_system')
    s.add_argument('--severity', default='')

    r = sub.add_parser('recent', help='show recent lessons')
    r.add_argument('--limit', type=int, default=10)
    r.add_argument('--source-system', default='', dest='source_system')
    r.add_argument('--severity', default='')

    args = parser.parse_args()
    if args.cmd == 'write':
        result = write_lesson(
            title=args.title,
            scenario=args.scenario,
            root_cause=args.root_cause,
            correct_action=args.correct_action,
            prevention_rule=args.prevention_rule,
            source_system=args.source_system,
            symptom=args.symptom,
            keywords=args.keywords,
            severity=args.severity,
            source_path=args.source_path,
            lesson_key=args.lesson_key or None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == 'get':
        result = get_lesson(args.lesson_key)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result else 1
    if args.cmd == 'search':
        result = search_lessons(
            args.query,
            limit=args.limit,
            source_system=args.source_system or None,
            severity=args.severity or None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == 'recent':
        result = get_recent_lessons(
            limit=args.limit,
            source_system=args.source_system or None,
            severity=args.severity or None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
