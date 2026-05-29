"""LLM adapter — classify() and respond(). Provider-agnostic.

Public API:
- classify(message, user) -> dict | None
- respond(prompt, user) -> str | None  (defined but not wired in Track C)
- complete(role, system, message, max_tokens, temperature) -> str | None
- responder_available() -> bool
"""
import json
import warnings

from app.config import settings

_MAX_MESSAGE_LEN = 1000

_INTENTS = [
    "add_expense", "ambiguous_expense", "ambiguous_batch", "get_summary", "set_budget",
    "add_todo", "list_todos", "complete_todo",
    "necesito_comprar", "add_to_shopping", "list_shopping", "check_shopping",
    "add_pantry_item", "list_pantry", "consume_pantry_item",
    "restock_pantry_item", "restock_all_pantry",
    "add_waiting", "list_waiting", "resolve_waiting",
    "recipe_new", "recipe_list", "recipe_show",
    "set_reminder",
    "tablero", "set_name",
    "confirm", "cancel", "help", "unknown",
]

_INTENT_SYSTEM_PROMPT = """You are an intent classifier for a Spanish WhatsApp personal assistant.
Classify the message and extract parameters. Return valid JSON only — no markdown.

Intents and their JSON shapes:
- add_expense: {"intent": "add_expense", "amount": <int>, "description": "<str>"}
- ambiguous_expense: {"intent": "ambiguous_expense", "amount": <int>}
  (amount given but no clear description/category)
- ambiguous_batch: {"intent": "ambiguous_batch", "amount": <int>, "items_csv": "<str>"}
  (supermercado line-items batch; same semantics as regex batch gasto)
- get_summary: {"intent": "get_summary"}
- set_budget: {"intent": "set_budget", "amount": <int>}
- add_todo: {"intent": "add_todo", "task": "<str>", "priority": "hoy"|"semana"|"mes"}
- list_todos: {"intent": "list_todos"}
- complete_todo: {"intent": "complete_todo", "task_fragment": "<str>"}
- necesito_comprar: {"intent": "necesito_comprar", "items_raw": "<comma-separated items>"}
- add_to_shopping: {"intent": "add_to_shopping", "item": "<str>"}
- list_shopping: {"intent": "list_shopping"}
- check_shopping: {"intent": "check_shopping", "item_fragment": "<str>"}
- add_pantry_item: {"intent": "add_pantry_item", "item": "<str>", "qty": <int>, "category": "cocina"|"baño"|"otros"}
- list_pantry: {"intent": "list_pantry"}
- consume_pantry_item: {"intent": "consume_pantry_item", "item_fragment": "<str>"}
- restock_pantry_item: {"intent": "restock_pantry_item", "item_fragment": "<str>"}
- restock_all_pantry: {"intent": "restock_all_pantry"}
- add_waiting: {"intent": "add_waiting", "description": "<str>"}
- list_waiting: {"intent": "list_waiting"}
- resolve_waiting: {"intent": "resolve_waiting", "fragment": "<str>"}
- recipe_new: {"intent": "recipe_new", "name": "<str>"}
- recipe_list: {"intent": "recipe_list"}
- recipe_show: {"intent": "recipe_show", "name_fragment": "<str>"}
- set_reminder: {"intent": "set_reminder", "task_fragment": "<str>", "remind_at": "<ISO 8601 datetime>"}
  (user wants a reminder for an existing todo or event; remind_at must be a future UTC datetime)
- tablero: {"intent": "tablero"}
- set_name: {"intent": "set_name", "name": "<str>"}
- confirm: {"intent": "confirm"}
- cancel: {"intent": "cancel"}
- help: {"intent": "help"}
- unknown: {"intent": "unknown"}

Rules:
- Amounts are Chilean pesos (integers). "5.000" or "5,000" means 5000.
- Decimal amounts like "1,5" or "1.5" → unknown (invalid for CLP).
- Default todo priority is "semana" unless the message says "hoy" or "mes".
- Default pantry category is "otros" unless message specifies cocina or baño.
- "pendiente X" or "tarea X" → always add_todo (a task the user
  must do themselves), never add_waiting.
- "esperando X" → add_waiting (something the user is waiting to
  receive from someone else).
- "me faltan X", "se me acabo X", "quedé sin X", "no tengo X" →
  consume_pantry_item (the item ran out), NOT add_to_shopping.
- "necesito comprar X" → necesito_comprar (NOT add_to_shopping);
  extract items as comma-separated list, splitting on "y" and ",".
- "sí", "si", "ok", "dale", "va", "listo" (standalone, likely responding to a pending action) → confirm.
- "no", "nope", "olvídalo", "olvidalo" (standalone) → cancel.
- "despensa" or "lista" (standalone) → unknown (handled before AI routing).
- "que puedo hacer" or "qué puedo hacer" (standalone) → unknown (handled before AI routing).
- "recuérdame X a las HH" or "recuerda X mañana" → set_reminder; extract task_fragment (the thing to be reminded about) and remind_at as ISO 8601 UTC.
- Return unknown if unsure."""


class _AnthropicProvider:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> str | None:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if not response.content:
            return None
        return response.content[0].text.strip() or None


class _GroqProvider:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> str | None:
        import requests
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("choices"):
            return None
        return data["choices"][0]["message"]["content"].strip() or None


class _StubProvider:
    """Returns canned responses keyed by message. Used in tests."""

    _registry: dict[str, str] = {}

    @classmethod
    def register(cls, message: str, response: str):
        cls._registry[message] = response

    @classmethod
    def clear(cls):
        cls._registry.clear()

    def __init__(self, api_key=None, model=None):
        pass

    def complete(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> str | None:
        return self._registry.get(user)


def _provider_for(role: str, user: dict):
    """role is 'classifier' or 'responder'."""
    if role == "classifier":
        provider_name = settings.classifier_provider
        api_key = settings.classifier_api_key
        model = settings.classifier_model
    else:
        provider_name = settings.responder_provider
        api_key = settings.responder_api_key
        model = settings.responder_model

    if provider_name == "stub":
        return _StubProvider()
    if provider_name == "none" or not api_key:
        return None
    if provider_name == "anthropic":
        return _AnthropicProvider(api_key, model)
    if provider_name == "groq":
        return _GroqProvider(api_key, model)
    return None


def _parse_intent_json(raw: str) -> dict | None:
    if not raw:
        return None
    if raw.startswith("```"):
        raw = raw.split("```")[1].removeprefix("json").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if result.get("intent") not in _INTENTS:
        return None
    if result.get("intent") == "unknown":
        return None
    return result


def _ai_enabled_for(user: dict) -> bool:
    if user.get("ai_mode") is False:
        return False
    return settings.classifier_provider != "none"


def _user_profile_prefix(user: dict) -> str:
    bits = []
    if user.get("name"):
        bits.append(f"User's name: {user['name']}")
    currency = user.get("currency") or "CLP"
    bits.append(f"Currency: {currency} (integer amounts only)")
    return "\n".join(bits)


def classify(message: str, user: dict) -> dict | None:
    if not _ai_enabled_for(user):
        return None
    if len(message) > _MAX_MESSAGE_LEN:
        return None
    provider = _provider_for("classifier", user)
    if provider is None:
        return None
    system = _user_profile_prefix(user) + "\n\n" + _INTENT_SYSTEM_PROMPT
    try:
        raw = provider.complete(
            system=system,
            user=message,
            max_tokens=512,
            temperature=0,
        )
    except Exception as e:
        warnings.warn(f"LLM classify failed ({type(e).__name__}): {e!r}")
        return None
    return _parse_intent_json(raw)


def complete(
    role: str,
    system: str,
    message: str,
    max_tokens: int = 512,
    temperature: float = 0,
) -> str | None:
    provider = _provider_for(role, {})
    if provider is None:
        return None
    try:
        return provider.complete(
            system=system,
            user=message,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as e:
        warnings.warn(f"LLM complete failed ({type(e).__name__}): {e!r}")
        return None


def responder_available() -> bool:
    return _provider_for("responder", {}) is not None


def respond(prompt: str, user: dict) -> str | None:
    """Not wired in Track C — defined for future conversational use."""
    if not _ai_enabled_for(user):
        return None
    provider = _provider_for("responder", user)
    if provider is None:
        return None
    system = (
        _user_profile_prefix(user)
        + "\n\nYou are Cazuela, a friendly Spanish WhatsApp assistant."
    )
    try:
        return provider.complete(
            system=system,
            user=prompt,
            max_tokens=512,
            temperature=0.3,
        )
    except Exception as e:
        warnings.warn(f"LLM respond failed ({type(e).__name__}): {e!r}")
        return None
