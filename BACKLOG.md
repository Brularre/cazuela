# Backlog

Deferred issues from code reviews. Not blocking current phase.

## Performance

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
