from app.db import client


def set_budget(amount: float, user: dict) -> str:
    client.table("budgets").upsert({
        "user_id": user["id"],
        "period": "mes",
        "amount": amount,
    }, on_conflict="user_id,period").execute()
    formatted = "$" + f"{amount:,.0f}".replace(",", ".")
    return f"✓ Presupuesto mensual guardado: {formatted}"
