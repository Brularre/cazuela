# MCP Context Schema

Cazuela uses a staged-action protocol for interactions that require
a propose → human-confirm cycle before committing to the database.
The `app/mcp/` module implements this protocol.

## Lifecycle

```
send_context()      → status: "pending"
request_action()    → status: "staged"   (agent proposes)
confirm()           → status: "confirmed" (written to DB)
rollback()          → status: "rolled_back"
```

TTL: 3600 seconds. Expired contexts are pruned on each `send_context` call.

---

## Context schema

| Field            | Type           | Description |
|------------------|----------------|-------------|
| `context_id`     | string (UUID)  | Unique identifier |
| `version`        | string         | Schema version (`"1.0"`) |
| `domain`         | string         | Feature domain (`"expense"`) |
| `user_id`        | string (UUID)  | Foreign key → users table |
| `created_at`     | ISO 8601 string | UTC timestamp |
| `expires_at`     | ISO 8601 string | UTC timestamp (TTL = 1h) |
| `status`         | string         | `pending`, `staged`, `confirmed`, `rolled_back` |
| `payload`        | object         | Domain-specific input data |
| `proposed`       | object or null | Agent's proposed action |
| `agent_model`    | string         | Model or stub name |
| `iteration_count`| integer        | Number of `request_action` calls |

### Sensitive fields — always redacted before logging

`phone`, `anthropic_key`, `supabase_key`, `google_tokens`, `password`

---

## Example: expense domain

### After `send_context()` — status: pending

```json
{
  "context_id": "a3f1e2b0-7c44-4d8e-9f10-123456789abc",
  "version": "1.0",
  "domain": "expense",
  "user_id": "11111111-1111-1111-1111-111111111111",
  "created_at": "2026-04-18T14:30:00+00:00",
  "expires_at": "2026-04-18T15:30:00+00:00",
  "status": "pending",
  "payload": {
    "raw_message": "pagué 5000",
    "amount": 5000.0,
    "date": "2026-04-18",
    "note": null,
    "user_history": {
      "comida": 8,
      "transporte": 3,
      "otros": 1
    }
  },
  "proposed": null,
  "agent_model": "stub-v1",
  "iteration_count": 0
}
```

### After `request_action()` — status: staged

```json
{
  "context_id": "a3f1e2b0-7c44-4d8e-9f10-123456789abc",
  "version": "1.0",
  "domain": "expense",
  "user_id": "11111111-1111-1111-1111-111111111111",
  "created_at": "2026-04-18T14:30:00+00:00",
  "expires_at": "2026-04-18T15:30:00+00:00",
  "status": "staged",
  "payload": {
    "raw_message": "pagué 5000",
    "amount": 5000.0,
    "date": "2026-04-18",
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

### After `confirm()` — status: confirmed

```json
{
  "context_id": "a3f1e2b0-7c44-4d8e-9f10-123456789abc",
  "status": "confirmed",
  "iteration_count": 1
}
```

---

## Payload fields by domain

### `expense`

| Field          | Type           | Required | Description |
|----------------|----------------|----------|-------------|
| `raw_message`  | string         | yes      | Original WhatsApp message |
| `amount`       | float          | yes      | Amount in CLP (integer pesos) |
| `date`         | string (date)  | yes      | ISO date of expense |
| `note`         | string or null | no       | Free-text note |
| `user_history` | object         | yes      | Category → count map (last 30 days, max 10 entries) |

### `proposed` (expense)

| Field        | Type   | Description |
|--------------|--------|-------------|
| `category`   | string | One of the fixed expense categories |
| `confidence` | float  | 0.0–1.0 |
| `reasoning`  | string | Human-readable explanation shown to user |

---

## Fixed expense categories

`comida`, `transporte`, `salud`, `hogar`, `entretenimiento`,
`ropa`, `tecnología`, `educación`, `viajes`, `otros`
