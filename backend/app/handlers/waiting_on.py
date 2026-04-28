"""
Waiting-on handler — TIEMPO feature.

Public API:
  add_waiting(description, user) -> str
    Creates a new waiting_on row with resolved=False.

  list_waiting(user) -> str
    Returns all unresolved items in chronological order.

  resolve_waiting(fragment, user) -> str
    Fuzzy-match by substring; marks first match as resolved=True.
"""
from app.db import client
    client.table("waiting_on").insert({
        "user_id": user["id"],
        "description": description,
    }).execute()
    return f"✓ Guardado: esperando {description}"


def list_waiting(user: dict) -> str:
    result = (
        client.table("waiting_on")
        .select("description")
        .eq("user_id", user["id"])
        .eq("resolved", False)
        .order("created_at", desc=False)
        .execute()
    )
    items = result.data or []
    if not items:
        return "No tienes nada esperando."
    lines = ["*Esperando:*"] + [f"• {item['description']}" for item in items]
    return "\n".join(lines)


def resolve_waiting(fragment: str, user: dict) -> str:
    result = (
        client.table("waiting_on")
        .select("id, description")
        .eq("user_id", user["id"])
        .eq("resolved", False)
        .execute()
    )
    items = result.data or []
    match = next((i for i in items if fragment.lower() in i["description"].lower()), None)
    if not match:
        return f"No encontré '{fragment}' en tus esperas."
    client.table("waiting_on").update({"resolved": True}).eq("id", match["id"]).execute()
    return f"✓ Resuelto: {match['description']}"
