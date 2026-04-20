import json
import warnings
import anthropic
from app.config import settings

_MAX_MESSAGE_LEN = 1000

_INTENTS = [
    "add_expense", "ambiguous_expense", "ambiguous_batch", "get_summary", "set_budget",
    "add_todo", "list_todos", "complete_todo",
    "necesito_comprar", "add_to_shopping", "list_shopping", "check_shopping",
    "add_pantry_item", "list_pantry", "consume_pantry_item",
    "restock_pantry_item", "restock_all_pantry",
    "add_waiting", "list_waiting", "resolve_waiting",
    "confirm", "cancel", "help", "unknown",
]

_SYSTEM_PROMPT = """You are an intent classifier for a Spanish WhatsApp personal assistant.
Classify the message and extract parameters. Return valid JSON only — no markdown.

Intents and their JSON shapes:
- add_expense: {"intent": "add_expense", "amount": <int>, "description": "<str>"}
- ambiguous_expense: {"intent": "ambiguous_expense", "amount": <int>}
  (amount given but no clear description/category)
- ambiguous_batch: {"intent": "ambiguous_batch", "amount": <int>, "items_csv": "<str>"}
  (supermercado line-items batch; same semantics as regex batch gasto)
- get_summary: {"intent": "get_summary"}
- set_budget: {"intent": "set_budget", "period": "semana", "amount": <int>}
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
- confirm: {"intent": "confirm"}
- cancel: {"intent": "cancel"}
- help: {"intent": "help"}
- unknown: {"intent": "unknown"}

Rules:
- Amounts are Chilean pesos (integers). "5.000" or "5,000" means 5000.
- Decimal amounts like "1,5" or "1.5" → unknown (invalid for CLP).
- Default todo priority is "semana" unless the message says "hoy" or "mes".
- Default pantry category is "otros" unless message specifies cocina or baño.
- "me faltan X", "se me acabo X", "quedé sin X", "no tengo X" →
  consume_pantry_item (the item ran out), NOT add_to_shopping.
- "necesito comprar X" → necesito_comprar (NOT add_to_shopping);
  extract items as comma-separated list, splitting on "y" and ",".
- Return unknown if unsure."""


def classify(message: str) -> dict | None:
    if not settings.use_ai_agent or not settings.anthropic_api_key:
        return None
    if len(message) > _MAX_MESSAGE_LEN:
        return None
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            temperature=0,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        if not response.content:
            warnings.warn("AI router: empty response from API")
            return None
        raw = response.content[0].text.strip()
        if not raw:
            warnings.warn("AI router: API returned empty text")
            return None
        if raw.startswith("```"):
            raw = raw.split("```")[1].removeprefix("json").strip()
        result = json.loads(raw)
        if result.get("intent") not in _INTENTS:
            return None
        if result.get("intent") == "unknown":
            return None
        return result
    except Exception as e:
        warnings.warn(f"AI router failed ({type(e).__name__}): {e!r}")
        return None
