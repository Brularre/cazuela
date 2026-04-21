from app.db import client


def create_recipe(user_id: str, name: str, servings: int = 2) -> dict:
    result = client.table("recipes").insert({
        "user_id": user_id,
        "name": name,
        "servings": servings,
    }).execute()
    return result.data[0]


def get_recipes(user_id: str) -> list[dict]:
    result = client.table("recipes").select("*").eq("user_id", user_id).execute()
    return result.data


def delete_recipe(user_id: str, recipe_id: str) -> None:
    client.table("recipes").delete().eq("id", recipe_id).eq("user_id", user_id).execute()


def add_ingredient(recipe_id: str, item: str, quantity: float | None = None, unit: str | None = None) -> dict:
    result = client.table("recipe_ingredients").insert({
        "recipe_id": recipe_id,
        "item": item,
        "quantity": quantity,
        "unit": unit,
    }).execute()
    return result.data[0]


def get_ingredients(recipe_id: str) -> list[dict]:
    result = (
        client.table("recipe_ingredients")
        .select("*")
        .eq("recipe_id", recipe_id)
        .execute()
    )
    return result.data


def replace_ingredients(recipe_id: str, ingredients: list[dict]) -> list[dict]:
    old = (
        client.table("recipe_ingredients")
        .select("recipe_id, item, quantity, unit")
        .eq("recipe_id", recipe_id)
        .execute()
    ).data or []
    client.table("recipe_ingredients").delete().eq("recipe_id", recipe_id).execute()
    try:
        result = client.table("recipe_ingredients").insert(ingredients).execute()
        return result.data
    except Exception:
        if old:
            client.table("recipe_ingredients").insert(old).execute()
        raise
