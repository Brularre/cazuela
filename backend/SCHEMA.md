# Cazuela — Database Schema

Live table definitions. Update this file after running any migration
(use `/schema-sync` skill if available).

All tables confirmed live via Supabase MCP on 2026-04-20.

---

## users ✓

Primary identity table. One row per WhatsApp number.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| phone | text | unique, format +56XXXXXXXXX |
| name | text | nullable |
| currency | text | default 'CLP' |
| anthropic_key | text | nullable, encrypted |
| ai_mode | boolean | default false |
| created_at | timestamptz | default now() |

---

## expenses ✓

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | nullable |
| amount | numeric | |
| currency | text | default 'CLP' |
| category | text | one of CATEGORY_KEYWORDS keys + "otros" |
| note | text | nullable, raw user input |
| date | date | default CURRENT_DATE |
| receipt_url | text | nullable |
| created_at | timestamptz | default now() |

**Categories (fixed list):**
comida, transporte, salud, hogar, entretenimiento,
ropa, tecnología, educación, viajes, otros

---

## todos ✓

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | nullable |
| task | text | |
| done | boolean | default false |
| due_date | date | nullable |
| priority | text | hoy \| semana \| mes, default semana |
| created_at | timestamptz | default now() |

---

## waiting_on ✓

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | nullable |
| description | text | |
| resolved | boolean | default false |
| created_at | timestamptz | default now() |

---

## shopping_list ✓

Manual shopping list for one-off items (not pantry staples).
Separate from pantry: items here are not stock-tracked.
Dashboard compras section shows both sources side by side.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | nullable |
| item | text | |
| quantity | integer | nullable |
| unit | text | nullable |
| checked | boolean | default false |
| source | text | default 'manual' |
| created_at | timestamptz | default now() |

---

## budgets ✓

Weekly spending limit per user. No monthly budget limit —
only a projected monthly estimate (weekly × 4) is shown
in the dashboard and resumen. Period is always 'semana'.
Upserted on conflict (user_id, period).

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | on delete cascade |
| period | text | always 'semana' |
| amount | numeric | spending limit |
| created_at | timestamptz | default now() |

---


## conversations ✓

Conversation history per user. Currently unused (0 rows).

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | nullable |
| role | text | 'user' \| 'assistant' |
| content | text | |
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

Stateful conversation contexts for the MCP staging pattern.
Used by the `expense`, `expense_batch`, and `reconciliation`
domains. RLS enabled; TTL = 1 hour.

| Column | Type | Notes |
|--------|------|-------|
| context_id | uuid PK | |
| version | text | default '1.0' |
| domain | text | expense \| expense_batch \| reconciliation \| pantry_add_batch |
| user_id | uuid FK → users(id) | |
| created_at | timestamptz | default now() |
| expires_at | timestamptz | created_at + 3600s |
| status | text | pending \| staged \| confirmed \| rolled_back |
| payload | jsonb | input data (amount, items_csv, etc.) |
| proposed | jsonb | nullable, agent suggestion |
| agent_model | text | stub-v1 or claude-haiku-4-5-20251001 |
| iteration_count | integer | default 0 |

Indexes: (user_id, status), (expires_at)

---

## pantry ✓

Threshold-based stock tracking. Items where
current_quantity < desired_quantity flag as needing restock.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | on delete cascade |
| item | text | free text name |
| desired_quantity | integer | threshold — how many to keep at home |
| current_quantity | integer | starts equal to desired at creation |
| category | text | cocina \| baño \| otros, default 'otros' |
| created_at | timestamptz | default now() |

---

## recipes ✓

Recipes created by the user, with a list of ingredients.
Ingredients are normalized (lowercase, no accents) to match
pantry item names for cross-referencing.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | on delete cascade |
| name | text | recipe display name |
| servings | int | default 2 |
| created_at | timestamptz | default now() |

---

## recipe_ingredients ✓

Ingredients belonging to a recipe. Cascade-deleted with recipe.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| recipe_id | uuid FK → recipes(id) | on delete cascade |
| item | text | normalized ingredient name |
| quantity | numeric | nullable |
| unit | text | nullable (taza, g, kg, etc.) |
| created_at | timestamptz | default now() |

---

## meal_plans ✓

One plan per user per week. week_start is always a Monday.
Unique constraint on (user_id, week_start).

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid FK → users(id) | on delete cascade |
| week_start | date | Monday of the planned week |
| created_at | timestamptz | default now() |

---

## meal_plan_entries ✓

Individual meal slots within a plan. day_of_week is a Spanish
day name (lunes–domingo). slot_name is user-defined (almuerzo,
cena, or any custom name). recipe_id is nullable — a slot can
exist with no recipe assigned yet.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| meal_plan_id | uuid FK → meal_plans(id) | on delete cascade |
| day_of_week | text | lunes/martes/.../domingo |
| slot_name | text | almuerzo/cena/custom |
| recipe_id | uuid FK → recipes(id) | on delete set null |
| created_at | timestamptz | default now() |

---

## Migrations run (in order)

1. Initial schema — users, expenses, todos, shopping_list,
   notes, wishlist, conversations
   (no file, applied manually early in project)
2. `waiting_on_migration.sql` — waiting_on table
3. `priority_todos_migration.sql` —
   alter todos add column priority
4. `otp_migration.sql` — otp_codes table
5. `mcp_contexts_migration.sql` — mcp_contexts table
6. `pantry_migration.sql` — pantry table
7. `pantry_category_migration.sql` — add category column to pantry
8. `budget_migration.sql` — budgets table
9. `meal_planning` — recipes, recipe_ingredients,
   meal_plans, meal_plan_entries tables
