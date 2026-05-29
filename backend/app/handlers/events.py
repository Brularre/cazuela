"""
Events handler — CALENDARIO feature.

Public API:
  add_event(title, starts_at, user, ends_at=None, category='otro') -> str
    Creates a calendar event. starts_at must be a UTC-aware datetime.

  list_events(user) -> str
    Returns upcoming events ordered by starts_at.

  delete_event(title_fragment, user) -> str
    Fuzzy-match by substring; hard-deletes the first upcoming match.

Time parsing:
  parse_event_time(text) -> datetime | None
    Accepts a small, well-tested set of Spanish phrasings and returns a
    UTC-aware datetime anchored to America/Santiago. Returns None on
    anything unrecognised. D2.2 will expand this into timeparse.py.
"""
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.db import client
from app.handlers.utils import find_first_substring

_TZ = ZoneInfo("America/Santiago")

_TIME_RE = re.compile(
    r"(?:hoy|mañana|manana)?\s*a\s+las?\s+(\d{1,2})(?::(\d{2}))?(?:\s*hrs?)?",
    re.IGNORECASE,
)
_TOMORROW_RE = re.compile(r"mañana|manana", re.IGNORECASE)


def parse_event_time(text: str) -> datetime | None:
    m = _TIME_RE.search(text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    now = datetime.now(_TZ)
    base = now.date()
    if _TOMORROW_RE.search(text):
        base = base + timedelta(days=1)
    local = datetime(base.year, base.month, base.day, hour, minute, tzinfo=_TZ)
    if local <= now and not _TOMORROW_RE.search(text):
        local += timedelta(days=1)
    return local.astimezone(timezone.utc)


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
