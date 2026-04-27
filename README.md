# Prepper - AI Interview Preparation

Prepper helps you practice interviews with an AI interviewer.

- `backend/`: Flask API that proxies requests to OpenRouter
- `frontend/`: Next.js web app
- `prepper-cli/`: reusable Python package + CLI for local interview practice and benchmarking

## Fresh Clone Setup

Use the dedicated setup guide: [SETUP.md](./SETUP.md) or simply run `./setup.sh` from the project root.

## Run Both Dev Servers

From the project root:

```bash
./run.sh
```

`./run.sh` defaults to `--dev` mode. This starts backend and frontend together and prints both logs in one terminal. Press `Ctrl+C` to stop both.

You can also run modes explicitly:

## Testing

Run all tests from the project root with:

```bash
./run.sh --test
```

This executes tests in order and stops on the first failure.

You can still run suites individually:

### Frontend

```bash
cd frontend
npm run test:unit
```

### Backend

```bash
backend/.venv/bin/python -m pytest backend/tests
```

### prepper-cli

```bash
prepper-cli/.venv/bin/python -m pytest prepper-cli/tests
```

## Project Structure

```text
prepper/
|- backend/
|- frontend/
`- prepper-cli/
```

## Backend Setup

```bash
cp .env.example .env           # then set OPENROUTER_API_KEY
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Backend URL: `http://127.0.0.1:5000`

### Backend API

- `GET /health`
- `POST /api/chat`

Example payload:

```json
{
  "message": "How can I improve for behavioral interviews?",
  "conversation_history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

`conversation_history` is optional. If provided, the backend forwards the last 10 messages as context.

## Backend Debug Logging

Enable detailed logs from the backend + `prepper-cli`:

```bash
cd backend
LOG_LEVEL=DEBUG python run.py
```

- Logs are written to `backend/logs/backend.log`
- Debug entries are also printed in console
- API responses are unchanged (debug info is only logged)

Default log level is `INFO`.

## Prompt Front Matter (Auto-Applied)

Each prompt file in `prepper-cli/src/prepper_cli/prompts/` supports YAML front matter settings:

```yaml
---
id: coding_focus
name: Coding Interview
temperature: 0.3
top_p: 1.0
frequency_penalty: 0.2
presence_penalty: 0.0
max_tokens: 700
---
```

These settings are applied automatically when a prompt is selected.

CLI default behavior: if you do not pass model-setting override flags, `prepper-cli` uses these prompt-file values.

## CLI (`prepper-cli`)

```bash
cp .env.example .env
cd prepper-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Core Usage

Interactive mode is the default (there is no `--interactive` flag):

```bash
prepper-cli
```

From the project root, you can run the same CLI without activating `prepper-cli/.venv` manually:

```bash
./cli.sh
```

Help and all other flags are passed through unchanged:

```bash
./cli.sh --help
./cli.sh --system-prompt coding_focus --difficulty hard
```

Pick a specific interviewer style:

```bash
prepper-cli --system-prompt coding_focus
```

List available prompts:

```bash
prepper-cli --list-system-prompts
```

Interview tuning:

```bash
prepper-cli --system-prompt coding_focus --difficulty hard --question-limit 4 --pass-threshold 7.5
```

Model settings overrides:

```bash
prepper-cli --system-prompt coding_focus --temperature 0.2 --top-p 0.9 --frequency-penalty 0.3 --presence-penalty -0.2 --max-tokens 500
```

Color + language:

```bash
prepper-cli --color --language de --system-prompt behavioral_focus
```

### Benchmark Mode (Important)

Benchmark mode runs a full simulated interview between:

- interviewer prompt (`--system-prompt`)
- simulated candidate (`good` by default, or `--bad-candidate`)

Use it to compare prompt quality and interviewer strictness.

Run a default benchmark (good candidate):

```bash
prepper-cli --benchmark --system-prompt behavioral_focus
```

Simulate a weak candidate:

```bash
prepper-cli --benchmark --system-prompt behavioral_focus --bad-candidate
```

Short, strict coding benchmark:

```bash
prepper-cli --benchmark --system-prompt coding_focus --difficulty hard --question-limit 3 --pass-threshold 8.0
```

Use one model for interview runtime and another for final interviewer scoring:

```bash
prepper-cli --benchmark --system-prompt behavioral_focus --model openai/gpt-4o-mini --benchmark-model openai/gpt-4.1
```

German benchmark run:

```bash
prepper-cli --benchmark --system-prompt behavioral_focus --language de --question-limit 2
```

Notes:

- `--good-candidate` and `--bad-candidate` only work with `--benchmark`
- If you omit both, benchmark uses the good candidate profile
- `--temperature`, `--top-p`, `--frequency-penalty`, `--presence-penalty`, and `--max-tokens` override runtime model settings

## Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local   # defaults to http://127.0.0.1:5000
npm run dev
```

Frontend URL: `http://localhost:3000`

If `localhost:5000` is unreliable on macOS, keep backend URL as `127.0.0.1:5000`.
