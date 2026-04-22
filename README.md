# Prepper — Interview Preparation App

An AI-powered interview preparation tool. The backend proxies questions to an LLM via OpenRouter; the frontend provides the user interface.

## Structure

```
prepper/
├── backend/   # Python Flask API
├── frontend/  # Next.js app
└── prepper-cli/ # Shared OpenRouter package + CLI
```

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then fill in your OPENROUTER_API_KEY
python run.py
```

The API runs at `http://127.0.0.1:5000`.

**Endpoints**

- `GET  /health` — health check
- `POST /api/chat` — send `{ "message": "...", "conversation_history": [...] }`, get back `{ "reply": "..." }`

`conversation_history` is optional. When provided it must be a list of `{ "role": "user" | "assistant", "content": "..." }` objects representing the prior turns. The backend passes the last 10 messages to the LLM as context (sliding window).

The backend uses the local `prepper-cli` package for all OpenRouter calls.

## Prompt Tuning Settings

Every bundled system prompt file includes a YAML front matter block that controls how the LLM responds. These settings are applied automatically when a prompt is selected — no manual tuning is required.

```yaml
---
id: coding_focus # Stable identifier used by the backend and CLI
name: Coding Interview # User-friendly label shown in the UI and CLI selector
temperature: 0.3 # Creativity/randomness (0.0–2.0)
top_p: 1.0 # Nucleus sampling cutoff (0.0–1.0)
frequency_penalty: 0.2 # Penalty for repeating the same tokens (0.0–2.0)
presence_penalty: 0.0 # Penalty for repeating any previously used token (0.0–2.0)
max_tokens: 700 # Maximum number of tokens in the model's response
---
```

**Field descriptions**

| Field               | What it does                                                                                                                                                                                                                                                                                |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                | Stable identifier matching the filename stem (e.g. `coding_focus`). Used programmatically by the backend and CLI — changing this is a breaking change.                                                                                                                                      |
| `name`              | Human-readable label shown in the prompt selector dropdown and the interactive CLI menu. Safe to update freely.                                                                                                                                                                             |
| `temperature`       | Controls output randomness. Lower values (e.g. `0.3`) produce focused, predictable answers — better for technical questions. Higher values (e.g. `0.7+`) produce more creative or varied responses.                                                                                         |
| `top_p`             | Nucleus sampling: the model draws only from tokens whose combined probability reaches this threshold. `1.0` means the full vocabulary is considered. Lower values (e.g. `0.9`) restrict the model to higher-confidence tokens. Tune either `temperature` or `top_p`, not both aggressively. |
| `frequency_penalty` | Discourages repeating tokens that have already appeared many times. Useful for long coaching replies that tend to reuse the same phrasing. A mild value (`0.2`) reduces repetition without noticeably constraining style.                                                                   |
| `presence_penalty`  | Discourages repeating any token that has appeared at all, pushing the model to introduce new ideas. Use lightly (e.g. `0.1`) for behavioral prompts where topic variety is helpful; keep at `0.0` for focused technical prompts.                                                            |
| `max_tokens`        | Hard cap on response length. Guards against unexpectedly long replies and controls API cost. Increase for prompts that require detailed explanations.                                                                                                                                       |

> **OpenRouter note:** These parameters are forwarded via the OpenAI-compatible API. Support varies by model and provider — a parameter may be silently ignored if the underlying model does not honour it.

To add a new prompt or customise tuning for an existing one, edit the corresponding `.md` file in `prepper-cli/src/prepper_cli/prompts/`.

## prepper-cli

```bash
cd prepper-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

One-shot mode:

```bash
prepper-cli "How should I prepare for behavioral interview questions?"
```

Interactive mode (maintains conversation context across all prompts in the session):

```bash
prepper-cli --interactive
```

## Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # uses http://127.0.0.1:5000 by default
npm run dev
```

The app runs at `http://localhost:3000`.

If `localhost:5000` behaves oddly on macOS, keep using `127.0.0.1:5000` for the backend URL.
