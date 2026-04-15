---
name: db-migration-gen
description: >
  Given a table name and its columns, generates the SQL migration
  to run in Supabase, a Pydantic model, and the basic query stubs
  needed to wire the table into a handler. Does not write files —
  outputs code for the developer to review first.
argument-hint: "<table-name> — <col: type, col: type, ...>"
agent: sub
---

You are generating database scaffolding for Cazuela,
a WhatsApp personal assistant backed by Supabase (Postgres).

DO NOT write any files. Output everything as markdown code blocks
for the developer to review.

## Step 1 — Read conventions

Read these files before generating anything:

- `backend/app/db/__init__.py` — Supabase client setup
- `backend/app/db/users.py` — example of how queries are written
- `backend/app/config.py` — settings model

## Step 2 — Understand the argument

The argument gives the table name and columns.
Example: `notes — id: uuid, user_id: uuid, content: text, created_at: timestamptz`

If no argument is given, ask the user for the table name
and columns before proceeding.

## Step 3 — Generate outputs

### Output 1: SQL migration

A single SQL block ready to paste into the Supabase SQL Editor:

- Table name and columns as specified
- `id uuid DEFAULT gen_random_uuid() PRIMARY KEY` unless overridden
- `user_id uuid REFERENCES users(id) ON DELETE CASCADE` for all
  user-scoped tables
- `created_at timestamptz DEFAULT now()` unless overridden
- Enable Row Level Security (RLS) with a policy that restricts
  each user to their own rows, keyed on `user_id`
- Add any obvious indexes (e.g. on `user_id`, on `created_at DESC`)

### Output 2: Pydantic model stub

A minimal Pydantic model that matches the table schema.
Place it in `backend/app/models/<table>.py` (show the path).
Follow the project style — no docstrings, no extra validators.
Use `pydantic.BaseModel`. Field types should match the SQL types.

### Output 3: Query stubs

A `backend/app/db/<table>.py` file with:
- The standard `from app.db import client` import
- One function per common operation needed for this table
  (insert, select by user_id, update if applicable, delete if applicable)
- Each function takes `user_id: str` and the relevant fields
- Returns `dict` or `list[dict]` from `result.data`
- No error handling beyond what users.py does (keep it simple)
- No docstrings, no type annotations on variables

## Step 4 — Integration checklist

After the code, list the manual steps:
- Run the SQL in Supabase SQL Editor
- Where to import the query module from in the handler
- Any env vars or config changes needed

## Rules

- Match existing code style exactly
- RLS is non-negotiable — always include it
- Keep the Pydantic model minimal — only fields that handlers
  will actually use
- If the column types are ambiguous, state your assumption
