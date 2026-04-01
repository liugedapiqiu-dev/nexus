from __future__ import annotations

import json

from .engine import HeartEngine


def main():
    engine = HeartEngine()
    examples = [
        "我现在有点焦虑，怕这件事搞砸了，能不能一步一步帮我？",
        "谢谢你，今天进展很顺，我很开心。",
        "我真的撑不住了，不想活了。",
    ]

    state = None
    for idx, text in enumerate(examples, start=1):
        result = engine.process_input(text, session_id="demo-session", current_state=state, write_memory=True, tags=["demo"])
        state = result.state
        print(f"\n--- Example {idx} ---")
        print("Input:", text)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
