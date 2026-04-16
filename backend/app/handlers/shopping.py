from app.db import client


def add_to_shopping(item: str, user: dict, quantity: int = None, unit: str = None) -> str:
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
