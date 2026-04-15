---
name: test-coverage-check
description: >
  Scans a handler or module and lists the untested paths:
  functions with no test, branches that tests don't reach,
  and edge cases worth adding. Read-only — produces a checklist,
  does not write tests.
argument-hint: "<module or handler path, e.g. app/handlers/notes.py>"
agent: sub
---

You are auditing test coverage for a Cazuela backend module.
Your job is to find gaps — untested functions, unreached branches,
and missing edge cases — and report them as a prioritised checklist.

DO NOT write any files or tests. Read only, then report.

## Step 1 — Read the target module

Read the file specified in the argument.
If no argument is given, read all files changed in the last commit
(`git diff HEAD~1 HEAD --name-only`) and check each Python file.

## Step 2 — Read the existing tests

Find the test file(s) that cover this module:
- `backend/tests/test_handlers.py` for handlers
- `backend/tests/test_router.py` for router patterns
- `backend/tests/test_mcp.py` for MCP module
- `backend/tests/test_integration.py` for end-to-end flows

Read them to understand what is already tested.

## Step 3 — Identify gaps

For each function or method in the target module, check:

1. **No test at all** — function is never called in any test
2. **Happy path only** — only the success case is tested,
   not the empty/missing/error case
3. **Missing edge cases** — specific inputs that would behave
   differently and are not covered:
   - Empty string or None inputs
   - No matching rows in DB
   - Multiple matching rows (for fuzzy match functions)
   - Boundary values (zero amounts, very long strings)

## Step 4 — Produce the report

Format as a prioritised checklist:

### Untested functions
List any functions with zero test coverage.

### Untested branches
For each function that has partial coverage, describe
the specific branch or case that is not tested.
Quote the relevant code line so it's easy to find.

### Recommended additions (prioritised)
A numbered list of tests worth adding, most impactful first.
For each: one sentence describing what to test and why it matters.

## Rules

- Do not suggest tests for things already covered
- Do not suggest style improvements or refactoring
- Keep the report under 400 words
- If coverage looks complete, say so explicitly —
  "Nothing significant missing" is a valid answer
