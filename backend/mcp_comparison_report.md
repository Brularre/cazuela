# MCP Integration: Design Comparison Report

**Project:** Cazuela — WhatsApp personal assistant
**Date:** 2026-04-15

---

## What MCP Solves Here

When a user sends an ambiguous message like `"pagué 5000"`,
the system cannot save the expense without knowing the category.
A multi-step flow is needed:

1. Parse the message and store context
2. Ask the agent to propose a category
3. Ask the user to confirm or cancel
4. Save or discard based on the reply

MCP (`app/mcp/`) implements this flow with a structured
in-memory context store. Each context has a UUID, TTL (1 hour),
status transitions (`pending → staged → confirmed / rolled_back`),
and a redaction layer that strips sensitive keys before
passing data to any agent.

---

## Alternatives Considered

### Option A — Stateless: ask Claude on every message

Every incoming message is sent directly to Claude Haiku
with the last N messages as context. Claude interprets
the intent and responds in one step.

**Trade-offs:**
- Requires an Anthropic API key for every user
- Costs money per message, even for trivial commands
- No audit trail of what the agent proposed vs what was confirmed
- Non-reproducible: same input can yield different outputs

### Option B — DB-backed context (Supabase table)

Store pending contexts as rows in a `mcp_contexts` table.
Look them up by UUID on the confirmation reply.

**Trade-offs:**
- Survives server restarts and multi-instance deploys
- Adds a DB round-trip on every ambiguous message
- Requires a migration and schema management
- More appropriate for production at scale

### Option C — Plain in-memory dict (no protocol)

Store pending state in a module-level dict,
with no TTL, no status transitions, no redaction.

**Trade-offs:**
- Simpler to implement
- No protection against unbounded memory growth
- No audit trail — impossible to tell if a context
  was confirmed, rolled back, or abandoned
- Sensitive data (user history, phone) could leak
  into agent inputs without a redaction layer

### Option D — MCP (chosen)

Structured in-memory store with:
- UUID context IDs + 8-character prefix for user-facing codes
- TTL enforced on read; `prune_expired()` called on write
- Status machine: `pending → staged → confirmed / rolled_back`
- `redact()` strips keys in `SENSITIVE_KEYS` before any agent sees them
- Deterministic stub agent (no API key required)
- `replay.py` script for reproducible testing against snapshots

---

## Comparison Summary

| Criterion              | Stateless (A) | DB-backed (B) | Plain dict (C) | MCP (D)   |
|------------------------|---------------|---------------|----------------|-----------|
| No API key required    | No            | Yes           | Yes            | Yes       |
| Survives restart       | Yes           | Yes           | No             | No        |
| Reproducible tests     | No            | Partial       | No             | Yes       |
| Sensitive data safety  | Depends       | Depends       | No             | Yes       |
| Audit trail            | No            | Yes           | No             | Yes       |
| Implementation cost    | Low           | Medium        | Very low       | Medium    |

---

## Decision and Rationale

MCP was chosen over the alternatives for three reasons:

**Cost.** A deterministic stub agent satisfies the multi-step
flow without requiring any Anthropic API calls.
Option A would charge users for every ambiguous message.

**Safety.** The `redact()` layer ensures that fields like
`phone` and `anthropic_key` are never passed to agent logic,
regardless of what ends up in the payload.
A plain dict (Option C) provides no such guarantee.

**Reproducibility.** The stub agent is deterministic —
same input always yields same output.
Combined with `replay.py` and snapshot fixtures,
agent behavior can be regression-tested in CI without
mocking a language model.

The main limitation of this implementation over Option B
is that contexts are lost on server restart.
This is acceptable for a personal assistant at current scale
(single-user sessions, short TTL) and is documented
as a known constraint in the codebase.
