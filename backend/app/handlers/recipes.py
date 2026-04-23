from app.mcp import client as mcp
from app.db.recipes import (
    create_recipe,
    get_recipes,
    get_ingredients,
    replace_ingredients,
)
from app.handlers.expenses import normalize


def _format_ingredient(ing: dict) -> str:
    parts = []
    if ing.get("quantity"):
        parts.append(str(ing["quantity"]))
    if ing.get("unit"):
        parts.append(ing["unit"])
    parts.append(ing.get("item", ""))
    return " ".join(p for p in parts if p)


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
                "quantity": ing.get("quantity"),
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
