import re

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
        return f"Gasto recibido: ${amount:,.0f} — {description} (guardando...)"

    if SUMMARY_PATTERN.match(message):
        return "Resumen próximamente 📊"

    return (
        "No entendí ese mensaje.\n\n"
        "Puedes decirme cosas como:\n"
        "• _gasté 5000 en almuerzo_\n"
        "• _resumen_"
    )
