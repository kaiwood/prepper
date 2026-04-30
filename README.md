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

```bash
./run.sh --dev
./run.sh --dev --color
```

## Testing

Run all tests from the project root with either command:

```bash
./run.sh --test
./run.sh --test --all
./run.sh --test --color
```

This executes backend, prepper-cli, local tooling, and frontend tests in order. It stops on the first failure.

Run one suite at a time with:

```bash
./run.sh --test --backend
./run.sh --test --frontend
./run.sh --test --cli
./run.sh --test --tools
```

Add `--color` to force colored runner, pytest, Node test, and Next dev output when your terminal supports it.

You can still run the underlying commands manually when debugging a suite:

```bash
cd frontend && npm run test:unit
(cd backend && .venv/bin/python -m pytest tests -q)
(cd prepper-cli && .venv/bin/python -m pytest tests -q)
backend/.venv/bin/python -m pytest tools
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
max_tokens: 5000
---
```

These settings are applied automatically when a prompt is selected.

CLI default behavior: if you do not pass model-setting override flags, `prepper-cli` uses these prompt-file values.

## CLI (`prepper-cli`)

```bash
cp .env.example .env # If not already done
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
- simulated candidate (`strong` by default, or `--weak-candidate`)

Use it to compare prompt quality and interviewer strictness.

Run a default benchmark (strong candidate):

```bash
prepper-cli --benchmark --system-prompt behavioral_focus
```

Simulate a weak candidate:

```bash
prepper-cli --benchmark --system-prompt behavioral_focus --weak-candidate
```

Short, strict coding benchmark:

```bash
prepper-cli --benchmark --system-prompt coding_focus --difficulty hard --question-limit 3 --pass-threshold 8.0
```

Use one model for interview runtime and another for final interviewer scoring:

```bash
prepper-cli --benchmark --system-prompt behavioral_focus --model openai/gpt-5.4 --benchmark-model openai/gpt-4.1
```

Print only comparable benchmark result JSON:

```bash
prepper-cli --benchmark-json --system-prompt behavioral_focus
```

The JSON result includes the runtime model, benchmark scoring model, and resolved runtime model settings.

German benchmark run:

```bash
prepper-cli --benchmark --system-prompt behavioral_focus --language de --question-limit 2
```

Notes:

- `--benchmark` prints the live transcript and bottom evaluation summary
- `--benchmark-json` runs benchmark mode without transcript output and prints interviewer result JSON
- Use either `--benchmark` or `--benchmark-json`, not both
- `--strong-candidate` and `--weak-candidate` only work in benchmark mode
- If you omit both, benchmark uses the strong candidate profile
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
