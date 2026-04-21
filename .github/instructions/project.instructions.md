---
description: "Use when working anywhere in the prepper monorepo. Covers overall structure, service layout, environment variable conventions, and dependency management."
applyTo: "**"
---

# Prepper — Project-Wide Conventions

## Monorepo Layout

```
prepper/
  backend/        # Flask API (Python)
  frontend/       # Next.js UI (TypeScript)
  prepper-cli/    # Pip-installable Python package consumed by both the CLI and backend
```

Services run **independently** — no Docker, no orchestration layer.

## Environment Variables

| Service  | File                  | Key variables                               |
| -------- | --------------------- | ------------------------------------------- |
| backend  | `backend/.env`        | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` |
| frontend | `frontend/.env.local` | `NEXT_PUBLIC_API_URL`                       |

- Never commit `.env` or `.env.local` files.
- Provide `.env.example` / `.env.local.example` as templates.
- Load env via `python-dotenv` on the backend; Next.js reads them automatically on the frontend.

## Python (backend + prepper-cli)

- Use `pip` + `venv`; commit `requirements.txt` (runtime) and `requirements-dev.txt` (dev/test).
- `prepper-cli` is installed as a local editable package (`pip install -e ../prepper-cli`).
- Never hard-code API keys or base URLs.

## Node / npm (frontend)

- Use `npm`; commit `package-lock.json`.
- No Yarn, no pnpm.

## Scope

This project is **interview-prep tooling only**. Do not add auth, persistence, or features beyond the stated scope without explicit agreement.
