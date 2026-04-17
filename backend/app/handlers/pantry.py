from app.db import client


def add_pantry_item(item: str, desired_qty: int, user: dict) -> str:
    existing = (
        client.table("pantry")
        .select("id")
        .eq("user_id", user["id"])
        .ilike("item", item)
        .execute()
    ).data or []
    if existing:
        client.table("pantry").update({
            "desired_quantity": desired_qty,
        }).eq("id", existing[0]["id"]).execute()
        return f"✓ Despensa actualizada: {item} (quieres {desired_qty})"
    client.table("pantry").insert({
        "user_id": user["id"],
        "item": item,
        "desired_quantity": desired_qty,
        "current_quantity": desired_qty,
    }).execute()
    return f"✓ Agregado a tu despensa: {item} (necesitas {desired_qty})"


def list_pantry(user: dict) -> str:
    result = (
        client.table("pantry")
        .select("item, current_quantity, desired_quantity")
        .eq("user_id", user["id"])
        .order("item")
        .execute()
    )
    items = result.data or []
    if not items:
        return "Tu despensa está vacía. Agrega ítems con _despensa: jabón 2_."
    lines = ["*Mi despensa:*"]
    for i in items:
        cur = i["current_quantity"]
        des = i["desired_quantity"]
        flag = " — *reponer*" if cur < des else ""
        lines.append(f"• {i['item']}: {cur}/{des}{flag}")
    return "\n".join(lines)


def consume_pantry_item(item_fragment: str, user: dict) -> str:
    result = (
        client.table("pantry")
        .select("id, item, current_quantity")
        .eq("user_id", user["id"])
        .execute()
    )
    items = result.data or []
    match = next(
        (i for i in items if item_fragment.lower() in i["item"].lower()),
        None,
    )
    if not match:
        return f"No encontré '{item_fragment}' en tu despensa."
    new_qty = max(0, match["current_quantity"] - 1)
    client.table("pantry").update({"current_quantity": new_qty}).eq("id", match["id"]).execute()
    if new_qty == 0:
        return f"✓ Usaste {match['item']} (sin stock — recuerda reponer)"
    return f"✓ Usaste {match['item']} (quedan {new_qty})"


def restock_pantry_item(item_fragment: str, user: dict) -> str:
    result = (
        client.table("pantry")
        .select("id, item, desired_quantity")
        .eq("user_id", user["id"])
        .execute()
    )
    items = result.data or []
    match = next(
        (i for i in items if item_fragment.lower() in i["item"].lower()),
        None,
    )
    if not match:
        return f"No encontré '{item_fragment}' en tu despensa."
    client.table("pantry").update({
        "current_quantity": match["desired_quantity"]
    }).eq("id", match["id"]).execute()
    return f"✓ Repuesto: {match['item']} ({match['desired_quantity']} disponibles)"


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
