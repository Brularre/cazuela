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

    result = (
        client.table("expenses")
        .select("amount, category")
        .eq("user_id", user["id"])
        .gte("date", monday.isoformat())
        .execute()
    )

    month_result = (
        client.table("expenses")
        .select("amount")
        .eq("user_id", user["id"])
        .gte("date", month_start.isoformat())
        .execute()
    )

    if not result.data:
        return "No hay gastos registrados esta semana."

    monthly_total = sum(float(r["amount"]) for r in (month_result.data or []))

    totals = aggregate_by_category(result.data)

    name = user.get("name")
    header = f"*Resumen semana del {monday.strftime('%d/%m')}*"
    lines = [f"¡Hola {name}! {header}\n" if name else f"{header}\n"]
    for category, total in totals.items():
        lines.append(f"• {category}: {format_amount(total)}")

    grand_total = sum(totals.values())
    lines.append(f"\n*Total: {format_amount(grand_total)}*")

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

    days_in_month = ((month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - month_start).days
    monthly_estimate = (monthly_total / today.day) * days_in_month
    lines.append(
        f"_Este mes llevas {format_amount(monthly_total)}"
        f" (estimado mensual: {format_amount(monthly_estimate)})_"
    )

    return "\n".join(lines)
