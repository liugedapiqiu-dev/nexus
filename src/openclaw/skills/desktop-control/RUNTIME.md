# desktop-control Runtime / Installation Notes

## Current runtime contract

This skill lives in a folder named `desktop-control`, but Python imports cannot use a hyphenated package name directly.

To keep the existing folder layout unchanged while making imports stable, use:

```python
from desktop_control import DesktopController
```

This works via the local compatibility shim:

- `desktop_control.py` → loads and re-exports the implementation from `__init__.py`

## Python boundary: system vs skill venv

### Recommended default
Use the skill-local virtualenv for all execution related to this skill:

```bash
cd ~/.openclaw/skills/desktop-control
./.venv/bin/python smoke_test.py
```

Reason:
- avoids polluting system Python
- keeps PyAutoGUI / Pillow / OpenCV / pyobjc versions reproducible
- reduces surprises when other projects upgrade shared packages

### System Python
System/Homebrew Python is only acceptable for bootstrapping or emergency debugging.
Do **not** rely on it as the long-term runtime contract unless you intentionally install the same pinned dependencies there.

## Create / refresh the venv

```bash
cd ~/.openclaw/skills/desktop-control
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r requirements-macos.txt
```

## Known working runtime on this machine

- OS: macOS (Darwin arm64)
- Python: 3.14.3
- venv path: `~/.openclaw/skills/desktop-control/.venv`

## Execution patterns

### Import test
```bash
cd ~/.openclaw/skills/desktop-control
./.venv/bin/python -c "from desktop_control import DesktopController; print('ok', DesktopController)"
```

### Safe smoke test
```bash
cd ~/.openclaw/skills/desktop-control
./.venv/bin/python smoke_test.py
```

### Demo suite
```bash
cd ~/.openclaw/skills/desktop-control
./.venv/bin/python demo.py
```

## skill.json alignment note

`skill.json` currently advertises:

```json
"entry": {
  "type": "cli",
  "command": "desktop-control"
}
```

But this repository does not install a PATH command named `desktop-control` by default.
So the practical runtime entry today is **Python-in-venv + local files**, not a globally installed CLI.

Until a real CLI wrapper is installed onto PATH, treat these as the supported entrypoints:

- `./.venv/bin/python smoke_test.py`
- `./.venv/bin/python demo.py`
- `./.venv/bin/python -c "from desktop_control import DesktopController"`

## Permissions / platform notes

Desktop automation on macOS may require:
- Accessibility permission
- Screen Recording permission (for screenshots / image recognition)
- Input Monitoring in some environments

If import succeeds but actions fail at runtime, check macOS privacy permissions first.
