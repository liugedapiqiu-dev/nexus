#!/usr/bin/env python3
"""Minimal smoke test for the desktop-control skill.

Goals:
- verify import path works via `desktop_control`
- verify controller init / screen size / mouse position
- verify Chinese `type_text()` goes through the clipboard paste path

The Chinese typing check is SAFE by default: it monkeypatches the actual paste
hotkey so it does not type into the active window.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))


def main() -> int:
    results = {
        "import": None,
        "controller_init": None,
        "screen_size": None,
        "mouse_position": None,
        "clipboard_roundtrip": None,
        "chinese_type_path": None,
        "notes": [],
    }

    try:
        import desktop_control
        from desktop_control import DesktopController
        results["import"] = "ok"
    except Exception as e:
        results["import"] = f"fail: {e}"
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    try:
        dc = DesktopController(failsafe=False)
        results["controller_init"] = "ok"
        results["screen_size"] = list(dc.get_screen_size())
        results["mouse_position"] = list(dc.get_mouse_position())
    except Exception as e:
        results["controller_init"] = f"fail: {e}"
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    original_clipboard = None
    try:
        original_clipboard = dc.get_from_clipboard()
        probe_text = "中文路径验证"
        dc.copy_to_clipboard(probe_text)
        roundtrip = dc.get_from_clipboard()
        results["clipboard_roundtrip"] = {
            "expected": probe_text,
            "actual": roundtrip,
            "ok": roundtrip == probe_text,
        }
    except Exception as e:
        results["clipboard_roundtrip"] = f"fail: {e}"

    calls = []
    old_hotkey = desktop_control.pyautogui.hotkey
    old_write = desktop_control.pyautogui.write
    old_copy = dc.copy_to_clipboard
    copied = {"text": None}

    def fake_hotkey(*keys, **kwargs):
        calls.append({"fn": "hotkey", "keys": list(keys), "kwargs": kwargs})

    def fake_write(text, **kwargs):
        calls.append({"fn": "write", "text": text, "kwargs": kwargs})

    def fake_copy(text):
        copied["text"] = text
        calls.append({"fn": "copy_to_clipboard", "text": text})

    try:
        desktop_control.pyautogui.hotkey = fake_hotkey
        desktop_control.pyautogui.write = fake_write
        dc.copy_to_clipboard = fake_copy
        dc.type_text("中文路径验证")

        used_clipboard = any(c["fn"] == "copy_to_clipboard" for c in calls)
        used_paste = any(c["fn"] == "hotkey" and c.get("keys") == ["command", "v"] for c in calls)
        used_direct_write = any(c["fn"] == "write" for c in calls)

        results["chinese_type_path"] = {
            "copied_text": copied["text"],
            "used_clipboard_copy": used_clipboard,
            "used_command_v": used_paste,
            "used_direct_write": used_direct_write,
            "ok": used_clipboard and used_paste and not used_direct_write,
            "calls": calls,
        }
    except Exception as e:
        results["chinese_type_path"] = f"fail: {e}"
    finally:
        desktop_control.pyautogui.hotkey = old_hotkey
        desktop_control.pyautogui.write = old_write
        dc.copy_to_clipboard = old_copy
        if original_clipboard is not None:
            try:
                dc.copy_to_clipboard(original_clipboard)
                results["notes"].append("clipboard restored")
            except Exception as e:
                results["notes"].append(f"clipboard restore failed: {e}")

    ok = (
        results["import"] == "ok"
        and results["controller_init"] == "ok"
        and isinstance(results["clipboard_roundtrip"], dict)
        and results["clipboard_roundtrip"].get("ok") is True
        and isinstance(results["chinese_type_path"], dict)
        and results["chinese_type_path"].get("ok") is True
    )

    results["overall"] = "pass" if ok else "fail"
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
