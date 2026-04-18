---
name: schema-sync
description: >
  Updates backend/SCHEMA.md after a migration is run.
  Reads all .sql migration files and handler code to
  reconcile the schema doc with the current state.
invocation: user
writes_files: [backend/SCHEMA.md]
---

# schema-sync

Keep `backend/SCHEMA.md` up to date after a migration.

## Steps

1. Read `backend/SCHEMA.md` to understand the current state
2. Read all `backend/migrations/*.sql` migration files
3. Read `backend/app/handlers/*.py` to infer tables used
   but not in a migration file
4. For each table:
   - If a migration file defines it: mark as ✓ confirmed
   - If only used in handlers: mark as ~ inferred
   - Update columns to match the migration or handler
5. Update the "Migrations run" list at the bottom of SCHEMA.md
   with any new migrations, in the order they were applied
6. Update the "Tables without confirmed migrations" note

## Rules

- Only write to `backend/SCHEMA.md` — no other files
- Preserve the existing format (markdown table, legend)
- If a column appears in a migration but not the handler
  (or vice versa), keep both and note the discrepancy
- Do not remove tables from SCHEMA.md even if unused —
  mark them as deprecated instead
- Keep line length under ~80 characters
