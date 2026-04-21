from app.db import client


def get_or_create_plan(user_id: str, week_start: str) -> dict:
    result = (
        client.table("meal_plans")
        .select("*")
        .eq("user_id", user_id)
        .eq("week_start", week_start)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    result = client.table("meal_plans").insert({
        "user_id": user_id,
        "week_start": week_start,
    }).execute()
    return result.data[0]


def get_entries(meal_plan_id: str) -> list[dict]:
    result = (
        client.table("meal_plan_entries")
        .select("*, recipes(name)")
        .eq("meal_plan_id", meal_plan_id)
        .execute()
    )
    return result.data


def upsert_entry(meal_plan_id: str, day_of_week: str, slot_name: str, recipe_id: str | None) -> dict:
    existing = (
        client.table("meal_plan_entries")
        .select("id")
        .eq("meal_plan_id", meal_plan_id)
        .eq("day_of_week", day_of_week)
        .eq("slot_name", slot_name)
        .limit(1)
        .execute()
    )
    if existing.data:
        result = (
            client.table("meal_plan_entries")
            .update({"recipe_id": recipe_id})
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        result = client.table("meal_plan_entries").insert({
            "meal_plan_id": meal_plan_id,
            "day_of_week": day_of_week,
            "slot_name": slot_name,
            "recipe_id": recipe_id,
        }).execute()
    return result.data[0]


def delete_entry(entry_id: str) -> None:
    client.table("meal_plan_entries").delete().eq("id", entry_id).execute()


def delete_slot(meal_plan_id: str, slot_name: str) -> None:
    client.table("meal_plan_entries").delete().eq("meal_plan_id", meal_plan_id).eq("slot_name", slot_name).execute()
