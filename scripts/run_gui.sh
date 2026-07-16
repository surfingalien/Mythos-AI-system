#!/usr/bin/env bash
# Run the Mythos desktop GUI (mic + wake word + speech). Always uses this
# repo's own venv directly, bypassing shell PATH/alias ambiguity entirely.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "No venv found at $REPO_ROOT/.venv — run: bash scripts/setup_mac.sh" >&2
  exit 1
fi
if ! "$VENV_PY" -c "import tkinter" 2>/dev/null; then
  echo "tkinter is missing. Run: brew install python-tk@3.12 && bash scripts/setup_mac.sh" >&2
  exit 1
fi
exec "$VENV_PY" -m mythos
