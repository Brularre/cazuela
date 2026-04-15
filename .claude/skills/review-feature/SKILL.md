---
name: review-feature
description: >
  Review new or modified files before merging. Produces a structured
  report covering correctness, test coverage, security, code style
  consistency, things that will break, and optional improvements.
  The developer is a junior learning to code — keep the report
  educational and specific. Quote relevant code when calling
  something out.
argument-hint: "[path or list of files to review]"
agent: sub
---

You are doing a code review. DO NOT modify any files — read only,
then produce a report.

Review the files specified in the argument (or infer them from
recent git changes if no argument is given). For each file,
also read the surrounding existing code to understand the project's
conventions.

Produce a structured report with these sections:

## 1. Bugs
Logic errors or edge cases that would cause real problems in
production. Be specific — quote the code and explain what breaks.

## 2. Things That Will Break
Patterns that will fail on real input (e.g., regex that doesn't
match what users will actually type), missing error handling at
system boundaries, import issues.

## 3. Test Coverage
Are the tests meaningful? List important scenarios that are missing.
Do not suggest tests for things already covered.

## 4. Security
Any sensitive data leaks, missing input validation at system
boundaries, or unsafe patterns.

## 5. Code Style Consistency
Violations of the project's style rules:
- No docstrings
- No type annotations on variables
- No comments unless logic is non-obvious
- No Tailwind (frontend)
- No features added beyond what was asked

## 6. Nice to Have (optional)
Small improvements worth flagging but not blocking the merge.
Keep this section short.

---

Rules:
- Be specific and educational — the developer is learning
- Quote the relevant code for every finding
- Keep the total report under 500 words
- If a section has nothing to report, write "Nothing to flag."
- End with a one-line merge verdict: LGTM / Fix before merging /
  Blocking issue found
