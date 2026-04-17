# Cazuela — Database Schema

Live table definitions. Update this file after running any migration
(use `/schema-sync` skill if available).

Legend: ✓ confirmed by migration file · ~ inferred from handler code

---

## users ✓

Primary identity table. One row per WhatsApp number.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| phone | text | unique, format +56XXXXXXXXX |
| created_at | timestamptz | default now() |

---

## expenses ~

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK → users(id) | on delete cascade |
| amount | numeric | |
| category | text | one of CATEGORY_KEYWORDS keys + "otros" |
| note | text | raw user input |
| date | text | YYYY-MM-DD, set at save time |
| created_at | timestamptz | default now() |

**Categories (fixed list):**
comida, transporte, salud, hogar, entretenimiento,
ropa, tecnología, educación, viajes, otros

---

## todos ~

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK → users(id) | on delete cascade |
| task | text | |
| done | boolean | default false |
| priority | text | hoy \| semana \| mes, default semana |
| created_at | timestamptz | default now() |

---

## waiting_on ✓

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | on delete cascade |
| description | text | |
| resolved | boolean | default false |
| created_at | timestamptz | default now() |

---

## otp_codes ✓

Short-lived one-time passwords for dashboard login.
10-minute expiry, marked used after first successful verify.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| phone | text | matches users.phone |
| code | text | 6-digit string |
| expires_at | timestamptz | now() + 10 min |
| used | boolean | default false |
| created_at | timestamptz | default now() |

---

## mcp_contexts ✓

Stateful conversation contexts for the MCP agent
(currently used only for ambiguous expense confirmation).

| Column | Type | Notes |
|--------|------|-------|
| context_id | uuid PK | |
| version | text | default '1.0' |
| domain | text | e.g. 'expense' |
| user_id | uuid FK → users(id) | on delete cascade |
| created_at | timestamptz | default now() |
| expires_at | timestamptz | |
| status | text | pending \| staged \| confirmed \| rolled_back |
| payload | jsonb | input data (amount, date, etc.) |
| proposed | jsonb | agent suggestion (category, reasoning) |
| agent_model | text | default 'stub-v1' |
| iteration_count | integer | default 0 |

Indexes: (user_id, status), (expires_at)
RLS: enabled, policy isolates by user_id

---

## shopping_list ~

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK → users(id) | on delete cascade |
| item | text | |
| quantity | integer | nullable |
| unit | text | nullable |
| checked | boolean | default false |
| created_at | timestamptz | default now() |

---

## notes ~

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK → users(id) | on delete cascade |
| content | text | |
| created_at | timestamptz | default now() |

---

## wishlist ~

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK → users(id) | on delete cascade |
| item | text | |
| price_estimate | numeric | nullable |
| created_at | timestamptz | default now() |

---

## Migrations run (in order)

1. Initial schema — users, expenses, todos
   (no file, applied manually early in project)
2. `waiting_on_migration.sql` — waiting_on table
3. `priority_todos_migration.sql` —
   alter todos add column priority
4. `otp_migration.sql` — otp_codes table
5. `mcp_contexts_migration.sql` — mcp_contexts table

## Tables without confirmed migrations

shopping_list, notes, wishlist — handlers exist in the codebase
but no migration files are present. Verify in Supabase before
using these features.
