"""Module enable/disable state. Dashboard-managed (no WhatsApp CRUD).

Public API:
- is_enabled(user, module) -> bool   (default True if no row)
- module_for_intent(intent) -> str | None

Module keys: dinero, tiempo, despensa, comida, calendario, recordatorios.
  despensa — shopping list + pantry stock
  comida   — recipes + meal planning
Missing user_modules row for a module means enabled (opt-out model).
"""
from app.db import client

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
}


def is_enabled(user: dict, module: str) -> bool:
    result = (
        client.table("user_modules")
        .select("enabled")
        .eq("user_id", user["id"])
        .eq("module", module)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return True
    return bool(rows[0]["enabled"])


def module_for_intent(intent: str) -> str | None:
    return _INTENT_MODULE.get(intent)
