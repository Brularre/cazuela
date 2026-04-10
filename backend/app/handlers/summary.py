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

    result = (
        client.table("expenses")
        .select("amount, category")
        .eq("user_id", user["id"])
        .gte("date", monday.isoformat())
        .execute()
    )

    if not result.data:
        return "No hay gastos registrados esta semana."

    totals = aggregate_by_category(result.data)

    lines = [f"*Resumen semana del {monday.strftime('%d/%m')}*\n"]
    for category, total in totals.items():
        lines.append(f"• {category}: {format_amount(total)}")

    grand_total = sum(totals.values())
    lines.append(f"\n*Total: {format_amount(grand_total)}*")

    return "\n".join(lines)
