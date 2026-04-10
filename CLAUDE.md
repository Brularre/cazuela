# Cazuela — Claude Code Project Guide

## About This Project

Cazuela is a daily life companion accessible via WhatsApp.
You send natural language messages in Spanish; a Claude agent interprets
them and routes to the appropriate feature.
A Next.js dashboard provides a visual overview and settings.

**Model:** Single hosted instance (multi-user, identified by WhatsApp
number). Users bring their own Anthropic API key for AI mode;
without one, manual (regex) mode is used.
Open source — self-hosting also documented.

## Immediate Milestone (Week 1)

The first shippable slice covers Phase 0 + Phase 1 expenses.
Everything else continues after.

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

**Skill to build:** `expense-aggregator-gen` — given a transaction schema
+ time boundary, generates the aggregation function, edge-case unit tests,
and sample data fixture.

**Artifacts:**
- `agent_log.txt` — maintained as we build, documenting Claude Code
  suggestions accepted/rejected and why

**Day plan:**
- Day 1–2: Phase 0 (scaffold, Twilio, Supabase, CI green)
- Day 3–4: Expense CRUD + WhatsApp manual parsing
- Day 5: Aggregation + summary + export
- Day 6: Skill + tests
- Day 7: Polish + demo

## Skills

| Priority | Skill | What it does |
|----------|-------|-------------|
| 1 | `agent-log-entry` | Reads git diff + context, appends a formatted entry to `agent_log.txt` |
| 2 | `handler-scaffold` | Given a feature name, generates model + DB queries + route + WhatsApp regex + tests |
| 3 | `expense-aggregator-gen` | Given time boundary, generates aggregation function + edge-case tests + fixture |
| 4 | `intent-pattern-gen` | Given a feature + Spanish example messages, generates manual mode regex + AI mode prompt fragment |
| 5 | `db-migration-gen` | Given table + columns, generates SQL migration + Pydantic model + query stubs |

- Use `/claude-api` when touching the Anthropic SDK or agent code
- Use `/simplify` after implementing a feature to check for
  unnecessary complexity

## Development Principles

- Messages and UI language: Spanish
- Security: never log sensitive data, validate inputs at boundaries
- Log architectural decisions in `agent_log.txt` after each
  significant decision

## Tech Stack

- **Backend:** Python + FastAPI
- **AI Agent:** Claude Haiku (via Anthropic SDK)
- **WhatsApp:** Twilio (sandbox for dev, production number for prod)
- **Database:** Supabase (managed Postgres)
- **Google integrations:** Google Calendar API + Google Sheets API
  (OAuth2 per user)
- **Dev tunneling:** Railway (early deployment replaces ngrok —
  work machine security blocks all tunneling tools)
- **Frontend:** Next.js (dashboard)
- **Deployment:** TBD (Railway or Render candidates)

## Agent Design

### AI Mode vs Manual Mode
- **AI mode** (requires user's Anthropic API key):
  Claude Haiku parses free-text intent
- **Manual mode** (default, free): regex/keyword rules parse structured
  commands
- Mode toggle available on dashboard and via WhatsApp command
- Only call Claude when message is ambiguous — reduces cost

### Stateful Conversation
- Last ~10 messages per user stored in DB and passed as context
- Long-term preferences stored in user profile and injected as system
  context

### Intent Types
- **Todo** — "llamar al banco" (no specific time, just needs doing)
- **Reminder** — "recordarme tomar la pastilla a las 9" (alert at time)
- **Calendar event** — "dentista el martes a las 3pm" (has duration)

## Feature Modules

### TIEMPO (Time Management)
- Calendar events → Google Calendar integration (read + write)
- Reminders → proactive WhatsApp messages at scheduled times
- Todos → task list without a specific time

### DINERO (Money)
- Expense tracking → amount, category (fixed list, AI-mapped), note, date
- Receipt scanning → photo → Claude vision extracts expense automatically
- Voice notes → audio → Whisper transcribes → processed like text
- Budget → spending limits per category, alerts when approaching
- Savings goals → tracks progress passively
- Email notifications → via Resend API

**Expense categories (fixed):**
comida, transporte, salud, hogar, entretenimiento, ropa,
tecnología, educación, viajes, otros

### COMIDA (Food)
- Meal planning → weekly plan (lunch + dinner per day)
- Despensa → tracks home supplies via Google Sheet
  (when quantity < threshold → suggested to shopping list)
- Shopping list → auto-generated from despensa + meal plan + manual adds

### DESEOS (Wants)
- Wishlist → items with optional price estimate and URL

### NOTAS (Quick Capture)
- Free-form notes, searchable from dashboard

### PERFIL (Profile & Settings)
- Name, currency, Anthropic API key (encrypted), AI mode toggle,
  Google Calendar auth, Google Sheets URL

### DASHBOARD (Next.js)
- Glanceable view: upcoming events, today's meals, todos, budget status
- Drill-down: expense charts, calendar, lists, notes
- Settings: profile, API key, mode toggle, integrations

## Feature Roadmap

| Phase | What | Notes |
|-------|------|-------|
| **0** | Infrastructure | Twilio webhook, user registration, Supabase, CI |
| **1** | Core agent + Expenses | Claude integration, expense tracking, receipt scanning, voice notes |
| **2** | Todos + Reminders + Google Calendar | Background scheduler |
| **3** | Budget + Savings goals + Email | Money module complete |
| **4** | Shopping list + Wishlist | Simple lists |
| **5** | Despensa + Google Sheets + Meal planning | Food module |
| **6** | Dashboard (Next.js) | Visual layer |
| **7** | Onboarding + multi-user polish | Makes it shareable |
| **8** | Recipes / cooking mode | Later feature |

## Data Models (Planned)

```
users           → id, phone, name, currency, anthropic_key (encrypted),
                  ai_mode, google_tokens (encrypted), sheets_url, created_at
conversations   → id, user_id, role (user/assistant), content, created_at
expenses        → id, user_id, amount, currency, category, note, date,
                  receipt_url
budgets         → id, user_id, category, limit_amount, period
savings_goals   → id, user_id, name, target_amount, current_amount, deadline
reminders       → id, user_id, message, scheduled_at, recurring,
                  google_event_id
todos           → id, user_id, task, done, due_date
calendar_events → id, user_id, title, start_at, end_at, location,
                  google_event_id
shopping_list   → id, user_id, item, quantity, unit, checked,
                  source (manual/despensa/meal_plan)
wishlist        → id, user_id, item, price_estimate, url, created_at
notes           → id, user_id, content, created_at
meal_plan       → id, user_id, date, meal_type, recipe_id
recipes         → id, user_id, name, ingredients (jsonb), steps (jsonb)
```

## Project Structure (Target)

```
cazuela/
├── backend/
│   ├── app/
│   │   ├── agent/          # Claude agent: intent parsing, routing, memory
│   │   ├── handlers/       # One module per feature
│   │   ├── models/         # Pydantic models
│   │   ├── routes/         # FastAPI routes
│   │   ├── db/             # Supabase client + queries
│   │   └── integrations/   # Google Calendar, Sheets, Twilio
│   ├── scheduler/          # Background job for proactive reminders
│   ├── main.py
│   └── requirements.txt
├── frontend/               # Next.js dashboard
└── CLAUDE.md
```
