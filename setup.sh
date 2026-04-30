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

ensure_frontend_env_local() {
  local example="$FRONTEND_DIR/.env.local.example"
  local target="$FRONTEND_DIR/.env.local"

  if [[ -f "$target" ]]; then
    return
  fi

  if [[ -f "$example" ]]; then
    cp "$example" "$target"
    echo "Created $target from $example"
    return
  fi

  cat >"$target" <<'EOF'
NEXT_PUBLIC_API_URL=http://127.0.0.1:5000
EOF
  echo "Created $target with default NEXT_PUBLIC_API_URL"
}

ensure_root_env() {
  local example="$SCRIPT_DIR/.env.example"
  local target="$SCRIPT_DIR/.env"

  if [[ -f "$target" ]]; then
    return
  fi

  if [[ -f "$example" ]]; then
    cp "$example" "$target"
    echo "Created $target from $example"
    return
  fi

  cat >"$target" <<'EOF'
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
PREPPER_DEFAULT_SYSTEM_PROMPT=coding_focus
OPENROUTER_MODEL=openai/gpt-5.4
EOF
  echo "Created $target with default OpenRouter settings"
}

ensure_root_env

echo "==> Setting up prepper-cli"
create_venv_if_missing "$PREPPER_CLI_DIR"
# shellcheck disable=SC1091
source "$PREPPER_CLI_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install --editable "$PREPPER_CLI_DIR"
deactivate

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

echo "==> Setting up frontend"
ensure_frontend_env_local
(
  cd "$FRONTEND_DIR"
  npm install
)

echo
echo "Setup complete."
echo "Set OPENROUTER_API_KEY in:"
echo "  - $SCRIPT_DIR/.env"
