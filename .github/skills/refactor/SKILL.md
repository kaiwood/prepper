---
name: refactor
description: "Guide a small LLM through code refactoring tasks with clear scope, safe steps, and minimal overhead."
argument-hint: "Describe the code area, refactoring goal, constraints, and behavior that must remain unchanged."
user-invocable: true
model: raptor-mini
---

# Refactor

Use this skill when you need to improve code structure or readability without changing behavior.

## When To Use

- Clean up existing code in backend, frontend, or prepper-cli
- Rename symbols, simplify logic, or remove duplication
- Preserve tests and public behavior

## Quick Checklist

1. Clarify scope

- Identify the files, functions, or components involved
- Confirm what must stay the same

2. Refactor in small steps

- Change one thing at a time
- Prefer existing repository patterns
- Keep the change local unless callers must also update

3. Validate

- Run targeted tests for changed code
- Confirm no behavior changes
- Review the result for readability and consistency

## Rules

- Do not add new features
- Preserve existing contracts and public interfaces
- Keep the refactor small and reversible
- Update tests only if the refactor changes internal structure, not behavior

## Done When

- The code is simpler or easier to understand
- Existing behavior is preserved
- Tests for the affected area still pass
