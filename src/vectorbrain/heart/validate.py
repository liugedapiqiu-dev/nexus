from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from heart.engine import HeartEngine
from heart.memory import memory_store
from runtime.heart_bridge import runtime_heart
from runtime.orchestrator import orchestrate


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    engine = HeartEngine()
    session_a = "agent:main:feishu:direct:ou_validate_heart"
    session_b = "agent:main:feishu:direct:ou_validate_heart:followup"

    r1 = engine.process_input(
        "我现在很焦虑，感觉快撑不住了，怕事情搞砸，帮我一步一步来！！！",
        session_id=session_a,
        write_memory=True,
        tags=["validation"],
    ).to_dict()
    check(r1["state"]["protective_mode"] in {"guarded", "supportive", "crisis"}, "高压输入未触发保护/支持模式")
    check(r1["policy"]["should_offer_comfort"] is True, "高压输入未触发安抚策略")
    check("clarity" in r1["signal"]["detected_needs"], "高压+一步一步 未识别 clarity need")

    r2 = engine.process_input(
        "谢谢你，我现在好多了。别太复杂，给我一个最小下一步就行。",
        session_id=session_a,
        write_memory=True,
        tags=["validation"],
    ).to_dict()
    check(r2["memory_summary"]["exists"] is True, "会话摘要未生成")
    check(r2["state"]["recovery_score"] >= 0.0, "恢复分未返回")
    check(r2["state"]["trajectory_label"] in {"recovering", "stabilizing", "steady", "positive_arc", "heavy_but_managed"}, "轨迹标签异常")

    _ = engine.process_input(
        "最近几次都容易慌，你先稳一点跟我说。",
        session_id=session_b,
        write_memory=True,
        tags=["validation", "cross_session"],
    ).to_dict()

    packet = runtime_heart.build_preprocess_packet(
        "用户有点紧张，希望回答更稳、更短。",
        session_id=session_b,
        write_memory=False,
    )
    check(packet["enabled"] is True, "preprocess packet 未启用")
    check("reply_guidance" in packet and "risk_flags" in packet, "preprocess packet 缺关键字段")
    check(bool(packet.get("assistant_prompt_append")), "Heart 未生成可注入上层 prompt 的 assistant_prompt_append")
    check(bool(packet.get("composer")), "Heart 未生成 response composer")
    check("profile_brief" in packet["reply_guidance"], "reply_guidance 缺跨 session profile_brief")

    orch = asyncio.run(
        orchestrate(
            {
                "title": "帮我给用户一个稳一点的回复",
                "description": "用户有点焦虑，希望一步一步来",
                "metadata": {
                    "session_id": session_b,
                    "heart_preprocess": True,
                    "heart_write_memory": False,
                },
            },
            dry_run=True,
        )
    )
    task = orch.get("task") or {}
    heart_meta = ((task.get("metadata") or {}).get("heart") or {})
    response_guidance = task.get("response_guidance") or {}
    check(bool(heart_meta), "orchestrator 未注入 heart preprocess 元数据")
    check("[Heart Composer Active]" in (task.get("description") or ""), "Heart 未真正注入 description/prompt 拼装链")
    check(bool(response_guidance.get("heart")), "orchestrator 未暴露 response_guidance.heart")

    conn = sqlite3.connect(str(memory_store.db_path))
    conn.row_factory = sqlite3.Row
    profile_row = conn.execute(
        "SELECT * FROM heart_identity_profiles WHERE profile_id = ?",
        (memory_store._infer_profile_id(session_b),),
    ).fetchone()
    conn.close()
    check(profile_row is not None, "长期情感画像表未写入")

    print(json.dumps(
        {
            "ok": True,
            "protective_mode": r1["state"]["protective_mode"],
            "recovery_trajectory": r2["state"]["trajectory_label"],
            "memory_summary_exists": r2["memory_summary"]["exists"],
            "orchestrator_heart_hook": bool(heart_meta),
            "heart_injected_description": "[Heart Composer Active]" in (task.get("description") or ""),
            "response_guidance_heart": bool(response_guidance.get("heart")),
            "assistant_prompt_append": packet["assistant_prompt_append"],
            "reply_guidance": packet["reply_guidance"],
            "composer": packet["composer"],
            "profile_id": memory_store._infer_profile_id(session_b),
            "profile_summary_exists": profile_row is not None,
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
