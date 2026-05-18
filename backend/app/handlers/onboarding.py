"""
Onboarding handler — new user setup flow (WhatsApp).

Public API:
  is_onboarding(user) -> bool
    True when the user has not completed onboarding.
    Checked by router.route() before normal dispatch.

  start_onboarding(user) -> str
    Returns the greeting sent on first contact.
    Called by main.py when get_or_create_user returns is_new=True.

  handle_onboarding(message, user) -> str
    Advances the flow one step:
      - name IS NULL  → save message as name, ask for budget
      - name IS SET   → parse budget amount or accept skip words,
                        then mark onboarding_complete=True
"""
import re

from app.db import client
from app.handlers.budget import set_budget
from app.handlers.utils import normalize, parse_clp_amount

_SKIP_WORDS = {"despues", "skip", "omitir", "no", "no se"}
_NAME_PREFIX_RE = re.compile(r'^(?:me llamo|soy)\s+', re.IGNORECASE)

_GREETING = (
    "¡Hola! Soy *Cazuela*, tu asistente personal.\n\n"
    "Te ayudo a llevar gastos, pendientes, despensa, recetas y más.\n\n"
    "Para empezar, ¿cómo te llamas?"
)

_BUDGET_PROMPT = (
    "¡Hola, {name}!\n\n"
    "¿Cuánto quieres gastar al mes?\n"
    "Escribe el monto (ej: _600.000_) o *después* para saltarte esto."
)

_DONE = (
    "¡Listo! Ya puedes usar Cazuela. Algunos comandos:\n\n"
    "• _gasté 5000 en almuerzo_ — registra un gasto\n"
    "• _pendiente: llamar al banco_ — agrega una tarea\n"
    "• _comprar: leche_ — agrega a la lista de compras\n\n"
    "Escribe *ayuda* para ver todos los comandos."
)


def is_onboarding(user: dict) -> bool:
    return not user.get("onboarding_complete", False)


def start_onboarding(user: dict) -> str:
    return _GREETING


def handle_onboarding(message: str, user: dict) -> str:
    message = message.strip()
    if user.get("name") is None:
        return _save_name(message, user)
    return _handle_budget(message, user)


def _save_name(raw: str, user: dict) -> str:
    name = _NAME_PREFIX_RE.sub('', raw).strip()
    name = name[:50]
    if not name:
        return "No entendí tu nombre. ¿Cómo te llamas?"
    client.table("users").update({"name": name}).eq("id", user["id"]).execute()
    return _BUDGET_PROMPT.format(name=name)


def _handle_budget(message: str, user: dict) -> str:
    if normalize(message) in _SKIP_WORDS:
        return _complete(user)
    amount = parse_clp_amount(message)
    if amount is not None and amount > 0:
        set_budget(amount, user)
        return _complete(user)
    return (
        "No entendí el monto. Escribe un número (ej: _600.000_) "
        "o *después* para saltarte esto."
    )


def _complete(user: dict) -> str:
    client.table("users").update({"onboarding_complete": True}).eq("id", user["id"]).execute()
    return _DONE
