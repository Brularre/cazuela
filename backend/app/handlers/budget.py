from app.db import client


def set_budget(amount: float, user: dict) -> str:
    client.table("budgets").upsert({
        "user_id": user["id"],
        "period": "semana",
        "amount": amount,
    }, on_conflict="user_id,period").execute()
    formatted = "$" + f"{amount:,.0f}".replace(",", ".")
    monthly = "$" + f"{amount * 4:,.0f}".replace(",", ".")
    return (
        f"✓ Presupuesto semanal guardado: {formatted}"
        f"\n_Trabajamos con semanas para mayor control diario."
        f" Tu estimado mensual sería {monthly} (4 semanas)._"
    )
