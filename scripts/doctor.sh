#!/usr/bin/env bash
# Mythos AI — environment diagnostic.
#
# Prints exactly which Python interpreter and virtualenv are in play,
# to catch the classic "wrong .venv is active" trap (e.g. a shell that
# auto-activates a same-named venv in $HOME instead of the repo's own).
#
# Usage: bash scripts/doctor.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$REPO_ROOT/.venv/bin/python"

echo "================================================================"
echo " Mythos AI — environment doctor"
echo "================================================================"
echo "Repo root:            $REPO_ROOT"
echo "Expected venv python:  $VENV_PY"
echo ""

echo "--- Shell resolution (what 'python'/'pip' actually run) ---"
echo "VIRTUAL_ENV (shell):   ${VIRTUAL_ENV:-<not set>}"
echo "which python:          $(command -v python 2>/dev/null || echo '<not found>')"
echo "which python3:         $(command -v python3 2>/dev/null || echo '<not found>')"
echo "which pip:             $(command -v pip 2>/dev/null || echo '<not found>')"
echo ""

if [ -n "${VIRTUAL_ENV:-}" ] && [ "$VIRTUAL_ENV" != "$REPO_ROOT/.venv" ]; then
  echo "!! WARNING: the active virtualenv is NOT this repo's .venv."
  echo "!!   Active:   $VIRTUAL_ENV"
  echo "!!   Expected: $REPO_ROOT/.venv"
  echo "!! Run: deactivate && cd \"$REPO_ROOT\" && source .venv/bin/activate"
  echo ""
fi

echo "--- The repo's own venv (ground truth, ignores your shell's PATH/aliases) ---"
if [ -x "$VENV_PY" ]; then
  echo "Exists:                yes"
  echo "Version:                $("$VENV_PY" --version 2>&1)"
  echo ""
  echo "Key packages installed in THIS venv:"
  "$VENV_PY" -m pip list 2>/dev/null | grep -iE "^(requests|openai|fastapi|uvicorn|wsproto|pyaudio|pyttsx3|edge-tts|speechrecognition|wikipedia|pywhatkit) " || echo "  (none of the expected packages found — run scripts/setup_mac.sh)"
else
  echo "Exists:                NO — run: bash scripts/setup_mac.sh"
fi
echo ""

echo "--- tkinter (needed only for the desktop GUI, not --text/--web/--headless) ---"
if [ -x "$VENV_PY" ]; then
  "$VENV_PY" -c "import tkinter; print('tkinter:               OK')" 2>/dev/null \
    || echo "tkinter:               MISSING — run: brew install python-tk@3.12 && bash scripts/setup_mac.sh"
fi
echo ""

echo "--- Port 8765 (default web UI port) ---"
PORT_PID="$(lsof -nP -iTCP:8765 -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -n "$PORT_PID" ]; then
  echo "In use by PID(s):      $PORT_PID"
  echo "  Free it with: kill -9 $PORT_PID"
  echo "  Or run Mythos on another port: WEB_PORT=8766 bash scripts/run_web.sh"
else
  echo "Free"
fi
echo "================================================================"
