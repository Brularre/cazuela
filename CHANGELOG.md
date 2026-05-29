# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added (Track D2)
- **`remind_at` columns** — `todos` and `events` both gain `remind_at timestamptz` and `remind_sent boolean`; partial indexes on `(remind_at) where remind_sent = false` for the 15-min cron query.
- **Natural-language time parser** — `backend/app/handlers/timeparse.py` with `parse_time()` and `parse_iso()`. Supports: `hoy/mañana a las HH[:MM]`, `el WEEKDAY a las HH`, `en N horas/minutos`. Returns None on unrecognised input; never guesses. All times stored as UTC, displayed in America/Santiago. DST-aware via `zoneinfo`.
- **`set_reminder` WhatsApp intent** — `recuérdame: X mañana a las 10` sets a reminder on a matching open todo or event; falls back from todos to events automatically. Gated behind the `recordatorios` module. AI-mode prompt updated to emit `set_reminder` JSON.
- **`send_interactive()`** — `notify.py` gains a free-form interactive button message sender. The daily digest uses it to carry a `Continuar` quick-reply button that resets Meta's 24-hour customer-service window when tapped.
- **Daily keep-alive digest** (`python -m app.jobs.send_digest`, Railway cron `0 13 * * *` UTC = 9 AM Santiago) — each morning, sends every user whose `recordatorios` module is enabled (and who has reminders due today or open todos) a WhatsApp interactive message with a `Continuar` button. Skips empty days. A False send return (closed window) is logged and swallowed; the user resumes the chain by messaging Cazuela next time.
- **Individual reminder cron job** (`python -m app.jobs.send_reminders`, Railway cron `*/15 * * * *`) — every 15 minutes, delivers plain-text `⏰ …` messages for all due, unsent reminders across todos and events. Marks each as sent on success; leaves failures untouched for the next pass (self-healing). Skips users with `recordatorios` disabled.
- **Dashboard reminder controls** — `TodosSection` and `CalendarSection` show a ⏰ button on each row; clicking it opens an inline `datetime-local` editor to set or clear `remind_at`. Saves via `PATCH /dashboard/todos/{id}/reminder` and `PATCH /dashboard/events/{id}/reminder`.

### Notes (D2 delivery model)
Proactive delivery only works while Meta's 24-hour customer-service window is open. The daily digest keeps it open by carrying a `Continuar` quick-reply button; tapping it resets the window for another 24 h. If a user does not tap for 24 h, the window closes and the next digest silently fails to deliver. Recovery is automatic and user-initiated: the moment the user sends any message to Cazuela, the window reopens and both the digest chain and individual reminders resume. No Meta message template is needed.

### Added (Track D1)
- **Module toggles** — `user_modules` table + `modules.py` handler; each feature module (dinero, tiempo, comida, calendario, recordatorios) can be enabled/disabled per user. Router guards every regex and AI-dispatched intent. Dashboard panel to flip toggles.
- **Calendar events** — WhatsApp CRUD (`evento: dentista mañana a las 10`, `mis eventos`, `borrar evento …`) gated behind `calendario` module. `events.py` handler with `parse_event_time` for Spanish time phrases. Events shown on dashboard.
- **iCal feed** — `GET /calendar/{token}.ics` returns a VCALENDAR feed of upcoming events. Token generated lazily per user and surfaced in the dashboard Calendar section.
- **Shared WhatsApp sender** — `backend/app/notify.py` with `send_text()`. OTP send now routes through it; eliminates the duplicate inline Meta call.

### Added (Track C, previously unreleased)
- Pluggable LLM adapter (`backend/app/llm.py`) with Anthropic, Groq, and stub providers
- Two-tier model config: `CLASSIFIER_*` env vars for intent routing, `RESPONDER_*` for conversational replies
- User profile injection (name, currency) prepended to AI prompts for personalization
- `_StubProvider` for deterministic, key-free testing of AI classification paths

### Changed
- AI classification now runs as a fallback **after** the regex chain, reducing unnecessary token usage
- `router.py` imports `classify` from `app.llm` instead of the removed `app.ai_router`

### Deprecated
- `USE_AI_AGENT` and `ANTHROPIC_API_KEY` env vars still work but prefer `CLASSIFIER_*` / `RESPONDER_*`

### Removed
- `backend/app/ai_router.py` — superseded by `backend/app/llm.py`

## [0.1.0] - 2026-05-27

### Added
- Expense tracking with auto-categorization and monthly budget
- Todos and waiting_on lists with priority levels
- Pantry stock management with low-stock alerts
- Recipes editor with AI ingredient suggestions
- Weekly meal planner cross-referenced against pantry
- Manual and pantry-derived shopping list
- WhatsApp OTP authentication
- Next.js dashboard: expenses, todos, pantry, recipes, meal plan, waiting_on
- MCP staging protocol for multi-turn WhatsApp flows
- Manual regex routing mode (default, no API key required)
- AI routing mode (optional, bring your own Anthropic API key)
