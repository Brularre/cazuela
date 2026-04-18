from app.db import client


def set_budget(period: str, amount: float, user: dict) -> str:
    client.table("budgets").upsert({
        "user_id": user["id"],
        "period": period,
        "amount": amount,
    }, on_conflict="user_id,period").execute()
    formatted = "$" + f"{amount:,.0f}".replace(",", ".")
    label = "semanal" if period == "semana" else "mensual"
    return f"✓ Presupuesto {label} guardado: {formatted}"
