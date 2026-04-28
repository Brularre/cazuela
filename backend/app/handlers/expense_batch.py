"""
Expense batch handler — DINERO feature (supermercado multi-item).

Handles the "gasté/pagué N en el súper: X, Y, Z" three-step MCP flow:

  1. handle_batch_create(raw_message, total_amount, items_csv, user)
     Creates an expense_batch MCP context containing the raw message,
     total amount, and items CSV. Runs 3 MCP iterations to get a final
     proposed breakdown. Returns (context_id, preview_text).

  2. handle_batch_confirm(context_id, user)
     Reads the confirmed context; inserts one expenses row per item.

  3. handle_batch_cancel(context_id, user)
     Rolls back the pending context — nothing is persisted.

Internal:
  _user_history_for(user_id) -> dict
    Returns category frequency from the past 30 days to bias the
    agent's category guesses toward the user's spending pattern.
"""
from datetime import date, timedelta

from app.db import client
from app.mcp import client as mcp


def handle_batch_create(
    raw_message: str, total_amount: float, items_csv: str, user: dict
) -> tuple[str, str]:
    context_id = mcp.send_context(
        "expense_batch",
        user["id"],
        {
            "raw_message": raw_message,
            "total_amount": total_amount,
            "items_csv": items_csv,
            "date": str(date.today()),
            "user_history": _user_history_for(user["id"]),
        },
    )
    last = None
    for _ in range(3):
        last = mcp.request_action(context_id)
    proposed = (last or {}).get("proposed") or {}
    if proposed.get("step") != 3:
        raise ValueError("flujo batch incompleto")
    items = proposed.get("items", [])
    lines = []
    for it in items:
        lines.append(
            f"• {it.get('name', '')}: {it.get('category', 'otros')} — "
            f"${it.get('amount', 0):,.0f}".replace(",", ".")
        )
    body = "\n".join(lines)
    reply = (
        f"Supermercado (${total_amount:,.0f} total):\n".replace(",", ".")
        + f"{body}\n\n"
        "Responde *confirmar* para guardar cada ítem o *cancelar*."
    )
    return context_id, reply


def handle_batch_confirm(context_id: str, user: dict) -> str:
    try:
        ctx = mcp.receive_result(context_id)
    except (ValueError, KeyError):
        return "Este gasto ya fue confirmado, cancelado, o expiró."
    proposed = ctx.get("proposed") or {}
    if proposed.get("step") != 3:
        return "El desglose no está listo; cancela e intenta de nuevo."
    items = proposed.get("items", [])
    payload = ctx.get("payload", {})
    raw_message = payload.get("raw_message", "")
    day = payload.get("date") or str(date.today())
    try:
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Este gasto ya fue confirmado, cancelado, o expiró."
    for it in items:
        amt = float(it.get("amount", 0))
        note = f"{raw_message} — {it.get('name', '')}"
        client.table("expenses").insert({
            "user_id": user["id"],
            "amount": amt,
            "category": it.get("category", "otros"),
            "note": note,
            "date": day,
        }).execute()
    parts = [
        f"${float(it.get('amount', 0)):,.0f} · {it.get('category', 'otros')}".replace(",", ".")
        for it in items
    ]
    return "✓ Gastos guardados (supermercado)\n" + "\n".join(parts)


def handle_batch_cancel(context_id: str, user: dict) -> str:
    try:
        mcp.rollback(context_id)
    except ValueError:
        return "Este gasto ya fue confirmado, cancelado, o expiró."
    return "Listado de supermercado cancelado."


def _user_history_for(user_id: str) -> dict:
    since = str(date.today() - timedelta(days=30))
    result = (
        client.table("expenses")
        .select("category")
        .eq("user_id", user_id)
        .gte("date", since)
        .execute()
    )
    history = {}
    for row in result.data or []:
        cat = row["category"]
        history[cat] = history.get(cat, 0) + 1
    return history
