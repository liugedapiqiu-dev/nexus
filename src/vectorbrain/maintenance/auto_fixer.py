#!/usr/bin/env python3
"""
VectorBrain Auto-Fixer
自动检测异常并调用 OpenClaw Agent 修复

依赖：
- OpenClaw 网关（18789 端口）必须启动
- notify_helper.py 发送飞书通知
- status.json 提供异常数据

每小时运行一次（通过 cron 或内置定时器）
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ============ 路径配置 ============
VHOME = Path.home() / ".vectorbrain"
STATE_FILE = VHOME / "maintenance" / "auto_fixer_state.json"
STATUS_FILE = VHOME / "monitor_center" / "status.json"
LOG_FILE = VHOME / "logs" / "auto_fixer.log"
OPENCLAW_BIN = Path.home() / ".npm-global" / "bin" / "openclaw"
NOTIFY_HELPER = VHOME / "common" / "notify_helper.py"

UTC = timezone.utc


# ============ 日志 ============
def log(msg: str, level: str = "info") -> None:
    ts = datetime.now(UTC).isoformat()
    line = f"[{ts}] [{level.upper()}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ============ 状态管理 ============
def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"last_run": None, "fixes": [], "stats": {"total": 0, "success": 0, "failed": 0}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_run": None, "fixes": [], "stats": {"total": 0, "success": 0, "failed": 0}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.rename(STATE_FILE)


# ============ OpenClaw 网关检测 ============
def is_gateway_running() -> bool:
    """检测 OpenClaw 网关是否在 18789 端口运行"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect(("127.0.0.1", 18789))
        return True
    except Exception:
        return False
    finally:
        sock.close()


# ============ 飞书通知 ============
def send_feishu(message: str) -> bool:
    """通过 notify_helper 发送飞书消息"""
    try:
        import sys
        sys.path.insert(0, str(NOTIFY_HELPER.parent))
        from common.notify_helper import send_feishu_message
        ok, detail = send_feishu_message(message, script="auto_fixer")
        return ok
    except Exception as e:
        log(f"飞书通知失败: {e}", "error")
        return False


# ============ OpenClaw Agent 调用 ============
def call_openclaw_agent(task_description: str, timeout: int = 180) -> tuple[bool, str]:
    """
    调用 OpenClaw Agent 执行修复任务
    返回: (success, response)
    """
    if not OPENCLAW_BIN.exists():
        return False, "openclaw binary not found"

    cmd = [
        str(OPENCLAW_BIN),
        "agent",
        "--message", task_description,
        "--json",
        "--timeout", str(timeout)
    ]

    env = dict(os.environ)
    npm_global = str(Path.home() / ".npm-global" / "bin")
    env["PATH"] = f"/usr/local/bin:/opt/homebrew/bin:{npm_global}:{env.get('PATH', '')}"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )

        if result.returncode == 0:
            # 尝试解析 JSON 响应
            try:
                resp = json.loads(result.stdout)
                return True, resp.get("text", "ok")
            except Exception:
                return True, result.stdout[:500] if result.stdout else "ok"
        else:
            return False, result.stderr[:500] if result.stderr else f"returncode={result.returncode}"

    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


# ============ 异常检测规则 ============
@dataclass
class FixRule:
    name: str
    check_path: str  # status.json 中的路径，如 "alerts[0].text"
    condition: str   # 简单条件表达式
    prompt_template: str  # 给 Agent 的提示模板
    cooldown_seconds: int = 3600  # 同类问题冷却时间


FIX_RULES = [
    FixRule(
        name="script_error",
        check_path="scripts_with_errors",
        condition="count > 0",
        prompt_template="VectorBrain 系统检测到脚本错误，请分析并修复：\n{issue_detail}\n\n请执行必要的诊断和修复操作。",
        cooldown_seconds=3600
    ),
    FixRule(
        name="service_down",
        check_path="services_down",
        condition="count > 0",
        prompt_template="VectorBrain 检测到服务停止，请尝试重启：\n{issue_detail}\n\n如果无法自动恢复，请报告具体原因。",
        cooldown_seconds=1800
    ),
    FixRule(
        name="critical_alert",
        check_path="critical_alerts",
        condition="count > 0",
        prompt_template="VectorBrain 收到严重告警，需要立即处理：\n{issue_detail}\n\n请分析问题并执行修复。",
        cooldown_seconds=1800
    ),
]


# ============ 异常收集 ============
def get_status() -> dict:
    """读取最新的 status.json"""
    if not STATUS_FILE.exists():
        return {}
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def check_cooldown(state: dict, rule_name: str, issue_key: str) -> bool:
    """检查是否在冷却期内"""
    now = time.time()
    key = f"{rule_name}:{issue_key}"

    for fix in state.get("fixes", []):
        if fix.get("issue_key") == key:
            last_fix = fix.get("fixed_at", 0)
            rule = next((r for r in FIX_RULES if r.name == rule_name), None)
            cooldown = rule.cooldown_seconds if rule else 3600
            if now - last_fix < cooldown:
                log(f"跳过 {key}，仍在冷却期内", "info")
                return True

    return False


def collect_issues(status: dict) -> list[dict]:
    """从 status.json 收集可修复的问题"""
    issues = []

    # 1. 检查脚本错误
    scripts = status.get("rankings", {}).get("scripts", [])
    error_scripts = [s for s in scripts if s.get("errors", 0) > 0]
    if error_scripts:
        for script in error_scripts[:3]:  # 最多处理 3 个
            issue_key = script.get("displayName", "unknown")
            issues.append({
                "rule": "script_error",
                "key": issue_key,
                "detail": f"脚本 '{issue_key}' 错误数: {script.get('errors', 0)}",
                "data": script
            })

    # 2. 检查停止的服务
    services = status.get("services", [])
    down_services = [s for s in services if not s.get("ok", True)]
    if down_services:
        for svc in down_services[:3]:
            issue_key = svc.get("name", "unknown")
            issues.append({
                "rule": "service_down",
                "key": issue_key,
                "detail": f"服务 '{issue_key}' 状态: {svc.get('info', 'stopped')}",
                "data": svc
            })

    # 3. 检查严重告警
    alerts = status.get("alerts", [])
    critical_alerts = [a for a in alerts if a.get("tone") == "critical"]
    if critical_alerts:
        for alert in critical_alerts[:3]:
            issue_key = alert.get("text", "")[:50]
            issues.append({
                "rule": "critical_alert",
                "key": issue_key,
                "detail": f"告警: {alert.get('text', '')}",
                "data": alert
            })

    return issues


# ============ 执行修复 ============
def run_fix(rule_name: str, issue_key: str, detail: str, prompt_template: str) -> tuple[bool, str]:
    """执行单个修复任务"""
    prompt = prompt_template.format(issue_detail=detail)

    log(f"开始修复: {rule_name} - {issue_key}", "info")

    # 调用 OpenClaw Agent
    ok, resp = call_openclaw_agent(prompt, timeout=180)

    return ok, resp


# ============ 主流程 ============
def main():
    log("=" * 50, "info")
    log("Auto-Fixer 启动", "info")

    # 1. 检查 OpenClaw 网关
    if not is_gateway_running():
        log("OpenClaw 网关未启动，跳过本次修复", "warn")
        return

    log("OpenClaw 网关运行中，开始检测异常", "info")

    # 2. 加载状态
    state = load_state()

    # 3. 读取最新状态
    status = get_status()
    if not status:
        log("无法读取 status.json", "error")
        return

    # 4. 收集问题
    issues = collect_issues(status)
    if not issues:
        log("未检测到可修复的问题", "info")
        return

    log(f"发现 {len(issues)} 个问题待处理", "info")

    # 5. 逐个处理
    fixed_count = 0
    failed_count = 0
    new_fixes = []

    for issue in issues:
        rule_name = issue["rule"]
        issue_key = issue["key"]
        issue_detail = issue["detail"]

        # 检查冷却期
        if check_cooldown(state, rule_name, issue_key):
            continue

        # 查找规则
        rule = next((r for r in FIX_RULES if r.name == rule_name), None)
        if not rule:
            continue

        # 执行修复
        ok, resp = run_fix(rule_name, issue_key, issue_detail, rule.prompt_template)

        fix_record = {
            "issue_key": f"{rule_name}:{issue_key}",
            "rule": rule_name,
            "detail": issue_detail,
            "fixed_at": time.time(),
            "success": ok,
            "response": resp[:200] if resp else ""
        }

        new_fixes.append(fix_record)

        if ok:
            fixed_count += 1
            log(f"✓ 修复成功: {issue_key}", "info")
        else:
            failed_count += 1
            log(f"✗ 修复失败: {issue_key} - {resp}", "error")

    # 6. 更新状态
    state["last_run"] = datetime.now(UTC).isoformat()
    state["fixes"] = (state.get("fixes", []) + new_fixes)[-50:]  # 保留最近 50 条
    state["stats"]["total"] = state["stats"].get("total", 0) + fixed_count + failed_count
    state["stats"]["success"] = state["stats"].get("success", 0) + fixed_count
    state["stats"]["failed"] = state["stats"].get("failed", 0) + failed_count
    state["issues_found"] = len(issues)
    state["issues_fixed"] = fixed_count
    state["issues_failed"] = failed_count

    save_state(state)

    # 7. 发送飞书通知
    if fixed_count > 0 or failed_count > 0:
        msg = f"""🛠️ VectorBrain Auto-Fixer 报告

⏰ 时间：{state['last_run']}
📊 检测到 {len(issues)} 个问题

✅ 已修复：{fixed_count} 个
❌ 失败：{failed_count} 个

"""
        if new_fixes:
            msg += "📝 最近修复：\n"
            for fix in new_fixes[:5]:
                status_icon = "✅" if fix["success"] else "❌"
                msg += f"{status_icon} {fix['issue_key']}\n"

        msg += "\n---\n由 VectorBrain Auto-Fixer 自动执行"

        send_feishu(msg)

    log(f"Auto-Fixer 完成: {fixed_count} 成功, {failed_count} 失败", "info")


if __name__ == "__main__":
    main()
