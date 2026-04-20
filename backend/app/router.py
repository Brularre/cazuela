import re
from datetime import date, timedelta
from app.db import client as db
from app.ai_router import classify
from app.handlers.expenses import save_expense
from app.handlers.expense_batch import (
    handle_batch_create,
    handle_batch_confirm,
    handle_batch_cancel,
)
from app.handlers.summary import get_week_summary
from app.handlers.todos import add_todo, list_todos, complete_todo
from app.handlers.shopping import add_to_shopping, list_shopping, check_item
from app.handlers.budget import set_budget
from app.handlers.waiting_on import add_waiting, list_waiting, resolve_waiting
from app.handlers.pantry import (
    add_pantry_item, list_pantry,
    consume_pantry_item, restock_pantry_item, restock_all_pantry,
)
from app.handlers.pantry_shopping import (
    handle_pantry_add_create,
    handle_pantry_add_confirm_despensa,
    handle_pantry_add_confirm_lista,
    handle_pantry_add_cancel,
)
from app.mcp import client as mcp

_DECIMAL_RE = re.compile(r'[.,]\d{1,2}$')

BATCH_EXPENSE_PATTERN = re.compile(
    r"^(?:gast[eé]?|pagu[eé])\s+([\d.,]+)\s+en\s+(?:el\s+)?s[uú]per(?:mercado)?[:]\s*(.+)$",
    re.IGNORECASE,
)


def _parse_clp_amount(raw: str) -> float | None:
    if _DECIMAL_RE.search(raw):
        return None
    return float(raw.replace(".", "").replace(",", ""))


EXPENSE_PATTERN = re.compile(
    r'^gast[eé]?\s+([\d.,]+)\s+(?:en\s+)?(.+)$',
    re.IGNORECASE
)
AMBIGUOUS_EXPENSE_PATTERN = re.compile(
    r'^pagu[eé]\s+([\d.,]+)(?:\s+(?:en\s+)?(.+))?$',
    re.IGNORECASE
)
SUMMARY_PATTERN = re.compile(r'^resumen', re.IGNORECASE)

TODO_ADD_PATTERN = re.compile(r'^(?:pendiente|tarea)[:\s]+(.+)$', re.IGNORECASE)
TODO_LIST_PATTERN = re.compile(r'^mis?\s+pendientes?$', re.IGNORECASE)
TODO_DONE_PATTERN = re.compile(r'^(?:listo|hice|complet[eé])[:\s]+(.+)$', re.IGNORECASE)

NECESITO_COMPRAR_PATTERN = re.compile(r'^necesito\s+comprar\s+(.+)$', re.IGNORECASE)
SHOPPING_ADD_PATTERN = re.compile(r'^(?:comprar|necesito)[:\s]+(.+)$', re.IGNORECASE)
SHOPPING_LIST_PATTERN = re.compile(r'^(?:lista\s+de\s+)?compras?$', re.IGNORECASE)
PANTRY_RESTOCK_PATTERN = re.compile(r'^compr[eé][:\s]+(.+)$', re.IGNORECASE)

BUDGET_SET_PATTERN = re.compile(
    r'^presupuesto\s+semana[:\s]+([\d.,]+)$', re.IGNORECASE
)

WAITING_ADD_PATTERN = re.compile(r'^esperando[:\s]+(.+)$', re.IGNORECASE)
WAITING_LIST_PATTERN = re.compile(r'^mis?\s+esperas?$', re.IGNORECASE)
WAITING_RESOLVE_PATTERN = re.compile(r'^lleg[oó][:\s]+(.+)$', re.IGNORECASE)

PANTRY_ADD_PATTERN = re.compile(
    r'^despensa(?:\s+(cocina|baño|otros))?[:\s]+(.+?)\s+(\d+)$',
    re.IGNORECASE
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
    "• _gasté 18000 en supermercado: pan, leche, queso, lavalozas_ — batch\n"
    "• _confirmar_ / _cancelar_ — responde cuando te pregunte\n"
    "• _resumen_ — resumen semanal\n\n"
    "*Presupuesto*\n"
    "• _presupuesto semana 150.000_\n"
    "• _presupuesto mes 500.000_\n\n"
    "*Pendientes*\n"
    "• _pendiente: llamar al banco_\n"
    "• _mis pendientes_\n"
    "• _listo: llamar al banco_\n\n"
    "*Compras*\n"
    "• _necesito comprar shampoo y balsamo_ — te pregunto dónde guardarlo\n"
    "• _comprar: leche_\n"
    "• _compras_ — ver lista\n"
    "• _compré leche_ — marcar como comprado\n\n"
    "*Esperando*\n"
    "• _esperando: respuesta del seguro_\n"
    "• _mis esperas_\n"
    "• _llegó: seguro_ — marcar como resuelto\n\n"
    "*Despensa*\n"
    "• _despensa cocina: arroz 3_ — agregar con categoría\n"
    "• _despensa: jabón 2_ — agregar (sin categoría → otros)\n"
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
    try:
        ctx = mcp.receive_result(context_id)
    except (ValueError, KeyError):
        return "Este gasto ya fue confirmado, cancelado, o expiró."
    if ctx.get("domain") == "expense_batch":
        return handle_batch_confirm(context_id, user)
    try:
        payload = ctx.get("payload", {})
        proposed = ctx.get("proposed", {})
        amount = payload.get("amount", 0)
        category = proposed.get("category", "otros")
        note = payload.get("raw_message", "")
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Este gasto ya fue confirmado, cancelado, o expiró."
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
    try:
        peek = mcp.receive_result(context_id)
    except (ValueError, KeyError):
        return "Este gasto ya fue confirmado, cancelado, o expiró."
    if peek.get("domain") == "expense_batch":
        return handle_batch_cancel(context_id, user)
    if peek.get("domain") == "pantry_add_batch":
        return handle_pantry_add_cancel(context_id, user)
    try:
        mcp.rollback(context_id)
    except ValueError:
        return "Este gasto ya fue confirmado, cancelado, o expiró."
    return "Gasto cancelado."


def _build_user_history(user_id: str) -> dict:
    since = str(date.today() - timedelta(days=30))
    result = db.table("expenses").select("category").eq("user_id", user_id).gte("date", since).execute()
    history = {}
    for row in (result.data or []):
        cat = row["category"]
        history[cat] = history.get(cat, 0) + 1
    return history


def _handle_ambiguous_expense(amount: float, raw_message: str, user: dict) -> str:
    context_id = mcp.send_context("expense", user["id"], {
        "raw_message": raw_message,
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


def _dispatch(intent: dict, raw_message: str, user: dict) -> str | None:
    name = intent.get("intent")
    if name == "add_expense":
        amount = intent.get("amount")
        description = intent.get("description")
        if amount is None or not description:
            return None
        return save_expense(amount, description, user)
    if name == "ambiguous_expense":
        amount = intent.get("amount")
        if amount is None:
            return None
        return _handle_ambiguous_expense(amount, raw_message, user)
    if name == "ambiguous_batch":
        amount = intent.get("amount")
        items_csv = intent.get("items_csv")
        if amount is None or not items_csv:
            return None
        _, reply = handle_batch_create(raw_message, float(amount), str(items_csv), user)
        return reply
    if name == "get_summary":
        return get_week_summary(user)
    if name == "set_budget":
        amount = intent.get("amount")
        if amount is None:
            return None
        return set_budget(amount, user)
    if name == "add_todo":
        task = intent.get("task")
        if not task:
            return None
        return add_todo(task, user, intent.get("priority", "semana"))
    if name == "list_todos":
        return list_todos(user)
    if name == "complete_todo":
        fragment = intent.get("task_fragment")
        if not fragment:
            return None
        return complete_todo(fragment, user)
    if name == "necesito_comprar":
        items_raw = intent.get("items_raw")
        if not items_raw:
            return None
        return handle_pantry_add_create(str(items_raw), user)
    if name == "add_to_shopping":
        item = intent.get("item")
        if not item:
            return None
        return add_to_shopping(item, user)
    if name == "list_shopping":
        return list_shopping(user)
    if name == "add_pantry_item":
        item = intent.get("item")
        qty = intent.get("qty")
        if not item or qty is None:
            return None
        return add_pantry_item(item, qty, user, intent.get("category", "otros"))
    if name == "list_pantry":
        return list_pantry(user)
    if name == "consume_pantry_item":
        fragment = intent.get("item_fragment")
        if not fragment:
            return None
        return consume_pantry_item(fragment, user)
    if name == "restock_pantry_item":
        fragment = intent.get("item_fragment")
        if not fragment:
            return None
        return restock_pantry_item(fragment, user)
    if name == "restock_all_pantry":
        return restock_all_pantry(user)
    if name == "add_waiting":
        description = intent.get("description")
        if not description:
            return None
        return add_waiting(description, user)
    if name == "list_waiting":
        return list_waiting(user)
    if name == "resolve_waiting":
        fragment = intent.get("fragment")
        if not fragment:
            return None
        return resolve_waiting(fragment, user)
    if name == "confirm":
        return _handle_confirm(user)
    if name == "cancel":
        return _handle_cancel(user)
    if name == "help":
        return HELP_TEXT
    return None


def route(message: str, user: dict) -> str:
    message = message.strip()

    match = BATCH_EXPENSE_PATTERN.match(message)
    if match:
        raw_amount = match.group(1)
        amount = _parse_clp_amount(raw_amount)
        if amount is None:
            return "Los montos van en pesos enteros. Ejemplo: _gasté 5000 en almuerzo_"
        items_csv = match.group(2).strip()
        _, reply = handle_batch_create(message, amount, items_csv, user)
        return reply

    if re.match(r'^(?:despensa|lista)$', message, re.IGNORECASE):
        pending_id = mcp.find_pending_for_user(user["id"])
        if pending_id:
            try:
                ctx = mcp.receive_result(pending_id)
                if ctx.get("domain") == "pantry_add_batch":
                    if message.lower() == "despensa":
                        return handle_pantry_add_confirm_despensa(pending_id, user)
                    return handle_pantry_add_confirm_lista(pending_id, user)
            except (ValueError, KeyError):
                pass

    intent = classify(message)
    if intent:
        try:
            result = _dispatch(intent, message, user)
            if result is not None:
                return result
        except Exception as e:
            import warnings
            warnings.warn(f"AI dispatch failed, falling back to regex: {e}")

    match = EXPENSE_PATTERN.match(message)
    if match:
        raw_amount, description = match.group(1), match.group(2).strip()
        amount = _parse_clp_amount(raw_amount)
        if amount is None:
            return "Los montos van en pesos enteros. Ejemplo: _gasté 5000 en almuerzo_"
        return save_expense(amount, description, user)

    match = AMBIGUOUS_EXPENSE_PATTERN.match(message)
    if match:
        raw_amount = match.group(1)
        amount = _parse_clp_amount(raw_amount)
        if amount is None:
            return "Los montos van en pesos enteros. Ejemplo: _pagué 5000_"
        description = match.group(2)
        if description:
            return save_expense(amount, description.strip(), user)
        return _handle_ambiguous_expense(amount, message, user)

    if SUMMARY_PATTERN.match(message):
        return get_week_summary(user)

    match = BUDGET_SET_PATTERN.match(message)
    if match:
        amount = _parse_clp_amount(match.group(1))
        if amount is None:
            return "Los montos van en pesos enteros. Ejemplo: _presupuesto semana 150.000_"
        return set_budget(amount, user)

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

    match = NECESITO_COMPRAR_PATTERN.match(message)
    if match:
        return handle_pantry_add_create(match.group(1).strip(), user)

    match = SHOPPING_ADD_PATTERN.match(message)
    if match:
        return add_to_shopping(match.group(1).strip(), user)

    if SHOPPING_LIST_PATTERN.match(message):
        return list_shopping(user)

    match = PANTRY_ADD_PATTERN.match(message)
    if match:
        category = (match.group(1) or "otros").lower()
        item = match.group(2).strip()
        qty = int(match.group(3))
        return add_pantry_item(item, qty, user, category)

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
        "• _comprar: leche_\n"
        "• _resumen_"
    )
