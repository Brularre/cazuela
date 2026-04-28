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
"""
from app.db import client
from app.handlers.utils import find_first_substring


def add_todo(task: str, user: dict, priority: str = "semana") -> str:
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
