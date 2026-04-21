---
description: "Use when writing or editing code in the prepper-cli/ directory. Covers package layout, public API, OpenRouter integration, CLI conventions, and testing."
applyTo: "prepper-cli/**"
---

# prepper-cli Conventions

## Package Layout

```
prepper-cli/
  src/prepper_cli/   # Source root (src-layout)
    __init__.py        # Public API — only export symbols here
    chat.py            # get_chat_reply() — core function
    conversation.py    # Conversation class — in-memory session history
    client.py          # OpenAI/OpenRouter client factory
    config.py          # Config dataclass + load_config()
    main.py            # CLI entry point (argparse)
  tests/               # pytest tests
  pyproject.toml       # Build + metadata
```

## Public API

`__init__.py` is the only public surface. Currently:

```python
from .chat import get_chat_reply
from .conversation import Conversation
__all__ = ["get_chat_reply", "Conversation"]
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
def get_chat_reply(
    message: str,
    conversation: Conversation | None = None,
    history_limit: int = 10,
) -> str
```

- Strip and validate input; raise `ValueError("message is required")` for empty input.
- Return the assistant's reply as a plain string (stripped).
- When `conversation` is provided, the last `history_limit - 1` messages are prepended to the request, and the new user/assistant turn is appended to `conversation` automatically.
- When `conversation` is `None` (default), behaviour is identical to the original stateless call — backward compatible.
- This function is consumed by both the CLI (`main.py`) and the Flask backend.

## Conversation Class (`conversation.py`)

- `Conversation` tracks a list of `{"role", "content"}` message dicts for a single session.
- Key methods: `add_user_message(content)`, `add_assistant_reply(content)`, `get_messages()`, `get_recent_messages(limit=10)`.
- `Conversation.from_messages(iterable)` reconstructs state from a serialised list; raises `ValueError` for invalid roles or non-string content.
- History is **in-memory only** — it is discarded when the process exits.
- Do not persist `Conversation` state to disk or a database in this package.

## CLI (main.py)

- Use `argparse` for argument parsing.
- Support single-message mode (`prepper-cli "prompt"`) and interactive mode (`prepper-cli -i` / `--interactive`).
- Interactive mode creates one `Conversation()` instance before the loop and passes it to every `get_chat_reply()` call, giving the LLM full session context.
- Single-message mode does **not** use a `Conversation` — it is a stateless one-shot call.
- Interactive loop exits cleanly on `EOF`, `KeyboardInterrupt`, or `exit`/`quit` input.
- Return integer exit codes from `main()`.

## Dependencies

- Runtime: `openai`, `python-dotenv` (declared in `pyproject.toml`).
- Dev/test: `pytest` — list in `requirements-dev.txt` or as an optional dep.
- Install locally as editable: `pip install -e ../prepper-cli`.

## Testing

- Tests live in `prepper-cli/tests/`.
- To be able to run tests, you need to activate the virtual environment first
- Run with `pytest` from the `prepper-cli/` directory.
