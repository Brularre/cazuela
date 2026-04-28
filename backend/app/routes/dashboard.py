import warnings
from datetime import date, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.db import client
from app.handlers.pantry import normalize as normalize_pantry_item
from app.handlers.expenses import normalize as normalize_item
from app.handlers.summary import aggregate_by_category
from app.middleware.auth import require_auth


router = APIRouter(prefix="/dashboard")

DAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]



@router.get("")
def get_dashboard(uid: str = Depends(require_auth)):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    expense_result = (
        client.table("expenses")
        .select("amount, category, date")
        .eq("user_id", uid)
        .gte("date", monday.isoformat())
        .execute()
    )
    expenses = expense_result.data or []

    by_day = {label: 0.0 for label in DAY_LABELS}
    for exp in expenses:
        d = date.fromisoformat(exp["date"])
        by_day[DAY_LABELS[d.weekday()]] += float(exp["amount"])
    by_day_list = [{"day": k, "amount": v} for k, v in by_day.items()]

    totals = aggregate_by_category(expenses)
    by_category_list = [{"category": k, "amount": v} for k, v in totals.items()]

    weekly_total = sum(float(e["amount"]) for e in expenses)

    month_result = (
        client.table("expenses")
        .select("amount")
        .eq("user_id", uid)
        .gte("date", month_start.isoformat())
        .execute()
    )
    monthly_total = sum(
        float(r["amount"]) for r in (month_result.data or [])
    )
    days_in_month = ((month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - month_start).days
    monthly_estimate = round((monthly_total / today.day) * days_in_month)

    budget_result = (
        client.table("budgets")
        .select("amount")
        .eq("user_id", uid)
        .eq("period", "mes")
        .execute()
    )
    budget = float(budget_result.data[0]["amount"]) if budget_result.data else None

    todo_result = (
        client.table("todos")
        .select("id, task, priority")
        .eq("user_id", uid)
        .eq("done", False)
        .execute()
    )
    pendientes = {"hoy": [], "semana": [], "mes": []}
    for row in (todo_result.data or []):
        bucket = row.get("priority", "semana")
        if bucket not in pendientes:
            bucket = "semana"
        pendientes[bucket].append({"id": row["id"], "task": row["task"]})

    waiting_result = (
        client.table("waiting_on")
        .select("id, description, created_at")
        .eq("user_id", uid)
        .eq("resolved", False)
        .order("created_at", desc=False)
        .execute()
    )
    esperando = [
        {"id": row["id"], "description": row["description"], "created_at": row["created_at"]}
        for row in (waiting_result.data or [])
    ]

    pantry_result = (
        client.table("pantry")
        .select("id, item, current_quantity, desired_quantity, category")
        .eq("user_id", uid)
        .order("item")
        .execute()
    )
    pantry_items = pantry_result.data or []

    compras = [
        {
            "id": i["id"],
            "item": i["item"],
            "current_quantity": i["current_quantity"],
            "desired_quantity": i["desired_quantity"],
            "category": i["category"],
            "source": "pantry",
        }
        for i in pantry_items
        if i["current_quantity"] < i["desired_quantity"]
    ]

    lista_result = (
        client.table("shopping_list")
        .select("id, item, quantity, unit")
        .eq("user_id", uid)
        .eq("checked", False)
        .order("id")
        .execute()
    )
    compras += [
        {"id": r["id"], "item": r["item"], "quantity": r.get("quantity"), "unit": r.get("unit"), "source": "lista"}
        for r in (lista_result.data or [])
    ]

    despensa = {"cocina": [], "baño": [], "otros": []}
    for i in pantry_items:
        bucket = i["category"] if i["category"] in despensa else "otros"
        despensa[bucket].append({
            "id": i["id"],
            "item": i["item"],
            "current_quantity": i["current_quantity"],
            "desired_quantity": i["desired_quantity"],
        })

    recipes_result = (
        client.table("recipes")
        .select("id, name, servings, recipe_ingredients(id, item, quantity, unit)")
        .eq("user_id", uid)
        .order("name")
        .execute()
    )
    recetas = [
        {**r, "ingredients": r.pop("recipe_ingredients", []) or []}
        for r in (recipes_result.data or [])
    ]

    plan_result = (
        client.table("meal_plans")
        .select("id, week_start, slots")
        .eq("user_id", uid)
        .eq("week_start", monday.isoformat())
        .limit(1)
        .execute()
    )
    plan = None
    try:
        if plan_result.data:
            plan_row = plan_result.data[0]
        else:
            ins = client.table("meal_plans").insert({
                "user_id": uid,
                "week_start": monday.isoformat(),
                "slots": ["almuerzo", "cena"],
            }).execute()
            plan_row = ins.data[0]

        plan_entries = (
            client.table("meal_plan_entries")
            .select("id, day_of_week, slot_name, recipe_id, recipes(name)")
            .eq("meal_plan_id", plan_row["id"])
            .execute()
        ).data or []

        plan = {
            "plan_id": plan_row["id"],
            "week_start": str(plan_row["week_start"]),
            "slots": plan_row.get("slots") or ["almuerzo", "cena"],
            "entries": [
                {
                    "id": e["id"],
                    "day_of_week": e["day_of_week"],
                    "slot_name": e["slot_name"],
                    "recipe_id": e["recipe_id"],
                    "recipe_name": (e.get("recipes") or {}).get("name"),
                }
                for e in plan_entries
            ],
        }
    except Exception as exc:
        warnings.warn(f"Failed to load meal plan for user {uid}: {exc}")

    return {
        "gastos": {
            "weekly_total": weekly_total,
            "monthly_total": monthly_total,
            "monthly_estimate": monthly_estimate,
            "budget": budget,
            "by_day": by_day_list,
            "by_category": by_category_list,
        },
        "pendientes": pendientes,
        "esperando": esperando,
        "compras": compras,
        "despensa": despensa,
        "recetas": recetas,
        "plan": plan,
    }


@router.patch("/todos/{todo_id}/complete")
def complete_todo(todo_id: str, uid: str = Depends(require_auth)):

    client.table("todos").update({"done": True}).eq("id", todo_id).eq("user_id", uid).execute()
    return {"ok": True}


@router.patch("/waiting_on/{item_id}/resolve")
def resolve_waiting(item_id: str, uid: str = Depends(require_auth)):

    client.table("waiting_on").update({"resolved": True}).eq("id", item_id).eq("user_id", uid).execute()
    return {"ok": True}


class PantryItemIn(BaseModel):
    item: str
    desired_quantity: int
    current_quantity: int | None = None
    category: Literal["cocina", "baño", "otros"] = "otros"


class PantryItemUpdate(BaseModel):
    desired_quantity: int | None = None
    current_quantity: int | None = Field(default=None, ge=0)
    category: Literal["cocina", "baño", "otros"] | None = None


@router.post("/pantry")
def create_pantry_item(body: PantryItemIn, uid: str = Depends(require_auth)):

    normalized = normalize_pantry_item(body.item)
    result = client.table("pantry").upsert({
        "user_id": uid,
        "item": normalized,
        "desired_quantity": body.desired_quantity,
        "current_quantity": body.current_quantity if body.current_quantity is not None else body.desired_quantity,
        "category": body.category,
    }, on_conflict="user_id,item").execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Pantry upsert returned no data")
    return {"ok": True, "id": result.data[0]["id"]}


class ShoppingListItemIn(BaseModel):
    item: str = Field(min_length=1, max_length=100)
    source: str = Field(default="manual", max_length=50)


@router.post("/shopping-list")
def add_shopping_list_item(body: ShoppingListItemIn, uid: str = Depends(require_auth)):

    normalized = normalize_pantry_item(body.item)
    existing = (
        client.table("shopping_list")
        .select("id")
        .eq("user_id", uid)
        .eq("item", normalized)
        .eq("checked", False)
        .execute()
    )
    if existing.data:
        return {"ok": True, "id": existing.data[0]["id"]}
    result = client.table("shopping_list").insert({
        "user_id": uid,
        "item": normalized,
        "source": body.source,
        "checked": False,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500)
    return {"ok": True, "id": result.data[0]["id"]}


@router.patch("/shopping/{item_id}/check")
def check_shopping_item(item_id: str, uid: str = Depends(require_auth)):

    client.table("shopping_list").update({"checked": True}).eq("id", item_id).eq("user_id", uid).execute()
    return {"ok": True}


@router.patch("/pantry/restock-all")
def restock_all(uid: str = Depends(require_auth)):

    items = (
        client.table("pantry")
        .select("id, desired_quantity, current_quantity")
        .eq("user_id", uid)
        .execute()
    ).data or []
    for i in [x for x in items if x["current_quantity"] < x["desired_quantity"]]:
        client.table("pantry").update({"current_quantity": i["desired_quantity"]}).eq("id", i["id"]).execute()
    return {"ok": True}


@router.patch("/pantry/{item_id}")
def update_pantry_item(item_id: str, body: PantryItemUpdate, uid: str = Depends(require_auth)):

    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        return {"ok": True}
    client.table("pantry").update(data).eq("id", item_id).eq("user_id", uid).execute()
    return {"ok": True}


@router.delete("/pantry/{item_id}")
def delete_pantry_item(item_id: str, uid: str = Depends(require_auth)):

    client.table("pantry").delete().eq("id", item_id).eq("user_id", uid).execute()
    return {"ok": True}


class RecipeIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    servings: int = Field(default=2, ge=1, le=100)


class RecipeIngredientIn(BaseModel):
    item: str = Field(min_length=1, max_length=100)
    quantity: float | None = Field(default=None, ge=0, le=10000)
    unit: str | None = Field(default=None, max_length=50)


class RecipeIngredientUpdate(BaseModel):
    item: str | None = Field(default=None, min_length=1, max_length=100)
    quantity: float | None = Field(default=None, ge=0, le=10000)
    unit: str | None = Field(default=None, max_length=50)


@router.post("/recipes")
def create_recipe_dashboard(body: RecipeIn, uid: str = Depends(require_auth)):

    result = client.table("recipes").insert({
        "user_id": uid,
        "name": body.name.strip(),
        "servings": body.servings,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500)
    return {"ok": True, "id": result.data[0]["id"]}


@router.delete("/recipes/{recipe_id}")
def delete_recipe_dashboard(recipe_id: str, uid: str = Depends(require_auth)):

    result = (
        client.table("recipes")
        .select("id")
        .eq("id", recipe_id)
        .eq("user_id", uid)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404)
    client.table("recipes").delete().eq("id", recipe_id).eq("user_id", uid).execute()
    return {"ok": True}


@router.post("/recipes/{recipe_id}/ingredients")
def add_ingredient_dashboard(
    recipe_id: str, body: RecipeIngredientIn, uid: str = Depends(require_auth)
):

    recipe = (
        client.table("recipes")
        .select("id")
        .eq("id", recipe_id)
        .eq("user_id", uid)
        .execute()
    )
    if not recipe.data:
        raise HTTPException(status_code=404)
    result = client.table("recipe_ingredients").insert({
        "recipe_id": recipe_id,
        "item": normalize_item(body.item),
        "quantity": body.quantity,
        "unit": body.unit,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500)
    return {"ok": True, "id": result.data[0]["id"]}


@router.patch("/recipes/{recipe_id}/ingredients/{ing_id}")
def update_ingredient_dashboard(
    recipe_id: str, ing_id: str, body: RecipeIngredientUpdate,
    uid: str = Depends(require_auth)
):

    recipe = (
        client.table("recipes")
        .select("id")
        .eq("id", recipe_id)
        .eq("user_id", uid)
        .execute()
    )
    if not recipe.data:
        raise HTTPException(status_code=404)
    data = body.model_dump(exclude_unset=True)
    if "item" in data and data["item"]:
        data["item"] = normalize_item(data["item"])
    if data:
        client.table("recipe_ingredients").update(data).eq("id", ing_id).eq("recipe_id", recipe_id).execute()
    return {"ok": True}


@router.delete("/recipes/{recipe_id}/ingredients/{ing_id}")
def delete_ingredient_dashboard(
    recipe_id: str, ing_id: str, uid: str = Depends(require_auth)
):

    recipe = (
        client.table("recipes")
        .select("id")
        .eq("id", recipe_id)
        .eq("user_id", uid)
        .execute()
    )
    if not recipe.data:
        raise HTTPException(status_code=404)
    client.table("recipe_ingredients").delete().eq("id", ing_id).eq("recipe_id", recipe_id).execute()
    return {"ok": True}


PLAN_DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


class MealPlanEntryIn(BaseModel):
    week_start: str
    day_of_week: str = Field(min_length=1, max_length=20)
    slot_name: str = Field(min_length=1, max_length=50)
    recipe_id: str | None = None


class SlotsUpdate(BaseModel):
    slots: list[str] = Field(min_length=1, max_length=10)

    @field_validator("slots")
    @classmethod
    def validate_slot_names(cls, v):
        for s in v:
            if len(s) < 1 or len(s) > 50:
                raise ValueError("Each slot name must be 1–50 characters")
        return v


def _get_or_create_plan(uid: str, week_start: date) -> dict:
    result = (
        client.table("meal_plans")
        .select("id, slots")
        .eq("user_id", uid)
        .eq("week_start", week_start.isoformat())
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    ins = client.table("meal_plans").insert({
        "user_id": uid,
        "week_start": week_start.isoformat(),
        "slots": ["almuerzo", "cena"],
    }).execute()
    return ins.data[0]


@router.get("/meal-plan")
def get_meal_plan(week: str | None = None, uid: str = Depends(require_auth)):

    try:
        week_start = date.fromisoformat(week) if week else date.today() - timedelta(days=date.today().weekday())
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid week date")

    plan_row = _get_or_create_plan(uid, week_start)
    entries = (
        client.table("meal_plan_entries")
        .select("id, day_of_week, slot_name, recipe_id, recipes(name)")
        .eq("meal_plan_id", plan_row["id"])
        .execute()
    ).data or []

    return {
        "plan_id": plan_row["id"],
        "week_start": week_start.isoformat(),
        "slots": plan_row.get("slots") or ["almuerzo", "cena"],
        "entries": [
            {
                "id": e["id"],
                "day_of_week": e["day_of_week"],
                "slot_name": e["slot_name"],
                "recipe_id": e["recipe_id"],
                "recipe_name": (e.get("recipes") or {}).get("name"),
            }
            for e in entries
        ],
    }


@router.post("/meal-plan/entries")
def upsert_meal_plan_entry(body: MealPlanEntryIn, uid: str = Depends(require_auth)):

    if body.day_of_week not in PLAN_DAYS:
        raise HTTPException(status_code=422, detail="Invalid day_of_week")
    try:
        week_start = date.fromisoformat(body.week_start)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid week_start")

    if body.recipe_id:
        recipe_check = (
            client.table("recipes")
            .select("id")
            .eq("id", body.recipe_id)
            .eq("user_id", uid)
            .execute()
        )
        if not recipe_check.data:
            raise HTTPException(status_code=404, detail="Recipe not found")

    plan_row = _get_or_create_plan(uid, week_start)
    plan_id = plan_row["id"]

    existing = (
        client.table("meal_plan_entries")
        .select("id")
        .eq("meal_plan_id", plan_id)
        .eq("day_of_week", body.day_of_week)
        .eq("slot_name", body.slot_name)
        .limit(1)
        .execute()
    )

    if body.recipe_id is None:
        if existing.data:
            client.table("meal_plan_entries").delete().eq("id", existing.data[0]["id"]).execute()
        return {"ok": True, "entry_id": None}

    if existing.data:
        client.table("meal_plan_entries").update({"recipe_id": body.recipe_id}).eq("id", existing.data[0]["id"]).execute()
        entry_id = existing.data[0]["id"]
    else:
        result = client.table("meal_plan_entries").insert({
            "meal_plan_id": plan_id,
            "day_of_week": body.day_of_week,
            "slot_name": body.slot_name,
            "recipe_id": body.recipe_id,
        }).execute()
        entry_id = result.data[0]["id"]

    return {"ok": True, "entry_id": entry_id}


@router.patch("/meal-plan/{plan_id}/slots")
def update_plan_slots(plan_id: str, body: SlotsUpdate, uid: str = Depends(require_auth)):

    result = (
        client.table("meal_plans")
        .select("id")
        .eq("id", plan_id)
        .eq("user_id", uid)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404)
    client.table("meal_plans").update({"slots": body.slots}).eq("id", plan_id).execute()
    return {"ok": True}


@router.post("/meal-plan/{plan_id}/shopping")
def generate_shopping(plan_id: str, uid: str = Depends(require_auth)):

    result = (
        client.table("meal_plans")
        .select("id")
        .eq("id", plan_id)
        .eq("user_id", uid)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404)

    entries = (
        client.table("meal_plan_entries")
        .select("recipe_id")
        .eq("meal_plan_id", plan_id)
        .not_.is_("recipe_id", "null")
        .execute()
    ).data or []
    recipe_ids = list({e["recipe_id"] for e in entries})

    if not recipe_ids:
        return {"added": [], "confirm": []}

    ingredients = (
        client.table("recipe_ingredients")
        .select("item, quantity, unit")
        .in_("recipe_id", recipe_ids)
        .execute()
    ).data or []

    grouped: dict[str, dict] = {}
    for ing in ingredients:
        key = normalize_pantry_item(ing["item"])
        if key not in grouped:
            grouped[key] = {"quantity": ing.get("quantity"), "unit": ing.get("unit")}
        else:
            existing = grouped[key]
            if existing["unit"] == ing.get("unit") and existing["quantity"] is not None and ing.get("quantity") is not None:
                existing["quantity"] = float(existing["quantity"]) + float(ing["quantity"])
            else:
                existing["quantity"] = None
                existing["unit"] = None
    unique_items = grouped

    pantry = (
        client.table("pantry")
        .select("id, item, current_quantity")
        .eq("user_id", uid)
        .execute()
    ).data or []
    pantry_map = {normalize_pantry_item(p["item"]): p for p in pantry}

    added = []
    confirm = []

    for item in sorted(unique_items):
        info = unique_items[item]
        qty = info["quantity"]
        unit = info["unit"]
        entry = pantry_map.get(item)
        if entry is None or entry["current_quantity"] == 0:
            existing = (
                client.table("shopping_list")
                .select("id")
                .eq("user_id", uid)
                .eq("item", item)
                .eq("checked", False)
                .execute()
            )
            if not existing.data:
                row = {"user_id": uid, "item": item, "source": "meal_plan", "checked": False}
                if qty is not None:
                    row["quantity"] = int(round(float(qty)))
                if unit:
                    row["unit"] = unit
                client.table("shopping_list").insert(row).execute()
            added.append({"item": item, "quantity": qty, "unit": unit})
        else:
            confirm.append({
                "item": item,
                "current_quantity": entry["current_quantity"],
                "pantry_id": entry["id"],
            })

    return {"added": added, "confirm": confirm}


@router.patch("/pantry/{item_id}/restock")
def restock_pantry_item(item_id: str, uid: str = Depends(require_auth)):

    result = (
        client.table("pantry")
        .select("desired_quantity")
        .eq("id", item_id)
        .eq("user_id", uid)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404)
    desired = result.data[0]["desired_quantity"]
    client.table("pantry").update({"current_quantity": desired}).eq("id", item_id).eq("user_id", uid).execute()
    return {"ok": True}
