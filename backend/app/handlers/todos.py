from app.db import client


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
        buckets[item["priority"]].append(item["task"])
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
    match = next((i for i in items if task_fragment.lower() in i["task"].lower()), None)
    if not match:
        return f"No encontré un pendiente con '{task_fragment}'."
    client.table("todos").update({"done": True}).eq("id", match["id"]).execute()
    return f"✓ Listo: {match['task']}"
