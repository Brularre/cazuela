MODEL_NAME = "stub-v1"


def propose(context: dict) -> dict:
    if context.get("domain") != "expense":
        return {"confirmed": True}

    history = context.get("payload", {}).get("user_history", {})
    if not history:
        return {"category": "otros", "confidence": 0.5, "reasoning": "sin historial"}

    best_category = max(history, key=lambda k: history[k])
    return {
        "category": best_category,
        "confidence": 0.8,
        "reasoning": "categoría más frecuente del usuario",
    }
