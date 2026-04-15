---
name: handler-scaffold
description: >
  Given a feature name and a description of what it does,
  generates the complete set of files needed to add a new
  WhatsApp feature to Cazuela: handler module, router patterns,
  and tests. Reads existing handlers first to match conventions
  exactly. Does not write files — outputs the code for the
  developer to review before applying.
argument-hint: "<feature-name> — <what it does and what commands it needs>"
agent: sub
---

You are scaffolding a new feature for Cazuela, a WhatsApp personal
assistant written in Python/FastAPI. Your job is to generate
production-ready code that the developer will review and then apply.

DO NOT write any files. Output the code as markdown code blocks,
one per file.

## Step 1 — Read the codebase conventions

Before generating anything, read these files to understand
the exact patterns to follow:

- `backend/app/handlers/todos.py` — simplest handler, use as primary model
- `backend/app/handlers/shopping.py` — shows fuzzy match pattern
- `backend/app/router.py` — shows how patterns and handlers are wired
- `backend/tests/test_router.py` — shows router test structure
- `backend/tests/test_handlers.py` — shows handler unit test structure

## Step 2 — Understand the argument

The argument tells you the feature name and what it does.
Example: `notes — store and list free-form notes`

If no argument is given, ask the user what feature they want
to scaffold before proceeding.

## Step 3 — Generate the files

Generate exactly these four outputs:

### Output 1: `backend/app/handlers/<feature>.py`

Follow the todos.py pattern exactly:
- Import `client` from `app.db` and `mcp` from `app.mcp`
- One function per operation (add, list, and any domain-specific action)
- Each write operation wraps DB insert in try/except with mcp.rollback on failure
- Return strings in Spanish with WhatsApp formatting
  (*bold*, _italic_, • bullet points)
- Empty list responses say "No tienes X." or similar
- No docstrings, no type annotations on variables, no comments

### Output 2: Router patterns and handler calls to add to `backend/app/router.py`

- One `re.compile` pattern per command, using `re.IGNORECASE`
- Pattern names follow the convention: `FEATURE_ACTION_PATTERN`
- Match Spanish natural language — no colons required
- Import line to add at the top
- The `if` blocks to add inside `route()`, in the right position
  (before the confirm/cancel block, after existing feature blocks)
- Update the help text entry in `HELP_TEXT` for this feature

### Output 3: `backend/tests/test_handlers.py` additions

Follow the pattern in the existing `test_handlers.py`:
- Mock both `app.handlers.<feature>.client` and
  `app.handlers.<feature>.mcp`
- One test per operation
- Test the empty-list case for list operations
- Test the fuzzy match case if the feature has one
- No docstrings

### Output 4: `backend/tests/test_router.py` additions

Follow the pattern in the existing `test_router.py`:
- Parametrized tests for each pattern with 2-3 example messages
- Use `patch("app.router.<handler_function>", return_value="ok")`
- Assert the right argument is extracted and passed to the handler

## Step 4 — Output a brief integration checklist

After the code, list the manual steps the developer needs to do
that the scaffold cannot do automatically:

- Which Supabase table needs to be created (with column names)
- Whether any existing file needs to be edited (router.py imports,
  HELP_TEXT) and exactly where

## Rules

- Match existing code style exactly — no extra abstractions,
  no error handling beyond what the existing handlers do,
  no features beyond what was asked
- Spanish strings only in user-facing output
- If the feature is ambiguous, make a reasonable assumption
  and state it at the top of the output
- Keep the output focused — one feature, one scaffold
