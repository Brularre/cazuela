import re
from datetime import date, timedelta
from app.db import client as db
from app.handlers.expenses import save_expense
from app.handlers.summary import get_week_summary
from app.handlers.todos import add_todo, list_todos, complete_todo
from app.handlers.wishlist import add_to_wishlist, list_wishlist
from app.handlers.shopping import add_to_shopping, list_shopping, check_item
from app.handlers.notes import add_note, list_notes, search_notes
from app.handlers.waiting_on import add_waiting, list_waiting, resolve_waiting
from app.handlers.pantry import (
    add_pantry_item, list_pantry,
    consume_pantry_item, restock_pantry_item, restock_all_pantry,
)
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
PANTRY_RESTOCK_PATTERN = re.compile(r'^compr[eé][:\s]+(.+)$', re.IGNORECASE)

NOTES_ADD_PATTERN = re.compile(r'^nota[:\s]+(.+)$', re.IGNORECASE)
NOTES_LIST_PATTERN = re.compile(r'^mis?\s+notas?$', re.IGNORECASE)
NOTES_SEARCH_PATTERN = re.compile(r'^buscar\s+notas?[:\s]+(.+)$', re.IGNORECASE)

WAITING_ADD_PATTERN = re.compile(r'^esperando[:\s]+(.+)$', re.IGNORECASE)
WAITING_LIST_PATTERN = re.compile(r'^mis?\s+esperas?$', re.IGNORECASE)
WAITING_RESOLVE_PATTERN = re.compile(r'^lleg[oó][:\s]+(.+)$', re.IGNORECASE)

PANTRY_ADD_PATTERN = re.compile(
    r'^despensa[:\s]+(.+?)\s+(\d+)$', re.IGNORECASE
)
PANTRY_LIST_PATTERN = re.compile(r'^mi\s+despensa$', re.IGNORECASE)
PANTRY_CONSUME_PATTERN = re.compile(r'^us[eé][:\s]+(.+)$', re.IGNORECASE)
PANTRY_RESTOCK_ALL_PATTERN = re.compile(r'^compr[eé]\s+todo$', re.IGNORECASE)

CONFIRM_PATTERN = re.compile(r'^confirmar$', re.IGNORECASE)
CANCEL_PATTERN = re.compile(r'^cancelar$', re.IGNORECASE)
HELP_PATTERN = re.compile(r'^ayuda$', re.IGNORECASE)

HELP_TEXT = (
    "*Comandos disponibles:*\n\n"
    "*Gastos*\n"
    "• _gasté 5000 en almuerzo_\n"
    "• _pagué 3000_ (sin categoría, te pregunto)\n"
    "• _confirmar_ / _cancelar_ — responde cuando te pregunte\n"
    "• _resumen_ — resumen semanal\n\n"
    "*Pendientes*\n"
    "• _pendiente: llamar al banco_\n"
    "• _mis pendientes_\n"
    "• _listo: llamar al banco_\n\n"
    "*Compras*\n"
    "• _comprar: leche_\n"
    "• _compras_ — ver lista\n"
    "• _compré leche_ — marcar como comprado\n\n"
    "*Deseos*\n"
    "• _quiero: zapatillas_\n"
    "• _mis deseos_\n\n"
    "*Notas*\n"
    "• _nota: compré flores hoy_\n"
    "• _mis notas_\n"
    "• _buscar nota: flores_\n\n"
    "*Esperando*\n"
    "• _esperando: respuesta del seguro_\n"
    "• _mis esperas_\n"
    "• _llegó: seguro_ — marcar como resuelto\n\n"
    "*Despensa*\n"
    "• _despensa: jabón 2_ — agregar con cantidad deseada\n"
    "• _mi despensa_ — ver stock\n"
    "• _usé: jabón_ — consumir uno\n"
    "• _compré: jabón_ — reponer uno\n"
    "• _compré todo_ — reponer todo lo que falta\n\n"
    "Escribe *ayuda* en cualquier momento para ver esto."
)


def _handle_confirm(user: dict) -> str:
    context_id = mcp.find_pending_for_user(user["id"])
    if not context_id:
        return "No tengo ningún gasto pendiente de confirmar."
    ctx = mcp.receive_result(context_id)
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


def _handle_cancel(user: dict) -> str:
    context_id = mcp.find_pending_for_user(user["id"])
    if not context_id:
        return "No tengo ningún gasto pendiente de cancelar."
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
        f"Responde *confirmar* o *cancelar*."
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
        task_raw = match.group(1).strip()
        priority = "semana"
        if re.match(r'^hoy[:\s]+', task_raw, re.IGNORECASE):
            task_raw = re.sub(r'^hoy[:\s]+', '', task_raw, flags=re.IGNORECASE).strip()
            priority = "hoy"
        elif re.match(r'^mes[:\s]+', task_raw, re.IGNORECASE):
            task_raw = re.sub(r'^mes[:\s]+', '', task_raw, flags=re.IGNORECASE).strip()
            priority = "mes"
        return add_todo(task_raw, user, priority)

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

    match = PANTRY_ADD_PATTERN.match(message)
    if match:
        item = match.group(1).strip()
        qty = int(match.group(2))
        return add_pantry_item(item, qty, user)

    if PANTRY_LIST_PATTERN.match(message):
        return list_pantry(user)

    match = PANTRY_CONSUME_PATTERN.match(message)
    if match:
        return consume_pantry_item(match.group(1).strip(), user)

    if PANTRY_RESTOCK_ALL_PATTERN.match(message):
        return restock_all_pantry(user)

    match = PANTRY_RESTOCK_PATTERN.match(message)
    if match:
        return restock_pantry_item(match.group(1).strip(), user)

    match = NOTES_ADD_PATTERN.match(message)
    if match:
        return add_note(match.group(1).strip(), user)

    if NOTES_LIST_PATTERN.match(message):
        return list_notes(user)

    match = NOTES_SEARCH_PATTERN.match(message)
    if match:
        return search_notes(match.group(1).strip(), user)

    match = WAITING_ADD_PATTERN.match(message)
    if match:
        return add_waiting(match.group(1).strip(), user)

    if WAITING_LIST_PATTERN.match(message):
        return list_waiting(user)

    match = WAITING_RESOLVE_PATTERN.match(message)
    if match:
        return resolve_waiting(match.group(1).strip(), user)

    if HELP_PATTERN.match(message):
        return HELP_TEXT

    if CONFIRM_PATTERN.match(message):
        return _handle_confirm(user)

    if CANCEL_PATTERN.match(message):
        return _handle_cancel(user)

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
