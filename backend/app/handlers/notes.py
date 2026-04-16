from app.db import client
from app.mcp import client as mcp


def add_note(content: str, user: dict) -> str:
    context_id = mcp.send_context("note", user["id"], {"content": content})
    try:
        client.table("notes").insert({"user_id": user["id"], "content": content}).execute()
        mcp.confirm(context_id)
    except Exception:
        mcp.rollback(context_id)
        raise
    return f"✓ Nota guardada: {content}"


def list_notes(user: dict) -> str:
    result = (
        client.table("notes")
        .select("content")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    items = result.data or []
    if not items:
        return "No tienes notas."
    lines = ["*Tus notas:*"] + [f"• {item['content']}" for item in items]
    return "\n".join(lines)


def search_notes(keyword: str, user: dict) -> str:
    result = (
        client.table("notes")
        .select("content")
        .eq("user_id", user["id"])
        .ilike("content", f"%{keyword}%")
        .execute()
    )
    items = result.data or []
    if not items:
        return f"No encontré notas con '{keyword}'."
    lines = [f"*Notas con '{keyword}':*"] + [f"• {item['content']}" for item in items]
    return "\n".join(lines)
