from app.db import client


def set_budget(period: str, amount: float, user: dict) -> str:
    client.table("budgets").upsert({
        "user_id": user["id"],
        "period": period,
        "amount": amount,
    }, on_conflict="user_id,period").execute()
    formatted = "$" + f"{amount:,.0f}".replace(",", ".")
    label = "semanal" if period == "semana" else "mensual"
    msg = f"✓ Presupuesto {label} guardado: {formatted}"
    if period == "semana":
        monthly = "$" + f"{amount * 4:,.0f}".replace(",", ".")
        msg += (
            f"\n_Trabajamos con semanas para mayor control diario."
            f" Tu estimado mensual sería {monthly} (4 semanas)._"
        )
    return msg
