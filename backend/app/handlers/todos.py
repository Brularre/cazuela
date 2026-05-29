"""
Todos handler — TIEMPO feature.

Public API:
  add_todo(task, user, priority='semana') -> str
    Creates a new todo. priority must be 'hoy', 'semana', or 'mes'.

  list_todos(user) -> str
    Returns open todos grouped by priority (hoy → semana → mes).

  complete_todo(task_fragment, user) -> str
    Fuzzy-match by substring; marks first match as done=True.

  delete_todo(task_fragment, user) -> str
    Fuzzy-match by substring; hard-deletes first match.

  set_todo_reminder(task_fragment, remind_at, user, recur=None) -> str | None
    Fuzzy-match by substring on open todos; writes remind_at, resets
    remind_sent to False, and optionally sets recur. Passing recur=None
    explicitly sets the column to null (clearing any existing recurrence).
    Returns None if no match found (caller may try events next).
    Appends " (se repite)" to the confirmation when recur is set.
"""
from datetime import datetime

from app.config import TZ as _TZ
from app.db import client
from app.handlers.utils import find_first_substring


def add_todo(task: str, user: dict, priority: str = "semana") -> str:
    task = task.strip()[:200]
    client.table("todos").insert({
        "user_id": user["id"],
        "task": task,
        "priority": priority,
    }).execute()
    return f"✓ Pendiente guardado: {task}"


def list_todos(user: dict) -> str:
    result = (
        client.table("todos")
        .select("task, priority")
        .eq("user_id", user["id"])
        .eq("done", False)
        .execute()
    )
    items = result.data or []
    if not items:
        return "No tienes pendientes."
    buckets = {"hoy": [], "semana": [], "mes": []}
    for item in items:
        key = item.get("priority") if item.get("priority") in buckets else "semana"
        buckets[key].append(item["task"])
    labels = {"hoy": "*Hoy:*", "semana": "*Esta semana:*", "mes": "*Este mes:*"}
    lines = []
    for key in ("hoy", "semana", "mes"):
        if buckets[key]:
            lines.append(labels[key])
            lines.extend(f"• {t}" for t in buckets[key])
    return "\n".join(lines)


def complete_todo(task_fragment: str, user: dict) -> str:
    result = client.table("todos").select("id, task").eq("user_id", user["id"]).eq("done", False).execute()
    items = result.data or []
    match = find_first_substring(items, task_fragment, "task")
    if not match:
        return f"No encontré un pendiente con '{task_fragment}'."
    client.table("todos").update({"done": True}).eq("id", match["id"]).execute()
    return f"✓ Listo: {match['task']}"


def delete_todo(task_fragment: str, user: dict) -> str:
    result = client.table("todos").select("id, task").eq("user_id", user["id"]).eq("done", False).execute()
    items = result.data or []
    match = find_first_substring(items, task_fragment, "task")
    if not match:
        return f"No encontré un pendiente con '{task_fragment}'."
    client.table("todos").delete().eq("id", match["id"]).execute()
    return f"✓ Borrado: {match['task']}"


def set_todo_reminder(task_fragment: str, remind_at: datetime, user: dict, recur: str | None = None) -> str | None:
    result = client.table("todos").select("id, task").eq("user_id", user["id"]).eq("done", False).execute()
    items = result.data or []
    match = find_first_substring(items, task_fragment, "task")
    if not match:
        return None
    update = {
        "remind_at": remind_at.isoformat(),
        "remind_sent": False,
        "recur": recur,
    }
    client.table("todos").update(update).eq("id", match["id"]).execute()
    time_str = remind_at.astimezone(_TZ).strftime("%d/%m %H:%M")
    msg = f"⏰ Recordatorio guardado: {match['task']} ({time_str})"
    if recur:
        msg += " (se repite)"
    return msg
