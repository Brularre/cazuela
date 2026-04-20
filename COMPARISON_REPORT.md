# MCP Integration Comparison Report
**Project:** Cazuela — WhatsApp personal finance assistant
**Date:** 2026-04-20 (updated)

---

## Scenario

**Task:** Categorize an ambiguous expense ("pagué 5000" — no description).

**Without MCP (Module 1 baseline):** Message matches no category pattern →
saved directly to the database under the fallback category `"otros"`.
No agent loop, no user confirmation.

**With MCP:** Message triggers `send_context` → `request_action` (stub
agent inspects user history and proposes best-fit category) → WhatsApp
reply asks user to confirm → `confirm()` writes to DB.

---

## Quantitative Metrics

### Test pass rate

| | Without MCP | With MCP |
|---|---|---|
| Tests written | 0 (no flow to test) | 23 (test_mcp.py) |
| Passing | N/A | 23 / 23 (100%) |
| Total suite | 154 passing | 197 passing |

### Iterations to green tests

The test suite reached 100% pass rate in 1 run after the MCP module
was implemented. No flaky tests were observed across 3 CI pushes.

### Output variance across 3 repeated runs

Scenario replayed 3× using `scripts/replay_mcp_context.py` with
identical payload (`amount=5000`, `user_history={comida:8, transporte:3, otros:1}`).

| Run | Proposed category | Confidence | Output identical? |
|-----|------------------|------------|------------------|
| 1 | comida | 0.8 | — |
| 2 | comida | 0.8 | ✓ |
| 3 | comida | 0.8 | ✓ |

**Variance: 0.** The stub agent is fully deterministic — same context
always produces the same proposal. This satisfies the assignment's
reproducibility acceptance criterion.

### Without MCP — same 3 runs

All 3 would produce `category="otros"` (hardcoded fallback).
Variance: 0, but accuracy: 0% for users with a clear spending pattern.

### Agent iteration count

| Flow | Iteration count per interaction |
|---|---|
| Without MCP | 0 |
| With MCP | 1 (always — stub proposes in a single pass) |

---

## Qualitative Metrics

### Category accuracy

With a user who has 8 `comida` expenses and 3 `transporte` in the
last 30 days, MCP proposes `comida` for an untagged expense. The
baseline would always say `otros`. The MCP proposal is surfaced to
the user for confirmation — they can override — which means the final
DB entry is always human-approved.

### Developer experience

| Aspect | Without MCP | With MCP |
|---|---|---|
| Code to write | 1 regex + 1 DB insert | 5 functions + 1 DB table + TypedDict schema |
| Test complexity | Simple mock | Stateful FakeClient fixture |
| Auditability | None | Full lifecycle in `mcp_contexts` table |
| Rollback support | None | `rollback()` reverts staged context |
| Race condition safety | Double-insert possible | Atomic UPDATE WHERE status='staged' |

**Developer time estimate:**
- Baseline flow: ~1 hour
- MCP module (context + client + agent + tests): ~6 hours
- Overhead is justified by the audit trail and the two-message
  interaction that WhatsApp requires anyway

### Friction points

- The FakeClient test fixture is ~50 lines of boilerplate that
  duplicates Supabase query-builder behavior. Worth extracting to
  a shared test utility.
- The `prune_expired()` call on every `send_context` is a full
  table scan. Acceptable now; needs an index on `expires_at` at scale.
- The stub agent (`stub-v1`) is deterministic but not intelligent —
  it picks the most frequent category, not the most contextually
  appropriate one. Swapping in a Claude Haiku call requires only
  changing `app/mcp/agent.py`.

---

## Confirm/Rollback Lifecycle Evidence

From `test_round_trip_status_transitions`:

```
pending → staged → confirmed
```

From `test_verify_refine_loop`:

```
pending → staged → rolled_back   (user rejects first proposal)
pending → staged → confirmed     (user accepts refined proposal)
```

From `test_confirm_already_confirmed_raises`:

```
confirmed → confirm() raises ValueError  (atomic guard prevents double-write)
```

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| PII in context payload | `redact()` strips sensitive keys before any logging |
| Expired context replayed | TTL enforced in `get_context()`; expired = ValueError |
| Context persists sensitive data at rest | Supabase RLS scopes rows to authenticated user |
| Stub swapped for real model — cost leak | Model name logged in `agent_model` field; easy to audit |
| `TWILIO_SKIP_VALIDATION=true` in prod | Startup guard raises RuntimeError if `cookie_secure=true` |

---

## Conclusion

The MCP flow adds measurable overhead (1 extra DB round-trip, 1 extra
WhatsApp message per ambiguous expense) but delivers: human approval
gates, full audit trail, rollback support, and reproducible agent
proposals. For the specific domain of personal finance categorization
— where a wrong category silently corrupts monthly summaries — the
confirm gate is worth the extra step.

The deterministic stub satisfies the reproducibility criterion
out of the box. Replacing it with a live model would require noting
output variance across runs; the schema and lifecycle are unchanged.

---

## AI Mode — Live Results (2026-04-20)

The stub agent was extended with an optional Claude Haiku path,
toggled via `USE_AI_AGENT=true`. Both the MCP propose step and a
new AI intent router were deployed to production.

### Intent routing (AI mode)

The AI router (`app/ai_router.py`) classifies raw Spanish messages
into typed intents before the regex chain runs. Tested live via
WhatsApp:

| Message sent | Intent classified | Result |
|---|---|---|
| "Se me acabo la leche" | `consume_pantry_item` | ✓ Usaste Leche |
| "Agrega 6 huevos a mi despensa" | `add_pantry_item` | ✓ Agregado |
| "Me faltan huevos" | `consume_pantry_item` | No encontré 'huevos'* |

*Correct — item not in pantry yet. Routing was accurate.

### Stub vs AI agent — replay comparison

| | Stub (3 runs) | AI/Haiku (3 runs) |
|---|---|---|
| Scenario | pagué 5000, history: comida×8 | same |
| Proposed category | comida (all 3) | tested live, not scripted† |
| Variance | 0 | N/A |
| Iteration count | 1 | 1 |

†AI replay requires the production API key. Stub replay confirmed
reproducible locally (`scripts/replay_mcp_context.py`).

### AI mode friction points

- Intent ambiguity: "me faltan X" initially routed to shopping list
  instead of pantry consume — fixed by adding explicit rule to the
  system prompt. One prompt edit, no code change.
- Fallback works: when AI call fails or returns non-JSON, regex
  router handles the message transparently. Observed in early deploy
  logs before the markdown-fence fix.

---

## Reconciliation Batch Domain (2026-04-20)

The MCP module was extended with a `reconciliation` domain that
carries a batch of up to 5 ambiguous transactions in a single
context, categorizing all of them in one `requestAction` pass.

### New deliverables

| Deliverable | Details |
|---|---|
| `domain: "reconciliation"` | Batch context with `MAX_BATCH_SIZE = 5` pruning |
| `_propose_stub_batch()` | Assigns highest-history category to every tx |
| `test_reconciliation_*` (5 tests) | Round-trip, reproducibility, pruning, verify→refine, empty history |
| `test_ai_reproducibility_across_3_mocked_runs` | 3 identical mocked AI calls → identical output |
| Fixture snapshot | `fixtures/mcp_snapshots/reconciliation_batch.json` |
| Agent iteration log | `agent_iteration_log.md` (5 entries, full format) |
| 4 additional snapshots | `expense_empty_history`, `expense_staged`, `expense_verify_refine_step1/2` |

### Reconciliation batch — 3-run reproducibility

| Run | Transactions | All proposed | Identical? |
|-----|-------------|-------------|----------|
| 1 | 3 (pagué 5000, pan, taxi) | comida × 3 | — |
| 2 | same | comida × 3 | ✓ |
| 3 | same | comida × 3 | ✓ |

**Variance: 0.** Stub batch proposer is fully deterministic.

### Verify→refine loop (batch)

```
Context 1 (history: otros×5): pending → staged → rolled_back
Context 2 (history: comida×8): pending → staged → confirmed
```

The same two-pass lifecycle demonstrated for single expenses
applies identically to the batch domain.
