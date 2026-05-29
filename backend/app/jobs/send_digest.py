"""Daily digest cron job.

Sends a morning interactive message with a Continuar quick-reply button
to every user who has the recordatorios module enabled (or no row, which
defaults to enabled) and has at least one reminder due today or open todo.

Entrypoint: python -m app.jobs.send_digest
Railway schedule: cron 0 13 * * * (13:00 UTC = 9:00 AM America/Santiago
standard time; adjust manually for DST if needed).

Delivery notes:
  - send_interactive() only works inside Meta's 24-hour customer-service
    window. A False return means the window was closed; the user resumes
    by messaging Cazuela next time. This is the accepted failure mode —
    do not treat it as an error or abort the run for remaining users.
  - The Continuar button tap is a plain inbound message. Receiving it
    resets the 24-hour window for another day.
"""
import warnings
from datetime import datetime, timezone

from app.config import TZ as _TZ
from app.db import client
from app.notify import send_interactive

_EXPLANATION = (
    "_Cazuela te saluda cada mañana para mantener activos tus "
    "recordatorios del día. Si en algún momento dejas de recibir "
    "mensajes, escríbele cualquier cosa y se reactivan._"
)


def _recordatorios_enabled(user_id: str) -> bool:
    result = (
        client.table("user_modules")
        .select("enabled")
        .eq("user_id", user_id)
        .eq("module", "recordatorios")
        .execute()
    )
    rows = result.data or []
    if not rows:
        return True
    return bool(rows[0]["enabled"])


def _reminders_due_today(user_id: str) -> tuple[list[dict], frozenset]:
    now = datetime.now(_TZ)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    result = (
        client.table("todos")
        .select("id, task, remind_at")
        .eq("user_id", user_id)
        .eq("done", False)
        .eq("remind_sent", False)
        .lte("remind_at", day_end.astimezone(timezone.utc).isoformat())
        .gte("remind_at", day_start.astimezone(timezone.utc).isoformat())
        .order("remind_at")
        .execute()
    )
    todo_rows = result.data or []
    todo_reminder_ids = frozenset(r["id"] for r in todo_rows)
    todo_reminders = [
        {
            "title": r["task"],
            "time": datetime.fromisoformat(r["remind_at"]).astimezone(_TZ).strftime("%H:%M"),
        }
        for r in todo_rows
    ]
    event_result = (
        client.table("events")
        .select("title, remind_at")
        .eq("user_id", user_id)
        .eq("remind_sent", False)
        .lte("remind_at", day_end.astimezone(timezone.utc).isoformat())
        .gte("remind_at", day_start.astimezone(timezone.utc).isoformat())
        .order("remind_at")
        .execute()
    )
    event_reminders = [
        {
            "title": r["title"],
            "time": datetime.fromisoformat(r["remind_at"]).astimezone(_TZ).strftime("%H:%M"),
        }
        for r in (event_result.data or [])
    ]
    return todo_reminders + event_reminders, todo_reminder_ids


def _open_todos(user_id: str, exclude_ids: frozenset = frozenset()) -> list[str]:
    result = (
        client.table("todos")
        .select("id, task")
        .eq("user_id", user_id)
        .eq("done", False)
        .order("created_at")
        .execute()
    )
    return [r["task"] for r in (result.data or []) if r["id"] not in exclude_ids]


def _build_body(reminders: list[dict], todos: list[str]) -> str:
    parts = ["☀️ Buenos días"]
    if reminders:
        parts.append("\n⏰ *Recordatorios de hoy:*")
        for r in reminders:
            parts.append(f"• {r['title']} ({r['time']})")
    if todos:
        parts.append("\n📋 *Pendientes:*")
        for t in todos:
            parts.append(f"• {t}")
    parts.append(f"\n{_EXPLANATION}")
    return "\n".join(parts)


def _all_users() -> list[dict]:
    result = client.table("users").select("id, phone").execute()
    return result.data or []


def main() -> None:
    users = _all_users()
    sent = 0
    skipped_empty = 0
    skipped_disabled = 0
    failed = 0

    for user in users:
        user_id = user["id"]
        phone = user["phone"]

        if not _recordatorios_enabled(user_id):
            skipped_disabled += 1
            continue

        reminders, todo_reminder_ids = _reminders_due_today(user_id)
        todos = _open_todos(user_id, exclude_ids=todo_reminder_ids)

        if not reminders and not todos:
            skipped_empty += 1
            continue

        body = _build_body(reminders, todos)
        ok = send_interactive(phone, body, ["Continuar"])
        if ok:
            sent += 1
        else:
            failed += 1

    warnings.warn(
        f"send_digest complete: sent={sent} skipped_empty={skipped_empty} "
        f"skipped_disabled={skipped_disabled} window_closed={failed}",
        stacklevel=1,
    )


if __name__ == "__main__":
    main()
