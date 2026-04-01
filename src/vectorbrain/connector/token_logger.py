#!/usr/bin/env python3
"""
🧠 VectorBrain Token 使用日志

功能：
- 记录所有 LLM API 调用的真实 token 消耗
- 持久化存储（网关重启不丢失）
- 支持查询、统计、导出

日志格式：JSONL（每行一条记录）
位置：~/.vectorbrain/logs/token_usage.log

作者：[YOUR_AI_NAME] 🧠
版本：1.0 (2026-03-13)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

# 配置
LOG_DIR = Path.home() / '.vectorbrain' / 'logs'
LOG_FILE = LOG_DIR / 'token_usage.log'
STATS_FILE = Path.home() / '.vectorbrain' / 'state' / 'global_token_stats.db'

def ensure_dirs():
    """确保目录存在"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)

def log_token(
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    session_key: str = None,
    session_id: str = None,
    duration_ms: int = None,
    request_id: str = None,
    cost: float = None,
    metadata: dict = None
):
    """
    记录一次 token 使用（追加到日志文件）
    
    Args:
        model: 模型名称 (e.g., "qwen3.5-plus")
        provider: 提供商 ("dashscope" | "ollama")
        input_tokens: 输入 token 数（从 API 响应获取）
        output_tokens: 输出 token 数（从 API 响应获取）
        session_key: 会话标识
        session_id: 会话 ID
        duration_ms: 请求耗时（毫秒）
        request_id: 请求 ID
        cost: 成本（人民币元）
        metadata: 额外元数据
    """
    ensure_dirs()
    
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "provider": provider,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "session_key": session_key,
        "session_id": session_id,
        "duration_ms": duration_ms,
        "request_id": request_id,
        "cost": cost,
        "metadata": metadata
    }
    
    # 追加到日志文件（JSONL 格式）
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    # 同时写入 SQLite 数据库（用于快速查询）
    try:
        import sqlite3
        conn = sqlite3.connect(str(STATS_FILE))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO token_usage 
            (timestamp, session_id, session_key, model, provider, input_tokens, output_tokens, total_tokens, duration_ms, request_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record["timestamp"],
            session_id,
            session_key,
            model,
            provider,
            input_tokens,
            output_tokens,
            record["total_tokens"],
            duration_ms,
            request_id,
            json.dumps(metadata, ensure_ascii=False) if metadata else None
        ))
        
        # 更新每日汇总
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT INTO daily_summary (date, total_input, total_output, total_tokens, request_count, unique_sessions)
            VALUES (?, ?, ?, ?, 1, 1)
            ON CONFLICT(date) DO UPDATE SET
                total_input = total_input + ?,
                total_output = total_output + ?,
                total_tokens = total_tokens + ?,
                request_count = request_count + 1
        ''', (today, input_tokens, output_tokens, record["total_tokens"], input_tokens, output_tokens, record["total_tokens"]))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ SQLite 写入失败：{e}", file=sys.stderr)
    
    return record

def get_stats(days: int = 7, session_key: str = None) -> Dict:
    """
    从日志文件统计 token 使用
    
    Args:
        days: 统计天数
        session_key: 可选，只统计特定会话
    
    Returns:
        统计字典
    """
    if not LOG_FILE.exists():
        return {"error": "日志文件不存在", "path": str(LOG_FILE)}
    
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    total_input = 0
    total_output = 0
    total_tokens = 0
    request_count = 0
    by_model = {}
    by_day = {}
    recent = []
    sessions = set()
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                ts = datetime.fromisoformat(record["timestamp"])
                
                if ts < cutoff:
                    continue
                
                if session_key and record.get("session_key") != session_key:
                    continue
                
                # 累计统计
                total_input += record.get("input_tokens", 0)
                total_output += record.get("output_tokens", 0)
                total_tokens += record.get("total_tokens", 0)
                request_count += 1
                
                if record.get("session_key"):
                    sessions.add(record["session_key"])
                
                # 按模型统计
                model_key = f"{record.get('model', 'unknown')}|{record.get('provider', 'unknown')}"
                if model_key not in by_model:
                    by_model[model_key] = {"model": record.get('model'), "provider": record.get('provider'), "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "request_count": 0}
                by_model[model_key]["input_tokens"] += record.get("input_tokens", 0)
                by_model[model_key]["output_tokens"] += record.get("output_tokens", 0)
                by_model[model_key]["total_tokens"] += record.get("total_tokens", 0)
                by_model[model_key]["request_count"] += 1
                
                # 按天统计
                day_key = ts.strftime('%Y-%m-%d')
                if day_key not in by_day:
                    by_day[day_key] = {"date": day_key, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "request_count": 0}
                by_day[day_key]["input_tokens"] += record.get("input_tokens", 0)
                by_day[day_key]["output_tokens"] += record.get("output_tokens", 0)
                by_day[day_key]["total_tokens"] += record.get("total_tokens", 0)
                by_day[day_key]["request_count"] += 1
                
                # 最近记录（保留最后 20 条）
                recent.append(record)
                
            except (json.JSONDecodeError, KeyError) as e:
                continue
    
    # 按日期排序
    by_day_sorted = sorted(by_day.values(), key=lambda x: x["date"], reverse=True)
    
    # 按 token 数排序模型
    by_model_sorted = sorted(by_model.values(), key=lambda x: x["total_tokens"], reverse=True)
    
    return {
        "summary": {
            "total_input": total_input,
            "total_output": total_output,
            "total_tokens": total_tokens,
            "request_count": request_count,
            "unique_sessions": len(sessions)
        },
        "by_model": by_model_sorted,
        "by_day": by_day_sorted,
        "recent": recent[-20:][::-1],  # 最近 20 条，倒序
        "period_days": days,
        "log_file": str(LOG_FILE),
        "log_file_size": LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
    }

def get_today_summary() -> Dict:
    """获取今日摘要"""
    stats = get_stats(days=1)
    return stats.get("summary", {})

def export_csv(output_path: str = None, days: int = 30) -> str:
    """导出为 CSV 文件"""
    import csv
    
    if output_path is None:
        output_path = Path.home() / '.vectorbrain' / 'logs' / f'token_export_{datetime.now().strftime("%Y%m%d")}.csv'
    else:
        output_path = Path(output_path)
    
    if not LOG_FILE.exists():
        return f"错误：日志文件不存在"
    
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['时间戳', '模型', '提供商', '输入 Token', '输出 Token', '总 Token', '会话', '耗时 (ms)', '请求 ID'])
        
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    ts = datetime.fromisoformat(record["timestamp"])
                    if ts >= cutoff:
                        writer.writerow([
                            record["timestamp"][:19],
                            record.get("model", ""),
                            record.get("provider", ""),
                            record.get("input_tokens", 0),
                            record.get("output_tokens", 0),
                            record.get("total_tokens", 0),
                            record.get("session_key", ""),
                            record.get("duration_ms", ""),
                            record.get("request_id", "")
                        ])
                except:
                    continue
    
    return f"✅ 已导出到：{output_path}"

# ===== 命令行工具 =====
if __name__ == '__main__':
    ensure_dirs()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'log':
            # 手动记录一条（测试用）
            if len(sys.argv) > 5:
                record = log_token(
                    model=sys.argv[2],
                    provider=sys.argv[3],
                    input_tokens=int(sys.argv[4]),
                    output_tokens=int(sys.argv[5]),
                    session_key=sys.argv[6] if len(sys.argv) > 6 else None
                )
                print(f"✅ 已记录：{json.dumps(record, ensure_ascii=False, indent=2)}")
            else:
                print("用法：python3 token_logger.py log <model> <provider> <input_tokens> <output_tokens> [session_key]")
        
        elif cmd == 'stats':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            stats = get_stats(days=days)
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        elif cmd == 'today':
            summary = get_today_summary()
            print(f"📊 今日 Token 使用统计")
            print(f"  输入：{summary.get('total_input', 0):,}")
            print(f"  输出：{summary.get('total_output', 0):,}")
            print(f"  总计：{summary.get('total_tokens', 0):,}")
            print(f"  请求数：{summary.get('request_count', 0):,}")
            print(f"  会话数：{summary.get('unique_sessions', 0)}")
            print(f"\n📁 日志文件：{LOG_FILE}")
            print(f"📊 文件大小：{LOG_FILE.stat().st_size / 1024:.1f} KB" if LOG_FILE.exists() else "")
        
        elif cmd == 'recent':
            stats = get_stats(days=1)
            for record in stats.get('recent', [])[:10]:
                print(f"{record['timestamp'][:19]} | {record['model']:20} | 输入 {record['input_tokens']:5} / 输出 {record['output_tokens']:5} | {record.get('session_key', '')[:30]}")
        
        elif cmd == 'export':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            result = export_csv(days=days)
            print(result)
        
        elif cmd == 'tail':
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            if LOG_FILE.exists():
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-n:]:
                        print(line.strip())
            else:
                print("日志文件不存在")
        
        else:
            print("🧠 VectorBrain Token 日志工具")
            print("=" * 60)
            print(f"日志文件：{LOG_FILE}")
            print()
            print("用法:")
            print("  log <model> <provider> <in> <out> [session]  - 记录一条")
            print("  stats [days]  - 查看统计")
            print("  today         - 查看今日")
            print("  recent        - 查看最近")
            print("  export [days] - 导出 CSV")
            print("  tail [n]      - 查看最后 n 条")
            print()
            print("示例:")
            print("  python3 token_logger.py today")
            print("  python3 token_logger.py stats 7")
            print("  python3 token_logger.py export 30")
    else:
        # 默认显示今日统计
        print("🧠 VectorBrain Token 日志")
        print("=" * 60)
        summary = get_today_summary()
        print(f"📊 今日统计:")
        print(f"  输入：{summary.get('total_input', 0):,} tokens")
        print(f"  输出：{summary.get('total_output', 0):,} tokens")
        print(f"  总计：{summary.get('total_tokens', 0):,} tokens")
        print(f"  请求：{summary.get('request_count', 0):,} 次")
        print()
        print(f"📁 日志：{LOG_FILE}")
        if LOG_FILE.exists():
            print(f"📊 大小：{LOG_FILE.stat().st_size / 1024:.1f} KB")
