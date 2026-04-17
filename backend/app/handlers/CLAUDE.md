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

Used by complete_todo, resolve_waiting, check_item:

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

## What exists

| File | Feature | Tables | Status |
|------|---------|--------|--------|
| expenses.py | Gastos | expenses | live |
| summary.py | Resumen semanal | expenses | live |
| todos.py | Pendientes | todos | live |
| waiting_on.py | Esperando | waiting_on | live |
| shopping.py | Compras | shopping_list | handler only* |
| notes.py | Notas | notes | handler only* |
| wishlist.py | Deseos | wishlist | handler only* |

*Handler and router patterns exist but Supabase table may not —
check SCHEMA.md before using.
