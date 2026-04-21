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
│       └── config.py         # Config dataclass + load_config()
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
```

## Usage

One-shot:

```bash
prepper-cli "How should I prepare for a backend interview?"
```

Interactive mode — maintains full conversation context across all prompts in the session:

```bash
prepper-cli --interactive
```

Type `exit` or `quit` to leave interactive mode. History is kept in memory for the duration of the session and discarded on exit.

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
