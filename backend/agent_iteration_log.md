# Agent Iteration Log

Records every AI interaction during development of the MCP integration.
One entry per interaction: timestamp, structured prompt, context reference,
model, output summary, diff summary, decision.

---

## 2026-04-15 — MCP module initial implementation

**Task:** Implement MCP context module, stub agent, client wrapper,
new handlers (todos / wishlist / shopping list), router updates,
tests, and replay script.

**Context snapshot:** N/A (initial implementation, no prior MCP context)

**Model:** claude-sonnet-4-6 (subagent + direct implementation)

**Prompt schema:**
1. Task: Implement MCP module for Cazuela per assignment spec
2. Context: New feature — no prior MCP code exists;
   existing handlers and tests must not be modified
3. Acceptance criteria: all tests pass; safety test passes;
   `replay.py` exits 0 with matching snapshot
4. Output format: code files written to worktree branch

**Output summary:**
- Created `app/mcp/context.py` — in-memory context store with TTL,
  pruning, and `redact()` safety function
- Created `app/mcp/agent.py` — deterministic stub: picks highest
  category in user_history, falls back to "otros"
- Created `app/mcp/client.py` — thin wrapper: send / request /
  receive / confirm / rollback
- Created `app/handlers/todos.py` — add, list, complete
- Created `app/handlers/wishlist.py` — add, list
- Created `app/handlers/shopping.py` — add, list, check off
- Updated `app/router.py` — new patterns for todos / wishlist /
  shopping + ambiguous expense → MCP flow
- Created `tests/test_mcp.py` — 12 tests covering round-trip,
  reproducibility, TTL, pruning, safety
- Created `replay.py` — injects snapshot and verifies agent output
- Created `fixtures/mcp_snapshots/expense_comida.json` — example
  snapshot for replay

**Decision:** Accepted

**Reason:** Implementation matches spec; no modifications to existing
handler or test files; all 12 MCP tests pass

---

## 2026-04-15 — Verify→refine loop test

**Prompt (structured schema):**
1. *Task:* Add a verify→refine loop test to `test_mcp.py`
   that simulates a failing first proposal and a passing
   second proposal after context refinement.
2. *Context:* `app/mcp/context.py` schema v1.0;
   stub agent in `app/mcp/agent.py` picks
   `max(user_history, key=count)`.
3. *Acceptance criteria:* Test asserts first proposal
   is "otros" (skewed history), rollback is called,
   second proposal with dominant "comida" history
   is "comida", context ends in "confirmed" status.
4. *Output format:* Single test function appended
   to `tests/test_mcp.py`; no other files modified.

**Input context snapshot:** See
`fixtures/mcp_snapshots/expense_comida.json`
(adapted: first run uses `{"otros": 5, "comida": 1}`,
second uses `{"comida": 8, "otros": 2}`).

**Model:** claude-sonnet-4-6

**Agent output:** `test_verify_refine_loop` added to
`tests/test_mcp.py`. Two contexts created: id1 (rolled
back after "otros" proposal), id2 (confirmed after
"comida" proposal). Iteration count on id2: 1.

**Diff summary:**
- `tests/test_mcp.py`: +25 lines (`test_verify_refine_loop`)

**Decision:** Accepted

**Reason:** Test cleanly demonstrates the two-step flow
with explicit status assertions at each stage.
No existing tests modified.
