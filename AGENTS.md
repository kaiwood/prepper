# AGENTS.md — AI Development Guidelines

## 🧠 Purpose

This file defines how AI agents should operate within this repository.

Goals:

- Maintain architectural integrity
- Avoid unnecessary changes
- Produce predictable, production-ready code
- Minimize regressions

---

## 🏗️ Architecture Overview

- Backend: Flask (service-oriented structure)
- Frontend: Next.js (functional components, hooks)
- CLI: interacts with LLM via API
- Clear separation of concerns is mandatory

DO NOT:

- Mix frontend/backend logic
- Introduce hidden coupling between layers

---

## ⚙️ General Coding Principles

- Prefer **simple, explicit solutions**
- Avoid unnecessary abstractions
- Keep functions small and focused
- Follow existing patterns in the codebase

PRIORITY ORDER:

1. Correctness
2. Readability
3. Consistency
4. Performance

---

## 🚫 Global Guardrails (CRITICAL)

### Scope Control

- DO NOT modify files unrelated to the task
- DO NOT refactor outside the defined scope
- DO NOT rename files unless explicitly required
- DO NOT create a Python .venv in the root directory

### Change Minimization

- Make the **smallest possible change** to achieve the goal
- Avoid “while we are here” improvements

### No Assumptions

- DO NOT guess missing requirements
- ASK if something is unclear

---

## 🔧 Refactoring Rules (STRICT)

Refactoring is ONLY allowed if:

- It is required to complete the task
- It improves clarity without changing behavior

### Safe Refactoring Includes:

- Extracting small functions
- Renaming variables for clarity
- Removing dead code (only if clearly unused)

### Forbidden Refactoring:

- Large-scale restructuring
- Introducing new design patterns
- Rewriting working code without explicit instruction

### Behavior Preservation

- Existing behavior MUST remain unchanged
- If behavior changes → document explicitly

---

## 🧪 Testing Rules

- Add tests for any new feature
- Do NOT remove existing tests unless they are broken
- If tests fail:
  - Fix implementation first
  - Only modify tests if they are incorrect

---

## 🔌 Backend (Flask)

- Use blueprints for structure
- Keep routes thin
- Business logic belongs in services
- Validate all inputs
- Handle errors explicitly

DO NOT:

- Put logic inside route handlers
- Introduce global mutable state

---

## 🎨 Frontend (Next.js)

- Functional components only
- Use hooks (no class components)
- Keep components small and reusable

DO NOT:

- Introduce unnecessary state
- Overcomplicate component structure

---

## 🔗 API Contracts

- NEVER change response formats without explicit instruction
- Maintain backward compatibility
- Document any API changes

---

## 🤖 AI-Specific Guardrails

### Avoid Overengineering

- Do NOT introduce patterns like:
  - dependency injection frameworks
  - complex abstractions
  - premature generalization

### Avoid Hallucinations

- Do NOT invent:
  - APIs
  - functions
  - config options

If unsure → ASK

---

### Deterministic Output

- Prefer predictable solutions over clever ones
- Avoid randomness or hidden side effects

---

### Explicitness

- Use clear naming
- Avoid magic values
- Avoid implicit behavior

---

## 🧭 Task Execution Strategy

When given a task:

1. Understand the exact requirement
2. Identify minimal required changes
3. Check impacted files
4. Implement changes
5. Verify no unintended side effects

---

## 🛑 Stop Conditions

STOP and ask for clarification if:

- Requirements are ambiguous
- Multiple architectural approaches are possible
- Task would require large refactoring
- Existing code conflicts with instructions

---

## ✅ Definition of Done

A task is complete when:

- Feature works as intended
- No unrelated files were modified
- Tests pass
- Code follows existing patterns
- No unnecessary complexity introduced

---

## 💬 Communication Rules

- Be concise
- Explain only when necessary
- Highlight assumptions clearly
- Prefer asking over guessing

---

## 🔒 Safety Rules

- Do not expose secrets
- Do not modify environment configs unless required
- Do not introduce security risks

---

## 🧩 Guiding Principle

> Act like a careful mid-level engineer working in a production codebase — not an innovator, not an architect, not a refactoring enthusiast.
