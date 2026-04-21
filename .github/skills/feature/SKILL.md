---
name: feature
description: "Plan and implement new features in the prepper monorepo. Use when adding backend Flask endpoints, frontend Next.js UI flows, prepper-cli behavior, or cross-service feature updates with tests and validation."
argument-hint: "Describe the feature goal, affected areas (backend/frontend/prepper-cli), constraints, and acceptance criteria."
user-invocable: true
---

# Create Feature

Use this quick checklist to implement a feature with clear quality gates.

## When To Use

- New product capability in backend, frontend, prepper-cli, or multiple services.
- Feature updates that need predictable scope, tests, and validation.

## Quick Checklist

1. Define the feature.

- State user value in one sentence.
- List acceptance criteria and non-goals.

2. Choose the implementation path.

- Backend only: route plus logic plus error handling.
- Frontend only: UI states plus API integration.
- CLI only: command behavior plus argument and output rules.
- Cross-service: define contract first, then update producer and consumer.

3. Ship the smallest vertical slice.

- Implement one end-to-end happy path before edge cases.
- Reuse established patterns in each service.

4. Add tests with the code.

- Cover happy path and primary failure path.
- Validate contract changes where services interact.

5. Validate and finish.

- Run targeted checks for changed behavior.
- Confirm acceptance criteria are met.
- Check if the README files need updating - but don't document every internal detail, only user-facing changes.
- If the architectural contract changed, check if the agent instruction files need updating - but only if the change affects how agents should interact with the service.
- Summarize changed files, test evidence, and remaining risks.

## Decision Rules

- If requirements are unclear, pause and ask focused questions.
- If scope is large, split into independent slices.
- If tests and assumptions conflict, trust acceptance criteria.
- If a contract changes, update all affected consumers in one change.

## Done Definition

- Acceptance criteria satisfied.
- Tests for changed behavior pass.
- Primary error states handled.
- Final summary includes scope, evidence, and risks.
