"""
Routing helpers and AI intent dispatcher — called by router.route().

Private helpers:
  _handle_set_name(name, user) -> str
  _handle_pantry_category_choice(n, context_id, user, ctx_data) -> str
  _hint_for_message(message) -> str
  _handle_bought(fragment, user, qty=None) -> str
  _handle_confirm(user) -> str
  _handle_cancel(user) -> str
  _handle_ambiguous_expense(amount, raw_message, user) -> str
  _dashboard_reply() -> str

AI dispatch:
  _dispatch(intent, raw_message, user) -> str | None
    Maps AI-classified intent dicts to handler calls.
    Returns None if the intent is unrecognised or required fields are
    missing; router.route() then falls through to manual regex matching.

Handler re-exports (used directly by router.route()):
  save_expense, handle_batch_create, get_week_summary, set_budget,
  add_todo, list_todos, complete_todo, delete_todo,
  add_to_shopping, list_shopping,
  handle_pantry_add_create, handle_pantry_add_confirm_despensa,
  handle_pantry_add_confirm_lista, handle_pantry_add_cancel,
  add_pantry_item, list_pantry, consume_pantry_item, set_pantry_stock,
  restock_all_pantry,
  add_waiting, list_waiting, resolve_waiting,
  nueva_receta, list_recipes, show_recipe, que_puedo_hacer,
  sugerir_recetas, elegir_receta,
"""
import warnings
from datetime import date

from app.db import client as db
from app.ai_router import classify
from app.copy import HELP_TEXT, _PANTRY_CATEGORIES, _CATEGORY_PROMPT
from app.config import settings
from app.mcp import client as mcp
from app.handlers.expenses import expense_history, save_expense
from app.handlers.expense_batch import (
    handle_batch_create,
    handle_batch_confirm,
    handle_batch_cancel,
)
from app.handlers.summary import format_amount, get_week_summary
from app.handlers.todos import add_todo, list_todos, complete_todo, delete_todo
from app.handlers.shopping import add_to_shopping, list_shopping, check_item
from app.handlers.budget import set_budget
from app.handlers.waiting_on import add_waiting, list_waiting, resolve_waiting
from app.handlers.pantry import (
    add_pantry_item,
    list_pantry,
    consume_pantry_item,
    restock_pantry_item,
    restock_all_pantry,
    set_pantry_stock,
)
from app.handlers.pantry_shopping import (
    handle_pantry_add_create,
    handle_pantry_add_confirm_despensa,
    handle_pantry_add_confirm_lista,
    handle_pantry_add_cancel,
)
from app.handlers.recipes import (
    nueva_receta,
    confirm_recipe_create,
    cancel_recipe_create,
    list_recipes,
    show_recipe,
    que_puedo_hacer,
    sugerir_recetas,
    elegir_receta,
    confirm_shopping_add,
    cancel_shopping_add,
)


def _handle_set_name(name: str, user: dict) -> str:
    clean = name.strip()
    if not clean:
        return "No entendí el nombre."
    db.table("users").update({"name": clean}).eq("id", user["id"]).execute()
    return f"¡Listo, {clean}!"


def _handle_pantry_category_choice(n: int, context_id: str, user: dict, ctx_data: dict) -> str:
    category = _PANTRY_CATEGORIES.get(n)
    if not category:
        return "Elige _elegir 1_ (Cocina), _elegir 2_ (Baño) o _elegir 3_ (Otros)."
    payload = ctx_data.get("payload", {})
    item = payload.get("item", "")
    qty = payload.get("qty", 1)
    try:
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        pass
    return add_pantry_item(item, qty, user, category)


def _hint_for_message(message: str) -> str:
    first = message.strip().split()[0].lower() if message.strip().split() else ""
    if first and first[0].isdigit():
        return "No entendí ese mensaje. ¿Querías registrar un gasto? Prueba _gasté [monto] en [descripción]_."
    if first in ("quiero", "tengo", "necesito", "hay"):
        return "No entendí ese mensaje. ¿Querías agregar un pendiente? Prueba _pendiente [tarea]_."
    return "No entendí ese mensaje. Escribe *ayuda* para ver los comandos disponibles."


def _handle_bought(fragment: str, user: dict, qty: int | None = None) -> str:
    results = []
    for result in (check_item(fragment, user), restock_pantry_item(fragment, user, qty)):
        if result and (not result.startswith("No encontré") or "Quisiste decir" in result):
            results.append(result)
    if results:
        return "\n".join(results)
    return f"No encontré '{fragment}' en tu lista ni en tu despensa."


def _handle_confirm(user: dict) -> str:
    context_id = mcp.find_pending_for_user(user["id"])
    if not context_id:
        return "No tengo ninguna operación pendiente de confirmar."
    try:
        ctx = mcp.receive_result(context_id)
    except (ValueError, KeyError):
        return "Esta operación ya fue confirmada, cancelada, o expiró."
    if ctx.get("domain") == "recipe_create":
        return confirm_recipe_create(context_id, user, ctx)
    if ctx.get("domain") == "expense_batch":
        return handle_batch_confirm(context_id, user)
    if ctx.get("domain") == "shopping_add_pending":
        return confirm_shopping_add(context_id, user, ctx)
    if ctx.get("domain") in ("recipe_match", "recipe_suggest"):
        n = len((ctx.get("proposed") or {}).get("suggestions", []))
        return f"Elige una opción del 1 al {n} con *elegir N*, o *cancelar*."
    payload = ctx.get("payload", {})
    proposed = ctx.get("proposed", {})
    amount = payload.get("amount", 0)
    category = proposed.get("category", "otros")
    note = payload.get("raw_message", "")
    try:
        db.table("expenses").insert({
            "user_id": user["id"],
            "amount": amount,
            "category": category,
            "note": note,
            "date": str(date.today()),
        }).execute()
    except Exception as e:
        warnings.warn(f"Expense insert failed for context {context_id}: {e}")
        return "Hubo un problema al guardar el gasto. Intenta _confirmar_ de nuevo."
    try:
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Este gasto ya fue confirmado, cancelado, o expiró."
    return f"✓ Gasto guardado\n{format_amount(amount)} · {category}"


def _handle_cancel(user: dict) -> str:
    context_id = mcp.find_pending_for_user(user["id"])
    if not context_id:
        return "No tengo ninguna operación pendiente de cancelar."
    try:
        peek = mcp.receive_result(context_id)
    except (ValueError, KeyError):
        return "Este gasto ya fue confirmado, cancelado, o expiró."
    if peek.get("domain") == "expense_batch":
        return handle_batch_cancel(context_id, user)
    if peek.get("domain") == "pantry_add_batch":
        return handle_pantry_add_cancel(context_id, user)
    if peek.get("domain") == "recipe_create":
        return cancel_recipe_create(context_id, user)
    if peek.get("domain") == "shopping_add_pending":
        return cancel_shopping_add(context_id, user)
    if peek.get("domain") in ("recipe_match", "recipe_suggest"):
        try:
            mcp.rollback(context_id)
        except ValueError:
            return "Esta operación ya fue confirmada, cancelada, o expiró."
        return "Sugerencias canceladas."
    try:
        mcp.rollback(context_id)
    except ValueError:
        return "Esta operación ya fue confirmada, cancelada, o expiró."
    return "Operación cancelada."


def _handle_ambiguous_expense(amount: float, raw_message: str, user: dict) -> str:
    context_id = mcp.send_context("expense", user["id"], {
        "raw_message": raw_message,
        "amount": amount,
        "date": str(date.today()),
        "note": None,
        "user_history": expense_history(user["id"]),
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


def _dashboard_reply() -> str:
    url = settings.dashboard_url
    return f"🔗 {url}" if url else "Tu tablero no tiene URL configurada aún."


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
    if name == "check_shopping":
        fragment = intent.get("item_fragment")
        if not fragment:
            return None
        return _handle_bought(fragment, user)
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
    if name == "recipe_new":
        recipe_name = intent.get("name")
        if not recipe_name:
            return None
        return nueva_receta(str(recipe_name), user)
    if name == "recipe_list":
        return list_recipes(user)
    if name == "recipe_show":
        fragment = intent.get("name_fragment")
        if not fragment:
            return None
        return show_recipe(str(fragment), user)
    if name == "tablero":
        return _dashboard_reply()
    if name == "set_name":
        name_val = intent.get("name")
        if not name_val:
            return None
        return _handle_set_name(str(name_val), user)
    return None
