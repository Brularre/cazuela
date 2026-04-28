"""
WhatsApp message router — entry point is route(message, user).

Routing order:
  1. Batch expense shortcut (regex, fast path)
  2. Pantry-add despensa/lista shortcuts (requires pending MCP context)
  3. Confirm/cancel shortcuts (sí/no/ok/…)
  4. AI classify → _dispatch (returns None on miss → fallthrough)
  5. Manual regex chain (all intents, in priority order)
  6. Fallback hint

See patterns.py for all compiled regexes.
See dispatch.py for helpers, _dispatch, and handler imports.
See copy.py for HELP_TEXT, WELCOME_TEXT, and static strings.
"""
import re
import warnings

from app.patterns import (
    _DECIMAL_RE,
    BATCH_EXPENSE_PATTERN,
    CONFIRM_SHORTCUT_PATTERN,
    CANCEL_SHORTCUT_PATTERN,
    EXPENSE_PATTERN,
    AMBIGUOUS_EXPENSE_PATTERN,
    SUMMARY_PATTERN,
    BUDGET_SET_PATTERN,
    TODO_ADD_PATTERN,
    TODO_LIST_PATTERN,
    TODO_DONE_PATTERN,
    TODO_DELETE_PATTERN,
    NECESITO_COMPRAR_PATTERN,
    SHOPPING_ADD_PATTERN,
    SHOPPING_LIST_PATTERN,
    PANTRY_ADD_PATTERN,
    PANTRY_LIST_PATTERN,
    PANTRY_CONSUME_PATTERN,
    PANTRY_SET_STOCK_PATTERN,
    PANTRY_SET_STOCK_QTY_LAST_PATTERN,
    PANTRY_RESTOCK_ALL_PATTERN,
    PANTRY_RESTOCK_PATTERN,
    WAITING_ADD_PATTERN,
    WAITING_LIST_PATTERN,
    WAITING_RESOLVE_PATTERN,
    RECIPE_NEW_PATTERN,
    RECIPE_LIST_PATTERN,
    RECIPE_SHOW_PATTERN,
    RECIPE_MATCH_PATTERN,
    RECIPE_SUGGEST_PATTERN,
    RECIPE_CHOOSE_PATTERN,
    ME_LLAMO_PATTERN,
    TABLERO_PATTERN,
    HELP_PATTERN,
    CONFIRM_PATTERN,
    CANCEL_PATTERN,
)
from app.copy import HELP_TEXT, WELCOME_TEXT, _CATEGORY_PROMPT  # noqa: F401 (WELCOME_TEXT re-exported for main.py)
from app.ai_router import classify
from app.dispatch import (
    _dispatch,
    _handle_confirm,
    _handle_cancel,
    _handle_bought,
    _handle_set_name,
    _dashboard_reply,
    _hint_for_message,
    _handle_pantry_category_choice,
    _handle_ambiguous_expense,
    save_expense,
    handle_batch_create,
    get_week_summary,
    set_budget,
    add_todo,
    list_todos,
    complete_todo,
    delete_todo,
    add_to_shopping,
    list_shopping,
    handle_pantry_add_create,
    handle_pantry_add_confirm_despensa,
    handle_pantry_add_confirm_lista,
    add_pantry_item,
    list_pantry,
    consume_pantry_item,
    set_pantry_stock,
    restock_all_pantry,
    add_waiting,
    list_waiting,
    resolve_waiting,
    nueva_receta,
    list_recipes,
    show_recipe,
    que_puedo_hacer,
    sugerir_recetas,
    elegir_receta,
)
from app.mcp import client as mcp


def _parse_clp_amount(raw: str) -> float | None:
    if _DECIMAL_RE.search(raw):
        return None
    return float(raw.replace(".", "").replace(",", ""))


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

    if CONFIRM_SHORTCUT_PATTERN.match(message) and mcp.find_pending_for_user(user["id"]):
        return _handle_confirm(user)

    if CANCEL_SHORTCUT_PATTERN.match(message) and mcp.find_pending_for_user(user["id"]):
        return _handle_cancel(user)

    intent = classify(message)
    if intent:
        try:
            result = _dispatch(intent, message, user)
            if result is not None:
                return result
        except Exception as e:
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
            return "Los montos van en pesos enteros. Ejemplo: _presupuesto 600.000_"
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

    match = TODO_DELETE_PATTERN.match(message)
    if match:
        return delete_todo(match.group(1).strip(), user)

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
        category_raw = match.group(1)
        item = match.group(2).strip()
        qty = int(match.group(3))
        if category_raw:
            return add_pantry_item(item, qty, user, category_raw.lower())
        mcp.send_context("pantry_add_category", user["id"], {"item": item, "qty": qty})
        return _CATEGORY_PROMPT

    if PANTRY_LIST_PATTERN.match(message):
        return list_pantry(user)

    match = PANTRY_CONSUME_PATTERN.match(message)
    if match:
        return consume_pantry_item(match.group(1).strip(), user)

    match = PANTRY_SET_STOCK_PATTERN.match(message)
    if match:
        return set_pantry_stock(match.group(2).strip(), int(match.group(1)), user)

    match = PANTRY_SET_STOCK_QTY_LAST_PATTERN.match(message)
    if match:
        return set_pantry_stock(match.group(1).strip(), int(match.group(2)), user)

    if PANTRY_RESTOCK_ALL_PATTERN.match(message):
        return restock_all_pantry(user)

    match = PANTRY_RESTOCK_PATTERN.match(message)
    if match:
        fragment = match.group(1).strip()
        qty_str = match.group(2)
        return _handle_bought(fragment, user, int(qty_str) if qty_str else None)

    match = WAITING_ADD_PATTERN.match(message)
    if match:
        return add_waiting(match.group(1).strip(), user)

    if WAITING_LIST_PATTERN.match(message):
        return list_waiting(user)

    match = WAITING_RESOLVE_PATTERN.match(message)
    if match:
        fragment = re.sub(r'^(?:el|la|los|las)\s+', '', match.group(1).strip(), flags=re.IGNORECASE)
        return resolve_waiting(fragment, user)

    match = RECIPE_NEW_PATTERN.match(message)
    if match:
        return nueva_receta(match.group(1).strip(), user)

    if RECIPE_LIST_PATTERN.match(message):
        return list_recipes(user)

    match = RECIPE_SHOW_PATTERN.match(message)
    if match:
        fragment = re.sub(r'^de\s+', '', match.group(1).strip(), flags=re.IGNORECASE)
        return show_recipe(fragment, user)

    if RECIPE_MATCH_PATTERN.match(message):
        return que_puedo_hacer(user)

    if RECIPE_SUGGEST_PATTERN.match(message):
        return sugerir_recetas(user)

    match = RECIPE_CHOOSE_PATTERN.match(message)
    if match:
        n = int(match.group(1))
        pending_id = mcp.find_pending_for_user(user["id"])
        if pending_id:
            try:
                ctx_data = mcp.receive_result(pending_id)
                if ctx_data.get("domain") == "pantry_add_category":
                    return _handle_pantry_category_choice(n, pending_id, user, ctx_data)
            except (ValueError, KeyError):
                pass
        return elegir_receta(n, user)

    match = ME_LLAMO_PATTERN.match(message)
    if match:
        return _handle_set_name(match.group(1), user)

    if TABLERO_PATTERN.match(message):
        return _dashboard_reply()

    if HELP_PATTERN.match(message):
        return HELP_TEXT

    if CONFIRM_PATTERN.match(message):
        return _handle_confirm(user)

    if CANCEL_PATTERN.match(message):
        return _handle_cancel(user)

    return _hint_for_message(message)
