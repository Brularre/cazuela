# Handlers — Conventions

One file per feature. Each file exports named functions
that the router calls directly.

## Imports

```python
from app.db import client          # always
from app.mcp import client as mcp  # only if the feature uses MCP
```

## Function signatures

```python
def add_X(text: str, user: dict) -> str:
def list_X(user: dict) -> str:
def resolve_X(fragment: str, user: dict) -> str:  # fuzzy match
```

`user` is always the full row from the `users` table
(has at least `id` and `phone`).

## Return format

Always return a Spanish string. WhatsApp formatting:
- `*bold*` for headers/labels
- `_italic_` for hints
- `• item` for list items
- `✓` prefix for success confirmations

## Fuzzy match pattern

```python
match = next(
    (i for i in items if fragment.lower() in i["field"].lower()),
    None
)
if not match:
    return f"No encontré '{fragment}'."
```

## Empty list pattern

```python
if not items:
    return "No tienes X."
```

## Docstrings and comments

- Every handler **module** has a module-level docstring listing its
  public API, tables touched, and any non-obvious constraints.
  Keep it up to date when adding or removing functions.
- Add a **function docstring** only when the signature + module
  docstring leave something genuinely unclear (a tricky algorithm,
  a DB edge case, a side-effect that isn't obvious).
- **No inline comments** — don't narrate what the code does line by
  line. Let the code and the module docstring do the talking.



| File | Feature | Tables | MCP | Status |
|------|---------|--------|-----|--------|
| expenses.py | Gastos individuales | expenses | no | live |
| expense_batch.py | Gastos supermercado (batch) | expenses | yes | live |
| budget.py | Presupuesto mensual | budgets | no | live |
| summary.py | Resumen semanal + estimado | expenses, budgets | no | live |
| todos.py | Pendientes | todos | no | live |
| waiting_on.py | Esperando | waiting_on | no | live |
| pantry.py | Despensa (stock) | pantry | no | live |
| pantry_shopping.py | "Necesito comprar" MCP flow | pantry, shopping_list | yes | live |
| shopping.py | Lista de compras manual | shopping_list | no | live |
| recipes.py | Recetas + sugerencias IA | recipes, recipe_ingredients, shopping_list | yes | live |

> **Budget note:** `budgets.period` is always `'mes'` (migrated from
> `'semana'` via `budgets_semana_to_mes.sql`). Do not insert `'semana'`.
