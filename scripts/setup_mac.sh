#!/usr/bin/env bash
# Mythos AI — one-shot macOS setup.
#
# Installs system dependencies via Homebrew, builds a fresh virtualenv
# INSIDE this repo (never in $HOME, to avoid activating the wrong venv),
# and installs all Python dependencies into it using explicit binary
# paths throughout — never relying on however `python`/`pip` happen to
# resolve in your shell.
#
# Usage:
#   cd Mythos-AI-system
#   bash scripts/setup_mac.sh
#
# Safe to re-run any time — it rebuilds the venv from scratch.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
echo "==> Repo root: $REPO_ROOT"

# --- 1. Homebrew ---
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found. Install it from https://brew.sh, then re-run this script." >&2
  exit 1
fi

# --- 2. System dependencies ---
# portaudio   -> required to build pyaudio (microphone capture)
# python-tk   -> provides the _tkinter module for the desktop GUI
# ffmpeg      -> provides ffplay, used to play edge-tts neural speech
echo "==> Installing system dependencies via Homebrew..."
brew install python@3.12 portaudio python-tk@3.12 ffmpeg

PYTHON_BIN="$(brew --prefix python@3.12)/bin/python3.12"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "Could not find python3.12 at $PYTHON_BIN" >&2
  exit 1
fi
echo "==> Using interpreter: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

# --- 3. Fresh venv, always inside the repo ---
VENV_DIR="$REPO_ROOT/.venv"
if [ -d "$VENV_DIR" ]; then
  echo "==> Removing existing venv at $VENV_DIR"
  rm -rf "$VENV_DIR"
fi
echo "==> Creating venv at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

VENV_PY="$VENV_DIR/bin/python"

# --- 4. Install Python dependencies (explicit venv path, no PATH ambiguity) ---
echo "==> Upgrading pip"
"$VENV_PY" -m pip install --upgrade pip

echo "==> Installing requirements.txt"
"$VENV_PY" -m pip install -r "$REPO_ROOT/requirements.txt"

echo "==> Installing web UI extras (fastapi, uvicorn, wsproto)"
"$VENV_PY" -m pip install fastapi uvicorn wsproto

# --- 5. .env ---
if [ ! -f "$REPO_ROOT/.env" ]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  echo "==> Created .env from .env.example — edit it to add your API keys."
else
  echo "==> .env already exists, leaving it as-is."
fi

echo ""
echo "================================================================"
echo " Setup complete."
echo ""
echo " This venv lives at exactly one place:"
echo "   $VENV_DIR"
echo ""
echo " Always run scripts/doctor.sh if anything seems off — it prints"
echo " exactly which interpreter and venv are actually active."
echo ""
echo " Try it now:"
echo "   bash scripts/run_text.sh"
echo "================================================================"
