# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
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
