# Cazuela — Claude Code Project Guide

## About This Project

Cazuela is a daily life companion accessible via WhatsApp. You send natural language messages in Spanish; a Claude agent interprets them and routes to the appropriate feature. A Next.js dashboard provides a visual overview and settings.

**Model:** Single hosted instance (multi-user, identified by WhatsApp number). Users bring their own Anthropic API key for AI mode; without one, manual (regex) mode is used. Open source — self-hosting also documented.

## Immediate Milestone (Week 1)

The first shippable slice covers Phase 0 + Phase 1 expenses. Everything else continues after.

**Scope:**
- Twilio WhatsApp webhook (manual mode: `"gasto 50 comida"` → saves expense)
- Expense CRUD via REST API
- Fixed category list with keyword mapping
- Weekly summary report on demand (`"resumen de la semana"`)
- CSV/JSON export endpoint
- Swagger UI (free from FastAPI)
- Unit tests: aggregation logic, category mapping
- Integration tests: expense CRUD + summary end-to-end
- GitHub Actions CI

**Skill to build:** `expense-aggregator-gen` — given a transaction schema + time boundary, generates the aggregation function, edge-case unit tests, and sample data fixture.

**Artifacts:**
- `agent_log.txt` — maintained as we build, documenting Claude Code suggestions accepted/rejected and why

**Day plan:**
- Day 1–2: Phase 0 (scaffold, Twilio, Supabase, CI green)
- Day 3–4: Expense CRUD + WhatsApp manual parsing
- Day 5: Aggregation + summary + export
- Day 6: Skill + tests
- Day 7: Polish + demo

## About the User

Bruno is a junior developer using this project as a learning opportunity. He wants to:
- Learn software engineering concepts as we build together
- Learn how to use Claude Code effectively (skills, agents, subagents)
- Build incrementally — one feature at a time, no premature complexity

**Approach:** Explain decisions as you make them. When choosing between two patterns, say why. Flag when something is a learning moment worth pausing on.

## How to Use Claude Code on This Project

### Subagents
- Always spawn subagents with `isolation: "worktree"` so their changes are isolated until reviewed
- Use subagents to implement; use the main thread to review, explain, and decide
- After each subagent finishes, walk Bruno through what it did before accepting
- Use **Explore** subagent for codebase-wide questions instead of grepping manually
- Use **Plan** subagent before starting any non-trivial implementation

### Skills (slash commands)
Skills encode "how we do things in Cazuela" — invoke them instead of repeating instructions.

| Priority | Skill | What it does |
|----------|-------|-------------|
| 1 | `agent-log-entry` | Reads git diff + context, appends a formatted entry to `agent_log.txt` (what was suggested, accepted/rejected, why) |
| 2 | `handler-scaffold` | Given a feature name, generates model + DB queries + route + WhatsApp regex + tests |
| 3 | `expense-aggregator-gen` | Given schema + time boundary, generates aggregation function + edge-case tests + fixture |
| 4 | `intent-pattern-gen` | Given a feature + Spanish example messages, generates manual mode regex + AI mode prompt fragment |
| 5 | `db-migration-gen` | Given table + columns, generates SQL migration + Pydantic model + query stubs |

- Use the **`/claude-api` skill** when touching the Anthropic SDK / agent code
- Use the **`/simplify` skill** after implementing a feature to check for unnecessary complexity
- Keep tasks granular — mark them done as you go so Bruno can follow along

## Development Principles

- Build incrementally. Don't scaffold features that aren't being built yet.
- Prefer simple and readable over clever.
- No premature abstractions. If a pattern appears twice, note it. Three times, extract it.
- Always explain the "why" behind architectural decisions.
- Security matters: never log sensitive data, validate all inputs at boundaries.
- Messages and UI language: Spanish.
- **Frontend styling: plain CSS classes — no Tailwind.** Use CSS modules or global stylesheets.
- **Line length in all written documents** (CLAUDE.md, agent_log.txt, skill files, etc.):
  break long lines at natural clause or sentence boundaries.
  Prefer multiple short lines over one long line. Aim for ~80 characters max.

## Tech Stack

- **Backend:** Python + FastAPI
- **AI Agent:** Claude Haiku (via Anthropic SDK) — cheapest capable model for intent parsing
- **WhatsApp:** Twilio (sandbox for dev, production number for prod)
- **Database:** Supabase (managed Postgres)
- **Google integrations:** Google Calendar API + Google Sheets API (OAuth2 per user)
- **Dev tunneling:** Railway (early deployment replaces ngrok —
  work machine security blocks all tunneling tools)
- **Frontend:** Next.js (dashboard)
- **Deployment:** TBD (Railway or Render candidates)

## Agent Design

### AI Mode vs Manual Mode
- **AI mode** (requires user's Anthropic API key): Claude Haiku parses free-text intent
- **Manual mode** (default, free): regex/keyword rules parse structured commands
- Mode toggle available on dashboard and via WhatsApp command
- Only call Claude when message is ambiguous (doesn't match manual patterns) — reduces cost

### Stateful Conversation
- Last ~10 messages per user stored in DB and passed as context to Claude
- Long-term preferences (name, currency, habits) stored in user profile and injected as system context
- Feels like a personal assistant with memory

### Intent Types
The agent must distinguish between:
- **Todo** — "llamar al banco" (no specific time, just needs doing)
- **Reminder** — "recordarme tomar la pastilla a las 9" (alert at exact time)
- **Calendar event** — "dentista el martes a las 3pm" (has duration, maybe location)

## Feature Modules

### TIEMPO (Time Management)
- Calendar events → Google Calendar integration (read + write)
- Appointments → same as calendar events, with location support
- Reminders → proactive WhatsApp messages at scheduled times
- Todos → task list without a specific time

### DINERO (Money)
- Expense tracking → amount, category (fixed list, AI-mapped), note, date
- Receipt scanning → send photo → Claude vision extracts expense automatically
- Budget → spending limits per category, alerts when approaching
- Savings goals → "quiero ahorrar X para Y en Z fecha" → tracks progress passively

**Expense categories (fixed):**
comida, transporte, salud, hogar, entretenimiento, ropa, tecnología, educación, viajes, otros

### COMIDA (Food)
- Meal planning → weekly plan (lunch + dinner per day, optionally breakfast)
- Today's view → "hoy: almuerzo - lasaña, cena - pollo al horno"
- Despensa → tracks home supplies (food pantry, cleaning products, etc.) with quantity thresholds
  - Backed by a Google Sheet the user controls (item, quantity, unit, threshold, category)
  - Cazuela reads and updates the sheet via Google Sheets API
  - When quantity < threshold → item automatically suggested to shopping list
- Shopping list → auto-generated from: despensa gaps + missing meal plan ingredients + manual adds
- Recipes (later phase) → stored recipes with ingredients + steps; cooking mode via WhatsApp

### DESEOS (Wants)
- Wishlist → items with optional price estimate and URL

### NOTAS (Quick Capture)
- Free-form notes, ideas, links — no category, no date, just saved
- Searchable from dashboard

### PERFIL (Profile & Settings)
- Name, preferred currency
- Anthropic API key (encrypted at rest)
- AI mode toggle
- Google Calendar authorization
- Google Sheets URL for despensa

### DASHBOARD (Next.js)
- **Glanceable view:** upcoming events, today's meals, pending todos, budget status
- **Drill-down sections:** expense charts by category/period, full calendar, all lists, notes
- **Settings page:** profile, API key, mode toggle, integrations

## Feature Roadmap

| Phase | What | Notes |
|-------|------|-------|
| **0** | Infrastructure | Twilio webhook, user registration, Supabase setup, ngrok |
| **1** | Core agent + Expenses | Claude integration, intent parsing, expense tracking, receipt scanning, quick notes |
| **2** | Todos + Reminders + Google Calendar | Background scheduler for proactive messages |
| **3** | Budget + Savings goals | Money module complete |
| **4** | Shopping list + Wishlist | Simple lists |
| **5** | Despensa + Google Sheets + Meal planning | Food module, full integration |
| **6** | Dashboard (Next.js) | Visual layer on working data |
| **7** | Onboarding + multi-user polish | Makes it shareable |
| **8** | Recipes / cooking mode | Later feature |

## Data Models (Planned)

```
users           → id, phone, name, currency, anthropic_key (encrypted), ai_mode,
                  google_tokens (encrypted), sheets_url, created_at
conversations   → id, user_id, role (user/assistant), content, created_at
expenses        → id, user_id, amount, currency, category, note, date, receipt_url
budgets         → id, user_id, category, limit_amount, period (monthly/weekly)
savings_goals   → id, user_id, name, target_amount, current_amount, deadline
reminders       → id, user_id, message, scheduled_at, recurring, google_event_id
todos           → id, user_id, task, done, due_date
calendar_events → id, user_id, title, start_at, end_at, location, google_event_id
shopping_list   → id, user_id, item, quantity, unit, checked, source (manual/despensa/meal_plan)
wishlist        → id, user_id, item, price_estimate, url, created_at
notes           → id, user_id, content, created_at
meal_plan       → id, user_id, date, meal_type (lunch/dinner/breakfast), recipe_id
recipes         → id, user_id, name, ingredients (jsonb), steps (jsonb)
```

## Project Structure (Target)

```
cazuela/
├── backend/
│   ├── app/
│   │   ├── agent/          # Claude agent: intent parsing, routing, conversation memory
│   │   ├── handlers/       # One module per feature (expenses, reminders, calendar...)
│   │   ├── models/         # Pydantic models
│   │   ├── routes/         # FastAPI routes (webhook, health, dashboard API)
│   │   ├── db/             # Supabase client + queries
│   │   └── integrations/   # Google Calendar, Google Sheets, Twilio
│   ├── scheduler/          # Background job for proactive reminders
│   ├── main.py
│   └── requirements.txt
├── frontend/               # Next.js dashboard
└── CLAUDE.md
```
