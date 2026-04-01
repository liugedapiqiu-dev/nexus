#!/usr/bin/env python3
"""VectorBrain lessons memory minimal adapter.

Phase 3 goal:
- formalize one non-intrusive writer for lessons_memory.db
- keep reflections / knowledge / episodic schemas untouched
- provide a tiny retrieval/view path without changing main knowledge retrieval
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
LESSONS_DB = VECTORBRAIN_ROOT / 'memory' / 'lessons_memory.db'
ALLOWED_SEVERITIES = {'low', 'medium', 'high', 'critical'}


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'


def _normalize_text(value: Optional[str]) -> str:
    return (value or '').strip()


def _normalize_severity(value: Optional[str]) -> str:
    severity = (_normalize_text(value) or 'medium').lower()
    return severity if severity in ALLOWED_SEVERITIES else 'medium'


def _slug(value: str) -> str:
    cleaned = ''.join(ch.lower() if ch.isalnum() else '_' for ch in value.strip())
    while '__' in cleaned:
        cleaned = cleaned.replace('__', '_')
    return cleaned.strip('_') or 'lesson'


def build_lesson_key(title: str, source_system: str, prevention_rule: str, scenario: str = '') -> str:
    parts = [_slug(source_system or 'vectorbrain'), _slug(title or 'lesson')]
    fingerprint = ' | '.join([
        _normalize_text(source_system),
        _normalize_text(title),
        _normalize_text(prevention_rule),
        _normalize_text(scenario),
    ])
    digest = hashlib.sha1(fingerprint.encode('utf-8')).hexdigest()[:12]
    return '.'.join([p for p in parts if p] + [digest])


def build_embedding_text(payload: Dict[str, Any]) -> str:
    ordered = [
        payload.get('title', ''),
        payload.get('scenario', ''),
        payload.get('symptom', ''),
        payload.get('root_cause', ''),
        payload.get('correct_action', ''),
        payload.get('prevention_rule', ''),
        payload.get('keywords', ''),
    ]
    return '\n'.join([_normalize_text(x) for x in ordered if _normalize_text(x)])


@dataclass
class LessonRecord:
    lesson_key: str
    title: str
    scenario: str = ''
    symptom: str = ''
    root_cause: str = ''
    correct_action: str = ''
    prevention_rule: str = ''
    keywords: str = ''
    severity: str = 'medium'
    source_system: str = 'vectorbrain'
    source_path: str = ''
    embedding_text: str = ''

    def as_db_tuple(self) -> tuple:
        return (
            self.lesson_key,
            self.title,
            self.scenario,
            self.symptom,
            self.root_cause,
            self.correct_action,
            self.prevention_rule,
            self.keywords,
            self.severity,
            self.source_system,
            self.source_path,
            self.embedding_text or build_embedding_text(self.__dict__),
        )


def _connect() -> sqlite3.Connection:
    LESSONS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(LESSONS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


def ensure_lessons_schema() -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_key TEXT,
            title TEXT NOT NULL,
            scenario TEXT,
            symptom TEXT,
            root_cause TEXT,
            correct_action TEXT,
            prevention_rule TEXT,
            keywords TEXT,
            severity TEXT DEFAULT 'medium',
            source_system TEXT,
            source_path TEXT,
            embedding_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    cur.execute('CREATE INDEX IF NOT EXISTS idx_lessons_severity ON lessons(severity)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_lessons_source_system ON lessons(source_system)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_lessons_created_at ON lessons(created_at)')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_lessons_lesson_key_unique ON lessons(lesson_key)')
    conn.commit()
    conn.close()


def write_lesson(*, title: str, scenario: str, root_cause: str, correct_action: str,
                 prevention_rule: str, source_system: str, symptom: str = '', keywords: str = '',
                 severity: str = 'medium', source_path: str = '', lesson_key: Optional[str] = None) -> Dict[str, Any]:
    """Canonical minimal writer for lessons_memory.db."""
    ensure_lessons_schema()

    title = _normalize_text(title)
    scenario = _normalize_text(scenario)
    root_cause = _normalize_text(root_cause)
    correct_action = _normalize_text(correct_action)
    prevention_rule = _normalize_text(prevention_rule)
    source_system = _normalize_text(source_system)
    symptom = _normalize_text(symptom)
    keywords = _normalize_text(keywords)
    severity = _normalize_severity(severity)
    source_path = _normalize_text(source_path)

    missing = [name for name, value in [
        ('title', title),
        ('scenario', scenario),
        ('root_cause', root_cause),
        ('correct_action', correct_action),
        ('prevention_rule', prevention_rule),
        ('source_system', source_system),
    ] if not value]
    if missing:
        raise ValueError(f"missing required lesson fields: {', '.join(missing)}")

    lesson_key = lesson_key or build_lesson_key(
        title=title,
        source_system=source_system,
        prevention_rule=prevention_rule,
        scenario=scenario,
    )
    record = LessonRecord(
        lesson_key=lesson_key,
        title=title,
        scenario=scenario,
        symptom=symptom,
        root_cause=root_cause,
        correct_action=correct_action,
        prevention_rule=prevention_rule,
        keywords=keywords,
        severity=severity,
        source_system=source_system,
        source_path=source_path,
    )

    now = _utc_now()
    conn = _connect()
    cur = conn.cursor()
    existing = cur.execute('SELECT id FROM lessons WHERE lesson_key = ?', (record.lesson_key,)).fetchone()

    if existing:
        cur.execute(
            '''
            UPDATE lessons
            SET title = ?, scenario = ?, symptom = ?, root_cause = ?, correct_action = ?,
                prevention_rule = ?, keywords = ?, severity = ?, source_system = ?, source_path = ?,
                embedding_text = ?, updated_at = ?
            WHERE lesson_key = ?
            ''',
            (
                record.title,
                record.scenario,
                record.symptom,
                record.root_cause,
                record.correct_action,
                record.prevention_rule,
                record.keywords,
                record.severity,
                record.source_system,
                record.source_path,
                record.embedding_text or build_embedding_text(record.__dict__),
                now,
                record.lesson_key,
            ),
        )
        lesson_id = int(existing['id'])
        action = 'updated'
    else:
        cur.execute(
            '''
            INSERT INTO lessons (
                lesson_key, title, scenario, symptom, root_cause, correct_action,
                prevention_rule, keywords, severity, source_system, source_path,
                embedding_text, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            record.as_db_tuple() + (now, now),
        )
        lesson_id = int(cur.lastrowid)
        action = 'inserted'

    conn.commit()
    conn.close()
    return {'status': action, 'lesson_id': lesson_id, 'lesson_key': record.lesson_key, 'db_path': str(LESSONS_DB)}


def get_lesson(lesson_key: str) -> Optional[Dict[str, Any]]:
    ensure_lessons_schema()
    key = _normalize_text(lesson_key)
    if not key:
        raise ValueError('lesson_key is required')

    conn = _connect()
    cur = conn.cursor()
    row = cur.execute('SELECT * FROM lessons WHERE lesson_key = ?', (key,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def search_lessons(query: str, limit: int = 10, source_system: Optional[str] = None,
                   severity: Optional[str] = None) -> List[Dict[str, Any]]:
    ensure_lessons_schema()
    q = _normalize_text(query)
    source_system = _normalize_text(source_system)
    severity = _normalize_severity(severity) if _normalize_text(severity) else ''
    conn = _connect()
    cur = conn.cursor()

    filters = []
    filter_params: List[Any] = []
    if source_system:
        filters.append('source_system = ?')
        filter_params.append(source_system)
    if severity:
        filters.append('severity = ?')
        filter_params.append(severity)
    where_prefix = f"WHERE {' AND '.join(filters)}" if filters else ''

    if not q:
        sql = f'SELECT * FROM lessons {where_prefix} ORDER BY datetime(updated_at) DESC, id DESC LIMIT ?'
        rows = cur.execute(sql, filter_params + [limit]).fetchall()
    else:
        like = f'%{q}%'
        query_filters = [
            'title LIKE ?', 'scenario LIKE ?', 'symptom LIKE ?', 'root_cause LIKE ?',
            'correct_action LIKE ?', 'prevention_rule LIKE ?', 'keywords LIKE ?',
            'embedding_text LIKE ?', 'lesson_key LIKE ?'
        ]
        text_clause = ' OR '.join(query_filters)
        sql = f'''
            SELECT * FROM lessons
            WHERE ({text_clause})
            {'AND ' + ' AND '.join(filters) if filters else ''}
            ORDER BY
                CASE WHEN title LIKE ? THEN 3 ELSE 0 END +
                CASE WHEN prevention_rule LIKE ? THEN 2 ELSE 0 END +
                CASE WHEN root_cause LIKE ? THEN 1 ELSE 0 END DESC,
                datetime(updated_at) DESC,
                id DESC
            LIMIT ?
        '''
        params = [like] * 9 + filter_params + [like, like, like, limit]
        rows = cur.execute(sql, params).fetchall()

    out = [dict(row) for row in rows]
    conn.close()
    return out


def get_recent_lessons(limit: int = 10, source_system: Optional[str] = None,
                       severity: Optional[str] = None) -> List[Dict[str, Any]]:
    return search_lessons('', limit=limit, source_system=source_system, severity=severity)


__all__ = [
    'LESSONS_DB',
    'build_embedding_text',
    'build_lesson_key',
    'ensure_lessons_schema',
    'get_lesson',
    'get_recent_lessons',
    'search_lessons',
    'write_lesson',
]
