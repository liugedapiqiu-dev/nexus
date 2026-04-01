#!/usr/bin/env python3
"""VectorBrain Execution Trace (Stage 2+)

Captures per-step execution records and persists them to disk.
Designed to be simple, JSON-first, and CLI-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json


def summarize_exec_result(exec_result: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize a tool execution result for human-friendly trace output."""
    summary: Dict[str, Any] = {
        "success": bool(exec_result.get("success")),
    }

    err = exec_result.get("error")
    if err:
        summary["error"] = (err[:200] + "...") if isinstance(err, str) and len(err) > 200 else err

    data = exec_result.get("data")
    if isinstance(data, dict):
        # common shapes
        if "results" in data and isinstance(data.get("results"), list):
            summary["results_count"] = len(data.get("results"))
            if data["results"]:
                first = data["results"][0]
                if isinstance(first, dict) and "url" in first:
                    summary["top_url"] = first.get("url")
        if "content" in data and isinstance(data.get("content"), str):
            content = data.get("content")
            summary["content_bytes"] = len(content.encode("utf-8"))
        if "path" in data:
            summary["path"] = data.get("path")
        if "bytes" in data:
            summary["bytes"] = data.get("bytes")

    return summary


@dataclass
class ExecutionTrace:
    task_id: str
    workflow: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    success: Optional[bool] = None
    total_seconds: Optional[float] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)

    def add_step(self, record: Dict[str, Any]) -> None:
        self.steps.append(record)

    def finish(self, success: bool, total_seconds: float) -> None:
        self.success = success
        self.total_seconds = total_seconds
        self.finished_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        # Back-compat: keep started_at/finished_at/total_seconds, but also expose a
        # normalized shape many UIs expect (ts + duration_ms).
        duration_ms = int(self.total_seconds * 1000) if self.total_seconds is not None else None
        return {
            "task_id": self.task_id,
            "workflow": self.workflow,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "success": self.success,
            "total_seconds": self.total_seconds,
            "duration_ms": duration_ms,
            "steps": self.steps,
        }

    def save(self, traces_dir: Optional[str] = None) -> Path:
        base = Path(traces_dir) if traces_dir else Path.home() / ".vectorbrain" / "traces"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"task_{self.task_id}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
