import re
from datetime import date, timedelta
from app.db import client as db
from app.handlers.expenses import save_expense
from app.handlers.summary import get_week_summary
from app.handlers.todos import add_todo, list_todos, complete_todo
from app.handlers.wishlist import add_to_wishlist, list_wishlist
from app.handlers.shopping import add_to_shopping, list_shopping, check_item
from app.mcp import client as mcp

EXPENSE_PATTERN = re.compile(
    r'^gast[eé]?\s+([\d.,]+)\s+(?:en\s+)?(.+)$',
    re.IGNORECASE
)
AMBIGUOUS_EXPENSE_PATTERN = re.compile(
    r'^pagu[eé]\s+([\d.,]+)',
    re.IGNORECASE
)
SUMMARY_PATTERN = re.compile(r'^resumen', re.IGNORECASE)

TODO_ADD_PATTERN = re.compile(r'^(?:pendiente|tarea)[:\s]+(.+)$', re.IGNORECASE)
TODO_LIST_PATTERN = re.compile(r'^mis?\s+pendientes?$', re.IGNORECASE)
TODO_DONE_PATTERN = re.compile(r'^(?:listo|hice|complet[eé])[:\s]+(.+)$', re.IGNORECASE)

WISHLIST_ADD_PATTERN = re.compile(
    r'^(?:quiero|deseo)[:\s]+(.+?)(?:\s+\$?([\d.,]+))?$', re.IGNORECASE
)
WISHLIST_LIST_PATTERN = re.compile(r'^mis?\s+deseos?$', re.IGNORECASE)

SHOPPING_ADD_PATTERN = re.compile(r'^(?:comprar|necesito)[:\s]+(.+)$', re.IGNORECASE)
SHOPPING_LIST_PATTERN = re.compile(r'^(?:lista\s+de\s+)?compras?$', re.IGNORECASE)
SHOPPING_CHECK_PATTERN = re.compile(r'^compr[eé][:\s]+(.+)$', re.IGNORECASE)

CONFIRM_PATTERN = re.compile(r'^confirmar\s+([a-f0-9]{8})', re.IGNORECASE)
CANCEL_PATTERN = re.compile(r'^cancelar\s+([a-f0-9]{8})', re.IGNORECASE)


def _handle_confirm(prefix: str, user: dict) -> str:
    context_id = mcp.find_by_prefix(prefix)
    if not context_id:
        return f"No encontré un contexto con código '{prefix}'."
    ctx = mcp.receive_result(context_id)
    if ctx.get("status") != "staged":
        return "Ese contexto ya fue procesado."
    payload = ctx.get("payload", {})
    proposed = ctx.get("proposed", {})
    amount = payload.get("amount", 0)
    category = proposed.get("category", "otros")
    note = payload.get("raw_message", "")
    mcp.confirm(context_id)
    db.table("expenses").insert({
        "user_id": user["id"],
        "amount": amount,
        "category": category,
        "note": note,
        "date": str(date.today()),
    }).execute()
    formatted = "$" + f"{amount:,.0f}".replace(",", ".")
    return f"✓ Gasto guardado\n{formatted} · {category}"


def _handle_cancel(prefix: str) -> str:
    context_id = mcp.find_by_prefix(prefix)
    if not context_id:
        return f"No encontré un contexto con código '{prefix}'."
    mcp.rollback(context_id)
    return "Gasto cancelado."


def _build_user_history(user_id: str) -> dict:
    since = str(date.today() - timedelta(days=30))
    result = db.table("expenses").select("category").eq("user_id", user_id).gte("date", since).execute()
    history = {}
    for row in (result.data or []):
        cat = row["category"]
        history[cat] = history.get(cat, 0) + 1
    return history


def _handle_ambiguous_expense(amount: float, user: dict) -> str:
    context_id = mcp.send_context("expense", user["id"], {
        "raw_message": f"pagué {amount}",
        "amount": amount,
        "date": str(date.today()),
        "note": None,
        "user_history": _build_user_history(user["id"]),
    })
    result = mcp.request_action(context_id)
    proposed = result.get("proposed", {})
    category = proposed.get("category", "otros")
    reasoning = proposed.get("reasoning", "")
    return (
        f"¿Es un gasto de *{category}*?\n"
        f"_{reasoning}_\n\n"
        f"Contexto guardado: `{context_id[:8]}`\n"
        f"Responde 'confirmar {context_id[:8]}' o 'cancelar {context_id[:8]}'"
    )


def route(message: str, user: dict) -> str:
    message = message.strip()

    match = EXPENSE_PATTERN.match(message)
    if match:
        raw_amount, description = match.group(1), match.group(2).strip()
        amount = float(raw_amount.replace(".", "").replace(",", "."))
        return save_expense(amount, description, user)

    match = AMBIGUOUS_EXPENSE_PATTERN.match(message)
    if match:
        raw_amount = match.group(1)
        amount = float(raw_amount.replace(".", "").replace(",", "."))
        return _handle_ambiguous_expense(amount, user)

    if SUMMARY_PATTERN.match(message):
        return get_week_summary(user)

    match = TODO_ADD_PATTERN.match(message)
    if match:
        return add_todo(match.group(1).strip(), user)

    if TODO_LIST_PATTERN.match(message):
        return list_todos(user)

    match = TODO_DONE_PATTERN.match(message)
    if match:
        return complete_todo(match.group(1).strip(), user)

    match = WISHLIST_ADD_PATTERN.match(message)
    if match:
        item = match.group(1).strip()
        price_str = match.group(2)
        price = float(price_str.replace(".", "").replace(",", ".")) if price_str else None
        return add_to_wishlist(item, user, price)

    if WISHLIST_LIST_PATTERN.match(message):
        return list_wishlist(user)

    match = SHOPPING_ADD_PATTERN.match(message)
    if match:
        return add_to_shopping(match.group(1).strip(), user)

    if SHOPPING_LIST_PATTERN.match(message):
        return list_shopping(user)

    match = SHOPPING_CHECK_PATTERN.match(message)
    if match:
        return check_item(match.group(1).strip(), user)

    match = CONFIRM_PATTERN.match(message)
    if match:
        return _handle_confirm(match.group(1).lower(), user)

    match = CANCEL_PATTERN.match(message)
    if match:
        return _handle_cancel(match.group(1).lower())

    return (
        "No entendí ese mensaje.\n\n"
        "Puedes decirme cosas como:\n"
        "• _gasté 5000 en almuerzo_\n"
        "• _pagué 3000_ (gasto sin categoría)\n"
        "• _pendiente: llamar al banco_\n"
        "• _quiero: zapatillas_\n"
        "• _comprar: leche_\n"
        "• _resumen_"
    )
