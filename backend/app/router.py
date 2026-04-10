import re
from app.handlers.expenses import save_expense
from app.handlers.summary import get_week_summary

EXPENSE_PATTERN = re.compile(
    r'^gast[eé]?\s+([\d.,]+)\s+(?:en\s+)?(.+)$',
    re.IGNORECASE
)

SUMMARY_PATTERN = re.compile(
    r'^resumen',
    re.IGNORECASE
)


def route(message: str, user: dict) -> str:
    message = message.strip()

    match = EXPENSE_PATTERN.match(message)
    if match:
        raw_amount, description = match.group(1), match.group(2).strip()
        amount = float(raw_amount.replace(".", "").replace(",", "."))
        return save_expense(amount, description, user)

    if SUMMARY_PATTERN.match(message):
        return get_week_summary(user)

    return (
        "No entendí ese mensaje.\n\n"
        "Puedes decirme cosas como:\n"
        "• _gasté 5000 en almuerzo_\n"
        "• _resumen_"
    )
