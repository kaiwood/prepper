---
description: "Use when writing or editing code in the prepper-cli/ directory. Covers package layout, public API, OpenRouter integration, CLI conventions, and testing."
applyTo: "prepper-cli/**"
---

# prepper-cli Conventions

## Package Layout

```
prepper-cli/
  src/prepper_cli/   # Source root (src-layout)
    __init__.py      # Public API — only export symbols here
    chat.py          # get_chat_reply() — core function
    client.py        # OpenAI/OpenRouter client factory
    config.py        # Config dataclass + load_config()
    main.py          # CLI entry point (argparse)
  tests/             # pytest tests
  pyproject.toml     # Build + metadata
```

## Public API

`__init__.py` is the only public surface. Currently:

```python
from .chat import get_chat_reply
__all__ = ["get_chat_reply"]
```

- Add new exported symbols to `__all__` in `__init__.py`.
- Internal helpers stay in their module; do not import them from outside the package.

## Configuration

- Config is loaded via `load_config()` in `config.py`, which reads env variables:
  - `OPENROUTER_API_KEY` (required)
  - `OPENROUTER_BASE_URL` (default: `https://openrouter.ai/api/v1`)
  - `OPENROUTER_MODEL` (default: `openai/gpt-4o-mini`)
- Use the `OpenRouterConfig` frozen dataclass; do not pass raw env strings around.
- `load_dotenv()` is called inside `load_config()` — don't call it elsewhere in the package.

## OpenRouter Client

- Use the **OpenAI Python SDK** pointed at OpenRouter (`base_url` from config).
- Obtain the client via `get_client()` in `client.py`; do not construct `OpenAI(...)` elsewhere.

## Core Function: `get_chat_reply`

```python
def get_chat_reply(message: str) -> str
```

- Strip and validate input; raise `ValueError("message is required")` for empty input.
- Return the assistant's reply as a plain string (stripped).
- This function is consumed by both the CLI (`main.py`) and the Flask backend — keep it side-effect-free.

## CLI (main.py)

- Use `argparse` for argument parsing.
- Support single-message mode (`prepper-cli "prompt"`) and interactive mode (`prepper-cli -i`).
- Interactive loop exits cleanly on `EOF`, `KeyboardInterrupt`, or `exit`/`quit` input.
- Return integer exit codes from `main()`.

## Dependencies

- Runtime: `openai`, `python-dotenv` (declared in `pyproject.toml`).
- Dev/test: `pytest` — list in `requirements-dev.txt` or as an optional dep.
- Install locally as editable: `pip install -e ../prepper-cli`.

## Testing

- Tests live in `prepper-cli/tests/`.
- Run with `pytest` from the `prepper-cli/` directory.
