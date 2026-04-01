"""
Verification / confirmation gate demo for desktop-control.
Non-destructive: screenshot, clipboard, window title, OCR status, text checks.

Focus: safe pre-send / post-send confirmation points for Feishu/Lark workflows.
This demo does NOT send any real message.
"""

import json
import tempfile
import os
import importlib.util
from pathlib import Path

MODULE_PATH = '/home/user/.openclaw/skills/desktop-control/__init__.py'
spec = importlib.util.spec_from_file_location('desktop_control_local', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
DesktopController = mod.DesktopController


def main():
    dc = DesktopController(failsafe=True)
    result = {
        'screen_size': dc.get_screen_size(),
        'capture_scale': dc.get_capture_scale(),
        'frontmost': dc.get_frontmost_app_info(),
        'ocr_status': dc.get_ocr_status(),
    }

    # screenshot verification
    fd, shot = tempfile.mkstemp(prefix='verify-demo-', suffix='.png')
    os.close(fd)
    Path(shot).unlink(missing_ok=True)
    dc.screenshot(filename=shot)
    result['screenshot'] = {
        'path': shot,
        'exists': os.path.exists(shot),
        'size': os.path.getsize(shot) if os.path.exists(shot) else 0,
    }

    # clipboard verification
    probe_text = 'desktop-control verify gate ok'
    dc.copy_to_clipboard(probe_text)
    result['clipboard_verify'] = dc.verify_clipboard(probe_text, contains=False)
    result['clipboard_extract'] = dc.extract_text(source='clipboard')

    # front app / window title verification
    window_title = result['frontmost'].get('window_title') or ''
    app_name = result['frontmost'].get('app_name') or ''
    title_probe = window_title or app_name
    result['frontmost_extract'] = dc.extract_text(source='window_title')
    result['frontmost_verify'] = (
        dc.verify_text_present(title_probe, source='window_title', contains=True)
        if title_probe else
        {'ok': False, 'reason': 'no_front_app_or_title'}
    )

    # pixel verification: sample center, then verify against itself
    w, h = dc.get_screen_size()
    cx, cy = w // 2, h // 2
    rgb = tuple(int(v) for v in dc.get_pixel_color(cx, cy))
    result['pixel_verify'] = dc.verify_pixel_color(cx, cy, rgb, tolerance=0)

    # image presence verification: crop a small center patch from screenshot, search it back on screen
    from PIL import Image
    patch = shot.replace('.png', '.patch.png')
    img = Image.open(shot)
    left = max(cx - 30, 0)
    top = max(cy - 20, 0)
    right = min(cx + 30, img.width)
    bottom = min(cy + 20, img.height)
    img.crop((left, top, right, bottom)).save(patch)
    result['image_verify'] = dc.verify_image_present(patch, confidence=0.9)

    # OCR text checks - expected to degrade cleanly when OCR is unavailable
    result['ocr_extract_fullscreen'] = dc.extract_text(source='ocr')
    result['ocr_verify_keyword'] = dc.verify_text_present('desktop-control', source='ocr')

    # Feishu/Lark-oriented safe confirmation chain examples (no send action)
    result['feishu_lark_safe_patterns'] = {
        'pre_send_window_gate': dc.verify_text_present('feishu', source='window_title', contains=True),
        'pre_send_input_gate': dc.verify_input_text('desktop-control verify gate ok', contains=False),
        'post_send_bubble_gate_example': dc.verify_text_present(
            'desktop-control verify gate ok',
            source='ocr',
            region=None,
            contains=True,
            lang='eng',
        ),
    }

    # Dedicated Feishu/Lark verification helpers (verify-only, region-first)
    demo_regions = {
        'header_region': None,
        'sidebar_region': None,
        'composer_region': None,
        'history_region': None,
    }
    result['feishu_lark_verify_only_chain'] = {
        'note': 'verify-only demo; regions are intentionally None here, so unknown/failed is acceptable and safer than blind success',
        'regions': demo_regions,
        'verify_target': dc.verify_feishu_lark_target(
            expected_name='[YOUR_NAME]',
            expected_type='person',
            disambiguation_hint='供应链主管',
            window_title_hint='Feishu',
            header_region=demo_regions['header_region'],
            sidebar_region=demo_regions['sidebar_region'],
        ),
        'verify_draft': dc.verify_feishu_lark_draft(
            expected_text='desktop-control verify gate ok',
            composer_region=demo_regions['composer_region'],
            compare_mode='normalized',
        ),
        'verify_sent': dc.verify_feishu_lark_sent(
            expected_text='desktop-control verify gate ok',
            history_region=demo_regions['history_region'],
            composer_region=demo_regions['composer_region'],
            match_fragment='verify gate ok',
        ),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
