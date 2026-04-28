"""
Summary handler — DINERO feature.

Public API:
  get_week_summary(user) -> str
    Returns a formatted Spanish summary covering:
    • this-week totals by category (since last Monday)
    • month-to-date total and a projected monthly estimate
    • monthly budget remaining (if a budgets row exists for the user)

  aggregate_by_category(expenses) -> dict
    Helper: collapses a list of expense dicts into {category: total},
    sorted descending by total. Used by the dashboard API too.

  format_amount(amount) -> str
    Chilean-style "$1.234.567" formatting.
"""
from collections import defaultdict
from datetime import date, timedelta
from app.db import client


def format_amount(amount: float) -> str:
    return "$" + f"{amount:,.0f}".replace(",", ".")


def aggregate_by_category(expenses: list) -> dict:
    totals = defaultdict(float)
    for expense in expenses:
        totals[expense["category"]] += float(expense["amount"])
    return dict(sorted(totals.items(), key=lambda x: -x[1]))


def get_week_summary(user: dict) -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    window_start = min(monday, month_start)
    result = (
        client.table("expenses")
        .select("amount, category, date")
        .eq("user_id", user["id"])
        .gte("date", window_start.isoformat())
        .execute()
    )
    all_rows = result.data or []
    week_rows = [r for r in all_rows if r["date"] >= monday.isoformat()]
    month_rows = [r for r in all_rows if r["date"] >= month_start.isoformat()]

    if not week_rows:
        return "No hay gastos registrados esta semana."

    monthly_total = sum(float(r["amount"]) for r in month_rows)

    totals = aggregate_by_category(week_rows)

    name = user.get("name")
    header = f"*Resumen semana del {monday.strftime('%d/%m')}*"
    lines = [f"¡Hola {name}! {header}\n" if name else f"{header}\n"]
    for category, total in totals.items():
        lines.append(f"• {category}: {format_amount(total)}")

    grand_total = sum(totals.values())
    lines.append(f"\n*Total: {format_amount(grand_total)}*")

    days_in_month = ((month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - month_start).days
    monthly_estimate = (monthly_total / today.day) * days_in_month
    lines.append(
        f"_Este mes llevas {format_amount(monthly_total)}"
        f" (estimado mensual: {format_amount(monthly_estimate)})_"
    )

    budget_result = (
        client.table("budgets")
        .select("amount")
        .eq("user_id", user["id"])
        .eq("period", "mes")
        .execute()
    )
    if budget_result.data:
        limit = float(budget_result.data[0]["amount"])
        remaining = limit - monthly_total
        if remaining >= 0:
            lines.append(
                f"Presupuesto mes: {format_amount(limit)}"
                f" — te quedan {format_amount(remaining)}"
            )
        else:
            lines.append(
                f"⚠ Presupuesto mes: {format_amount(limit)}"
                f" — excedido por {format_amount(-remaining)}"
            )

    return "\n".join(lines)
