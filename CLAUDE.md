# Cazuela — Project Guide

WhatsApp life assistant (Python/FastAPI) + Next.js dashboard.
Users send Spanish messages; a Claude agent routes to the right feature.
Multi-user, identified by phone number.

## Tech Stack

- **Backend:** Python + FastAPI, deployed on Railway
- **AI:** Claude Haiku (manual regex mode is the default; AI mode
  requires user's own Anthropic API key)
- **WhatsApp:** Twilio
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

Skills output code blocks for review — nothing is written until
manually applied. Run `/review-feature` before every push.

## Development Principles

- UI and messages: Spanish
- Never log sensitive data; validate inputs at system boundaries only
- Log significant architectural decisions in `agent_log.txt`
- Tests: `cd backend && .venv/bin/pytest`

## Feature Roadmap

| Phase | What | Status |
|-------|------|--------|
| 0 | Infrastructure | done |
| 1 | Expenses + WhatsApp parsing | done |
| 2 | Todos + waiting_on | done |
| 3 | Weekly budget + monthly estimate | done |
| 4 | Shopping list | live |
| 5 | Despensa + "necesito comprar" MCP flow | despensa live; batch add live |
| 5b | Meal planning + Google Sheets | planned |
| 6 | Dashboard (Next.js) | live; expenses, todos, pantry, waiting_on |
| 7 | Onboarding + multi-user polish | planned |

## Feature Modules

**DINERO** — expenses (live), weekly budget + monthly estimate (live)
Expense categories: comida, transporte, salud, hogar,
entretenimiento, ropa, tecnología, educación, viajes, otros

**TIEMPO** — todos (live); reminders and calendar decided against

**COMIDA** — despensa/pantry (live); "necesito comprar" → MCP →
confirm to despensa or lista (live); shopping list fully live (manual
add + check off, shown on dashboard alongside pantry-derived items);
meal planning + Google Sheets (planned)

**DASHBOARD** — expenses + budget bar + monthly estimate, todos,
waiting_on, pantry management, combined shopping list (pantry +
manual); auth via WhatsApp OTP + session cookie
