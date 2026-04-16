---
name: integration-test-gen
description: >
  Given a handler name, generates end-to-end integration tests
  that hit the /webhook endpoint via FastAPI's TestClient,
  mocking only the DB layer. Use when adding integration tests
  for a new feature.
argument-hint: "<handler-name> — e.g. notes"
agent: sub
---

You are generating integration tests for Cazuela, a WhatsApp personal
assistant written in Python/FastAPI. Your job is to generate tests
that the developer will review before applying.

DO NOT write any files. Output the tests as a single markdown
code block.

## Step 1 — Read the existing pattern

Read `backend/tests/test_integration.py` to understand the exact
structure in use: how `TestClient` is set up, how `FAKE_USER` is
defined, how patches are applied, and what each test asserts.

## Step 2 — Read the handler

Read `backend/app/handlers/<feature>.py`.
Note every function and exactly what DB calls each one makes —
the table name, the chain of method calls (`.select()`, `.eq()`,
`.order()`, `.ilike()`, `.insert()`, `.update()`), and what
the handler returns as a Spanish string.

## Step 3 — Read the router

Read `backend/app/router.py`.
Find the pattern(s) that trigger this handler and note
an example message string for each operation.

## Step 4 — Generate the tests

Generate a single Python code block containing one test function
per handler operation. Follow these rules exactly:

### Test structure

- Decorate with `@patch("app.db.users.client")` (always first,
  always needed for user lookup) and
  `@patch("app.handlers.<feature>.client")` (second, for DB ops)
- Parameter order: `(mock_handler_client, mock_users_client)`
  — this is reversed from decorator order (innermost decorator
  is first param)
- Always set the users mock:
  `mock_users_client.table.return_value.select.return_value`
  `.eq.return_value.execute.return_value.data = [FAKE_USER]`
- POST to `/webhook` with
  `data={"Body": "...", "From": "whatsapp:+56912345678"}`
- Assert `response.status_code == 200`
- Assert key Spanish strings from the handler's return value
  are in `response.text` — match exactly, including symbols
  like `✓`, `•`, `*bold*`

### Mock chains to use

Match the DB call chain precisely to the handler code:

- **add operations** (insert):
  `mock_handler_client.table.return_value.insert`
  `.return_value.execute.return_value = None`

- **list operations** (select + eq + optional order):
  Set `.data` on the final `.execute.return_value` of the
  full chain the handler uses. If the handler calls `.order()`,
  include it in the chain.

- **search operations** (select + eq + ilike):
  `mock_handler_client.table.return_value.select`
  `.return_value.eq.return_value.ilike.return_value`
  `.execute.return_value.data = [...]`

- **fuzzy-match update operations** (select first, then update):
  Set the select chain to return rows with at least `id` and
  the item field, then set
  `mock_handler_client.table.return_value.update`
  `.return_value.eq.return_value.execute.return_value = None`

### Coverage required

- One test per operation (add, list, complete/check, search, etc.)
- For list operations: one test with items, one empty-list test
- For search operations: one found test, one not-found test
- For fuzzy-match operations: one found test is enough

### Style rules

- No docstrings, no comments, no type annotations
- Function names: `test_<feature>_<operation>` and
  `test_<feature>_<operation>_empty` for empty-list cases
- Use `FAKE_USER` and `client` (TestClient) — they are already
  defined in the file, do not redefine them
- Spanish strings in assertions must match exactly what the handler
  returns — copy them from the handler source

## Step 5 — Output

Output the result as a single fenced Python code block.
Do not write files. The developer will review and append
the block to `backend/tests/test_integration.py`.
