from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from app.db import client
from app.handlers.summary import aggregate_by_category
from app.middleware.auth import require_auth


router = APIRouter(prefix="/dashboard")

DAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _get_user_id(phone: str) -> str:
    result = client.table("users").select("id").eq("phone", phone).execute()
    if not result.data:
        raise HTTPException(status_code=404)
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

    return {
        "gastos": {
            "weekly_total": weekly_total,
            "by_day": by_day_list,
            "by_category": by_category_list,
        },
        "pendientes": pendientes,
        "esperando": esperando,
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
