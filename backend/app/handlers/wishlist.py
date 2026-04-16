from app.db import client


def add_to_wishlist(item: str, user: dict, price_estimate: float = None) -> str:
    client.table("wishlist").insert({
        "user_id": user["id"],
        "item": item,
        "price_estimate": price_estimate,
    }).execute()
    price_str = (" (~$" + f"{price_estimate:,.0f}".replace(",", ".") + ")") if price_estimate else ""
    return f"✓ Agregado a tu lista de deseos: {item}{price_str}"


def list_wishlist(user: dict) -> str:
    result = (
        client.table("wishlist")
        .select("item, price_estimate")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    items = result.data or []
    if not items:
        return "Tu lista de deseos está vacía."
    lines = ["*Lista de deseos:*"]
    for i in items:
        price = (" ~$" + f"{i['price_estimate']:,.0f}".replace(",", ".")) if i.get("price_estimate") else ""
        lines.append(f"• {i['item']}{price}")
    return "\n".join(lines)
