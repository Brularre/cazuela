"""
Events handler — CALENDARIO feature.

Public API:
  add_event(title, starts_at, user, ends_at=None, category='otro') -> str
    Creates a calendar event. starts_at must be a UTC-aware datetime.

  list_events(user) -> str
    Returns upcoming events ordered by starts_at.

  delete_event(title_fragment, user) -> str
    Fuzzy-match by substring; hard-deletes the first upcoming match.

  set_event_reminder(title_fragment, remind_at, user) -> str | None
    Fuzzy-match by substring on upcoming events; writes remind_at and
    resets remind_sent to False. Returns None if no match found.

  parse_event_time(text, now=None) -> datetime | None
    Thin wrapper around timeparse.parse_time. Kept for backwards compat.
"""
from datetime import datetime, timezone

from app.config import TZ as _TZ
from app.db import client
from app.handlers.timeparse import parse_time
from app.handlers.utils import find_first_substring


def parse_event_time(text: str, now: datetime | None = None) -> datetime | None:
    return parse_time(text, now=now)


def add_event(title: str, starts_at: datetime, user: dict, ends_at=None, category: str = "otro") -> str:
    client.table("events").insert({
        "user_id": user["id"],
        "title": title.strip()[:200],
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat() if ends_at else None,
        "category": category,
    }).execute()
    time_str = starts_at.astimezone(_TZ).strftime("%d/%m %H:%M")
    return f"📅 Evento guardado: {title.strip()} ({time_str})"


def list_events(user: dict) -> str:
    now = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("events")
        .select("title, starts_at, category")
        .eq("user_id", user["id"])
        .gte("starts_at", now)
        .order("starts_at")
        .limit(20)
        .execute()
    )
    items = result.data or []
    if not items:
        return "No tienes eventos próximos."
    lines = ["*Próximos eventos:*"]
    for e in items:
        dt = datetime.fromisoformat(e["starts_at"]).astimezone(_TZ)
        lines.append(f"• {e['title']} — {dt.strftime('%d/%m %H:%M')}")
    return "\n".join(lines)


def delete_event(title_fragment: str, user: dict) -> str:
    now = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("events")
        .select("id, title")
        .eq("user_id", user["id"])
        .gte("starts_at", now)
        .execute()
    )
    items = result.data or []
    match = find_first_substring(items, title_fragment, "title")
    if not match:
        return f"No encontré un evento con '{title_fragment}'."
    client.table("events").delete().eq("id", match["id"]).execute()
    return f"✓ Evento eliminado: {match['title']}"


def set_event_reminder(title_fragment: str, remind_at: datetime, user: dict) -> str | None:
    now = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("events")
        .select("id, title")
        .eq("user_id", user["id"])
        .gte("starts_at", now)
        .execute()
    )
    items = result.data or []
    match = find_first_substring(items, title_fragment, "title")
    if not match:
        return None
    client.table("events").update({
        "remind_at": remind_at.isoformat(),
        "remind_sent": False,
    }).eq("id", match["id"]).execute()
    time_str = remind_at.astimezone(_TZ).strftime("%d/%m %H:%M")
    return f"⏰ Recordatorio guardado: {match['title']} ({time_str})"
