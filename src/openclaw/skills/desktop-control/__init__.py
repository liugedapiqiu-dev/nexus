"""
Desktop Control - Advanced Mouse, Keyboard, and Screen Automation
The best ever possible responsive desktop control for OpenClaw
"""

import pyautogui
import time
import sys
from typing import Tuple, Optional, List, Union, Dict
from pathlib import Path
import logging
import subprocess
import tempfile
import shutil
import re

# Configure PyAutoGUI
pyautogui.MINIMUM_DURATION = 0  # Allow instant movements
pyautogui.MINIMUM_SLEEP = 0     # No forced delays
pyautogui.PAUSE = 0             # No pause between function calls

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DesktopController:
    """
    Advanced desktop automation controller with mouse, keyboard, and screen operations.
    Designed for maximum responsiveness and reliability.
    """
    
    def __init__(self, failsafe: bool = True, require_approval: bool = False):
        """
        Initialize desktop controller.
        
        Args:
            failsafe: Enable failsafe (move mouse to corner to abort)
            require_approval: Require user confirmation for actions
        """
        self.failsafe = failsafe
        self.require_approval = require_approval
        pyautogui.FAILSAFE = failsafe
        
        # Get screen info
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Desktop Controller initialized. Screen: {self.screen_width}x{self.screen_height}")
        logger.info(f"Failsafe: {failsafe}, Require Approval: {require_approval}")
    
    # ========== MOUSE OPERATIONS ==========
    
    def move_mouse(self, x: int, y: int, duration: float = 0, smooth: bool = True) -> None:
        """
        Move mouse to absolute screen coordinates.
        
        Args:
            x: X coordinate (pixels from left)
            y: Y coordinate (pixels from top)
            duration: Movement time in seconds (0 = instant)
            smooth: Use smooth movement (cubic bezier)
        """
        if self._check_approval(f"move mouse to ({x}, {y})"):
            if smooth and duration > 0:
                pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
            else:
                pyautogui.moveTo(x, y, duration=duration)
            logger.debug(f"Moved mouse to ({x}, {y}) in {duration}s")
    
    def move_relative(self, x_offset: int, y_offset: int, duration: float = 0) -> None:
        """
        Move mouse relative to current position.
        
        Args:
            x_offset: Pixels to move horizontally (+ = right, - = left)
            y_offset: Pixels to move vertically (+ = down, - = up)
            duration: Movement time in seconds
        """
        if self._check_approval(f"move mouse relative ({x_offset}, {y_offset})"):
            pyautogui.move(x_offset, y_offset, duration=duration)
            logger.debug(f"Moved mouse relative ({x_offset}, {y_offset})")
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, 
              button: str = 'left', clicks: int = 1, interval: float = 0.1) -> None:
        """
        Perform mouse click.
        
        Args:
            x, y: Coordinates to click (None = current position)
            button: 'left', 'right', 'middle'
            clicks: Number of clicks (1 = single, 2 = double, etc.)
            interval: Delay between multiple clicks
        """
        position_str = f"at ({x}, {y})" if x is not None else "at current position"
        if self._check_approval(f"{button} click {position_str}"):
            pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
            logger.info(f"{button.capitalize()} click {position_str} (x{clicks})")
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Convenience method for double-click."""
        self.click(x, y, clicks=2)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Convenience method for right-click."""
        self.click(x, y, button='right')
    
    def middle_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Convenience method for middle-click."""
        self.click(x, y, button='middle')
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.5, button: str = 'left') -> None:
        """
        Drag and drop operation.
        
        Args:
            start_x, start_y: Starting coordinates
            end_x, end_y: Ending coordinates
            duration: Drag duration in seconds
            button: Mouse button to use ('left', 'right', 'middle')
        """
        if self._check_approval(f"drag from ({start_x}, {start_y}) to ({end_x}, {end_y})"):
            pyautogui.moveTo(start_x, start_y)
            time.sleep(0.05)  # Small delay to ensure position
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
            logger.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
    
    def scroll(self, clicks: int, direction: str = 'vertical', 
               x: Optional[int] = None, y: Optional[int] = None) -> None:
        """
        Scroll mouse wheel.
        
        Args:
            clicks: Scroll amount (+ = up/left, - = down/right)
            direction: 'vertical' or 'horizontal'
            x, y: Position to scroll at (None = current position)
        """
        if x is not None and y is not None:
            pyautogui.moveTo(x, y)
        
        if direction == 'vertical':
            pyautogui.scroll(clicks)
        else:
            pyautogui.hscroll(clicks)
        logger.debug(f"Scrolled {direction} {clicks} clicks")
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """
        Get current mouse coordinates.
        
        Returns:
            (x, y) tuple
        """
        pos = pyautogui.position()
        return (pos.x, pos.y)
    
    # ========== KEYBOARD OPERATIONS ==========
    
    def type_text(self, text: str, interval: float = 0, wpm: Optional[int] = None) -> None:
        """
        Type text with configurable speed.

        对 ASCII 文本走 pyautogui.write；
        对中文/emoji/其他非 ASCII 文本优先走“剪贴板 + 粘贴”，提升输入法兼容性。
        """
        if wpm is not None:
            # Convert WPM to interval (assuming avg 5 chars per word)
            chars_per_second = (wpm * 5) / 60
            interval = 1.0 / chars_per_second

        preview = text[:50] + ('...' if len(text) > 50 else '')
        if not self._check_approval(f"type text: '{preview}'"):
            return

        needs_clipboard_paste = any(ord(ch) > 127 for ch in text)
        if needs_clipboard_paste:
            try:
                self.copy_to_clipboard(text)
                pyautogui.hotkey('command', 'v', interval=max(interval, 0.02))
                logger.info(f"Pasted non-ASCII text via clipboard: '{preview}'")
                return
            except Exception as e:
                logger.warning(f"Clipboard paste path failed, falling back to direct typing: {e}")

        pyautogui.write(text, interval=interval)
        logger.info(f"Typed text: '{preview}' (interval={interval:.3f}s)")
    
    def press(self, key: str, presses: int = 1, interval: float = 0.1) -> None:
        """
        Press and release a key.
        
        Args:
            key: Key name (e.g., 'enter', 'space', 'a', 'f1')
            presses: Number of times to press
            interval: Delay between presses
        """
        if self._check_approval(f"press '{key}' {presses}x"):
            pyautogui.press(key, presses=presses, interval=interval)
            logger.info(f"Pressed '{key}' {presses}x")
    
    def hotkey(self, *keys, interval: float = 0.05) -> None:
        """
        Execute keyboard shortcut (e.g., Ctrl+C, Alt+Tab).
        
        Args:
            *keys: Keys to press together (e.g., 'ctrl', 'c')
            interval: Delay between key presses
        """
        keys_str = '+'.join(keys)
        if self._check_approval(f"hotkey: {keys_str}"):
            pyautogui.hotkey(*keys, interval=interval)
            logger.info(f"Executed hotkey: {keys_str}")
    
    def key_down(self, key: str) -> None:
        """Press and hold a key without releasing."""
        pyautogui.keyDown(key)
        logger.debug(f"Key down: '{key}'")
    
    def key_up(self, key: str) -> None:
        """Release a held key."""
        pyautogui.keyUp(key)
        logger.debug(f"Key up: '{key}'")
    
    # ========== SCREEN OPERATIONS ==========
    
    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None,
                   filename: Optional[str] = None):
        """
        Capture screen or region.
        
        Args:
            region: (left, top, width, height) for partial capture
            filename: Path to save image (None = return PIL Image)
            
        Returns:
            PIL Image object (if filename is None)
        """
        img = pyautogui.screenshot(region=region)
        
        if filename:
            img.save(filename)
            logger.info(f"Screenshot saved to: {filename}")
        else:
            logger.debug(f"Screenshot captured (region={region})")
            return img
    
    def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        Get RGB color of pixel at coordinates.
        
        Args:
            x, y: Screen coordinates
            
        Returns:
            (r, g, b) tuple
        """
        color = pyautogui.pixel(x, y)
        return color
    
    def find_on_screen(self, image_path: str, confidence: float = 0.8,
                       region: Optional[Tuple[int, int, int, int]] = None):
        """
        Find image on screen using template matching.
        Requires OpenCV (opencv-python).
        
        Args:
            image_path: Path to template image
            confidence: Match threshold 0-1 (0.8 = 80% match)
            region: Search region (left, top, width, height)
            
        Returns:
            (x, y, width, height) of match, or None if not found
        """
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence, region=region)
            if location:
                logger.info(f"Found '{image_path}' at {location}")
                return location
            else:
                logger.debug(f"'{image_path}' not found on screen")
                return None
        except Exception as e:
            logger.error(f"Error finding image: {e}")
            return None
    
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get screen resolution.
        
        Returns:
            (width, height) tuple
        """
        return (self.screen_width, self.screen_height)
    
    # ========== WINDOW OPERATIONS ==========
    
    def get_all_windows(self) -> List[str]:
        """
        Get list of all open window titles.
        
        Returns:
            List of window title strings
        """
        try:
            import pygetwindow as gw
            windows = gw.getAllTitles()
            # Filter out empty titles
            windows = [w for w in windows if w.strip()]
            return windows
        except ImportError:
            logger.error("pygetwindow not installed. Run: pip install pygetwindow")
            return []
        except Exception as e:
            logger.error(f"Error getting windows: {e}")
            return []
    
    def activate_window(self, title_substring: str) -> bool:
        """
        Bring window to front by title (partial match).
        
        Args:
            title_substring: Part of window title to match
            
        Returns:
            True if window was activated, False otherwise
        """
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_substring)
            if windows:
                windows[0].activate()
                logger.info(f"Activated window: '{windows[0].title}'")
                return True
            else:
                logger.warning(f"No window found with title containing: '{title_substring}'")
                return False
        except ImportError:
            logger.error("pygetwindow not installed")
            return False
        except Exception as e:
            logger.error(f"Error activating window: {e}")
            return False
    
    def get_active_window(self) -> Optional[str]:
        """
        Get title of currently focused window.

        On macOS, pygetwindow may return a raw string or an object whose
        ``title`` attribute is itself callable. Fall back to frontmost app info
        when a reliable title is unavailable.
        """
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active:
                if isinstance(active, str):
                    return active
                title = getattr(active, 'title', None)
                if callable(title):
                    title = title()
                if title:
                    return title
        except ImportError:
            logger.error("pygetwindow not installed")
        except Exception as e:
            logger.error(f"Error getting active window via pygetwindow: {e}")

        info = self.get_frontmost_app_info()
        return info.get('window_title') or info.get('app_name')
    
    def get_frontmost_app_info(self) -> dict:
        """
        Best-effort frontmost application / window info for macOS.

        Returns:
            Dict with app_name, bundle_id, pid, window_title, and source.
        """
        info = {
            'app_name': None,
            'bundle_id': None,
            'pid': None,
            'window_title': None,
            'source': 'unknown',
        }

        try:
            from AppKit import NSWorkspace
            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if app is not None:
                info['app_name'] = str(app.localizedName() or '') or None
                info['bundle_id'] = str(app.bundleIdentifier() or '') or None
                info['pid'] = int(app.processIdentifier())
                info['source'] = 'nsworkspace'
        except Exception as e:
            logger.debug(f"NSWorkspace frontmost app lookup failed: {e}")

        script = """tell application "System Events"
    try
        set frontApp to first application process whose frontmost is true
        set appName to name of frontApp
        set winName to ""
        try
            if (count of windows of frontApp) > 0 then
                set winName to name of front window of frontApp
            end if
        end try
        return appName & linefeed & winName
    on error errMsg
        return "" & linefeed & ""
    end try
end tell"""
        try:
            proc = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if proc.returncode == 0:
                lines = (proc.stdout or '').splitlines()
                if lines:
                    if lines[0].strip() and not info['app_name']:
                        info['app_name'] = lines[0].strip()
                    if len(lines) > 1 and lines[1].strip():
                        info['window_title'] = lines[1].strip()
                    if info['app_name'] or info['window_title']:
                        info['source'] = 'osascript'
        except Exception as e:
            logger.debug(f"AppleScript frontmost window lookup failed: {e}")

        return info

    # ========== CLIPBOARD OPERATIONS ==========
    
    def copy_to_clipboard(self, text: str) -> None:
        """
        Copy text to clipboard.
        
        Args:
            text: Text to copy
        """
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.info(f"Copied to clipboard: '{text[:50]}...'")
        except ImportError:
            logger.error("pyperclip not installed. Run: pip install pyperclip")
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
    
    def get_from_clipboard(self) -> Optional[str]:
        """
        Get text from clipboard.
        
        Returns:
            Clipboard text, or None if error
        """
        try:
            import pyperclip
            text = pyperclip.paste()
            logger.debug(f"Got from clipboard: '{text[:50]}...'")
            return text
        except ImportError:
            logger.error("pyperclip not installed. Run: pip install pyperclip")
            return None
        except Exception as e:
            logger.error(f"Error getting clipboard: {e}")
            return None
    
    # ========== VERIFICATION / CONFIRMATION GATE ==========

    def save_debug_snapshot(self, filename: Optional[str] = None,
                            region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """Capture a screenshot and return the saved file path."""
        if not filename:
            fd, filename = tempfile.mkstemp(prefix='desktop-control-', suffix='.png')
            Path(filename).unlink(missing_ok=True)
        self.screenshot(region=region, filename=filename)
        return filename

    def get_capture_scale(self) -> Tuple[float, float]:
        """
        Estimate screenshot pixel scale vs logical desktop coordinates.

        Useful on Retina displays where screenshot/template-match coordinates may
        be 2x the pyautogui mouse coordinate space.
        """
        img = self.screenshot()
        x_scale = float(img.width) / float(self.screen_width)
        y_scale = float(img.height) / float(self.screen_height)
        return (x_scale, y_scale)

    def _normalize_text(self, text: Optional[str], *, case_sensitive: bool = False,
                        collapse_whitespace: bool = True) -> str:
        """Normalize text for safer verification matching."""
        value = '' if text is None else str(text)
        if collapse_whitespace:
            value = re.sub(r'\s+', ' ', value).strip()
        return value if case_sensitive else value.lower()

    def _prepare_image_for_ocr(self, image_path: str, scale_factor: int = 2) -> str:
        """Create a higher-contrast temporary image to improve OCR recall."""
        from PIL import Image, ImageEnhance, ImageOps

        image = Image.open(image_path)
        image = ImageOps.grayscale(image)
        image = ImageEnhance.Contrast(image).enhance(2.0)
        if scale_factor and scale_factor > 1:
            image = image.resize(
                (max(1, image.width * scale_factor), max(1, image.height * scale_factor)),
                Image.Resampling.LANCZOS,
            )
        image = image.point(lambda p: 255 if p > 160 else 0)

        fd, prepared_path = tempfile.mkstemp(prefix='desktop-control-ocr-', suffix='.png')
        Path(prepared_path).unlink(missing_ok=True)
        image.save(prepared_path)
        return prepared_path

    def _extract_window_title_text(self) -> dict:
        """Best-effort text extraction from the active window title."""
        info = self.get_frontmost_app_info()
        parts = [x for x in [info.get('window_title'), info.get('app_name')] if x]
        text = ' | '.join(parts).strip()
        return {
            'ok': bool(text),
            'engine': 'window_title',
            'text': text or None,
            'frontmost': info,
            'source': 'window_title',
            'reason': None if text else 'window_title_unavailable',
        }

    def _extract_clipboard_text(self) -> dict:
        """Best-effort text extraction from clipboard for focused input checks."""
        text = self.get_from_clipboard()
        return {
            'ok': text is not None,
            'engine': 'clipboard',
            'text': text,
            'source': 'clipboard',
            'reason': None if text is not None else 'clipboard_unavailable',
        }

    def verify_clipboard(self, expected_text: str, contains: bool = True,
                         case_sensitive: bool = True) -> dict:
        """Verify clipboard text against expectation."""
        actual = self.get_from_clipboard()
        if actual is None:
            return {'ok': False, 'reason': 'clipboard_unavailable', 'actual': None}
        actual_cmp = actual if case_sensitive else str(actual).lower()
        expected_cmp = expected_text if case_sensitive else expected_text.lower()
        ok = expected_cmp in actual_cmp if contains else actual_cmp == expected_cmp
        return {
            'ok': ok,
            'actual': str(actual),
            'expected': expected_text,
            'mode': 'contains' if contains else 'equals',
        }

    def verify_frontmost_app(self, expected_substring: str, case_sensitive: bool = False) -> dict:
        """Verify the current frontmost app/window contains a target substring."""
        info = self.get_frontmost_app_info()
        hay = ' | '.join([x for x in [info.get('app_name'), info.get('window_title')] if x])
        needle = expected_substring
        if not case_sensitive:
            hay = hay.lower()
            needle = needle.lower()
        ok = needle in hay if hay else False
        return {'ok': ok, 'expected': expected_substring, 'info': info}

    def verify_pixel_color(self, x: int, y: int,
                           expected_rgb: Tuple[int, int, int], tolerance: int = 10) -> dict:
        """Verify a pixel is within tolerance of an expected RGB value."""
        actual = self.get_pixel_color(x, y)
        actual_rgb = tuple(int(v) for v in actual)
        diffs = [abs(a - b) for a, b in zip(actual_rgb, expected_rgb)]
        ok = all(d <= tolerance for d in diffs)
        return {
            'ok': ok,
            'actual': actual_rgb,
            'expected': tuple(int(v) for v in expected_rgb),
            'diffs': diffs,
            'tolerance': tolerance,
            'point': (x, y),
        }

    def verify_image_present(self, image_path: str, confidence: float = 0.8,
                             region: Optional[Tuple[int, int, int, int]] = None) -> dict:
        """Verify whether a template image is visible on screen."""
        location = self.find_on_screen(image_path, confidence=confidence, region=region)
        location_tuple = None
        logical_location = None
        scale = self.get_capture_scale()
        if location is not None:
            location_tuple = tuple(int(v) for v in location)
            sx, sy = scale
            logical_location = (
                int(round(location_tuple[0] / sx)),
                int(round(location_tuple[1] / sy)),
                int(round(location_tuple[2] / sx)),
                int(round(location_tuple[3] / sy)),
            )
        return {
            'ok': location is not None,
            'image_path': image_path,
            'confidence': confidence,
            'region': region,
            'location': location_tuple,
            'logical_location': logical_location,
            'capture_scale': scale,
        }

    def get_ocr_status(self) -> dict:
        """Report whether local OCR is available."""
        reasons = []
        tesseract_path = shutil.which('tesseract')
        if tesseract_path is None:
            reasons.append('tesseract binary not found')
        try:
            import pytesseract  # noqa: F401
            pytesseract_ok = True
        except Exception:
            pytesseract_ok = False
            reasons.append('pytesseract module not installed')
        available = bool(tesseract_path and pytesseract_ok)
        return {
            'ok': available,
            'engine': 'tesseract' if available else None,
            'binary_path': tesseract_path,
            'reasons': reasons,
        }

    def extract_text(self, image_path: Optional[str] = None,
                     region: Optional[Tuple[int, int, int, int]] = None,
                     lang: str = 'eng',
                     source: str = 'auto',
                     prefer_preprocess: bool = True,
                     psm: Optional[int] = None) -> dict:
        """
        Extract text from a window title, clipboard, or screenshot.

        Sources:
        - auto: prefer window_title when no image/region is given, otherwise OCR
        - window_title: read frontmost window/app title only
        - clipboard: read current clipboard text only
        - ocr: run OCR on image_path or a fresh screenshot / region

        Returns a structured dict instead of throwing so callers can build safe,
        explicit confirmation gates before risky desktop actions.
        """
        source = (source or 'auto').lower()
        attempted_sources = []

        if source == 'auto':
            sources = ['ocr'] if (image_path or region) else ['window_title', 'ocr']
        elif source in {'window_title', 'clipboard', 'ocr'}:
            sources = [source]
        elif source in {'window_title_or_ocr', 'title_or_ocr'}:
            sources = ['window_title', 'ocr']
        elif source in {'clipboard_or_ocr', 'input_or_ocr'}:
            sources = ['clipboard', 'ocr']
        else:
            return {'ok': False, 'reason': 'unsupported_source', 'source': source, 'text': None}

        for current_source in sources:
            attempted_sources.append(current_source)

            if current_source == 'window_title':
                result = self._extract_window_title_text()
                result['attempted_sources'] = attempted_sources.copy()
                if result.get('ok'):
                    return result
                continue

            if current_source == 'clipboard':
                result = self._extract_clipboard_text()
                result['attempted_sources'] = attempted_sources.copy()
                if result.get('ok'):
                    return result
                continue

            if current_source == 'ocr':
                status = self.get_ocr_status()
                if not status['ok']:
                    result = {
                        'ok': False,
                        'reason': 'ocr_unavailable',
                        'status': status,
                        'text': None,
                        'source': 'ocr',
                        'attempted_sources': attempted_sources.copy(),
                    }
                    continue
                try:
                    import pytesseract
                    from PIL import Image

                    temp_path = None
                    prepared_path = None
                    target_path = image_path
                    if not target_path:
                        temp_path = self.save_debug_snapshot(region=region)
                        target_path = temp_path
                    ocr_path = target_path
                    if prefer_preprocess:
                        prepared_path = self._prepare_image_for_ocr(target_path)
                        ocr_path = prepared_path

                    config_parts = []
                    if psm is not None:
                        config_parts.extend(['--psm', str(int(psm))])
                    config = ' '.join(config_parts) if config_parts else ''
                    text = pytesseract.image_to_string(Image.open(ocr_path), lang=lang, config=config)
                    result = {
                        'ok': True,
                        'engine': 'tesseract',
                        'text': text,
                        'image_path': target_path,
                        'ocr_image_path': ocr_path,
                        'preprocessed': bool(prepared_path),
                        'source': 'ocr',
                        'attempted_sources': attempted_sources.copy(),
                        'lang': lang,
                        'psm': psm,
                    }
                    if temp_path:
                        result['temporary_image'] = True
                    return result
                except Exception as e:
                    result = {
                        'ok': False,
                        'reason': 'ocr_error',
                        'error': str(e),
                        'text': None,
                        'source': 'ocr',
                        'attempted_sources': attempted_sources.copy(),
                    }
                    continue

        result['attempted_sources'] = attempted_sources
        return result

    def verify_text_present(self, expected_text: str, image_path: Optional[str] = None,
                            region: Optional[Tuple[int, int, int, int]] = None,
                            case_sensitive: bool = False, lang: str = 'eng',
                            source: str = 'auto', contains: bool = True,
                            collapse_whitespace: bool = True,
                            prefer_preprocess: bool = True,
                            psm: Optional[int] = None) -> dict:
        """
        Verify text presence via a chosen extraction source.

        Safe defaults for messaging workflows:
        - frontmost title checks: source='window_title'
        - focused compose box checks: source='clipboard_or_ocr'
        - message bubble / partial screenshot checks: source='ocr', region=(...)
        """
        extracted = self.extract_text(
            image_path=image_path,
            region=region,
            lang=lang,
            source=source,
            prefer_preprocess=prefer_preprocess,
            psm=psm,
        )
        if not extracted.get('ok'):
            return {'ok': False, 'reason': extracted.get('reason'), 'extraction': extracted}

        actual_text = extracted.get('text') or ''
        hay = self._normalize_text(actual_text, case_sensitive=case_sensitive,
                                   collapse_whitespace=collapse_whitespace)
        needle = self._normalize_text(expected_text, case_sensitive=case_sensitive,
                                      collapse_whitespace=collapse_whitespace)
        matched = needle in hay if contains else hay == needle
        return {
            'ok': matched,
            'expected': expected_text,
            'actual': actual_text,
            'normalized_expected': needle,
            'normalized_actual': hay,
            'mode': 'contains' if contains else 'equals',
            'source': extracted.get('source'),
            'extraction': extracted,
        }

    def verify_input_text(self, expected_text: str,
                          region: Optional[Tuple[int, int, int, int]] = None,
                          case_sensitive: bool = False,
                          contains: bool = False,
                          lang: str = 'eng') -> dict:
        """
        Verify focused input content with a clipboard-first safe fallback chain.

        Intended for pre-send confirmation in Feishu/Lark compose boxes after a
        deliberate manual copy/select step. This method does not perform any
        risky UI mutation by itself.
        """
        return self.verify_text_present(
            expected_text=expected_text,
            region=region,
            case_sensitive=case_sensitive,
            lang=lang,
            source='clipboard_or_ocr',
            contains=contains,
            collapse_whitespace=True,
            prefer_preprocess=True,
            psm=6,
        )


    def _build_signal(self, name: str, result: dict, *, expected: Optional[str] = None,
                      pass_states: Tuple[str, ...] = ('passed',),
                      meta: Optional[dict] = None) -> dict:
        """Normalize verification sub-signals into a common evidence shape."""
        payload = dict(result or {})
        raw_ok = payload.get('ok')
        status = 'passed' if raw_ok else payload.get('status', 'failed')
        if status not in {'passed', 'failed', 'unknown', 'skipped', 'needs_review'}:
            status = 'passed' if raw_ok else 'failed'
        signal = {
            'name': name,
            'status': status,
            'matched': status in pass_states,
            'expected': expected,
            'actual': payload.get('actual', payload.get('text')),
            'source': payload.get('source') or payload.get('engine'),
            'reason': payload.get('reason'),
            'confidence': payload.get('confidence', 1.0 if raw_ok else 0.0),
            'evidence': payload,
        }
        if meta:
            signal['meta'] = meta
        return signal

    def _finalize_signal_set(self, stage: str, signals: List[dict], *,
                             pass_rule: str, success_threshold: int = 2,
                             strict_failures: Optional[Tuple[str, ...]] = None) -> dict:
        """Aggregate verification signals into a machine-readable stage result."""
        strict_failures = strict_failures or ()
        passed = [s for s in signals if s.get('status') == 'passed']
        failed = [s for s in signals if s.get('status') == 'failed']
        unknown = [s for s in signals if s.get('status') in {'unknown', 'needs_review'}]

        status = 'failed'
        reason = 'insufficient_evidence'
        if any((s.get('reason') in strict_failures) for s in failed):
            status = 'failed'
            reason = next(s.get('reason') for s in failed if s.get('reason') in strict_failures)
        elif pass_rule == 'one_of' and passed:
            status = 'passed'
            reason = 'at_least_one_signal_matched'
        elif pass_rule == 'two_of_n' and len(passed) >= success_threshold:
            status = 'passed'
            reason = 'multi_signal_match'
        elif pass_rule == 'history_plus_empty' and any(s.get('name') == 'history_match' and s.get('status') == 'passed' for s in signals):
            status = 'passed'
            reason = 'history_match'
        elif pass_rule == 'history_plus_empty' and any(s.get('name') == 'composer_empty' and s.get('status') == 'passed' for s in signals) and any(s.get('name') == 'history_context' and s.get('status') == 'passed' for s in signals):
            status = 'passed'
            reason = 'composer_cleared_with_history_context'
        elif unknown and not failed:
            status = 'unknown'
            reason = 'evidence_unavailable'
        elif failed:
            status = 'failed'
            reason = failed[0].get('reason') or 'verification_failed'

        confidence = 0.0
        if signals:
            confidence = round(sum(float(s.get('confidence', 0.0) or 0.0) for s in signals) / len(signals), 3)
        if status == 'passed' and pass_rule == 'two_of_n':
            confidence = max(confidence, 0.9 if len(passed) >= 2 else 0.75)
        elif status == 'passed':
            confidence = max(confidence, 0.8)
        elif status == 'unknown':
            confidence = min(confidence, 0.5)

        return {
            'ok': status == 'passed',
            'state': stage,
            'status': status,
            'reason': reason,
            'confidence': confidence,
            'signals': signals,
            'summary': {
                'passed': len(passed),
                'failed': len(failed),
                'unknown': len(unknown),
                'total': len(signals),
            },
        }

    def verify_feishu_lark_target(self, expected_name: str,
                                  expected_type: Optional[str] = None,
                                  disambiguation_hint: Optional[str] = None,
                                  window_title_hint: Optional[str] = None,
                                  header_region: Optional[Tuple[int, int, int, int]] = None,
                                  sidebar_region: Optional[Tuple[int, int, int, int]] = None,
                                  lang: str = 'chi_sim+eng') -> dict:
        """
        VERIFY_TARGET helper for Feishu/Lark.

        Uses local evidence only: frontmost app/window title, header OCR, sidebar OCR.
        Does not click, type, or send. Caller should provide local regions when available.
        """
        signals = []

        if window_title_hint:
            app_probe = self.verify_text_present(window_title_hint, source='window_title', contains=True, lang=lang)
            app_reason = None if app_probe.get('ok') else 'window_title_mismatch'
            signals.append(self._build_signal('window_title', {**app_probe, 'reason': app_reason}, expected=window_title_hint, meta={'role': 'app_or_title'}))
        else:
            signals.append(self._build_signal('window_title', {'ok': False, 'status': 'unknown', 'reason': 'window_title_hint_missing', 'source': 'window_title'}, expected=None, meta={'role': 'app_or_title'}))

        if header_region is not None:
            header_probe = self.verify_text_present(expected_name, source='ocr', region=header_region, contains=True, lang=lang, psm=6)
            header_reason = None if header_probe.get('ok') else 'header_target_missing'
            signals.append(self._build_signal('header_match', {**header_probe, 'reason': header_reason}, expected=expected_name, meta={'region': header_region, 'role': 'target_header'}))
            if disambiguation_hint:
                disamb = self.verify_text_present(disambiguation_hint, source='ocr', region=header_region, contains=True, lang=lang, psm=6)
                disamb_reason = None if disamb.get('ok') else 'header_disambiguation_missing'
                signals.append(self._build_signal('header_disambiguation', {**disamb, 'reason': disamb_reason}, expected=disambiguation_hint, meta={'region': header_region, 'role': 'target_header_disambiguation'}))
        else:
            signals.append(self._build_signal('header_match', {'ok': False, 'status': 'unknown', 'reason': 'header_region_missing', 'source': 'ocr'}, expected=expected_name))

        if sidebar_region is not None:
            sidebar_probe = self.verify_text_present(expected_name, source='ocr', region=sidebar_region, contains=True, lang=lang, psm=6)
            sidebar_reason = None if sidebar_probe.get('ok') else 'sidebar_target_missing'
            signals.append(self._build_signal('sidebar_match', {**sidebar_probe, 'reason': sidebar_reason}, expected=expected_name, meta={'region': sidebar_region, 'role': 'conversation_sidebar'}))
        else:
            signals.append(self._build_signal('sidebar_match', {'ok': False, 'status': 'unknown', 'reason': 'sidebar_region_missing', 'source': 'ocr'}, expected=expected_name))

        result = self._finalize_signal_set('VERIFY_TARGET', signals, pass_rule='two_of_n', success_threshold=2, strict_failures=('target_mismatch', 'target_ambiguous'))
        result['target'] = {
            'expected_name': expected_name,
            'expected_type': expected_type,
            'disambiguation_hint': disambiguation_hint,
            'window_title_hint': window_title_hint,
        }
        return result

    def verify_feishu_lark_draft(self, expected_text: str,
                                 composer_region: Optional[Tuple[int, int, int, int]] = None,
                                 lang: str = 'chi_sim+eng',
                                 compare_mode: str = 'normalized') -> dict:
        """VERIFY_DRAFT helper for Feishu/Lark compose box confirmation."""
        contains = compare_mode == 'prefix'
        signals = []

        clipboard_probe = self.verify_text_present(
            expected_text,
            source='clipboard',
            contains=contains,
            lang=lang,
        ) if contains else self.verify_text_present(
            expected_text,
            source='clipboard',
            contains=False,
            lang=lang,
        )
        clipboard_reason = None
        if not clipboard_probe.get('ok'):
            actual = (clipboard_probe.get('actual') or '') if isinstance(clipboard_probe, dict) else ''
            clipboard_reason = 'draft_empty' if not actual.strip() else 'draft_mismatch'
        signals.append(self._build_signal('clipboard_readback', {**clipboard_probe, 'reason': clipboard_reason}, expected=expected_text, meta={'role': 'composer_clipboard'}))

        if composer_region is not None:
            ocr_probe = self.verify_text_present(expected_text, source='ocr', region=composer_region, contains=contains, lang=lang, psm=6) if contains else self.verify_text_present(expected_text, source='ocr', region=composer_region, contains=False, lang=lang, psm=6)
            ocr_reason = None
            if not ocr_probe.get('ok'):
                actual = (ocr_probe.get('actual') or '') if isinstance(ocr_probe, dict) else ''
                ocr_reason = 'draft_empty' if not actual.strip() else 'draft_unreadable'
            signals.append(self._build_signal('composer_ocr', {**ocr_probe, 'reason': ocr_reason}, expected=expected_text, meta={'region': composer_region, 'role': 'composer_region'}))
        else:
            signals.append(self._build_signal('composer_ocr', {'ok': False, 'status': 'unknown', 'reason': 'composer_region_missing', 'source': 'ocr'}, expected=expected_text))

        result = self._finalize_signal_set('VERIFY_DRAFT', signals, pass_rule='one_of')
        if result['status'] == 'failed':
            reasons = [s.get('reason') for s in signals if s.get('reason')]
            if 'draft_empty' in reasons:
                result['reason'] = 'draft_empty'
            elif 'draft_unreadable' in reasons and not any(s.get('status') == 'passed' for s in signals):
                result['reason'] = 'draft_unreadable'
            else:
                result['reason'] = 'draft_corrupted'
        result['message'] = {
            'expected_text': expected_text,
            'compare_mode': compare_mode,
        }
        return result

    def verify_feishu_lark_sent(self, expected_text: str,
                                history_region: Optional[Tuple[int, int, int, int]] = None,
                                composer_region: Optional[Tuple[int, int, int, int]] = None,
                                lang: str = 'chi_sim+eng',
                                match_fragment: Optional[str] = None) -> dict:
        """VERIFY_SENT helper for Feishu/Lark using local history/composer evidence only."""
        fragment = match_fragment or expected_text[:80]
        signals = []

        if history_region is not None:
            history_probe = self.verify_text_present(fragment, source='ocr', region=history_region, contains=True, lang=lang, psm=6)
            history_reason = None if history_probe.get('ok') else 'send_not_observed'
            signals.append(self._build_signal('history_match', {**history_probe, 'reason': history_reason}, expected=fragment, meta={'region': history_region, 'role': 'message_history'}))
            signals.append(self._build_signal('history_context', {'ok': True, 'source': 'ocr', 'text': 'history_region_provided', 'confidence': 0.7}, expected='history_region_present', meta={'region': history_region}))
        else:
            signals.append(self._build_signal('history_match', {'ok': False, 'status': 'unknown', 'reason': 'history_region_missing', 'source': 'ocr'}, expected=fragment))

        if composer_region is not None:
            composer_extract = self.extract_text(source='ocr', region=composer_region, lang=lang, psm=6)
            actual = (composer_extract.get('text') or '') if composer_extract.get('ok') else ''
            normalized_actual = self._normalize_text(actual)
            normalized_expected = self._normalize_text(expected_text)
            empty_like = not normalized_actual or normalized_actual == normalized_expected[:len(normalized_actual)] and len(normalized_actual) < max(4, len(normalized_expected)//4)
            payload = {
                **composer_extract,
                'ok': bool(composer_extract.get('ok')) and empty_like,
                'actual': actual,
                'reason': None if (composer_extract.get('ok') and empty_like) else ('composer_not_empty' if composer_extract.get('ok') else composer_extract.get('reason', 'draft_unreadable')),
                'confidence': 0.75 if (composer_extract.get('ok') and empty_like) else composer_extract.get('confidence', 0.0),
            }
            signals.append(self._build_signal('composer_empty', payload, expected='empty_or_cleared', meta={'region': composer_region, 'role': 'composer_after_send'}))
        else:
            signals.append(self._build_signal('composer_empty', {'ok': False, 'status': 'unknown', 'reason': 'composer_region_missing', 'source': 'ocr'}, expected='empty_or_cleared'))

        result = self._finalize_signal_set('VERIFY_SENT', signals, pass_rule='history_plus_empty')
        if result['status'] == 'failed' and result['reason'] == 'composer_not_empty' and not any(s.get('name') == 'history_match' and s.get('status') == 'passed' for s in signals):
            result['status'] = 'unknown'
            result['ok'] = False
            result['reason'] = 'send_uncertain'
        result['message'] = {
            'expected_text': expected_text,
            'match_fragment': fragment,
        }
        return result


    # ========== REGION TEMPLATE / OCR HELPERS ==========

    def get_region_templates(self, app_name: str = 'feishu') -> dict:
        """
        Return normalized region templates for chat UIs.

        Coordinates are expressed as fractions of the full visible content area:
        (x, y, width, height), each in the range [0, 1].

        These templates are intentionally conservative and optimized for OCR
        verification, not pixel-perfect clicking.
        """
        app = (app_name or 'feishu').strip().lower()
        if app in {'lark'}:
            app = 'feishu'

        templates = {
            'feishu': {
                'chat_header': (0.22, 0.025, 0.56, 0.085),
                'header': (0.22, 0.025, 0.56, 0.085),
                'conversation_header': (0.22, 0.025, 0.56, 0.085),
                'message_list': (0.22, 0.115, 0.56, 0.62),
                'messages': (0.22, 0.115, 0.56, 0.62),
                'chat_body': (0.22, 0.115, 0.56, 0.62),
                'composer_input': (0.22, 0.77, 0.56, 0.16),
                'input_box': (0.22, 0.77, 0.56, 0.16),
                'draft_input': (0.22, 0.77, 0.56, 0.16),
            }
        }
        return templates.get(app, templates['feishu']).copy()

    def resolve_region_template(self, template_name: str,
                                app_name: str = 'feishu',
                                image_size: Optional[Tuple[int, int]] = None,
                                padding: Union[int, Tuple[int, int, int, int]] = 0) -> dict:
        """Resolve a normalized template name into an absolute pixel region."""
        templates = self.get_region_templates(app_name=app_name)
        if template_name not in templates:
            return {
                'ok': False,
                'reason': 'unknown_template',
                'template_name': template_name,
                'available_templates': sorted(templates.keys()),
                'app_name': app_name,
            }

        if image_size is None:
            image_size = self.get_screen_size()
        width, height = int(image_size[0]), int(image_size[1])
        nx, ny, nw, nh = templates[template_name]
        x = int(round(nx * width))
        y = int(round(ny * height))
        w = int(round(nw * width))
        h = int(round(nh * height))

        if isinstance(padding, int):
            left = top = right = bottom = int(padding)
        else:
            left, top, right, bottom = [int(v) for v in padding]

        x = max(0, x - left)
        y = max(0, y - top)
        w = max(1, min(width - x, w + left + right))
        h = max(1, min(height - y, h + top + bottom))
        region = (x, y, w, h)
        return {
            'ok': True,
            'template_name': template_name,
            'app_name': app_name,
            'image_size': (width, height),
            'normalized_region': templates[template_name],
            'region': region,
            'padding': (left, top, right, bottom),
        }

    def _crop_image_to_region(self, image_path: str,
                              region: Tuple[int, int, int, int]) -> str:
        """Crop an image to a region and return a temporary file path."""
        from PIL import Image

        x, y, w, h = [int(v) for v in region]
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            cropped = img.crop((x, y, x + w, y + h))
            fd, temp_path = tempfile.mkstemp(prefix='desktop-control-region-', suffix='.png')
            Path(temp_path).unlink(missing_ok=True)
            cropped.save(temp_path)
        return temp_path

    def extract_text_by_template(self,
                                 template_name: str,
                                 app_name: str = 'feishu',
                                 image_path: Optional[str] = None,
                                 lang: str = 'eng',
                                 prefer_preprocess: bool = True,
                                 psm: Optional[int] = 6,
                                 padding: Union[int, Tuple[int, int, int, int]] = 0) -> dict:
        """
        Extract text from a reusable UI template region.

        If image_path is provided, OCR runs on a cropped sub-image derived from the
        template. Otherwise the template resolves against the current screen.
        """
        image_size = None
        if image_path:
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    image_size = img.size
            except Exception as e:
                return {
                    'ok': False,
                    'reason': 'image_open_failed',
                    'error': str(e),
                    'image_path': image_path,
                    'template_name': template_name,
                    'app_name': app_name,
                }

        resolved = self.resolve_region_template(
            template_name=template_name,
            app_name=app_name,
            image_size=image_size,
            padding=padding,
        )
        if not resolved.get('ok'):
            return resolved

        if image_path:
            try:
                cropped_path = self._crop_image_to_region(image_path, resolved['region'])
                result = self.extract_text(
                    image_path=cropped_path,
                    lang=lang,
                    source='ocr',
                    prefer_preprocess=prefer_preprocess,
                    psm=psm,
                )
                result['template'] = resolved
                result['template_crop_path'] = cropped_path
                result['source_image_path'] = image_path
                return result
            except Exception as e:
                return {
                    'ok': False,
                    'reason': 'template_crop_failed',
                    'error': str(e),
                    'template': resolved,
                    'image_path': image_path,
                }

        result = self.extract_text(
            region=resolved['region'],
            lang=lang,
            source='ocr',
            prefer_preprocess=prefer_preprocess,
            psm=psm,
        )
        result['template'] = resolved
        return result

    def verify_text_in_template(self,
                                expected_text: str,
                                template_name: str,
                                app_name: str = 'feishu',
                                image_path: Optional[str] = None,
                                case_sensitive: bool = False,
                                contains: bool = True,
                                collapse_whitespace: bool = True,
                                lang: str = 'eng',
                                prefer_preprocess: bool = True,
                                psm: Optional[int] = 6,
                                padding: Union[int, Tuple[int, int, int, int]] = 0) -> dict:
        """Verify text inside a reusable UI template region."""
        extracted = self.extract_text_by_template(
            template_name=template_name,
            app_name=app_name,
            image_path=image_path,
            lang=lang,
            prefer_preprocess=prefer_preprocess,
            psm=psm,
            padding=padding,
        )
        if not extracted.get('ok'):
            return {'ok': False, 'reason': extracted.get('reason'), 'extraction': extracted}

        actual_text = extracted.get('text') or ''
        hay = self._normalize_text(actual_text, case_sensitive=case_sensitive,
                                   collapse_whitespace=collapse_whitespace)
        needle = self._normalize_text(expected_text, case_sensitive=case_sensitive,
                                      collapse_whitespace=collapse_whitespace)
        matched = needle in hay if contains else hay == needle
        return {
            'ok': matched,
            'expected': expected_text,
            'actual': actual_text,
            'normalized_expected': needle,
            'normalized_actual': hay,
            'mode': 'contains' if contains else 'equals',
            'template_name': template_name,
            'app_name': app_name,
            'template': extracted.get('template'),
            'extraction': extracted,
        }

    # ========== UTILITY METHODS ==========
    
    def pause(self, seconds: float) -> None:
        """
        Pause automation for specified duration.
        
        Args:
            seconds: Time to pause
        """
        logger.info(f"Pausing for {seconds}s...")
        time.sleep(seconds)
    
    def is_safe(self) -> bool:
        """
        Check if it's safe to continue automation.
        Returns False if mouse is in a corner (failsafe position).
        
        Returns:
            True if safe to continue
        """
        if not self.failsafe:
            return True
        
        x, y = self.get_mouse_position()
        corner_tolerance = 5
        
        # Check corners
        corners = [
            (0, 0),  # Top-left
            (self.screen_width - 1, 0),  # Top-right
            (0, self.screen_height - 1),  # Bottom-left
            (self.screen_width - 1, self.screen_height - 1)  # Bottom-right
        ]
        
        for cx, cy in corners:
            if abs(x - cx) <= corner_tolerance and abs(y - cy) <= corner_tolerance:
                logger.warning(f"Mouse in corner ({x}, {y}) - FAILSAFE TRIGGERED")
                return False
        
        return True
    
    def _check_approval(self, action: str) -> bool:
        """
        Check if user approves action (if approval mode is enabled).
        
        Args:
            action: Description of action
            
        Returns:
            True if approved (or approval not required)
        """
        if not self.require_approval:
            return True
        
        response = input(f"Allow: {action}? [y/n]: ").strip().lower()
        approved = response in ['y', 'yes']
        
        if not approved:
            logger.warning(f"Action declined: {action}")
        
        return approved
    
    # ========== CONVENIENCE METHODS ==========
    
    def alert(self, text: str = '', title: str = 'Alert', button: str = 'OK') -> None:
        """Show alert dialog box."""
        pyautogui.alert(text=text, title=title, button=button)
    
    def confirm(self, text: str = '', title: str = 'Confirm', buttons: List[str] = None) -> str:
        """Show confirmation dialog with buttons."""
        if buttons is None:
            buttons = ['OK', 'Cancel']
        return pyautogui.confirm(text=text, title=title, buttons=buttons)
    
    def prompt(self, text: str = '', title: str = 'Input', default: str = '') -> Optional[str]:
        """Show input prompt dialog."""
        return pyautogui.prompt(text=text, title=title, default=default)


# ========== QUICK ACCESS FUNCTIONS ==========

# Global controller instance for quick access
_controller = None

def get_controller(**kwargs) -> DesktopController:
    """Get or create global controller instance."""
    global _controller
    if _controller is None:
        _controller = DesktopController(**kwargs)
    return _controller


# Convenience function exports
def move_mouse(x: int, y: int, duration: float = 0) -> None:
    """Quick mouse move."""
    get_controller().move_mouse(x, y, duration)

def click(x: Optional[int] = None, y: Optional[int] = None, button: str = 'left') -> None:
    """Quick click."""
    get_controller().click(x, y, button=button)

def type_text(text: str, wpm: Optional[int] = None) -> None:
    """Quick text typing."""
    get_controller().type_text(text, wpm=wpm)

def hotkey(*keys) -> None:
    """Quick hotkey."""
    get_controller().hotkey(*keys)

def screenshot(filename: Optional[str] = None):
    """Quick screenshot."""
    return get_controller().screenshot(filename=filename)


# ========== DEMONSTRATION ==========

if __name__ == "__main__":
    print("🖱️  Desktop Control Skill - Test Mode")
    print("=" * 50)
    
    # Initialize controller
    dc = DesktopController(failsafe=True)
    
    # Display info
    print(f"\n📺 Screen Size: {dc.get_screen_size()}")
    print(f"🖱️  Current Mouse Position: {dc.get_mouse_position()}")
    
    # Test window operations
    print(f"\n🪟 Active Window: {dc.get_active_window()}")
    
    windows = dc.get_all_windows()
    print(f"\n📋 Open Windows ({len(windows)}):")
    for i, title in enumerate(windows[:10], 1):  # Show first 10
        print(f"  {i}. {title}")
    
    print("\n✅ Desktop Control ready!")
    print("⚠️  Move mouse to any corner to trigger failsafe")
    
    # Keep running to allow testing
    print("\nController is ready. Import this module to use it in your OpenClaw skills!")
