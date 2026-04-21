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
