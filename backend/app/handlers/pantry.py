"""
Pantry handler — COMIDA feature (despensa / stock tracking).

Public API:
  add_pantry_item(item, desired_qty, user, category='otros') -> str
    Upsert by normalized item name. Sets both desired and current
    quantity on create; updates desired/current/category on conflict.

  list_pantry(user) -> str
    Grouped by category (cocina → baño → otros). Flags low-stock items.

  consume_pantry_item(item_fragment, user) -> str
    Decrements current_quantity by 1 (floor 0). Fuzzy-match lookup.

  restock_pantry_item(item_fragment, user, qty=None) -> str
    If qty given: adds qty to current (cap 9999).
    If qty is None: resets current to desired_quantity.

  set_pantry_stock(item_fragment, qty, user) -> str
    Hard-sets current_quantity to qty (cap 9999).

  restock_all_pantry(user) -> str
    Resets all below-threshold items to their desired_quantity.

  normalize(text) -> str
    NFKD strip + lowercase; used for fuzzy pantry lookups.
    Note: expenses.py has its own slightly different normalize();
    pantry uses the NFKD variant to match item names stored as ASCII.
"""
import unicodedata
from app.db import client


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def _find_pantry_item(items: list, item_fragment: str) -> dict | str:
    needle = normalize(item_fragment)
    match = next(
        (i for i in items if needle in normalize(i["item"]) or normalize(i["item"]) in needle),
        None,
    )
    if match:
        return match
    needle_words = set(needle.split())
    suggestion = next(
        (i for i in items if needle_words & set(normalize(i["item"]).split())),
        None,
    )
    if suggestion:
        return (
            f"No encontré '{item_fragment}' en tu despensa. "
            f"¿Quisiste decir _{suggestion['item']}_?"
        )
    return f"No encontré '{item_fragment}' en tu despensa."


def add_pantry_item(item: str, desired_qty: int, user: dict, category: str = "otros") -> str:
    normalized = normalize(item)
    existing = (
        client.table("pantry")
        .select("id")
        .eq("user_id", user["id"])
        .ilike("item", normalized)
        .execute()
    ).data or []
    if existing:
        client.table("pantry").update({
            "desired_quantity": desired_qty,
            "current_quantity": desired_qty,
            "category": category,
        }).eq("id", existing[0]["id"]).execute()
        return f"✓ Despensa actualizada: {normalized} (quieres {desired_qty})"
    client.table("pantry").insert({
        "user_id": user["id"],
        "item": normalized,
        "desired_quantity": desired_qty,
        "current_quantity": desired_qty,
        "category": category,
    }).execute()
    return f"✓ Agregado a tu despensa: {normalized} (necesitas {desired_qty})"


def list_pantry(user: dict) -> str:
    result = (
        client.table("pantry")
        .select("item, current_quantity, desired_quantity, category")
        .eq("user_id", user["id"])
        .order("item")
        .execute()
    )
    items = result.data or []
    if not items:
        return "Tu despensa está vacía. Ejemplo: _despensa cocina arroz 3_ o _despensa jabón 2_."
    grouped = {"cocina": [], "baño": [], "otros": []}
    for i in items:
        bucket = i["category"] if i["category"] in grouped else "otros"
        grouped[bucket].append(i)
    labels = {"cocina": "Cocina", "baño": "Baño", "otros": "Otros"}
    lines = ["*Mi despensa:*"]
    for cat in ("cocina", "baño", "otros"):
        if not grouped[cat]:
            continue
        lines.append(f"*{labels[cat]}:*")
        for i in grouped[cat]:
            cur = i["current_quantity"]
            des = i["desired_quantity"]
            flag = " — *reponer*" if cur < des else ""
            lines.append(f"• {i['item']}: {cur}/{des}{flag}")
    return "\n".join(lines)


def consume_pantry_item(item_fragment: str, user: dict) -> str:
    items = (
        client.table("pantry")
        .select("id, item, current_quantity")
        .eq("user_id", user["id"])
        .execute()
    ).data or []
    found = _find_pantry_item(items, item_fragment)
    if isinstance(found, str):
        return found
    new_qty = max(0, found["current_quantity"] - 1)
    client.table("pantry").update({"current_quantity": new_qty}).eq("id", found["id"]).execute()
    if new_qty == 0:
        return f"✓ Usaste {found['item']} (sin stock — recuerda reponer)"
    return f"✓ Usaste {found['item']} (quedan {new_qty})"


def restock_pantry_item(item_fragment: str, user: dict, qty: int | None = None) -> str:
    items = (
        client.table("pantry")
        .select("id, item, current_quantity, desired_quantity")
        .eq("user_id", user["id"])
        .execute()
    ).data or []
    found = _find_pantry_item(items, item_fragment)
    if isinstance(found, str):
        return found
    new_qty = min((found["current_quantity"] or 0) + qty, 9999) if qty is not None else found["desired_quantity"]
    client.table("pantry").update({"current_quantity": new_qty}).eq("id", found["id"]).execute()
    return f"✓ Repuesto: {found['item']} ({new_qty} disponibles)"


def set_pantry_stock(item_fragment: str, qty: int, user: dict) -> str:
    items = (
        client.table("pantry")
        .select("id, item, desired_quantity")
        .eq("user_id", user["id"])
        .execute()
    ).data or []
    found = _find_pantry_item(items, item_fragment)
    if isinstance(found, str):
        return found
    new_qty = min(qty, 9999)
    client.table("pantry").update({"current_quantity": new_qty}).eq("id", found["id"]).execute()
    return f"✓ Stock actualizado: {found['item']} ({new_qty} disponibles)"


def restock_all_pantry(user: dict) -> str:
    items = (
        client.table("pantry")
        .select("id, item, desired_quantity, current_quantity")
        .eq("user_id", user["id"])
        .execute()
    ).data or []
    low = [i for i in items if i["current_quantity"] < i["desired_quantity"]]
    if not low:
        return "Tu despensa ya está al día."
    for item in low:
        client.table("pantry").update({
            "current_quantity": item["desired_quantity"]
        }).eq("id", item["id"]).execute()
    n = len(low)
    noun = "ítem repuesto" if n == 1 else "ítems repuestos"
    return f"✓ Despensa al día ({n} {noun})."
