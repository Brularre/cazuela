from app.db import client
from app.mcp import client as mcp


def add_todo(task: str, user: dict) -> str:
    context_id = mcp.send_context("todo", user["id"], {"task": task, "due_date": None})
    mcp.confirm(context_id)
    client.table("todos").insert({"user_id": user["id"], "task": task}).execute()
    return f"✓ Pendiente guardado: {task}"


def list_todos(user: dict) -> str:
    result = client.table("todos").select("task, done").eq("user_id", user["id"]).eq("done", False).execute()
    items = result.data or []
    if not items:
        return "No tienes pendientes."
    lines = ["*Tus pendientes:*"] + [f"• {item['task']}" for item in items]
    return "\n".join(lines)


def complete_todo(task_fragment: str, user: dict) -> str:
    result = client.table("todos").select("id, task").eq("user_id", user["id"]).eq("done", False).execute()
    items = result.data or []
    match = next((i for i in items if task_fragment.lower() in i["task"].lower()), None)
    if not match:
        return f"No encontré un pendiente con '{task_fragment}'."
    client.table("todos").update({"done": True}).eq("id", match["id"]).execute()
    return f"✓ Listo: {match['task']}"
