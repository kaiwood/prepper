# Prepper — Interview Preparation App

An AI-powered interview preparation tool. The backend proxies questions to an LLM via OpenRouter; the frontend provides the user interface.

## Structure

```
prepper/
├── backend/   # Python Flask API
└── frontend/  # Next.js app
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

The API runs at `http://localhost:5000`.

**Endpoints**
- `GET  /health`   — health check
- `POST /api/chat` — send `{ "message": "..." }`, get back `{ "reply": "..." }`

## Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # adjust if backend runs on a different port
npm run dev
```

The app runs at `http://localhost:3000`.
