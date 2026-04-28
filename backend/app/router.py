import re
import warnings
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
from app.handlers.todos import add_todo, list_todos, complete_todo, delete_todo
from app.handlers.shopping import add_to_shopping, list_shopping, check_item
from app.handlers.budget import set_budget
from app.handlers.waiting_on import add_waiting, list_waiting, resolve_waiting
from app.handlers.pantry import (
    add_pantry_item, list_pantry,
    consume_pantry_item, restock_pantry_item, restock_all_pantry,
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
from app.config import settings
from app.mcp import client as mcp

_DECIMAL_RE = re.compile(r'[.,]\d{1,2}$')

BATCH_EXPENSE_PATTERN = re.compile(
    r"^(?:gast[eé]|pagu[eé])\s+([\d.,]+)\s+en\s+(?:el\s+)?s[uú]per(?:mercado)?[:\s]+(.+)$",
    re.IGNORECASE,
)


def _parse_clp_amount(raw: str) -> float | None:
    if _DECIMAL_RE.search(raw):
        return None
    return float(raw.replace(".", "").replace(",", ""))


EXPENSE_PATTERN = re.compile(
    r'^gast[eé]\s+([\d.,]+)\s+(?:en\s+)?(.+)$',
    re.IGNORECASE
)
AMBIGUOUS_EXPENSE_PATTERN = re.compile(
    r'^pagu[eé]\s+([\d.,]+)(?:\s+(?:en\s+)?(.+))?$',
    re.IGNORECASE
)
SUMMARY_PATTERN = re.compile(r'^resumen(?:\s+.*)?$', re.IGNORECASE)

TODO_ADD_PATTERN = re.compile(r'^(?:pendiente|tarea)[:\s]+(.+)$', re.IGNORECASE)
TODO_LIST_PATTERN = re.compile(r'^mis?\s+pendientes?$', re.IGNORECASE)
TODO_DONE_PATTERN = re.compile(r'^(?:listo|hice|complet[eé])[:\s]+(.+)$', re.IGNORECASE)
TODO_DELETE_PATTERN = re.compile(r'^borrar\s+pendiente[:\s]+(.+)$', re.IGNORECASE)

NECESITO_COMPRAR_PATTERN = re.compile(r'^necesito\s+comprar\s+(.+)$', re.IGNORECASE)
SHOPPING_ADD_PATTERN = re.compile(r'^(?:comprar|necesito)[:\s]+(.+)$', re.IGNORECASE)
SHOPPING_LIST_PATTERN = re.compile(r'^(?:lista\s+de\s+)?compras?$', re.IGNORECASE)
PANTRY_RESTOCK_PATTERN = re.compile(r'^compr[eé][:\s]+(.+?)(?:\s+(\d+))?$', re.IGNORECASE)

BUDGET_SET_PATTERN = re.compile(
    r'^presupuesto[:\s]+([\d.,]+)$', re.IGNORECASE
)

WAITING_ADD_PATTERN = re.compile(r'^esperando[:\s]+(.+)$', re.IGNORECASE)
WAITING_LIST_PATTERN = re.compile(r'^(?:mis?\s+esperas?|qué\s+espero|que\s+espero|ver\s+esperas?)$', re.IGNORECASE)
WAITING_RESOLVE_PATTERN = re.compile(r'^lleg[oó][:\s]+(.+)$', re.IGNORECASE)

PANTRY_ADD_PATTERN = re.compile(
    r'^despensa(?:\s+(cocina|baño|otros))?[:\s]+(.+?)\s+(\d+)$',
    re.IGNORECASE
)
PANTRY_LIST_PATTERN = re.compile(r'^mi\s+despensa$', re.IGNORECASE)
PANTRY_SET_STOCK_PATTERN = re.compile(r'^stock\s+(\d+)\s+(.+)$', re.IGNORECASE)
PANTRY_SET_STOCK_QTY_LAST_PATTERN = re.compile(r'^stock\s+(.+?)\s+(\d+)$', re.IGNORECASE)
PANTRY_CONSUME_PATTERN = re.compile(r'^us[eé][:\s]+(.+)$', re.IGNORECASE)
PANTRY_RESTOCK_ALL_PATTERN = re.compile(r'^compr[eé]\s+todo$', re.IGNORECASE)

CONFIRM_PATTERN = re.compile(r'^confirmar$', re.IGNORECASE)
CANCEL_PATTERN = re.compile(r'^cancelar$', re.IGNORECASE)
CONFIRM_SHORTCUT_PATTERN = re.compile(r'^(?:s[ií]|ok|dale|va|listo)$', re.IGNORECASE)
CANCEL_SHORTCUT_PATTERN = re.compile(r'^(?:no|nope|olvídalo|olvidalo)$', re.IGNORECASE)
HELP_PATTERN = re.compile(r'^ayuda\b', re.IGNORECASE)
TABLERO_PATTERN = re.compile(r'^(?:mi\s+)?tablero$', re.IGNORECASE)
ME_LLAMO_PATTERN = re.compile(r'^me\s+llamo\s+(.+)$', re.IGNORECASE)

RECIPE_NEW_PATTERN = re.compile(
    r'^nueva\s+receta[:\s]+(.+)$', re.IGNORECASE
)
RECIPE_LIST_PATTERN = re.compile(r'^mis?\s+recetas?$', re.IGNORECASE)
RECIPE_SHOW_PATTERN = re.compile(r'^receta[:\s]+(.+)$', re.IGNORECASE)
RECIPE_MATCH_PATTERN = re.compile(
    r'^(?:qué|que)\s+puedo\s+hacer\??$', re.IGNORECASE
)
RECIPE_SUGGEST_PATTERN = re.compile(
    r'^(?:(?:qué|que)\s+cocino|sugiéreme\s+recetas?|sugierme\s+recetas?)\??$',
    re.IGNORECASE,
)
RECIPE_CHOOSE_PATTERN = re.compile(r'^elegir\s+(\d+)$', re.IGNORECASE)

HELP_TEXT = (
    "*Comandos disponibles:*\n\n"
    "*Gastos*\n"
    "• _gasté 5000 en almuerzo_\n"
    "• _pagué 3000_ (sin categoría, te pregunto)\n"
    "• _gasté 18000 en supermercado pan, leche, queso, lavalozas_ — batch\n"
    "• _confirmar_ / _cancelar_ — responde cuando te pregunte\n"
    "• _resumen_ — resumen semanal\n\n"
    "*Presupuesto*\n"
    "• _presupuesto 600.000_\n\n"
    "*Pendientes*\n"
    "• _pendiente llamar al banco_\n"
    "• _mis pendientes_\n"
    "• _listo: llamar al banco_\n"
    "• _borrar pendiente llamar al banco_\n\n"
    "*Compras*\n"
    "• _necesito comprar shampoo y balsamo_ — te pregunto dónde guardarlo\n"
    "• _comprar leche_\n"
    "• _compras_ — ver lista\n"
    "• _compré leche_ — marcar como comprado\n\n"
    "*Esperando*\n"
    "• _esperando respuesta del seguro_\n"
    "• _mis esperas_\n"
    "• _llegó seguro_ — marcar como resuelto\n\n"
    "*Despensa*\n"
    "• _despensa cocina arroz 3_ — agregar con categoría\n"
    "• _despensa jabón 2_ — agregar (sin categoría → otros)\n"
    "• _mi despensa_ — ver stock\n"
    "• _usé jabón_ — consumir uno\n"
    "• _compré jabón_ — reponer uno\n"
    "• _compré jabón 3_ — reponer sumando 3\n"
    "• _stock 2 jabón_ o _stock jabón 2_ — fijar stock exacto\n"
    "• _compré todo_ — reponer todo lo que falta\n\n"
    "*Recetas*\n"
    "• _nueva receta: cazuela_ — crear receta (con IA si está activa)\n"
    "• _mis recetas_ — ver todas\n"
    "• _receta cazuela_ — ver ingredientes\n"
    "• _qué puedo hacer_ — recetas con lo que tienes en tu despensa\n"
    "• _qué cocino_ — sugerencias de nuevas recetas con IA\n"
    "• _elegir 2_ — elegir una sugerencia después de pedirlas\n\n"
    "Escribe *ayuda* en cualquier momento para ver esto.\n\n"
    "*Tu perfil*\n"
    "• _me llamo Bruno_ — guardar tu nombre\n\n"
    "*Tablero*\n"
    "• _tablero_ — link al dashboard web"
)

WELCOME_TEXT = (
    "¡Hola! Soy Cazuela, tu asistente personal por WhatsApp.\n\n"
    "*Lo que puedo hacer:*\n"
    "• *Gastos* — _gasté 5000 en almuerzo_ · _resumen_\n"
    "• *Presupuesto* — _presupuesto 600.000_\n"
    "• *Pendientes* — _pendiente llamar al banco_\n"
    "• *Lista de compras* — _comprar leche_\n"
    "• *Esperando* — _esperando respuesta del seguro_\n"
    "• *Despensa* — _despensa cocina arroz 3_\n"
    "• *Recetas* — _nueva receta: cazuela_\n"
    "• *Tablero web* — _tablero_\n\n"
    "Escribe *ayuda* para ver todos los comandos.\n\n"
    "¿Cómo te llamo? Escribe *me llamo [tu nombre]* para que te recuerde."
)


def _handle_set_name(name: str, user: dict) -> str:
    clean = name.strip()
    if not clean:
        return "No entendí el nombre."
    db.table("users").update({"name": clean}).eq("id", user["id"]).execute()
    return f"¡Listo, {clean}!"


_PANTRY_CATEGORIES = {1: "cocina", 2: "baño", 3: "otros"}

_CATEGORY_PROMPT = (
    "¿En qué categoría?\n"
    "_elegir 1_ Cocina · _elegir 2_ Baño · _elegir 3_ Otros\n"
    "O _cancelar_ para no guardar."
)


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
    formatted = "$" + f"{amount:,.0f}".replace(",", ".")
    return f"✓ Gasto guardado\n{formatted} · {category}"


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
        url = settings.dashboard_url or "Tu tablero no tiene URL configurada aún."
        return f"🔗 {url}" if settings.dashboard_url else url
    if name == "set_name":
        name_val = intent.get("name")
        if not name_val:
            return None
        return _handle_set_name(str(name_val), user)
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
        url = settings.dashboard_url or "Tu tablero no tiene URL configurada aún."
        return f"🔗 {url}" if settings.dashboard_url else url

    if HELP_PATTERN.match(message):
        return HELP_TEXT

    if CONFIRM_PATTERN.match(message):
        return _handle_confirm(user)

    if CANCEL_PATTERN.match(message):
        return _handle_cancel(user)

    return _hint_for_message(message)
