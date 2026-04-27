# Setup After Fresh Clone

Use separate virtual environments in `prepper-cli/` and `backend/`. Do not create a root-level `.venv`.

## Prerequisites

- Python 3.10+ available as `python3`
- Node.js + npm

## Manual Setup

From the project root:

```bash
# 1) prepper-cli venv + editable install
cd prepper-cli
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install --editable .
cp .env.example .env           # if .env does not exist
# set OPENROUTER_API_KEY in prepper-cli/.env
deactivate
cd ..

# 2) backend venv + deps
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env           # if .env does not exist
# set OPENROUTER_API_KEY in backend/.env
deactivate
cd ..

# 3) frontend dependencies
cd frontend
cp .env.local.example .env.local   # if .env.local does not exist
npm install
cd ..
```

`--editable` (same as `-e`) links `prepper-cli` to local source so edits are picked up without reinstalling.

## Environment Files and API Key

- `prepper-cli/.env.example` -> copy to `prepper-cli/.env`
- `backend/.env.example` -> copy to `backend/.env`
- `frontend/.env.local.example` -> copy to `frontend/.env.local`

For frontend backend-mode calls, set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`.
Default value for local development:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:5000
```

If you change `frontend/.env.local`, restart the frontend dev server so Next.js picks up the new `NEXT_PUBLIC_*` values.

Set `OPENROUTER_API_KEY=...` in both:

- `prepper-cli/.env`
- `backend/.env`

## One-Command Setup

Run from project root:

```bash
./setup.sh
```

This script automates all steps above:

- Creates/uses `prepper-cli/.venv` and `backend/.venv`
- Installs `prepper-cli` with `pip install --editable .`
- Installs backend dependencies
- Runs `npm install` in `frontend/`
- Copies `frontend/.env.local.example` to `frontend/.env.local` when missing (and writes a safe default URL if the example file is unavailable)
- Copies other env example files when target files are missing
