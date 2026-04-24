# prepper-cli

Standalone Python package for OpenRouter chat calls used by Prepper.

## Structure

```text
prepper-cli/
├── src/
│   └── prepper_cli/
│       ├── main.py           # CLI entry point (argparse)
│       ├── chat.py           # get_chat_reply() — core function
│       ├── conversation.py   # Conversation class — in-memory history
│       ├── client.py         # OpenAI/OpenRouter client factory
│       ├── config.py         # Config dataclass + load_config()
│       ├── system_prompts.py # System prompt discovery/loading
│       └── prompts/          # Bundled system prompts (.md)
└── tests/
    ├── test_smoke.py
    └── test_conversation.py
```

## Setup

```bash
cd prepper-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .

# optional for running tests
pip install pytest
```

Create a `.env` file (or export env vars):

```bash
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-4o-mini
PREPPER_DEFAULT_SYSTEM_PROMPT=interview_coach
```

## Usage

Interactive mode is the default and maintains full conversation context across all prompts in the session:

```bash
prepper-cli
```

Interactive mode with an explicit system prompt:

```bash
prepper-cli --system-prompt coding_focus
```

Interactive mode with color and language:

```bash
prepper-cli --color --language de --system-prompt behavioral_focus
```

Interactive mode supports interview tuning flags when the selected prompt uses interview scoring:

```bash
prepper-cli --system-prompt coding_focus --difficulty hard --question-limit 3 --pass-threshold 7.2
```

Benchmark mode keeps the simulated candidate flow and candidate-profile flags:

```bash
prepper-cli --benchmark --system-prompt behavioral_focus --bad-candidate
```

Interactive mode starts with a prompt selector so you can choose which coaching style to use for that session when `--system-prompt` is not provided. There is no separate `--interactive` flag anymore.

List available system prompts:

```bash
prepper-cli --list-system-prompts
```

Type `exit` or `quit` to leave interactive mode. History is kept in memory for the duration of the session and discarded on exit.

## Prompt Front Matter

Each bundled prompt in `src/prepper_cli/prompts/` starts with a YAML front matter block:

```yaml
---
id: coding_focus # Stable identifier (matches filename stem)
name: Coding Interview # User-friendly label in UI and CLI selector
temperature: 0.3 # Creativity/randomness (0.0–2.0)
top_p: 1.0 # Nucleus sampling cutoff (0.0–1.0)
frequency_penalty: 0.2 # Penalty for token repetition (0.0–2.0)
presence_penalty: 0.0 # Penalty for any previously used token (0.0–2.0)
max_tokens: 700 # Maximum response length in tokens
---
Prompt body goes here…
```

**Settings explained**

| Field               | Effect                                                                                                                                                     |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `temperature`       | Lower = more deterministic and focused (good for technical questions). Higher = more creative and varied (better for open-ended exploration).              |
| `top_p`             | Restricts sampling to the top probability mass. `1.0` uses the full vocabulary. Tune this _or_ `temperature`, not both simultaneously.                     |
| `frequency_penalty` | Reduces repetition of tokens that already appeared often. A small value (`0.2`) keeps responses from looping on the same phrasing.                         |
| `presence_penalty`  | Encourages the model to introduce topics not yet mentioned. Use a low value (`0.1`) for broader behavioral prompts; keep `0.0` for focused technical ones. |
| `max_tokens`        | Caps response length. Higher values allow more detailed answers; lower values keep replies concise and reduce API cost.                                    |

> **OpenRouter note:** These parameters are forwarded as-is via the OpenAI-compatible API. Not every model/provider honours all fields — unsupported parameters may be silently ignored.

The `id` field must match the file stem (e.g. `coding_focus.md` → `id: coding_focus`). The `name` field is the display label used in the frontend dropdown and the interactive CLI prompt selector.

## Conversation History API

The public API now exports a `Conversation` class alongside `get_chat_reply`:

```python
from prepper_cli import get_chat_reply, Conversation

conv = Conversation()

# Each call appends the turn to conv and sends the last 10 messages as context:
reply1 = get_chat_reply("Tell me about Python decorators", conversation=conv)
reply2 = get_chat_reply("Can you give me an example?", conversation=conv)

# Without a Conversation the call is stateless (original behaviour preserved):
reply = get_chat_reply("One-shot question")
```

You can also reconstruct a `Conversation` from a serialised history list (e.g. received from the backend):

```python
conv = Conversation.from_messages([
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
])
```
