"""iCal feed — read-only per-user calendar subscription.

Public API:
- GET /calendar/{token}.ics  → text/calendar (VCALENDAR)

The token is an unguessable URL-safe secret stored on the user row.
It is generated lazily on the first call to generate_calendar_token().
No session auth is required — the token itself is the credential.
"""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.db import client

router = APIRouter()

_VCAL_HEADER = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "PRODID:-//Cazuela//ES\r\n"
    "CALSCALE:GREGORIAN\r\n"
    "METHOD:PUBLISH\r\n"
)
_VCAL_FOOTER = "END:VCALENDAR\r\n"


def _fold(line: str) -> str:
    """Fold long iCal lines at 75 octets per RFC 5545.

    Walks back from the 75-byte boundary to avoid splitting multi-byte
    UTF-8 codepoints (e.g. ñ, ó, emoji).
    """
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line + "\r\n"
    parts = []
    while len(encoded) > 75:
        cut = 75
        while cut > 0 and (encoded[cut] & 0xC0) == 0x80:
            cut -= 1
        parts.append(encoded[:cut].decode("utf-8"))
        encoded = encoded[cut:]
    parts.append(encoded.decode("utf-8"))
    return "\r\n ".join(parts) + "\r\n"


def _format_dt(iso: str) -> str:
    dt = datetime.fromisoformat(iso).astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def generate_calendar_token(user_id: str) -> str:
    result = (
        client.table("users")
        .select("calendar_token")
        .eq("id", user_id)
        .execute()
    )
    row = (result.data or [{}])[0]
    token = row.get("calendar_token")
    if not token:
        token = secrets.token_urlsafe(32)
        client.table("users").update({"calendar_token": token}).eq("id", user_id).execute()
    return token


@router.get("/calendar/{token}.ics")
def ical_feed(token: str):
    result = (
        client.table("users")
        .select("id")
        .eq("calendar_token", token)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404)
    user_id = result.data[0]["id"]

    now_iso = datetime.now(timezone.utc).isoformat()
    events_result = (
        client.table("events")
        .select("id, title, starts_at, ends_at, category")
        .eq("user_id", user_id)
        .gte("starts_at", now_iso)
        .order("starts_at")
        .limit(200)
        .execute()
    )
    events = events_result.data or []

    lines = [_VCAL_HEADER]
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for ev in events:
        dtstart = _format_dt(ev["starts_at"])
        dtend = _format_dt(ev["ends_at"]) if ev.get("ends_at") else dtstart
        uid = f"{ev['id']}@cazuela"
        vevent = (
            "BEGIN:VEVENT\r\n"
            + _fold(f"UID:{uid}")
            + _fold(f"DTSTAMP:{now_stamp}")
            + _fold(f"DTSTART:{dtstart}")
            + _fold(f"DTEND:{dtend}")
            + _fold(f"SUMMARY:{ev['title']}")
            + "END:VEVENT\r\n"
        )
        lines.append(vevent)
    lines.append(_VCAL_FOOTER)

    return Response(
        content="".join(lines),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=cazuela.ics"},
    )
