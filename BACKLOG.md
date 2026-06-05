# Backlog

Deferred issues from code reviews. Not blocking current phase.

## Security

- **N6** OTP 60s cooldown check is not atomic — two concurrent
  requests can both pass SELECT and both INSERT. Low risk (duplicate
  SMS at worst).

## Correctness

- **#25** Long messages are not capped before DB insert.
- **#26** Frontend `getServerSideProps` swallows non-401 errors
  silently.
- **#27** Optimistic UI doesn't roll back on failure (e.g. module
  toggle stays flipped even if the PATCH fails).

## Performance

- **#21** `prune_expired` runs on every `send_context` — full-table
  scan in the hot path.
- **N11** `update_context` does two round trips (read + write);
  could be one query with `.gt("expires_at", now)`.
- **N12** `is_enabled` in `handlers/modules.py` fires a DB query per
  intent — no caching. Fine at current scale; revisit if latency
  becomes an issue.

## Dead Code / Hygiene

- **#18** `pydantic.ConfigDict` import should be `SettingsConfigDict`.
- **N8** `_make_db` helper in `test_auth.py` is unused.
- `check_item` in `shopping.py` is dead code — router maps
  `compré X` to pantry restock, never shopping list.
- **N13** `_MODULE_DISABLED` string is defined in both `router.py`
  and `dispatch.py`. Extract to a shared constant.

## Design Decisions (documented, not bugs)

- **N14** Per-user `anthropic_key` column exists in DB and is
  redacted from logs, but the new pluggable LLM adapter reads
  `CLASSIFIER_API_KEY` env var only — per-user keys are not
  currently plumbed through. Decision: global key only for now;
  revisit if per-user billing is needed.

## Fixed (removed from active list on 2026-06-05)

- **N5** OTP brute-force limit → FIXED (otp_attempts_migration + enforcement in auth.py)
- **#22** JWT KeyError → 500 → FIXED (middleware/auth.py)
- **N4** Expense/reminder lost after mcp.confirm() → FIXED (both single and batch paths)
- **#14** add_pantry_item didn't reset current_quantity → FIXED
- **#13** Dashboard POST /pantry always inserted → FIXED
- **#20** get_or_create_user race → FIXED (catch unique violation + re-select)
- **#7** CSRF on dashboard mutations → MITIGATED (SameSite=Strict + no CORS)
- **#8** /export token in query string → FIXED (Authorization header)
- **#12** Pantry accent duplicates → FIXED (eq on normalized; existing data unaffected)
- **IDOR** handle_snooze_reply had no user_id ownership filter → FIXED
- **BOUNDS** snooze minutes were unbounded → FIXED (1–1440)
- **RECUR** _advance_recur crashed cron on unknown recur value → FIXED
- **ICAL** SUMMARY not RFC-escaped → FIXED
- **TZ** Anthropic provider had no timeout (600s default) → FIXED (10s)
