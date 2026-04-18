from datetime import date, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db import client
from app.handlers.summary import aggregate_by_category
from app.middleware.auth import require_auth


router = APIRouter(prefix="/dashboard")

DAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _get_user_id(phone: str) -> str:
    result = client.table("users").select("id").eq("phone", phone).execute()
    if not result.data:
        raise HTTPException(status_code=401)
    return result.data[0]["id"]


@router.get("")
def get_dashboard(phone: str = Depends(require_auth)):
    uid = _get_user_id(phone)

    today = date.today()
    monday = today - timedelta(days=today.weekday())

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

    budget_result = (
        client.table("budgets")
        .select("amount")
        .eq("user_id", uid)
        .eq("period", "semana")
        .execute()
    )
    weekly_budget = float(budget_result.data[0]["amount"]) if budget_result.data else None

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
        }
        for i in pantry_items
        if i["current_quantity"] < i["desired_quantity"]
    ]

    despensa = {"cocina": [], "baño": [], "otros": []}
    for i in pantry_items:
        despensa[i["category"]].append({
            "id": i["id"],
            "item": i["item"],
            "current_quantity": i["current_quantity"],
            "desired_quantity": i["desired_quantity"],
        })

    return {
        "gastos": {
            "weekly_total": weekly_total,
            "weekly_budget": weekly_budget,
            "by_day": by_day_list,
            "by_category": by_category_list,
        },
        "pendientes": pendientes,
        "esperando": esperando,
        "compras": compras,
        "despensa": despensa,
    }


@router.patch("/todos/{todo_id}/complete")
def complete_todo(todo_id: str, phone: str = Depends(require_auth)):
    uid = _get_user_id(phone)
    client.table("todos").update({"done": True}).eq("id", todo_id).eq("user_id", uid).execute()
    return {"ok": True}


@router.patch("/waiting_on/{item_id}/resolve")
def resolve_waiting(item_id: str, phone: str = Depends(require_auth)):
    uid = _get_user_id(phone)
    client.table("waiting_on").update({"resolved": True}).eq("id", item_id).eq("user_id", uid).execute()
    return {"ok": True}


class PantryItemIn(BaseModel):
    item: str
    desired_quantity: int
    category: Literal["cocina", "baño", "otros"] = "otros"


class PantryItemUpdate(BaseModel):
    desired_quantity: int | None = None
    category: Literal["cocina", "baño", "otros"] | None = None


@router.post("/pantry")
def create_pantry_item(body: PantryItemIn, phone: str = Depends(require_auth)):
    uid = _get_user_id(phone)
    result = client.table("pantry").insert({
        "user_id": uid,
        "item": body.item,
        "desired_quantity": body.desired_quantity,
        "current_quantity": body.desired_quantity,
        "category": body.category,
    }).execute()
    return {"ok": True, "id": result.data[0]["id"]}


@router.patch("/pantry/restock-all")
def restock_all(phone: str = Depends(require_auth)):
    uid = _get_user_id(phone)
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
def update_pantry_item(item_id: str, body: PantryItemUpdate, phone: str = Depends(require_auth)):
    uid = _get_user_id(phone)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        return {"ok": True}
    client.table("pantry").update(data).eq("id", item_id).eq("user_id", uid).execute()
    return {"ok": True}


@router.delete("/pantry/{item_id}")
def delete_pantry_item(item_id: str, phone: str = Depends(require_auth)):
    uid = _get_user_id(phone)
    client.table("pantry").delete().eq("id", item_id).eq("user_id", uid).execute()
    return {"ok": True}


@router.patch("/pantry/{item_id}/restock")
def restock_pantry_item(item_id: str, phone: str = Depends(require_auth)):
    uid = _get_user_id(phone)
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
