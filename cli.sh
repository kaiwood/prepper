#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$SCRIPT_DIR/prepper-cli"
CLI_VENV_PYTHON="$CLI_DIR/.venv/bin/python"

if [[ ! -x "$CLI_VENV_PYTHON" ]]; then
  echo "Error: prepper-cli virtualenv is missing at prepper-cli/.venv." >&2
  echo "Run ./setup.sh (or set up prepper-cli/.venv manually) and try again." >&2
  exit 1
fi

cd "$CLI_DIR"
exec "$CLI_VENV_PYTHON" -m prepper_cli.main "$@"
