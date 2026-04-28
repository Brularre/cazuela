# Cazuela — Project Guide

WhatsApp life assistant (Python/FastAPI) + Next.js dashboard.
Users send Spanish messages; a Claude agent routes to the right feature.
Multi-user, identified by phone number.

## Tech Stack

- **Backend:** Python + FastAPI, deployed on Railway
- **AI:** Claude Haiku (manual regex mode is the default; AI mode
  requires user's own Anthropic API key)
- **WhatsApp:** Meta WhatsApp Cloud API (graph.facebook.com v19.0)
- **Database:** Supabase (managed Postgres)
- **Frontend:** Next.js (dashboard), deployed on Railway
- **Schema:** see `backend/SCHEMA.md` for live table definitions

## Skills

| Skill | What it does |
|-------|-------------|
| `handler-scaffold` | Generates handler + router patterns + tests |
| `integration-test-gen` | Generates end-to-end integration tests |
| `db-migration-gen` | Generates SQL migration + Pydantic model |
| `intent-pattern-gen` | Generates regex + AI prompt fragment |
| `expense-aggregator-gen` | Generates aggregation function + tests |
| `test-coverage-check` | Lists untested paths — read only |
| `review-feature` | Full code review before merging |
| `agent-log-entry` | Appends decision entry to `agent_log.txt` |
| `schema-sync` | Updates `backend/SCHEMA.md` after a migration |
| `update-comparison-report` | Re-runs MCP replay experiment and updates `COMPARISON_REPORT.md` |

Skills output code blocks for review — nothing is written until
manually applied. Run `/review-feature` before every push.

## Development Principles

- UI and messages: Spanish
- Never log sensitive data; validate inputs at system boundaries only
- Log significant architectural decisions in `agent_log.txt`
- Tests: `cd backend && .venv/bin/pytest`

## Code Style

- **No inline comments** — do not add comments before or inside
  functions to narrate what the code does. The code should speak
  for itself.
- **Module docstrings yes** — every handler module (`backend/app/handlers/*.py`)
  has a module-level docstring listing its public API and any
  non-obvious constraints. Keep it up to date when adding functions.
- **Function docstrings only when needed** — add a docstring to a
  function only if the signature + module docstring don't make the
  behaviour obvious (e.g. a non-trivial algorithm, a gotcha with the
  DB layer, a surprising edge case). Skip docstrings for
  straightforward CRUD functions.

## Feature Roadmap

| Phase | What | Status |
|-------|------|--------|
| 0 | Infrastructure | done |
| 1 | Expenses + WhatsApp parsing | done |
| 2 | Todos + waiting_on | done |
| 3 | Monthly budget + monthly estimate | done |
| 4 | Shopping list | live |
| 5 | Despensa + "necesito comprar" MCP flow | despensa live; batch add live |
| 5b | Meal planning | live |
| 6 | Dashboard (Next.js) | live; expenses, todos, pantry, waiting_on, recipes, meal plan |
| 7 | Onboarding + multi-user polish | planned |

## Feature Modules

**DINERO** — expenses (live), monthly budget + monthly estimate (live)
Expense categories: comida, transporte, salud, hogar,
entretenimiento, ropa, tecnología, educación, viajes, otros
Budget is stored with `period='mes'`; the summary shows a projected
monthly estimate (spend-to-date ÷ days elapsed × days in month).

**TIEMPO** — todos (live); reminders and calendar decided against

**COMIDA** — despensa/pantry (live); "necesito comprar" → MCP →
confirm to despensa or lista (live); shopping list fully live (manual
add + check off, shown on dashboard alongside pantry-derived items);
recipes (WhatsApp + dashboard, AI ingredient suggestions via Haiku);
meal planning (weekly grid, custom slots, shopping list generation
cross-referenced against pantry)

**DASHBOARD** — expenses + budget bar + monthly estimate, todos,
waiting_on, pantry management, combined shopping list (pantry +
manual), recipes editor, weekly meal planner;
auth via WhatsApp OTP + session cookie

## File Map (quick reference)

| What you need | File |
|---------------|------|
| Entry point (WhatsApp message) | `backend/main.py` → `backend/app/router.py` → `route()` |
| Add/edit a regex pattern | `backend/app/patterns.py` |
| Edit help/welcome text | `backend/app/copy.py` |
| Add an AI dispatch case | `backend/app/dispatch.py` → `_dispatch()` |
| Feature handler (CRUD) | `backend/app/handlers/<feature>.py` |
| All handler public APIs (index) | `backend/app/handlers/__init__.py` |
| MCP confirm/cancel logic | `backend/app/dispatch.py` → `_handle_confirm()` / `_handle_cancel()` |
| Dashboard REST API | `backend/app/routes/dashboard.py` |
| Auth routes (OTP login) | `backend/app/routes/auth.py` |
| Export/import routes | `backend/app/routes/export_import.py` |
| MCP staging protocol | `backend/app/mcp/` (`client.py`, `agent.py`, `context.py`) |
| DB client | `backend/app/db/__init__.py` |
| Schema reference | `backend/SCHEMA.md` |
| MCP context schema | `backend/mcp_context_schema.md` |

## Code Style

- **No inline comments** — do not add comments before or inside
  functions to narrate what the code does. The code should speak
  for itself.
- **Module docstrings yes** — every handler module (`backend/app/handlers/*.py`)
  has a module-level docstring listing its public API and any
  non-obvious constraints. Keep it up to date when adding functions.
- **Function docstrings only when needed** — add a docstring to a
  function only if the signature + module docstring don't make the
  behaviour obvious (e.g. a non-trivial algorithm, a gotcha with the
  DB layer, a surprising edge case). Skip docstrings for
  straightforward CRUD functions.
