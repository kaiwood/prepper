# prepper-cli

Standalone Python package for OpenRouter chat calls used by Prepper.

## Structure

```text
prepper-cli/
├── src/
│   └── prepper_cli/
│       ├── main.py
│       ├── chat.py
│       ├── client.py
│       └── config.py
└── tests/
	└── test_smoke.py
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

Interactive mode:

```bash
prepper-cli --interactive
```

Type `exit` or `quit` to leave interactive mode.
