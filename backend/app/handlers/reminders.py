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

  stage_reminder(fragment, remind_at, user, recur=None, ambiguous=False) -> str
    Stages a reminder_set MCP context echoing the parsed interpretation
    and returns a confirmation prompt. Nothing is written until the user
    confirms, so a misparsed time/task can be cancelled instead of
    silently creating a wrong reminder. When ambiguous is set (a 12h hour
    given with no am/pm qualifier), appends a correction hint.

  confirm_reminder(context_id, user, ctx) -> str
    Commits a staged reminder_set context: attaches the reminder to a
    matching todo, then a matching event, else creates a new todo.

  cancel_reminder(context_id, user) -> str
    Rolls back a staged reminder_set context.

Tables touched: todos, events.
"""
from datetime import datetime, timedelta, timezone

from app.config import TZ as _TZ
from app.db import client
from app.mcp import client as mcp
from app.handlers.todos import set_todo_reminder, create_todo_reminder
from app.handlers.events import set_event_reminder


def _format_when(remind_at: datetime, recur: str | None) -> str:
    time_str = remind_at.astimezone(_TZ).strftime("%d/%m %H:%M")
    return f"{time_str} (se repite)" if recur else time_str


def _ambiguity_hint(remind_at: datetime) -> str | None:
    hour = remind_at.astimezone(_TZ).hour
    if 13 <= hour <= 19:
        alt = hour - 12
        return f"_Asumí la tarde. Si era a las {alt} de la mañana, escribe *{alt} am*._"
    if 8 <= hour <= 11:
        return f"_Asumí la mañana. Si era a las {hour} de la noche, escribe *{hour} pm*._"
    return None


def stage_reminder(
    fragment: str,
    remind_at: datetime,
    user: dict,
    recur: str | None = None,
    ambiguous: bool = False,
) -> str:
    context_id = mcp.send_context("reminder_set", user["id"], {
        "fragment": fragment,
        "remind_at": remind_at.isoformat(),
        "recur": recur,
    })
    mcp.request_action(context_id)
    lines = [f"⏰ ¿Te recuerdo *{fragment}* el {_format_when(remind_at, recur)}?"]
    if ambiguous and (hint := _ambiguity_hint(remind_at)):
        lines.append(hint)
    lines.append("Responde *sí* para confirmar o *no* para cancelar.")
    return "\n".join(lines)


def confirm_reminder(context_id: str, user: dict, ctx: dict) -> str:
    payload = ctx.get("payload", {})
    fragment = payload.get("fragment", "")
    remind_at_raw = payload.get("remind_at")
    recur = payload.get("recur")
    if not fragment or not remind_at_raw:
        return "No pude recuperar el recordatorio. Intenta de nuevo."
    remind_at = datetime.fromisoformat(remind_at_raw)
    try:
        mcp.confirm(context_id)
    except (ValueError, KeyError):
        return "Este recordatorio ya fue confirmado, cancelado, o expiró."
    result = set_todo_reminder(fragment, remind_at, user, recur=recur)
    if result is None:
        result = set_event_reminder(fragment, remind_at, user, recur=recur)
    if result is None:
        result = create_todo_reminder(fragment, remind_at, user, recur=recur)
    return result


def cancel_reminder(context_id: str, user: dict) -> str:
    try:
        mcp.rollback(context_id)
    except ValueError:
        return "Este recordatorio ya fue confirmado, cancelado, o expiró."
    return "Recordatorio cancelado."


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
