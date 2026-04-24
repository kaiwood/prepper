#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

if [[ ! -d "$BACKEND_DIR" || ! -d "$FRONTEND_DIR" ]]; then
  echo "Error: run.sh must live in the prepper project root (with backend/ and frontend/)."
  exit 1
fi

BACKEND_PY="python"
if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  BACKEND_PY="$BACKEND_DIR/.venv/bin/python"
fi

cleanup() {
  local exit_code=$?
  trap - INT TERM EXIT

  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  exit "$exit_code"
}

trap cleanup INT TERM EXIT

(
  cd "$BACKEND_DIR"
  PYTHONUNBUFFERED=1 "$BACKEND_PY" run.py 2>&1 | awk '{ print "[backend] " $0; fflush(); }'
) &
BACKEND_PID=$!

(
  cd "$FRONTEND_DIR"
  npm run dev 2>&1 | awk '{ print "[frontend] " $0; fflush(); }'
) &
FRONTEND_PID=$!

echo "Started backend (PID $BACKEND_PID) and frontend (PID $FRONTEND_PID)."
echo "Press Ctrl+C to stop both services."

wait -n "$BACKEND_PID" "$FRONTEND_PID"
