# Cazuela — Agent Iteration Log

Records every AI interaction: prompt given to the agent, context
snapshot at call time, model + settings, agent output, diff
accepted, and reason for accepting or rejecting.

Schema pointer: `backend/mcp_context_schema.md`
Format: one entry per agent interaction, newest at bottom.

---

## 2026-04-15T14:30:00Z — MCP stub: initial categorization

**Prompt:**
```
1. Categorize ambiguous expense: "pagué 5000" (no description).
2. Context: mcp_context_schema.md v1.0, domain=expense.
   Schema pointer: backend/mcp_context_schema.md
3. Acceptance: proposed.category ∈ CATEGORIES;
   test_stub_picks_highest_history passes.
4. Output: {"category": "<str>", "confidence": <float>,
   "reasoning": "<str>"}
```

**Context snapshot:**
`backend/fixtures/mcp_snapshots/expense_comida.json`

**Model:** stub-v1
**Settings:** deterministic (no API call); picks max(user_history)

**Agent output:**
```json
{
  "category": "comida",
  "confidence": 0.8,
  "reasoning": "categoría más frecuente del usuario"
}
```

**Diff applied:**
```
mcp_contexts row updated:
  status: "pending" → "staged"
  proposed: null → {"category": "comida", ...}
  iteration_count: 0 → 1
```

**Decision:** Accepted
**Reason:** comida×8 is the dominant category — correct output.

---

## 2026-04-15T15:00:00Z — MCP stub: verify→refine loop

**Prompt:**
```
1. Categorize ambiguous expense: "pagué 5000"
   (initial history skewed to otros).
2. Context: mcp_context_schema.md v1.0, domain=expense.
   Schema pointer: backend/mcp_context_schema.md
3. Acceptance: test_verify_refine_loop passes;
   status transitions staged→rolled_back, then new
   context staged→confirmed.
4. Output: {"category": "<str>", "confidence": <float>,
   "reasoning": "<str>"}
```

**Context snapshot (step 1):**
`backend/fixtures/mcp_snapshots/expense_verify_refine_step1.json`

**Model:** stub-v1
**Settings:** deterministic; picks max(user_history)

**Agent output (step 1 — rolled back):**
```json
{
  "category": "otros",
  "confidence": 0.8,
  "reasoning": "categoría más frecuente del usuario"
}
```

**Reason for rollback:** History seeded with otros×5, comida×1.
User rejected proposal and corrected the context.

**Context snapshot (step 2):**
`backend/fixtures/mcp_snapshots/expense_verify_refine_step2.json`

**Agent output (step 2 — confirmed):**
```json
{
  "category": "comida",
  "confidence": 0.8,
  "reasoning": "categoría más frecuente del usuario"
}
```

**Diff applied:**
```
Context 1: staged → rolled_back
Context 2: pending → staged → confirmed
  proposed: {"category": "comida", "confidence": 0.8, ...}
  iteration_count: 0 → 1
```

**Decision:** Accepted (step 2)
**Reason:** Corrected context (comida×8 dominant) produced the
right proposal. Verify→refine loop validated.

---

## 2026-04-18T11:00:00Z — Claude Haiku: expense categorization (live)

**Prompt:**
```
1. Categorize ambiguous expense: "pagué 5000" (no description).
2. Context: mcp_context_schema.md v1.0, domain=expense.
   Schema pointer: backend/mcp_context_schema.md
3. Acceptance: category ∈ CATEGORIES; confidence > 0.5;
   reasoning in Spanish.
4. Output: {"category": "<str>", "confidence": <float>,
   "reasoning": "<str in Spanish>"}
```

**Context snapshot:**
`backend/fixtures/mcp_snapshots/expense_comida.json`

**Model:** claude-haiku-4-5-20251001
**Settings:** temperature=0, max_tokens=128

**Agent output:**
```json
{
  "category": "comida",
  "confidence": 0.85,
  "reasoning": "El historial del usuario muestra comida como
                categoría dominante"
}
```

**Diff applied:** Live Railway deploy; expense saved with
category="comida" after user replied "confirmar" via WhatsApp.

**Decision:** Accepted
**Reason:** Category matches dominant history; confidence > 0.8;
user confirmed in 2-message interaction.

---

## 2026-04-18T12:15:00Z — Claude Haiku: intent routing (live, bug)

**Prompt:**
```
1. Classify intent of WhatsApp message: "Me faltan huevos".
2. Context: ai_router.py system prompt, _INTENTS list.
   Schema pointer: backend/app/ai_router.py:_SYSTEM_PROMPT
3. Acceptance: intent == "consume_pantry_item"
   (item ran out, not a purchase request).
4. Output: {"intent": "<str>", "item_fragment": "<str>"}
```

**Model:** claude-haiku-4-5-20251001
**Settings:** temperature=0, max_tokens=128

**Agent output (incorrect):**
```json
{"intent": "add_to_shopping", "item": "huevos"}
```

**Expected:** `{"intent": "consume_pantry_item", "item_fragment": "huevos"}`

**Diff applied (fix to system prompt):**
```diff
 Rules:
+- "me faltan X", "se me acabo X", "quedé sin X", "no tengo X" →
+  consume_pantry_item (the item ran out), NOT add_to_shopping.
```

**Decision:** Rejected — system prompt patched
**Reason:** "me faltan" is ambiguous without an explicit rule.
Claude defaulted to the shopping interpretation.
One-line prompt addition resolved it with no code change.

---

## 2026-04-18T12:30:00Z — Claude Haiku: intent routing (live, after fix)

**Prompt:**
```
1. Classify intent of WhatsApp message: "Me faltan huevos".
2. Context: ai_router.py system prompt (with pantry consume rule).
   Schema pointer: backend/app/ai_router.py:_SYSTEM_PROMPT
3. Acceptance: intent == "consume_pantry_item".
4. Output: {"intent": "<str>", "item_fragment": "<str>"}
```

**Model:** claude-haiku-4-5-20251001
**Settings:** temperature=0, max_tokens=128

**Agent output:**
```json
{"intent": "consume_pantry_item", "item_fragment": "huevos"}
```

**Diff applied:** None — routing correct.
Handler replied "No encontré 'huevos' en tu despensa"
(item not in pantry yet — correct behavior).

**Decision:** Accepted
**Reason:** Routing correct post-fix; handler behavior also correct.

---

## 2026-04-20T10:00:00Z — MCP stub: reconciliation batch (3 expenses)

**Prompt:**
```
1. Categorize batch of 3 ambiguous expenses in a single
   reconciliation context.
2. Context: mcp_context_schema.md v1.0, domain=reconciliation.
   Schema pointer: backend/mcp_context_schema.md
3. Acceptance: test_reconciliation_batch_round_trip passes;
   proposed.categorizations has one entry per transaction;
   test_reconciliation_batch_reproducibility confirms 3× identical.
4. Output: {"categorizations": [{"index": <int>,
   "category": "<str>", "confidence": <float>,
   "reasoning": "<str>"}, ...]}
```

**Context snapshot:**
`backend/fixtures/mcp_snapshots/reconciliation_batch.json`

**Model:** stub-v1
**Settings:** deterministic; all transactions get max(user_history)

**Agent output:**
```json
{
  "categorizations": [
    {"index": 0, "category": "comida", "confidence": 0.8,
     "reasoning": "categoría más frecuente del usuario"},
    {"index": 1, "category": "comida", "confidence": 0.8,
     "reasoning": "categoría más frecuente del usuario"},
    {"index": 2, "category": "comida", "confidence": 0.8,
     "reasoning": "categoría más frecuente del usuario"}
  ]
}
```

**Diff applied:**
```
mcp_contexts row updated:
  status: "pending" → "staged"
  proposed: null → {"categorizations": [...]}
  iteration_count: 0 → 1
```

**Decision:** Accepted
**Reason:** All 3 categorizations returned; format correct;
3× identical output confirmed by test suite (variance = 0).

---

## 2026-04-21T10:00:00Z — MCP stub: recipe_create domain (AI off)

**Prompt:**
```
1. Propose ingredients for recipe: "cazuela".
2. Context: mcp_context_schema.md v1.0, domain=recipe_create.
   Schema pointer: backend/mcp_context_schema.md
3. Acceptance: proposed.ingredients is a list;
   status transitions pending→staged→confirmed;
   3× identical output confirmed.
4. Output: {"ingredients": [{"item": "<str>",
   "quantity": <number|null>, "unit": "<str|null>"}]}
```

**Context snapshot:**
`backend/fixtures/mcp_snapshots/recipe_cazuela.json`

**Model:** stub-v1
**Settings:** use_ai_agent=False; returns empty list immediately

**Agent output:**
```json
{"ingredients": []}
```

**Diff applied:**
```
mcp_contexts row updated:
  status: "pending" → "staged"
  proposed: null → {"ingredients": []}
  iteration_count: 0 → 1
```

**Decision:** Accepted
**Reason:** Stub correctly returns empty ingredients when AI
is off. Recipe saved with hint to activate AI mode.
3× identical output confirmed by benchmark (variance = 0).

---

## 2026-04-21T10:30:00Z — MCP claude-t0: recipe_create domain (AI on, mocked)

**Prompt:**
```
1. Propose ingredients for recipe: "cazuela".
2. Context: mcp_context_schema.md v1.0, domain=recipe_create.
   Schema pointer: backend/mcp_context_schema.md
3. Acceptance: proposed.ingredients has ≥1 item;
   each item has at least "item" field;
   3× identical output under temperature=0.
4. Output: {"ingredients": [{"item": "<str>",
   "quantity": <number|null>, "unit": "<str|null>"}]}
```

**Context snapshot:**
`backend/fixtures/mcp_snapshots/recipe_cazuela.json`

**Model:** claude-haiku-4-5-20251001 (mocked in benchmark)
**Settings:** temperature=0, max_tokens=512, use_ai_agent=True

**Agent output:**
```json
{
  "ingredients": [
    {"item": "carne de vacuno", "quantity": 500, "unit": "g"},
    {"item": "papa", "quantity": 4, "unit": null},
    {"item": "choclo", "quantity": 2, "unit": null},
    {"item": "zapallo", "quantity": 200, "unit": "g"},
    {"item": "zanahoria", "quantity": 2, "unit": null},
    {"item": "caldo de carne", "quantity": 1, "unit": "litro"}
  ]
}
```

**Diff applied:**
```
mcp_contexts row updated:
  status: "pending" → "staged"
  proposed: null → {"ingredients": [...6 items...]}
  iteration_count: 0 → 1
After confirm: 1 recipe row + 6 ingredient rows written
```

**Decision:** Accepted
**Reason:** 6 canonical cazuela ingredients returned in correct
format. 3× identical output under temperature=0 (variance = 0).
Constraint enforcement confirmed: switching AI flag off produces
0 ingredients (different context → different output).

---

## 2026-04-21 — Documentation and CI gap-closing

**Suggested:** Rewrote COMPARISON_REPORT.md and
mcp_context_schema.md to cover expense_batch and
reconciliation domains; added replay CI step to ci.yml;
added `replay-check` Makefile target; updated SCHEMA.md
mcp_contexts description; redirected backend/mcp_comparison_report.md
to root-level report.
**Decision:** Accepted
**Rationale:** Assignment requires evidence that all
three domains (expense, expense_batch, reconciliation)
are tested and documented. Replay fixtures now run on
every CI push, catching regressions without a live API.

---
