from collections import defaultdict
from datetime import date, timedelta
from app.db import client


def format_amount(amount: float) -> str:
    return "$" + f"{amount:,.0f}".replace(",", ".")


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

    totals: dict[str, float] = defaultdict(float)
    for expense in result.data:
        totals[expense["category"]] += float(expense["amount"])

    lines = [f"*Resumen semana del {monday.strftime('%d/%m')}*\n"]
    for category, total in sorted(totals.items(), key=lambda x: -x[1]):
        lines.append(f"• {category}: {format_amount(total)}")

    grand_total = sum(totals.values())
    lines.append(f"\n*Total: {format_amount(grand_total)}*")

    return "\n".join(lines)
