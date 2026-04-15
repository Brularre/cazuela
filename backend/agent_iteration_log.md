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
