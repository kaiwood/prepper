# Prepper Monorepo Agent Guide

Use this file as the project-level operating guide for coding agents working in this repository.

## Project Scope

Prepper is interview-prep tooling only.

- Do not add auth, persistence layers, or unrelated product features unless explicitly requested.
- Keep changes aligned with interview simulation, chat UX, prompt management, and scoring flows.

## Monorepo Layout

```text
prepper/
|- backend/      # Flask API
|- frontend/     # Next.js app (App Router, TypeScript, Tailwind)
`- prepper-cli/  # Python package consumed by CLI + backend
```

Services run independently (no Docker/orchestration in repo defaults).

## Environment and Dependency Rules

### Python (backend and prepper-cli)

- Always run Python commands from the service directory.
  - Good: `cd backend && .venv/bin/python -m pytest tests -q`
  - Good: `cd prepper-cli && .venv/bin/python -m pytest tests -q`
- Do not create a root-level virtualenv.
- Backend and prepper-cli use separate `.venv` environments.
- Install `prepper-cli` as editable where needed (`pip install -e ../prepper-cli`).

### Node (frontend)

- Use `npm` only.
- Commit `package-lock.json` for dependency changes.

### Environment Files

- Backend: `backend/.env` (`OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`)
- Frontend: `frontend/.env.local` (`NEXT_PUBLIC_API_URL`)
- prepper-cli: `prepper-cli/.env` (`OPENROUTER_API_KEY`, optional model/base URL overrides)
- Never commit real env files; keep and update example templates.

## Current Runtime Behavior (Source of Truth)

When instructions conflict with implementation, follow current code behavior and avoid accidental regressions.

- Backend app factory: `backend/app/__init__.py`
- CORS restricted to localhost:3000 variants.
- Rate limiting enabled via `flask-limiter`.
- Backend currently supports interview sessions with in-memory `interview_id` state for interview-enabled prompts.
- Active backend routes include:
  - `GET /health`
  - `GET /api/prompts`
  - `POST /api/chat/start`
  - `POST /api/chat`

## Backend Conventions (Flask)

- Use Blueprints in `backend/app/routes/` and register in app factory.
- Return JSON with `jsonify(...)` consistently.
- Validate and strip user input; return 400 for invalid client input.
- Route-level preflight handlers (`OPTIONS`) are expected for browser preflighted endpoints.
- Use `prepper_cli` APIs for LLM behavior; do not call OpenRouter directly from backend route code.

## Frontend Conventions (Next.js)

- Use App Router patterns in `frontend/app/`.
- Use TypeScript (avoid `any`) and Tailwind utility classes.
- Read relevant Next.js docs in `node_modules/next/dist/docs/` before framework-specific changes.
- Use `NEXT_PUBLIC_API_URL` for backend calls.
- Keep chat flow aligned with backend contract:
  - load prompt metadata from `/api/prompts`
  - start interview sessions via `/api/chat/start` when needed
  - continue turns via `/api/chat` with `interview_id` and `conversation_history`

## prepper-cli Conventions

- Public package surface should be exported from `prepper-cli/src/prepper_cli/__init__.py`.
- System prompt files live in `prepper-cli/src/prepper_cli/prompts/` and use front matter metadata.
- CLI supports interactive interview flow and benchmark mode; preserve flag behavior in `main.py`.
- Keep config and OpenRouter client creation centralized (`config.py`, `client.py`).

## Validation Commands

Run only what is relevant to your change.

- Backend tests: `cd backend && .venv/bin/python -m pytest tests -q`
- Frontend tests: `cd frontend && npm run test:unit`
- prepper-cli tests: `cd prepper-cli && .venv/bin/python -m pytest tests -q`
- Full dev runner (root): `./run.sh`

## Change Discipline

- Keep edits minimal and scoped.
- Do not silently change API response shapes used by frontend/CLI.
- Preserve CORS and rate-limit protections unless explicitly asked to alter them.
- Prefer backward-compatible changes unless breaking changes are requested.
