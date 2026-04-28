from app.db import client as db
from app.mcp import client as mcp
from app.db.recipes import (
    create_recipe,
    get_recipes,
    get_ingredients,
    replace_ingredients,
)
from app.handlers.expenses import normalize
from app.handlers.shopping import add_many_to_shopping


def _coerce_quantity(raw) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _format_ingredient(ing: dict) -> str:
    parts = []
    if ing.get("quantity"):
        parts.append(str(ing["quantity"]))
    if ing.get("unit"):
        parts.append(ing["unit"])
    parts.append(ing.get("item", ""))
    return " ".join(p for p in parts if p)


def _format_suggestion_line(idx: int, name: str, have: int, total: int, missing: list) -> str:
    if total > 0:
        coverage = f"usa {have}/{total}"
    else:
        coverage = "sin ingredientes registrados"
    missing_str = f", falta: {', '.join(missing)}" if missing else ""
    return f"{idx}. {name} — {coverage}{missing_str}"


def nueva_receta(name: str, user: dict) -> str:
    if len(name.strip()) > 100:
        return "El nombre es demasiado largo (máximo 100 caracteres)."

    context_id = mcp.send_context("recipe_create", user["id"], {
        "recipe_name": name.strip(),
        "ai_mode": bool(user.get("ai_mode")),
    })
    result = mcp.request_action(context_id)
    proposed = result.get("proposed", {})
    ingredients = proposed.get("ingredients", [])

    if not ingredients:
        mcp.confirm(context_id)
        create_recipe(user["id"], name.strip())
        hint = (
            "_Activa el modo IA para que te sugiera ingredientes._"
            if not user.get("ai_mode")
            else "_Agrega los ingredientes en el dashboard._"
        )
        return f"✓ Receta *{name}* creada.\n{hint}"

    lines = [f"*Ingredientes sugeridos para {name}:*"]
    for ing in ingredients:
        lines.append(f"• {_format_ingredient(ing)}")
    lines.append("\n_Estos ingredientes son aproximados, puedes editarlos a gusto en tu tablero._")
    lines.append("¿Los guardamos? Responde *confirmar* o *cancelar*.")
    return "\n".join(lines)


def confirm_recipe_create(context_id: str, user: dict, ctx: dict) -> str:
    proposed = ctx.get("proposed", {})
    ingredients = proposed.get("ingredients", [])
    payload = ctx.get("payload", {})
    recipe_name = payload.get("recipe_name", "receta")
    try:
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Esta operación ya fue confirmada, cancelada, o expiró."

    recipe = create_recipe(user["id"], recipe_name)
    if ingredients:
        rows = [
            {
                "recipe_id": recipe["id"],
                "item": normalize(ing["item"]),
                "quantity": _coerce_quantity(ing.get("quantity")),
                "unit": ing.get("unit"),
            }
            for ing in ingredients
        ]
        replace_ingredients(recipe["id"], rows)
    return (
        f"✓ *{recipe_name}* guardada "
        f"con {len(ingredients)} ingredientes."
    )


def cancel_recipe_create(context_id: str, user: dict) -> str:
    try:
        mcp.rollback(context_id)
    except ValueError:
        return "Esta operación ya fue confirmada, cancelada, o expiró."
    return "Receta cancelada."


def list_recipes(user: dict) -> str:
    recipes = get_recipes(user["id"])
    if not recipes:
        return (
            "No tienes recetas guardadas. "
            "Crea una con _nueva receta: cazuela_."
        )
    lines = ["*Mis recetas:*"]
    for r in recipes:
        lines.append(f"• {r['name']} ({r.get('servings', 2)} personas)")
    return "\n".join(lines)


def show_recipe(name_fragment: str, user: dict) -> str:
    recipes = get_recipes(user["id"])
    needle = normalize(name_fragment)
    match = next(
        (r for r in recipes if needle in normalize(r["name"])),
        None,
    )
    if not match:
        return f"No encontré una receta llamada '{name_fragment}'."
    ingredients = get_ingredients(match["id"])
    if not ingredients:
        return (
            f"*{match['name']}* — sin ingredientes. "
            f"Edita en el dashboard."
        )
    lines = [f"*{match['name']}* ({match.get('servings', 2)} personas):"]
    for ing in ingredients:
        lines.append(f"• {_format_ingredient(ing)}")
    return "\n".join(lines)


def que_puedo_hacer(user: dict) -> str:
    recipes = get_recipes(user["id"])
    if not recipes:
        return (
            "No tienes recetas guardadas. "
            "Crea una con _nueva receta: cazuela_."
        )

    pantry_result = (
        db.table("pantry")
        .select("item, current_quantity")
        .eq("user_id", user["id"])
        .execute()
    )
    pantry_items = pantry_result.data or []
    pantry_in_stock = [
        normalize(i["item"])
        for i in pantry_items
        if i["current_quantity"] > 0
    ]

    recipe_data = []
    for r in recipes:
        ingredients = get_ingredients(r["id"])
        recipe_data.append({
            "recipe_id": r["id"],
            "name": r["name"],
            "ingredients": [normalize(ing["item"]) for ing in ingredients],
        })

    context_id = mcp.send_context("recipe_match", user["id"], {
        "recipes": recipe_data,
        "pantry_in_stock": pantry_in_stock,
    })
    result = mcp.request_action(context_id)
    proposed = result.get("proposed", {})
    suggestions = proposed.get("suggestions", [])

    if all(s["total"] == 0 for s in suggestions):
        mcp.rollback(context_id)
        return (
            "Tus recetas no tienen ingredientes registrados. "
            "Agrega ingredientes en el dashboard."
        )

    lines = ["*Recetas que puedes hacer:*\n"]
    for i, s in enumerate(suggestions, 1):
        lines.append(_format_suggestion_line(
            i, s["name"], s["have"], s["total"], s["missing"]
        ))
    lines.append("\n_Responde *elegir N* (ej: *elegir 1*) o *cancelar*._")
    return "\n".join(lines)


def sugerir_recetas(user: dict) -> str:
    if not user.get("ai_mode"):
        return "_Activa el modo IA en el dashboard para recibir sugerencias de recetas._"

    pantry_result = (
        db.table("pantry")
        .select("item, current_quantity, desired_quantity")
        .eq("user_id", user["id"])
        .execute()
    )
    pantry_items = pantry_result.data or []
    if not pantry_items:
        return "Tu despensa está vacía. Agrega items con _despensa cocina arroz 3_ primero."

    existing_recipes = get_recipes(user["id"])
    existing_names = [r["name"] for r in existing_recipes]

    context_id = mcp.send_context("recipe_suggest", user["id"], {
        "pantry": [
            {
                "item": normalize(i["item"]),
                "current": i["current_quantity"],
                "desired": i["desired_quantity"],
            }
            for i in pantry_items
        ],
        "existing_recipe_names": existing_names,
        "n": 5,
    })
    result = mcp.request_action(context_id)
    proposed = result.get("proposed", {})
    suggestions = proposed.get("suggestions", [])

    if not suggestions:
        return "_No pude generar sugerencias en este momento. Intenta de nuevo más tarde._"

    lines = ["*Sugerencias para tu despensa:*\n"]
    for i, s in enumerate(suggestions, 1):
        have = len(s.get("uses_pantry", []))
        total = have + len(s.get("missing", []))
        lines.append(_format_suggestion_line(
            i, s["name"], have, total, s.get("missing", [])
        ))
    lines.append("\n_Responde *elegir N* (ej: *elegir 2*) o *cancelar*._")
    return "\n".join(lines)


def elegir_receta(n: int, user: dict) -> str:
    context_id = mcp.find_pending_for_user(user["id"])
    if not context_id:
        return (
            "No tengo ninguna sugerencia pendiente. "
            "Pide nuevas con _qué puedo hacer_ o _qué cocino_."
        )
    try:
        ctx_data = mcp.receive_result(context_id)
    except (ValueError, KeyError):
        return "Las sugerencias expiraron. Pide nuevas con _qué puedo hacer_ o _qué cocino_."

    domain = ctx_data.get("domain")
    if domain not in ("recipe_match", "recipe_suggest"):
        return (
            "No tengo ninguna sugerencia pendiente. "
            "Pide nuevas con _qué puedo hacer_ o _qué cocino_."
        )

    proposed = ctx_data.get("proposed") or {}
    suggestions = proposed.get("suggestions", [])

    if not suggestions:
        return "No tengo sugerencias para elegir."

    if n < 1 or n > len(suggestions):
        return f"Solo hay {len(suggestions)} sugerencias. Elige entre 1 y {len(suggestions)}."

    chosen = suggestions[n - 1]
    missing = chosen.get("missing", [])

    if domain == "recipe_suggest":
        recipe = create_recipe(user["id"], chosen["name"])
        ingredients = chosen.get("ingredients", [])
        if ingredients:
            rows = [
                {
                    "recipe_id": recipe["id"],
                    "item": normalize(ing["item"]),
                    "quantity": _coerce_quantity(ing.get("quantity")),
                    "unit": ing.get("unit"),
                }
                for ing in ingredients
            ]
            replace_ingredients(recipe["id"], rows)
        confirmation = f"✓ *{chosen['name']}* guardada con {len(ingredients)} ingredientes."
    else:
        confirmation = f"✓ *{chosen['name']}* seleccionada. ¡A cocinar!"

    try:
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Esta operación ya fue confirmada, cancelada, o expiró."

    if not missing:
        return confirmation

    shop_ctx_id = mcp.send_context("shopping_add_pending", user["id"], {
        "items": missing,
        "source": "recipe",
    })
    mcp.request_action(shop_ctx_id)

    missing_str = ", ".join(missing)
    return (
        f"{confirmation}\n\n"
        f"Faltan: *{missing_str}*.\n"
        f"¿Los agrego a la lista de compras? Responde *sí* o *no*."
    )


def confirm_shopping_add(context_id: str, user: dict, ctx_data: dict) -> str:
    payload = ctx_data.get("payload", {})
    items = payload.get("items", [])
    source = payload.get("source", "recipe")
    try:
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Esta operación ya fue confirmada, cancelada, o expiró."
    n = add_many_to_shopping(items, user, source)
    noun = "ítem agregado" if n == 1 else "ítems agregados"
    return f"✓ {n} {noun} a la lista de compras. ¡Buen provecho!"


def cancel_shopping_add(context_id: str, user: dict) -> str:
    try:
        mcp.rollback(context_id)
    except ValueError:
        return "Esta operación ya fue confirmada, cancelada, o expiró."
    return "¡Buen provecho!"
