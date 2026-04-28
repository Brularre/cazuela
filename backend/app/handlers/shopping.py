"""
Shopping list handler — COMIDA feature (lista de compras manual).

Public API:
  add_to_shopping(item, user, quantity=None, unit=None) -> str
    Inserts one row into shopping_list (source defaults to 'manual').

  add_many_to_shopping(items, user, source='manual') -> int
    Bulk-inserts a list of item strings. Returns the count inserted.
    Used by the recipes handler when adding missing ingredients.

  list_shopping(user) -> str
    Returns all unchecked items with optional quantity/unit.

  check_item(item_fragment, user) -> str
    Fuzzy-match by substring; marks first unchecked match as checked=True.
"""
from app.db import client
    client.table("shopping_list").insert({
        "user_id": user["id"],
        "item": item,
        "quantity": quantity,
        "unit": unit,
    }).execute()
    qty_str = (f" x{quantity} {unit or ''}").strip() if quantity else ""
    return f"✓ Agregado a la lista: {item}{qty_str}"


def list_shopping(user: dict) -> str:
    result = (
        client.table("shopping_list")
        .select("item, quantity, unit, checked")
        .eq("user_id", user["id"])
        .eq("checked", False)
        .execute()
    )
    items = result.data or []
    if not items:
        return "La lista de compras está vacía."
    lines = ["*Lista de compras:*"]
    for i in items:
        qty = (f" x{i['quantity']} {i.get('unit') or ''}").strip() if i.get("quantity") else ""
        lines.append(f"• {i['item']}{qty}")
    return "\n".join(lines)


def check_item(item_fragment: str, user: dict) -> str:
    result = (
        client.table("shopping_list")
        .select("id, item")
        .eq("user_id", user["id"])
        .eq("checked", False)
        .execute()
    )
    items = result.data or []
    match = next((i for i in items if item_fragment.lower() in i["item"].lower()), None)
    if not match:
        return f"No encontré '{item_fragment}' en la lista."
    client.table("shopping_list").update({"checked": True}).eq("id", match["id"]).execute()
    return f"✓ Marcado: {match['item']}"


def add_many_to_shopping(items: list[str], user: dict, source: str = "manual") -> int:
    if not items:
        return 0
    rows = [{"user_id": user["id"], "item": item, "source": source} for item in items]
    client.table("shopping_list").insert(rows).execute()
    return len(rows)
