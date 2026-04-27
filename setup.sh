#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

PREPPER_CLI_DIR="$SCRIPT_DIR/prepper-cli"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

if [[ ! -d "$PREPPER_CLI_DIR" || ! -d "$BACKEND_DIR" || ! -d "$FRONTEND_DIR" ]]; then
  echo "Error: run setup.sh from the prepper project root." >&2
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: '$PYTHON_BIN' not found. Set PYTHON_BIN or install Python 3." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm not found. Install Node.js and npm first." >&2
  exit 1
fi

create_venv_if_missing() {
  local dir="$1"
  local venv_dir="$dir/.venv"
  if [[ ! -d "$venv_dir" ]]; then
    echo "Creating virtual environment: $venv_dir"
    "$PYTHON_BIN" -m venv "$venv_dir"
  else
    echo "Using existing virtual environment: $venv_dir"
  fi
}

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ -f "$src" && ! -f "$dst" ]]; then
    cp "$src" "$dst"
    echo "Created $dst from $src"
  fi
}

echo "==> Setting up prepper-cli"
create_venv_if_missing "$PREPPER_CLI_DIR"
# shellcheck disable=SC1091
source "$PREPPER_CLI_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install --editable "$PREPPER_CLI_DIR"
deactivate
copy_if_missing "$PREPPER_CLI_DIR/.env.example" "$PREPPER_CLI_DIR/.env"

echo "==> Setting up backend"
create_venv_if_missing "$BACKEND_DIR"
# shellcheck disable=SC1091
source "$BACKEND_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
(
  cd "$BACKEND_DIR"
  python -m pip install -r requirements.txt
)
deactivate
copy_if_missing "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"

echo "==> Setting up frontend"
copy_if_missing "$FRONTEND_DIR/.env.local.example" "$FRONTEND_DIR/.env.local"
(
  cd "$FRONTEND_DIR"
  npm install
)

echo
echo "Setup complete."
echo "Set OPENROUTER_API_KEY in:"
echo "  - $PREPPER_CLI_DIR/.env"
echo "  - $BACKEND_DIR/.env"
