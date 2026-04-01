#!/usr/bin/env python3
"""VectorBrain Message Tools - wired to OpenClaw CLI."""

from __future__ import annotations

from runtime.tools.registry import tool_registry, Tool
from runtime.adapters.openclaw_cli import send_message as openclaw_send_message
from common.notify_helper import append_pending_notification, mark_notification_status
from typing import Dict, Any


async def send_message_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        channel = input.get("channel", "feishu")
        message = input["message"]
        target = input.get("target")
        dry_run = bool(input.get("dry_run", False))
        queue_on_failure = bool(input.get("queue_on_failure", False))
        notification_type = str(input.get("notification_type") or "message_send")
        script = str(input.get("script") or "runtime.tools.message_tools")
        notification_payload = {
            "type": notification_type,
            "channel": channel,
            "target": target,
            "message": message,
        }

        print(f"[send_message] Sending via {channel} dry_run={dry_run}: {message[:50]}...")
        res = openclaw_send_message(channel=channel, message=message, target=target, dry_run=dry_run, timeout=60)

        if res["ok"]:
            payload = res.get("json") if isinstance(res.get("json"), dict) else None
            return {
                "success": True,
                "data": {
                    "channel": channel,
                    "target": target,
                    "dry_run": dry_run,
                    "response": payload or res.get("stdout"),
                    "command": res.get("command"),
                },
                "error": None,
            }

        error_text = res.get("stderr") or f"openclaw message send failed with code {res.get('returncode')}"
        failure_data = {
            "channel": channel,
            "target": target,
            "dry_run": dry_run,
            "command": res.get("command"),
            "stdout": res.get("stdout"),
        }
        if queue_on_failure and not dry_run:
            queued, queue_detail = append_pending_notification(notification_payload, script=script)
            failure_data["queued"] = queued
            failure_data["queue_detail"] = queue_detail
            if queued:
                mark_notification_status(queue_detail, status="failed", send_detail=error_text, script=script)

        return {
            "success": False,
            "data": failure_data,
            "error": error_text,
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


send_message_tool = Tool(
    name="send_message",
    display_name="Send Message",
    description="Send a message via OpenClaw CLI (feishu, telegram, whatsapp, etc.)",
    capabilities=["communication", "message", "notify"],
    input_schema={
        "type": "object",
        "required": ["message"],
        "properties": {
            "message": {"type": "string", "description": "Message content"},
            "channel": {"type": "string", "description": "Channel (feishu, telegram, etc.)"},
            "target": {"type": "string", "description": "Target user/chat ID"},
            "dry_run": {"type": "boolean", "description": "Validate and preview send without delivery", "default": False},
            "queue_on_failure": {"type": "boolean", "description": "Append pending notification and record failure reason when send fails", "default": False},
            "notification_type": {"type": "string", "description": "Pending notification type label"},
            "script": {"type": "string", "description": "Caller script name for failure logging"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "channel": {"type": "string"},
            "target": {"type": "string"},
            "dry_run": {"type": "boolean"},
            "response": {},
            "command": {"type": "array"},
        },
    },
    handler=send_message_handler,
    timeout=60,
    version="2.0",
    allow_dry_run=True,
)

tool_registry.register(send_message_tool)
