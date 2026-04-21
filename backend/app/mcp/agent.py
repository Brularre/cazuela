import json
import re
import warnings
import anthropic
from app.config import settings
from app.handlers.expenses import map_category, normalize

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
    result.setdefault("reasoning", "categorizado por IA")
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


def _match_explicit_category_map(payload: dict, raw_message: str) -> dict | None:
    cmap = payload.get("category_map")
    if not isinstance(cmap, dict) or not cmap:
        return None
    nraw = normalize(raw_message)
    for key in sorted(cmap.keys(), key=lambda k: len(normalize(str(k))), reverse=True):
        if normalize(str(key)) in nraw:
            cat = cmap[key]
            if cat not in CATEGORIES:
                cat = "otros"
            return {
                "category": cat,
                "confidence": 0.9,
                "reasoning": "mapeo explícito del usuario",
            }
    return None


def _propose_stub(context: dict) -> dict:
    payload = context.get("payload", {})
    raw_message = payload.get("raw_message", "")
    mapped = _match_explicit_category_map(payload, raw_message)
    if mapped is not None:
        return mapped
    history = payload.get("user_history", {})
    if not history:
        return {"category": "otros", "confidence": 0.5, "reasoning": "sin historial"}
    best_category = max(history, key=lambda k: history[k])
    return {
        "category": best_category,
        "confidence": 0.8,
        "reasoning": "categoría más frecuente del usuario",
    }


def _propose_batch_extract(context: dict) -> dict:
    payload = context.get("payload", {})
    raw_csv = (payload.get("items_csv") or "").strip()
    names = [p.strip() for p in raw_csv.split(",") if p.strip()]
    return {
        "step": 1,
        "items": [{"name": n} for n in names],
        "reasoning": "ítems extraídos del mensaje del usuario",
    }


def _propose_batch_categorize(context: dict) -> dict:
    proposed = context.get("proposed") or {}
    items_in = proposed.get("items") or []
    out = []
    for it in items_in:
        name = it.get("name", "")
        cat = map_category(name)
        out.append({"name": name, "category": cat})
    return {
        "step": 2,
        "items": out,
        "reasoning": "categorías por palabras clave y reglas internas",
    }


def _split_total_clp(total: int, n: int) -> list[int]:
    if n <= 0:
        return []
    base = total // n
    rem = total % n
    amounts = [base] * n
    for i in range(rem):
        amounts[i] += 1
    return amounts


def _propose_batch_split(context: dict) -> dict:
    payload = context.get("payload", {})
    proposed = context.get("proposed") or {}
    total = int(float(payload.get("total_amount", 0)))
    items_in = proposed.get("items") or []
    n = len(items_in)
    amounts = _split_total_clp(total, n)
    out = []
    for it, amt in zip(items_in, amounts):
        out.append({
            "name": it.get("name", ""),
            "category": it.get("category", "otros"),
            "amount": amt,
        })
    return {
        "step": 3,
        "items": out,
        "reasoning": "monto total repartido en pesos enteros",
    }


def _propose_expense_batch(context: dict) -> dict:
    proposed = context.get("proposed")
    step = (proposed or {}).get("step") or 0
    if proposed is None or step < 1:
        return _propose_batch_extract(context)
    if step == 1:
        return _propose_batch_categorize(context)
    if step == 2:
        return _propose_batch_split(context)
    return proposed


def _propose_stub_batch(context: dict) -> dict:
    payload = context.get("payload", {})
    transactions = payload.get("transactions", [])
    history = payload.get("user_history", {})
    best = max(history, key=lambda k: history[k]) if history else "otros"
    return {
        "categorizations": [
            {
                "index": i,
                "category": best,
                "confidence": 0.8,
                "reasoning": "categoría más frecuente del usuario",
            }
            for i in range(len(transactions))
        ]
    }


_PANTRY_KEYWORDS = {
    "baño": [
        "shampoo", "champú", "champu", "balsamo", "bálsamo", "jabón", "jabon",
        "pasta dental", "cepillo", "desodorante", "papel higiénico",
        "papel higienico", "toalla", "loción", "locion", "crema", "perfume",
    ],
    "cocina": [
        "aceite", "sal", "azúcar", "azucar", "harina", "arroz", "fideos",
        "café", "cafe", "té", "te", "leche", "huevo", "pan", "mantequilla",
        "queso", "yogur", "cereal", "vinagre",
    ],
}

_ITEM_SPLIT_RE = re.compile(r",\s*|\s+y\s+", re.IGNORECASE)


def _infer_pantry_category(item_name: str) -> str:
    lower = item_name.lower()
    for cat, keywords in _PANTRY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return cat
    return "otros"


def _propose_pantry_add_batch(context: dict) -> dict:
    payload = context.get("payload", {})
    items_raw = (payload.get("items_raw") or "").strip()
    names = [p.strip() for p in _ITEM_SPLIT_RE.split(items_raw) if p.strip()]
    items = [{"name": n, "category": _infer_pantry_category(n)} for n in names]
    return {
        "items": items,
        "reasoning": "categorías inferidas por palabras clave",
    }


_RECIPE_SYSTEM_PROMPT = (
    "You are a cooking assistant. Given a dish name, return a typical "
    "ingredient list. Respond with valid JSON only — no markdown, no "
    "explanation outside the JSON. Use Spanish ingredient names. "
    "Format: {\"ingredients\": [{\"item\": \"<name>\", "
    "\"quantity\": <number or null>, \"unit\": \"<string or null>\"}]}"
)


def _propose_recipe_create(context: dict) -> dict:
    payload = context.get("payload", {})
    recipe_name = payload.get("recipe_name", "")
    if not (settings.use_ai_agent and settings.anthropic_api_key):
        return {"ingredients": []}
    ai_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = ai_client.messages.create(
        model=MODEL_NAME,
        max_tokens=512,
        temperature=0,
        system=_RECIPE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Ingredients for: {recipe_name}"}],
    )
    if not response.content:
        return {"ingredients": []}
    try:
        return json.loads(response.content[0].text.strip())
    except json.JSONDecodeError:
        return {"ingredients": []}


def get_model_for(context: dict) -> str:
    domain = context.get("domain")
    if domain in ("expense_batch", "reconciliation", "pantry_add_batch"):
        return STUB_MODEL_NAME
    if domain in ("expense", "recipe_create") and settings.use_ai_agent and settings.anthropic_api_key:
        return MODEL_NAME
    return STUB_MODEL_NAME


def propose(context: dict) -> dict:
    domain = context.get("domain")
    if domain == "reconciliation":
        return _propose_stub_batch(context)
    if domain == "expense_batch":
        return _propose_expense_batch(context)
    if domain == "pantry_add_batch":
        return _propose_pantry_add_batch(context)
    if domain == "recipe_create":
        return _propose_recipe_create(context)
    if domain != "expense":
        return {"confirmed": True}
    if settings.use_ai_agent and settings.anthropic_api_key:
        try:
            return _propose_ai(context)
        except Exception as e:
            warnings.warn(f"AI agent failed, falling back to stub: {e}")
    return _propose_stub(context)
