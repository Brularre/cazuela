"""Reminder button-reply handler — TIEMPO/RECORDATORIOS feature.

Public API:
  handle_snooze_reply(button_id, user) -> str | None
    Parses a WhatsApp button_reply id of the form:
      "snooze:{table}:{item_id}:{minutes}"  — postpone the reminder
      "done:{table}:{item_id}"              — acknowledge as done

    snooze: updates remind_at to now + minutes, resets remind_sent to
            False so the cron will fire again.
    done/todos: marks the todo done=True by id (direct lookup, no fuzzy
                match).
    done/events: acknowledges without mutating the event.
    Unrecognised id: returns None so the caller can fall through to the
                     normal text router.

Tables touched: todos, events.
"""
from datetime import datetime, timedelta, timezone

from app.db import client


def handle_snooze_reply(button_id: str, user: dict) -> str | None:
    parts = button_id.split(":")
    if len(parts) < 3:
        return None

    action = parts[0]

    if action == "snooze":
        if len(parts) != 4:
            return None
        _, table, item_id, minutes_str = parts
        if table not in ("todos", "events"):
            return None
        try:
            minutes = int(minutes_str)
        except ValueError:
            return None
        new_remind_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        client.table(table).update({
            "remind_at": new_remind_at.isoformat(),
            "remind_sent": False,
        }).eq("id", item_id).execute()
        return f"⏰ Te recuerdo en {minutes} min."

    if action == "done":
        if len(parts) != 3:
            return None
        _, table, item_id = parts
        if table == "todos":
            client.table("todos").update({"done": True}).eq("id", item_id).execute()
            return "✅ Listo."
        if table == "events":
            return "✅ Listo."
        return None

    return None
