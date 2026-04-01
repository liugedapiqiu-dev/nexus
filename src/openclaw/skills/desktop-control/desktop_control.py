"""Compatibility wrapper for importing the desktop-control skill as `desktop_control`.

The skill folder is named `desktop-control`, which is not a valid Python package name.
This shim loads the implementation from the sibling `__init__.py` and re-exports
its public symbols so existing imports like `from desktop_control import DesktopController`
work reliably.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_IMPL_PATH = Path(__file__).with_name("__init__.py")
_SPEC = importlib.util.spec_from_file_location("desktop_control_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load desktop-control implementation from {_IMPL_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

for _name, _value in vars(_MODULE).items():
    if not _name.startswith("_"):
        globals()[_name] = _value

__all__ = [name for name in globals() if not name.startswith("_")]
