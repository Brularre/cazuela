import json
import warnings
import anthropic
from app.config import settings

MODEL_NAME = "claude-haiku-4-5-20251001"
STUB_MODEL_NAME = "stub-v1"

CATEGORIES = [
    "comida", "transporte", "salud", "hogar", "entretenimiento",
    "ropa", "tecnología", "educación", "viajes", "otros",
]

_SYSTEM_PROMPT = (
    "You are a personal finance assistant. Categorize the given expense "
    "into exactly one of these categories: "
    + ", ".join(CATEGORIES)
    + ". Respond with valid JSON only — no markdown, no explanation outside the JSON. "
    "Format: {\"category\": \"<category>\", \"confidence\": <0.0-1.0>, "
    "\"reasoning\": \"<one sentence in Spanish>\"}"
)


def _parse_ai_response(raw: str) -> dict:
    result = json.loads(raw)
    if result.get("category") not in CATEGORIES:
        result["category"] = "otros"
    result.setdefault("confidence", 0.5)
    result.setdefault("reasoning", "")
    if not result.get("reasoning"):
        result["reasoning"] = "categorizado por IA"
    return result


def _propose_ai(context: dict) -> dict:
    payload = context.get("payload", {})
    history = payload.get("user_history", {})
    user_message = (
        f"Expense: {payload.get('raw_message', '')}\n"
        f"Amount: {payload.get('amount', 0)} CLP\n"
        f"User's recent category counts: {json.dumps(history, ensure_ascii=False)}\n"
        "What category best fits this expense?"
    )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=128,
        temperature=0,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    if not response.content:
        raise ValueError("Empty response from AI agent")
    return _parse_ai_response(response.content[0].text.strip())


def _propose_stub(context: dict) -> dict:
    history = context.get("payload", {}).get("user_history", {})
    if not history:
        return {"category": "otros", "confidence": 0.5, "reasoning": "sin historial"}
    best_category = max(history, key=lambda k: history[k])
    return {
        "category": best_category,
        "confidence": 0.8,
        "reasoning": "categoría más frecuente del usuario",
    }


def propose(context: dict) -> dict:
    if context.get("domain") != "expense":
        return {"confirmed": True}
    if settings.use_ai_agent and settings.anthropic_api_key:
        try:
            return _propose_ai(context)
        except Exception as e:
            warnings.warn(f"AI agent failed, falling back to stub: {e}")
    return _propose_stub(context)
