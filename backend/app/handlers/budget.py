"""
Budget handler — DINERO feature.

Public API:
  set_budget(amount, user) -> str
    Upserts a monthly spending limit for the user.
    budgets.period is always 'mes' (migrated from 'semana').
    Conflict key: (user_id, period).
"""
from app.db import client
from app.handlers.summary import format_amount


def set_budget(amount: float, user: dict) -> str:
    client.table("budgets").upsert({
        "user_id": user["id"],
        "period": "mes",
        "amount": amount,
    }, on_conflict="user_id,period").execute()
    formatted = format_amount(amount)
    return f"✓ Presupuesto mensual guardado: {formatted}"
