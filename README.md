# Prepper - AI Interview Preparation

Prepper helps you practice interviews with an AI interviewer.

- `backend/`: Flask API that proxies requests to OpenRouter
- `frontend/`: Next.js web app
- `prepper-cli/`: reusable Python package + CLI for local interview practice and benchmarking

## Fresh Clone Setup

Use the dedicated setup guide: [SETUP.md](./SETUP.md) or run setup from the project root:

```bash
./prepper.sh --setup
```

## Run Both Dev Servers

From the project root:

```bash
./prepper.sh
```

`./prepper.sh` defaults to `--dev` mode. This starts backend and frontend together and prints both logs in one terminal. Press `Ctrl+C` to stop both.

You can also run modes explicitly:

```bash
./prepper.sh --dev
./prepper.sh -d
./prepper.sh --dev --color
```

## Testing

Run all tests from the project root with either command:

```bash
./prepper.sh --test
./prepper.sh -t
./prepper.sh --test --all
./prepper.sh --test --color
```

This executes backend, prepper-cli, local tooling, and frontend tests in order. It stops on the first failure.

Run one suite at a time with:

```bash
./prepper.sh --test --backend
./prepper.sh --test --frontend
./prepper.sh --test --cli
./prepper.sh --test --tools
```

Add `--color` to `--dev` or `--test` to force colored runner, pytest, Node test, and Next dev output when your terminal supports it. For interactive prepper-cli transcripts, pass `--color` after `--interactive` or `-i`. Benchmark transcripts started with `--benchmark` or `-b` use colored output by default.

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
|- prepper-cli/
`- tools/
```

## Backend Setup

```bash
cp .env.example .env           # then set LLM_API_KEY or OPENROUTER_API_KEY
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Backend URL: `http://127.0.0.1:5000`

### LLM Backend

The app uses an OpenAI-compatible chat completions client. The generic env names below are preferred:

```env
LLM_API_KEY=your_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-5.4
```

The existing `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, and `OPENROUTER_MODEL` names still work as fallbacks.

For a local llama.cpp server:

```bash
llama-server \
  -m /path/to/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf \
  -c 16384 \
  --host 127.0.0.1 \
  --port 8080
```

Then set root `.env`:

```env
LLM_API_KEY=local-dummy
LLM_BASE_URL=http://127.0.0.1:8080/v1
LLM_MODEL=ministral
```

Use an instruct GGUF model for interview/chat behavior.

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
max_tokens: 1200
---
```

These settings are applied automatically when a prompt is selected.

CLI default behavior: if you do not pass model-setting override flags, `prepper-cli` uses these prompt-file values.

The bundled interview prompts currently default `max_tokens` to `1200`; lower this further when running local models with small context windows.

## CLI (`prepper-cli`)

```bash
cp .env.example .env # If not already done
cd prepper-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Core Usage

Interactive mode is the default when you run the installed `prepper-cli` command directly:

```bash
prepper-cli
```

From the project root, you can run the same CLI without activating `prepper-cli/.venv` manually:

```bash
./prepper.sh --interactive
./prepper.sh -i
```

Help and all other flags are passed through unchanged:

```bash
./prepper.sh --interactive --help
./prepper.sh -i --interview-style coding_focus --difficulty hard
```

Pick a specific interviewer style:

```bash
prepper-cli --interview-style coding_focus
```

List available prompts:

```bash
prepper-cli --list-interview-styles
```

Interview tuning:

```bash
prepper-cli --interview-style coding_focus --difficulty hard --question-limit 4 --pass-threshold 7.5
```

Model settings overrides:

```bash
prepper-cli --interview-style coding_focus --temperature 0.2 --top-p 0.9 --frequency-penalty 0.3 --presence-penalty -0.2 --max-tokens 500
```

Color + language:

```bash
./prepper.sh -i --color --language de --interview-style behavioral_focus
./prepper.sh -i --color --language fr --interview-style behavioral_focus
```

### Benchmark Mode (Important)

Benchmark mode runs a full simulated interview between:

- interviewer style (`--interview-style`)
- simulated candidate (`strong` by default, or `--weak-candidate`)

Use it to compare prompt quality and interviewer strictness.

Run a default benchmark (strong candidate):

```bash
./prepper.sh --benchmark --interview-style behavioral_focus
./prepper.sh -b --interview-style behavioral_focus
```

Simulate a weak candidate:

```bash
./prepper.sh -b --interview-style behavioral_focus --weak-candidate
```

Short, strict coding benchmark:

```bash
./prepper.sh -b --interview-style coding_focus --difficulty hard --question-limit 3 --pass-threshold 8.0
```

Use one model for interview runtime and another for final interviewer scoring:

```bash
./prepper.sh -b --interview-style behavioral_focus --model openai/gpt-5.4 --benchmark-model openai/gpt-4.1
```

Print only comparable benchmark result JSON:

```bash
./prepper.sh -i --benchmark-json --interview-style behavioral_focus
```

The JSON result includes the runtime model, benchmark scoring model, and resolved runtime model settings.

German and French benchmark run:

```bash
./prepper.sh -b --interview-style behavioral_focus --language de --question-limit 2
./prepper.sh -b --interview-style behavioral_focus --language fr --question-limit 2
```

Notes:

- `--benchmark` prints the live transcript and bottom evaluation summary
- `-b` is the short alias for `--benchmark`
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
