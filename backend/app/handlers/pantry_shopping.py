"""
Pantry-shopping MCP handler — COMIDA feature.

Handles the "necesito comprar X, Y, Z" two-step MCP flow:

  1. handle_pantry_add_create(items_raw, user)
     Sends a pantry_add_batch MCP context. The agent parses the
     free-text list and proposes {name, category} for each item.
     Returns a confirmation prompt asking whether to route items
     to despensa or lista de compras.

  2a. handle_pantry_add_confirm_despensa(context_id, user)
      Confirms context; upserts items into the pantry table.

  2b. handle_pantry_add_confirm_lista(context_id, user)
      Confirms context; inserts items into shopping_list (source='mcp').

  3. handle_pantry_add_cancel(context_id, user)
     Rolls back the pending MCP context.

Valid pantry categories: cocina | baño | otros

Constants:
  _VALID_PANTRY_CATEGORIES — frozenset of allowed category strings for MCP upserts.
"""
from app.db import client
from app.mcp import client as mcp

_VALID_PANTRY_CATEGORIES = frozenset({"cocina", "baño", "otros"})


def handle_pantry_add_create(items_raw: str, user: dict) -> str:
    context_id = mcp.send_context("pantry_add_batch", user["id"], {
        "items_raw": items_raw,
    })
    result = mcp.request_action(context_id)
    proposed = result.get("proposed", {})
    items = proposed.get("items", [])
    if not items:
        mcp.rollback(context_id)
        return "No entendí qué necesitas comprar."
    lines = ["¿Dónde los agrego?"]
    for it in items:
        lines.append(f"• {it['name']} ({it['category']})")
    lines.append("\nResponde *despensa* o *lista*.")
    return "\n".join(lines)


def handle_pantry_add_confirm_despensa(context_id: str, user: dict) -> str:
    try:
        ctx = mcp.receive_result(context_id)
        proposed = ctx.get("proposed", {})
        items = proposed.get("items", [])
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Esta operación ya fue confirmada, cancelada, o expiró."
    rows = [
        {
            "user_id": user["id"],
            "item": it["name"],
            "desired_quantity": 1,
            "current_quantity": 0,
            "category": it["category"] if it["category"] in _VALID_PANTRY_CATEGORIES else "otros",
        }
        for it in items
    ]
    client.table("pantry").insert(rows).execute()
    names = ", ".join(it["name"] for it in items)
    return f"✓ Agregado a tu despensa: {names} (por reponer)"


def handle_pantry_add_confirm_lista(context_id: str, user: dict) -> str:
    try:
        ctx = mcp.receive_result(context_id)
        proposed = ctx.get("proposed", {})
        items = proposed.get("items", [])
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Esta operación ya fue confirmada, cancelada, o expiró."
    rows = [{"user_id": user["id"], "item": it["name"]} for it in items]
    client.table("shopping_list").insert(rows).execute()
    names = ", ".join(it["name"] for it in items)
    return f"✓ Agregado a tu lista de compras: {names}"


def handle_pantry_add_cancel(context_id: str, user: dict) -> str:
    try:
        mcp.rollback(context_id)
    except ValueError:
        return "Esta operación ya fue confirmada, cancelada, o expiró."
    return "Operación cancelada."
