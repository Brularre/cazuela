"""Module enable/disable state. Dashboard-managed (no WhatsApp CRUD).

Public API:
- is_enabled(user, module) -> bool   (default True if no row)
- module_for_intent(intent) -> str | None

Module keys: dinero, tiempo, despensa, comida, calendario, recordatorios.
  despensa — shopping list + pantry stock
  comida   — recipes + meal planning
Missing user_modules row for a module means enabled (opt-out model).
"""
import time
from app.db import client

_MODULE_CACHE: dict[tuple, tuple[bool, float]] = {}
_CACHE_TTL = 30.0

_INTENT_MODULE: dict[str, str] = {
    "add_expense": "dinero",
    "ambiguous_expense": "dinero",
    "get_summary": "dinero",
    "set_budget": "dinero",
    "add_todo": "tiempo",
    "list_todos": "tiempo",
    "complete_todo": "tiempo",
    "delete_todo": "tiempo",
    "add_waiting": "tiempo",
    "list_waiting": "tiempo",
    "resolve_waiting": "tiempo",
    "add_to_shopping": "despensa",
    "list_shopping": "despensa",
    "add_pantry_item": "despensa",
    "list_pantry": "despensa",
    "consume_pantry_item": "despensa",
    "nueva_receta": "comida",
    "list_recipes": "comida",
    "show_recipe": "comida",
    "que_puedo_hacer": "comida",
    "sugerir_recetas": "comida",
    "elegir_receta": "comida",
    "add_event": "calendario",
    "list_events": "calendario",
    "delete_event": "calendario",
    "set_reminder": "recordatorios",
}


def is_enabled(user: dict, module: str) -> bool:
    key = (user["id"], module)
    now = time.monotonic()
    cached = _MODULE_CACHE.get(key)
    if cached is not None:
        value, ts = cached
        if now - ts < _CACHE_TTL:
            return value
    result = (
        client.table("user_modules")
        .select("enabled")
        .eq("user_id", user["id"])
        .eq("module", module)
        .execute()
    )
    rows = result.data or []
    value = True if not rows else bool(rows[0]["enabled"])
    _MODULE_CACHE[key] = (value, now)
    return value


def bust_module_cache(user_id: str) -> None:
    for key in [k for k in _MODULE_CACHE if k[0] == user_id]:
        del _MODULE_CACHE[key]


MODULE_DISABLED_MSG = "Ese módulo está desactivado. Actívalo en el tablero."


def module_for_intent(intent: str) -> str | None:
    return _INTENT_MODULE.get(intent)
