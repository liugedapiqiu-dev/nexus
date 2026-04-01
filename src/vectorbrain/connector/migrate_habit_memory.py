#!/usr/bin/env python3
"""
迁移/补种 Habit Memory

目标：
- 把散落在 workspace / VectorBrain 文档里的“用户习惯 / 偏好 / 口径 / 表格填写风格”
  迁移到 ~/.vectorbrain/memory/habit_memory.db
- 保持幂等：重复执行不会无限重复写入
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List

VECTORBRAIN_ROOT = Path.home() / '.vectorbrain'
WORKSPACE = Path('/home/user/.openclaw/workspace')
HABIT_DB = VECTORBRAIN_ROOT / 'memory' / 'habit_memory.db'


SEED_RECORDS = [
    {
        'key': 'habit:feishu_bitable:table_ids_and_usage',
        'category': 'habit.feishu_bitable',
        'confidence': 0.95,
        'source': 'manual_seed',
        'content': '南野科技多维表格使用习惯：南野科技 app_token=UPcwbHbUwah0d4s937ncGpL1nQe；采购下单跟进表 table_id=tbliKfGvvbRNOM8z；采购任务明细 table_id=tblEjxQWrQyEihpu。遇到飞书多维表格问题时，应优先沿 VectorBrain 成功经验反查 app_token / table_id，而不是先走浏览器人工查找。',
    },
    {
        'key': 'habit:feishu_bitable:filling_style_purchase_task_detail',
        'category': 'habit.feishu_bitable_style',
        'confidence': 0.98,
        'source': 'manual_seed',
        'content': '[YOUR_NAME]在采购任务明细中的填写风格：更重视真实推进信息，而非形式化存档；字段填写偏好是短状态 + 具体进度说明 + 明确卡点 + 可执行需求描述。',
    },
    {
        'key': 'habit:feishu_bitable:filling_style_purchase_order_followup',
        'category': 'habit.feishu_bitable_style',
        'confidence': 0.97,
        'source': 'manual_seed',
        'content': '[YOUR_NAME]在采购下单跟进表中的填写习惯：先录入采购单号（PO）、日期、产品名称/型号/尺寸/数量/供应商/单价等核心下单信息；后续逐步补充跟进记录、已完成付款、实际应付金额、质检状态/结果/备注、出库时间、出货图。跟进记录风格偏一句话短进度，不写长篇。',
    },
    {
        'key': 'habit:communication:emoji_preference',
        'category': 'habit.communication',
        'confidence': 0.92,
        'source': str(WORKSPACE / 'memory/2026-03-16.md'),
        'content': '和[YOUR_NAME]对话时，多用一些自然的 emoji，减少冰冷感，让交流更亲近一些。',
    },
    {
        'key': 'habit:documentation:system_reports_location',
        'category': 'habit.documentation',
        'confidence': 0.94,
        'source': str(WORKSPACE / 'memory/2026-03-16.md'),
        'content': '像治疗报告、修复总结、维修记录这类系统报告，统一写在 ~/.vectorbrain/ 目录下，不要散落到 workspace/docs。',
    },
    {
        'key': 'habit:workflow:vectorbrain_retrieval_priority_for_personal_context',
        'category': 'habit.workflow',
        'confidence': 0.96,
        'source': str(WORKSPACE / 'AGENTS.md'),
        'content': '当问题涉及过去经验、项目上下文、个人习惯、历史决策时，优先走 VectorBrain 检索链路：先知识记忆，再文件记忆，再情景记忆；不要先凭印象回答。',
    },
]

# 轻量自动抽取规则：从部分文件里抓明显的“用户偏好/习惯”句子

NOISE_PATTERNS = [
    'session_history', '会话历史', 'batch_', 'skill_library', 'auto_extracted_', '日报', '工作日报'
]

def is_noise(category: str, key: str, value: str) -> bool:
    hay = f"{category} {key} {value}"
    return any(p in hay for p in NOISE_PATTERNS)

AUTO_SOURCE_FILES = [
    WORKSPACE / 'memory/2026-03-16.md',
    WORKSPACE / 'memory/2026-03-18.md',
    WORKSPACE / 'TOOLS.md',
    WORKSPACE / 'MEMORY.md',
    WORKSPACE / 'memory/2026-03-09-task-migration.md',
    WORKSPACE / 'memory/2026-03-10-skill-check.md',
]

PATTERNS = [
    re.compile(r'用户偏好[：: ](.+)'),
    re.compile(r'用户当前工作口径偏好已进一步明确[：: ](.+)'),
    re.compile(r'填写风格[：: ](.+)'),
    re.compile(r'填写习惯[：: ](.+)'),
    re.compile(r'更重视(.+)'),
    re.compile(r'统一写在 (.+)'),
    re.compile(r'多用一些自然的 emoji(.+)'),
]


def ensure_db() -> None:
    HABIT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(HABIT_DB)
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            source_worker TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            embedding_vector TEXT
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_habit_category ON knowledge(category)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_habit_key ON knowledge(key)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_habit_updated_at ON knowledge(updated_at)')
    conn.commit()
    conn.close()


def upsert_record(*, key: str, category: str, content: str, source: str, confidence: float = 1.0) -> None:
    payload = json.dumps(
        {
            'content': content,
            'source': source,
            'captured_at': datetime.now().isoformat(),
        },
        ensure_ascii=False,
    )
    now = datetime.now().isoformat()
    conn = sqlite3.connect(HABIT_DB)
    conn.execute(
        '''
        INSERT INTO knowledge (category, key, value, source_worker, confidence, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            category=excluded.category,
            value=excluded.value,
            source_worker=excluded.source_worker,
            confidence=excluded.confidence,
            updated_at=excluded.updated_at
        ''',
        (category, key, payload, 'habit_memory_migrator', confidence, now, now),
    )
    conn.commit()
    conn.close()


def seed_manual_records() -> int:
    n = 0
    for rec in SEED_RECORDS:
        upsert_record(
            key=rec['key'],
            category=rec['category'],
            content=rec['content'],
            source=rec['source'],
            confidence=rec['confidence'],
        )
        n += 1
    return n


def auto_extract_records() -> List[Dict]:
    found: List[Dict] = []
    seen = set()
    for path in AUTO_SOURCE_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        lines = [ln.strip('- ').strip() for ln in text.splitlines() if ln.strip()]
        for ln in lines:
            for pat in PATTERNS:
                m = pat.search(ln)
                if not m:
                    continue
                content = ln
                key = f"habit:auto:{path.stem}:{abs(hash(content)) % 10**10}"
                if key in seen:
                    continue
                seen.add(key)
                if is_noise('habit.auto_extracted', key, content):
                    continue
                found.append(
                    {
                        'key': key,
                        'category': 'habit.auto_extracted',
                        'content': content,
                        'source': str(path),
                        'confidence': 0.72,
                    }
                )
    return found


def main() -> None:
    ensure_db()
    seeded = seed_manual_records()
    auto_records = auto_extract_records()
    for rec in auto_records:
        if is_noise(rec['category'], rec['key'], rec['content']):
            continue
        upsert_record(**rec)

    conn = sqlite3.connect(HABIT_DB)
    total = conn.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0]
    samples = conn.execute('SELECT key, category FROM knowledge ORDER BY updated_at DESC LIMIT 20').fetchall()
    conn.close()

    print(json.dumps(
        {
            'habit_db': str(HABIT_DB),
            'seeded': seeded,
            'auto_extracted': len(auto_records),
            'total_records': total,
            'recent_keys': samples,
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == '__main__':
    main()
