#!/usr/bin/env bash
# Run the Mythos web chat UI. Kills any stale process already holding the
# target port (a common leftover from a previous run that wasn't stopped
# cleanly), then starts the server using this repo's own venv directly —
# bypassing shell PATH/alias ambiguity entirely.
#
# Usage:
#   bash scripts/run_web.sh            # port 8765
#   WEB_PORT=8766 bash scripts/run_web.sh   # custom port
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$REPO_ROOT/.venv/bin/python"
PORT="${WEB_PORT:-8765}"

if [ ! -x "$VENV_PY" ]; then
  echo "No venv found at $REPO_ROOT/.venv — run: bash scripts/setup_mac.sh" >&2
  exit 1
fi

EXISTING_PID="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -n "$EXISTING_PID" ]; then
  echo "Killing stale process on port $PORT (PID $EXISTING_PID)"
  kill -9 $EXISTING_PID
  sleep 0.5
fi

echo "Starting Mythos web UI on http://127.0.0.1:$PORT"
WEB_PORT="$PORT" exec "$VENV_PY" -m mythos --web
