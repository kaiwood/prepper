# HR Prototype

The HR prototype extends Prepper with fixture-backed company/candidate context, HR-domain tools, candidate-fit retrieval, candidate-fit interviews, and a setup assistant.

## Scope

- Prototype only: no auth, database persistence, LinkedIn scraping, or scheduling.
- HR context and interview sessions are stored in backend memory for the running process.
- Company pages, resumes, profile text, transcripts, and chat input are treated as untrusted.
- Backend HR endpoints are rate limited to 10 requests per minute per client IP.
- Unexpected HR API failures return generic errors to avoid leaking resume, profile, company, or transcript content.

## Fixture Format

Fixtures live under `app/fixtures/hr/<fixture_id>/`.

Required files:

```text
company.md
role.md
resume.md
profile.md
transcripts/strong.md
transcripts/weak.md
```

Use Markdown headings to make chunks and summaries deterministic. Transcript files are Markdown replays with interviewer turns, candidate turns, tool/source events, and expected final result metadata. Validate fixtures before using them in workflows.

```bash
cd app
.venv/bin/prepper-cli hr fixtures list
.venv/bin/prepper-cli hr fixtures validate --fixture demo_hr
```

## Environment

For mock mode, no credentials are required.

For live LLM mode, set the root `.env` values. Chat/model calls can use the generic `LLM_*` names; live HR retrieval currently requires the OpenRouter embedding names.

```env
LLM_API_KEY=your_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-5.4
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_EMBEDDING_MODEL=your_embedding_model
```

`OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, and `OPENROUTER_MODEL` remain supported as chat model fallbacks. `HR_SIMULATION_MODE` in `.env.example` is documentation-only; choose mode with CLI/API flags.

## CLI Commands

Run from `app/` with `.venv/bin/prepper-cli`, or use an installed `prepper-cli`.

Build and inspect context:

```bash
prepper-cli hr context build --fixture demo_hr --mode mock --out tmp/hr-context.json
prepper-cli hr context inspect --context tmp/hr-context.json --json
prepper-cli hr context retrieve --context tmp/hr-context.json --query "company values" --mode mock --json
```

Retrieval searches candidate resume/profile evidence only. Company and role context are used to shape the semantic query so returned snippets are candidate facts relevant to the opportunity.

Run tools:

```bash
prepper-cli hr tool run fetch_company_website --fixture demo_hr --mode mock --json
prepper-cli hr tool run extract_candidate_profile --fixture demo_hr --mode mock --json
prepper-cli hr tool run retrieve_company_context --context tmp/hr-context.json --query "interest in company" --mode mock --json
```

Replay deterministic interviews:

```bash
prepper-cli hr interview replay --fixture demo_hr --transcript fixtures/hr/demo_hr/transcripts/strong.md --json
prepper-cli hr interview replay --fixture demo_hr --transcript fixtures/hr/demo_hr/transcripts/weak.md --json
```

Run full workflows:

```bash
prepper-cli hr workflow run --fixture demo_hr --mode mock --json
prepper-cli hr workflow run --fixture demo_hr --mode llm --candidate strong --json
```

Generate a reusable live transcript:

```bash
prepper-cli hr interview simulate --fixture demo_hr --candidate strong --mode llm --out tmp/hr-strong-run.md --json
```

Ask the setup assistant:

```bash
prepper-cli hr assistant ask --fixture demo_hr --message "What should I ask first?" --mode mock --json
```

## Backend and Frontend Manual Check

1. Start the backend and frontend.
2. In the Admin/HR setup UI, enter company URL or company text, role description, resume text, and optional profile text.
3. Build HR context and confirm summaries, sources, and tool results appear.
4. Start the HR candidate-fit interview from the built context.
5. Answer until the final score appears.
6. Confirm source/tool displays update during interview turns.
7. Confirm the existing non-HR interview flow still works.

API endpoints:

- `POST /api/hr/context`
- `POST /api/hr/interview/start`
- `POST /api/hr/interview`
- `POST /api/hr/assistant`

## Verification

```bash
cd backend && .venv/bin/python -m pytest tests -q
cd app && .venv/bin/python -m pytest tests -q
cd frontend && npm run test:unit
```

Mock workflow for CI/local repeatability:

```bash
cd app && .venv/bin/prepper-cli hr workflow run --fixture demo_hr --mode mock --json
```

Live workflow for manual validation with credentials:

```bash
cd app && .venv/bin/prepper-cli hr workflow run --fixture demo_hr --mode llm --candidate strong --json
```
