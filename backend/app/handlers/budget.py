"""
Budget handler — DINERO feature.

Public API:
  set_budget(amount, user) -> str
    Upserts a monthly spending limit for the user.
    budgets.period is always 'mes' (migrated from 'semana').
    Conflict key: (user_id, period).
"""
from app.db import client
    client.table("budgets").upsert({
        "user_id": user["id"],
        "period": "mes",
        "amount": amount,
    }, on_conflict="user_id,period").execute()
    formatted = "$" + f"{amount:,.0f}".replace(",", ".")
    return f"✓ Presupuesto mensual guardado: {formatted}"
