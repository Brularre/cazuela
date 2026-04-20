# MCP Context Schema

Documents every field in a Cazuela MCP context object,
why it exists, and its constraints.

---

## Example context — single expense (staged)

```json
{
  "context_id": "a3f1c2d4-e5b6-7890-abcd-ef1234567890",
  "version": "1.0",
  "domain": "expense",
  "user_id": "11111111-1111-1111-1111-111111111111",
  "created_at": "2026-04-15T14:00:00+00:00",
  "expires_at": "2026-04-15T15:00:00+00:00",
  "status": "staged",
  "payload": {
    "raw_message": "pagué 5000",
    "amount": 5000.0,
    "date": "2026-04-15",
    "note": null,
    "user_history": {
      "comida": 8,
      "transporte": 3,
      "otros": 1
    }
  },
  "proposed": {
    "category": "comida",
    "confidence": 0.8,
    "reasoning": "categoría más frecuente del usuario"
  },
  "agent_model": "stub-v1",
  "iteration_count": 1
}
```

## Example context — expense_batch (step 3 / confirmed)

```json
{
  "context_id": "b4c5d6e7-0000-0000-0000-000000000002",
  "version": "1.0",
  "domain": "expense_batch",
  "user_id": "11111111-1111-1111-1111-111111111111",
  "created_at": "2026-04-20T10:00:00+00:00",
  "expires_at": "2026-04-20T11:00:00+00:00",
  "status": "confirmed",
  "payload": {
    "raw_message": "gasté 18000 en supermercado: pan, leche, queso, lavalozas",
    "total_amount": 18000.0,
    "items_csv": "pan, leche, queso, lavalozas",
    "date": "2026-04-20",
    "user_history": {"comida": 5}
  },
  "proposed": {
    "step": 3,
    "items": [
      {"name": "pan", "category": "comida", "amount": 4500},
      {"name": "leche", "category": "comida", "amount": 4500},
      {"name": "queso", "category": "comida", "amount": 4500},
      {"name": "lavalozas", "category": "hogar", "amount": 4500}
    ],
    "reasoning": "monto total repartido en pesos enteros"
  },
  "agent_model": "stub-v1",
  "iteration_count": 3
}
```

## Example context — reconciliation batch (staged)

```json
{
  "context_id": "ffffffff-0000-0000-0000-000000000005",
  "version": "1.0",
  "domain": "reconciliation",
  "user_id": "11111111-1111-1111-1111-111111111111",
  "created_at": "2026-04-20T10:00:00+00:00",
  "expires_at": "2026-04-20T11:00:00+00:00",
  "status": "staged",
  "payload": {
    "transactions": [
      {"raw_message": "pagué 5000", "amount": 5000, "date": "2026-04-18"},
      {"raw_message": "compré pan", "amount": 1500, "date": "2026-04-18"},
      {"raw_message": "taxi al trabajo", "amount": 3000, "date": "2026-04-18"}
    ],
    "user_history": {"comida": 8, "transporte": 3}
  },
  "proposed": {
    "categorizations": [
      {"index": 0, "category": "comida",
       "confidence": 0.8, "reasoning": "categoría más frecuente"},
      {"index": 1, "category": "comida",
       "confidence": 0.8, "reasoning": "categoría más frecuente"},
      {"index": 2, "category": "comida",
       "confidence": 0.8, "reasoning": "categoría más frecuente"}
    ]
  },
  "agent_model": "stub-v1",
  "iteration_count": 1
}
```

---

## Field reference

### `context_id`
- **Type:** string (UUID4)
- **Why it exists:** Primary key for context lookup.
  Exposed to users as an 8-character hex prefix
  (e.g. `a3f1c2d4`) for confirm/cancel commands.
- **Constraints:** Unique, generated on `create_context`.

### `version`
- **Type:** string
- **Why it exists:** Allows future schema evolution without
  breaking existing stored contexts.
  A context with `version: "1.0"` can be processed by
  any code that understands that version.
- **Constraints:** Currently always `"1.0"`.

### `domain`
- **Type:** string — one of `expense`, `expense_batch`,
  `reconciliation`, `todo`, `wishlist`, `shopping_list`
- **Why it exists:** Determines which agent logic runs
  during `requestAction`.
  - `expense` — single ambiguous transaction; stub or
    Claude Haiku proposes one category.
  - `expense_batch` — supermarket receipt with a CSV of
    items and a single total amount. Agent runs 3
    sequential steps: extract names → assign categories
    → split total. Handler:
    `backend/app/handlers/expense_batch.py`.
  - `reconciliation` — batch of up to `MAX_BATCH_SIZE = 5`
    transactions; stub proposes a category for each in
    one pass.
  - Other domains return `{"confirmed": true}` immediately.
- **Constraints:** Required. No default.

### `user_id`
- **Type:** string (UUID)
- **Why it exists:** Scopes the context to a single user.
  Used by handlers to write to the correct DB rows
  after confirmation.
- **Constraints:** Must match a valid `users.id` in
  Supabase. Never included in redacted context passed
  to agents (it is a top-level field, not inside
  `payload`).

### `created_at`
- **Type:** string (ISO 8601 UTC)
- **Why it exists:** Audit trail. Records when the
  multi-step flow started.
- **Constraints:** Set once at creation; never mutated.

### `expires_at`
- **Type:** string (ISO 8601 UTC)
- **Why it exists:** Enforces the TTL (time-to-live).
  Contexts for which the user never replies are discarded
  after 1 hour (`TTL_SECONDS = 3600`).
  1 hour was chosen as long enough for a user to see a
  WhatsApp notification and reply, but short enough to
  bound memory usage on a single-process server.
- **Constraints:** `created_at + 3600s`. Read by
  `get_context`; expired contexts raise `ValueError`.

### `status`
- **Type:** string — state machine
- **Why it exists:** Provides an explicit audit trail of
  where the context is in the flow.
  Prevents double-confirmation or confirming a
  rolled-back context.
- **Transitions:**
  ```
  pending → staged (after requestAction)
  staged  → confirmed (after confirm)
  staged  → rolled_back (after rollback)
  ```
- **Constraints:** Only `staged` contexts can be confirmed
  or rolled back. The router checks status before writing
  to the DB.

### `payload`
- **Type:** dict — domain-specific
- **Why it exists:** Carries the data the agent needs
  to make a proposal, and the handler needs to write
  to the DB after confirmation.
- **Expense payload fields:**
  - `raw_message` — original WhatsApp text
  - `amount` — parsed float
  - `date` — ISO date string (YYYY-MM-DD)
  - `note` — optional free-text note
  - `user_history` — dict of category → count
    (last 30 days, pruned to `MAX_HISTORY_ENTRIES = 10`)
- **expense_batch payload fields:**
  - `raw_message` — original WhatsApp text
  - `total_amount` — total spend as float (CLP)
  - `items_csv` — comma-separated item names; pruned to
    `MAX_ITEMS = 10` entries at creation time
  - `date` — ISO date string (YYYY-MM-DD)
  - `user_history` — same format as expense domain
- **Reconciliation payload fields:**
  - `transactions` — list of up to `MAX_BATCH_SIZE = 5`
    transaction dicts (each with `raw_message`, `amount`,
    `date`). Longer lists are truncated at creation time.
  - `user_history` — same format as expense domain
- **Optional fields (any domain):**
  - `user_profile` — free-form dict of user preferences.
    Pruned to `MAX_USER_PROFILE_JSON_CHARS = 500` chars
    at creation time (alphabetical key eviction).
    See `backend/app/mcp/context.py`.
  - `category_map` — dict mapping keyword → category
    for explicit user-defined overrides. Pruned to
    `MAX_CATEGORY_MAP_KEYS = 20` entries. Checked first
    in `_propose_stub`; takes priority over history.
- **Safety:** `redact()` strips any key in `SENSITIVE_KEYS`
  from the payload before passing to agent logic.
  Sensitive keys: `phone`, `anthropic_key`, `supabase_key`,
  `google_tokens`, `password`.

### `proposed`
- **Type:** dict or null
- **Why it exists:** Stores the agent's proposal so the
  confirmation handler can read it without re-running
  the agent.
- **Fields (expense domain):**
  - `category` — proposed category string
  - `confidence` — float 0–1
  - `reasoning` — human-readable explanation shown to user
- **Fields (expense_batch domain, step 1):**
  - `step: 1`, `items: [{"name": "<str>"}, ...]`
- **Fields (expense_batch domain, step 2):**
  - `step: 2`, `items: [{"name": ..., "category": ...}, ...]`
- **Fields (expense_batch domain, step 3):**
  - `step: 3`, `items: [{"name", "category", "amount"}, ...]`
- **Fields (reconciliation domain):**
  - `categorizations: [{"index", "category",
    "confidence", "reasoning"}, ...]`
- **Constraints:** `null` until `requestAction` is called.
  For `expense_batch`, populated incrementally across 3
  calls; `confirm()` is only safe after `step == 3`.

### `agent_model`
- **Type:** string
- **Why it exists:** Records which model or stub produced
  the proposal. Needed for reproducibility — if the stub
  algorithm changes, contexts created under `"stub-v1"`
  can be replayed and compared against the old behaviour.
  If `USE_AI_AGENT=true`, updated to the live model name
  after `requestAction` so the log reflects what
  actually ran.
- **Values:** `"stub-v1"` (default) or
  `"claude-haiku-4-5-20251001"` (AI mode).

### `iteration_count`
- **Type:** integer
- **Why it exists:** Counts how many times `requestAction`
  was called on this context. For `expense_batch` this is
  always 3 on a healthy flow; for `expense` and
  `reconciliation` it is 1 (or more if verify→refine
  rollback cycles were used).
- **Constraints:** Starts at 0; incremented by 1 on each
  `requestAction` call.

---

## Token budgeting & pruning rules

All pruning happens at `create_context` time — never
silently during retrieval.

| Field | Cap | Constant | Eviction strategy |
|---|---|---|---|
| `user_history` | 10 keys | `MAX_HISTORY_ENTRIES` | Keep top-N by count |
| `transactions` | 5 entries | `MAX_BATCH_SIZE` | Truncate tail |
| `items_csv` | 10 items | `MAX_ITEMS` | Truncate tail |
| `user_profile` | 500 chars (JSON) | `MAX_USER_PROFILE_JSON_CHARS` | Alphabetical key eviction |
| `category_map` | 20 keys | `MAX_CATEGORY_MAP_KEYS` | Truncate (insertion order) |

Constants live in `backend/app/mcp/context.py`.

---

## Retention policy

**`mcp_contexts` table (Supabase):**
- TTL = 1 hour (`TTL_SECONDS = 3600`).
- `prune_expired()` is called on every `send_context()`
  and deletes all rows where `expires_at < now()`.
- No manual rotation needed — the table is self-pruning.

**`agent_iteration_log.md` (repo root):**
- Append-only markdown file.
- Manual rotation: archive old entries to
  `agent_iteration_log_YYYY.md` when the file exceeds
  ~200 entries. No automated pruning.

**`backend/mcp_interaction_log.jsonl`:**
- Append-only JSONL written by `backend/replay.py`.
- Manual rotation: archive when the file exceeds ~1 MB.

---

## Redaction policy

The following keys are stripped from any dict passed to
agent logic, regardless of nesting depth:

```
phone, anthropic_key, supabase_key, google_tokens, password
```

This is enforced by `context.redact()`.
A CI test (`test_no_sensitive_keys_in_serialized_context`)
asserts that none of these keys appear in the redacted
output.
