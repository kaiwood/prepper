#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python >/dev/null 2>&1; then
  exec python "$SCRIPT_DIR/tools/dev_runner.py"
fi

exec python3 "$SCRIPT_DIR/tools/dev_runner.py"
