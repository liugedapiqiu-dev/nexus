#!/bin/zsh
set -e
VENV="$HOME/.vectorbrain/.venv-tools"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install -U pip
pip install pypdf
python - <<'PY'
import pypdf
print('PYPDF_OK', pypdf.__version__)
PY
