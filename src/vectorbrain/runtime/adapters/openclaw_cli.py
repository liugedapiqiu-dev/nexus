#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional


class OpenClawCLIError(RuntimeError):
    pass


_JSON_BLOCK_RE = re.compile(r"(\{[\s\S]*\}|\[[\s\S]*\])")


def openclaw_path() -> str:
    path = shutil.which("openclaw")
    if not path:
        raise OpenClawCLIError("openclaw CLI not found in PATH")
    return path


def _extract_json_blob(text: str) -> Optional[Any]:
    text = (text or "").strip()
    if not text:
        return None

    # Fast path: whole output is JSON.
    try:
        return json.loads(text)
    except Exception:
        pass

    # Common OpenClaw case: banner/log lines before JSON.
    lines = [line for line in text.splitlines() if line.strip()]
    for i in range(len(lines)):
        chunk = "\n".join(lines[i:]).strip()
        if not chunk:
            continue
        if not (chunk.startswith("{") or chunk.startswith("[")):
            continue
        try:
            return json.loads(chunk)
        except Exception:
            continue

    # Fallback: greedy JSON block extraction.
    for match in _JSON_BLOCK_RE.finditer(text):
        chunk = match.group(1).strip()
        if not chunk:
            continue
        try:
            return json.loads(chunk)
        except Exception:
            continue

    return None


def run_openclaw(args: List[str], *, timeout: int = 120, expect_json: bool = False) -> Dict[str, Any]:
    cmd = [openclaw_path(), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    combined = "\n".join(part for part in [stdout, stderr] if part).strip()

    result: Dict[str, Any] = {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "combined": combined,
        "command": cmd,
    }
    if expect_json:
        parsed = _extract_json_blob(stdout) or _extract_json_blob(combined)
        if parsed is not None:
            result["json"] = parsed
        elif stdout or stderr:
            result["json_error"] = "No valid JSON object found in OpenClaw output"
    return result


def send_message(*, channel: Optional[str], message: str, target: Optional[str] = None, dry_run: bool = False, timeout: int = 60) -> Dict[str, Any]:
    args = ["message", "send", "--json", "--message", message]
    if channel:
        args += ["--channel", channel]
    if target:
        args += ["--target", target]
    if dry_run:
        args += ["--dry-run"]
    return run_openclaw(args, timeout=timeout, expect_json=True)


def run_local_agent(*, message: str, timeout: int = 300, channel: Optional[str] = None, session_id: Optional[str] = None, deliver: bool = False) -> Dict[str, Any]:
    args = ["agent", "--local", "--json", "--message", message, "--timeout", str(timeout)]
    if channel:
        args += ["--channel", channel]
    if session_id:
        args += ["--session-id", session_id]
    if deliver:
        args += ["--deliver"]
    return run_openclaw(args, timeout=timeout + 30, expect_json=True)


def list_skills(*, eligible_only: bool = False, timeout: int = 60) -> Dict[str, Any]:
    args = ["skills", "list", "--json"]
    if eligible_only:
        args.append("--eligible")
    return run_openclaw(args, timeout=timeout, expect_json=True)


def skill_info(name: str, *, timeout: int = 60) -> Dict[str, Any]:
    return run_openclaw(["skills", "info", name, "--json"], timeout=timeout, expect_json=True)


def normalize_skill_list_payload(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        skills = payload.get("skills")
        if isinstance(skills, list):
            return [s for s in skills if isinstance(s, dict)]
    if isinstance(payload, list):
        return [s for s in payload if isinstance(s, dict)]
    return []


def normalize_skill_info_payload(payload: Any, fallback_name: Optional[str] = None) -> Dict[str, Any]:
    if isinstance(payload, dict):
        if "name" in payload:
            return payload
        if isinstance(payload.get("skill"), dict):
            return payload["skill"]
    return {"name": fallback_name} if fallback_name else {}
