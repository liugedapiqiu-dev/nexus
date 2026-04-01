#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SERVER = [sys.executable, str(Path.home() / ".vectorbrain" / "runtime" / "mcp_server.py")]


def rpc(proc, _id, method, params=None):
    req = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}}
    proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError(f"no response for {method}")
    return json.loads(line)


def main():
    proc = subprocess.Popen(SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        calls = [
            (1, "initialize", {}),
            (2, "tools/list", {}),
            (3, "skills/list", {}),
            (4, "tools/call", {"name": "web_search", "arguments": {"query": "OpenClaw AI agent", "count": 3}}),
            (5, "tools/call", {"name": "web_fetch", "arguments": {"url": "https://example.com", "max_chars": 500}}),
            (6, "tools/call", {"name": "send_message", "arguments": {"channel": "feishu", "target": "oc_test_target", "message": "VectorBrain MCP smoketest", "dry_run": True}}),
            (7, "task/route", {"title": "use weather skill to check Shanghai weather"}),
            (8, "tools/call", {"name": "openclaw_skill", "arguments": {"skill": "weather", "task": "check Shanghai weather", "mode": "inspect"}}),
            (9, "orchestrate", {"title": "Search OpenClaw project and save to file", "dry_run": True}),
        ]

        all_ok = True
        for _id, method, params in calls:
            resp = rpc(proc, _id, method, params)
            ok = "error" not in resp
            all_ok = all_ok and ok
            print(f"\n=== {method} ===")
            print(json.dumps(resp, ensure_ascii=False, indent=2)[:4000])

        sys.exit(0 if all_ok else 1)
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
