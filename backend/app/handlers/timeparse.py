"""Natural-language time parser for Spanish WhatsApp messages.

Public API:
  parse_time(text, now=None) -> datetime | None
    Parses a small, fixed set of Spanish time phrasings and returns
    a UTC-aware datetime. Returns None if unrecognised or in the past.

  extract_fragment(text) -> str
    Strips the recognized time phrase from text, returning the
    task/event fragment. Used when parsing reminder commands.

  parse_iso(iso_str, now=None) -> datetime | None
    Validates an ISO 8601 datetime string (from the AI classifier).
    Ensures it is a future UTC-aware datetime. Returns None on failure.

Supported phrasings (manual mode):
  - hoy a las HH[:MM]            today at given time
  - mañana a las HH[:MM]         tomorrow at given time
  - el WEEKDAY a las HH[:MM]     next occurrence of named weekday
  - en N horas / en N minutos    relative offset from now

All outputs normalised to America/Santiago and stored as UTC timestamptz.
Accent variants accepted: miercoles / miércoles, sabado / sábado, manana / mañana.
"""
import re
from datetime import datetime, timedelta, timezone

from app.config import TZ as _TZ

_WEEKDAY_MAP = {
    "lunes": 0,
    "martes": 1,
    "miércoles": 2,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sábado": 5,
    "sabado": 5,
    "domingo": 6,
}

_TIME_PART = r"(?:a\s+las?\s+)?(\d{1,2})(?::(\d{2}))?(?:\s*hrs?)?"

_HOY_MANANA_RE = re.compile(
    r"\b(hoy|ma[nñ]ana)\b\s*" + _TIME_PART,
    re.IGNORECASE,
)
_WEEKDAY_RE = re.compile(
    r"\b(?:el\s+)?(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b\s*" + _TIME_PART,
    re.IGNORECASE,
)
_RELATIVE_RE = re.compile(
    r"\ben\s+(\d+)\s+(horas?|minutos?|mins?)\b",
    re.IGNORECASE,
)


def _as_santiago(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_TZ)
    return dt.astimezone(_TZ)


def _build_local(base_date, hour: int, minute: int) -> datetime:
    return datetime(base_date.year, base_date.month, base_date.day, hour, minute, tzinfo=_TZ)


def _parse_hhmm(h_str: str, min_str: str | None) -> tuple[int, int] | None:
    hour, minute = int(h_str), int(min_str or 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def parse_time(text: str, now: datetime | None = None) -> datetime | None:
    now_local = _as_santiago(now) if now is not None else datetime.now(_TZ)

    m = _RELATIVE_RE.search(text)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower().rstrip("s")
        delta = timedelta(hours=n) if unit.startswith("hora") else timedelta(minutes=n)
        return (now_local + delta).astimezone(timezone.utc)

    m = _HOY_MANANA_RE.search(text)
    if m:
        anchor, h_str, min_str = m.group(1).lower(), m.group(2), m.group(3)
        hm = _parse_hhmm(h_str, min_str)
        if hm is None:
            return None
        hour, minute = hm
        base = now_local.date()
        if anchor in ("mañana", "manana"):
            base = base + timedelta(days=1)
        local = _build_local(base, hour, minute)
        if local <= now_local:
            return None
        return local.astimezone(timezone.utc)

    m = _WEEKDAY_RE.search(text)
    if m:
        weekday_str = m.group(1).lower()
        h_str, min_str = m.group(2), m.group(3)
        if h_str is None:
            return None
        hm = _parse_hhmm(h_str, min_str)
        if hm is None:
            return None
        hour, minute = hm
        target_wd = _WEEKDAY_MAP.get(weekday_str)
        if target_wd is None:
            return None
        today_wd = now_local.weekday()
        days_ahead = (target_wd - today_wd) % 7
        if days_ahead == 0:
            candidate = _build_local(now_local.date(), hour, minute)
            if candidate <= now_local:
                days_ahead = 7
        base = now_local.date() + timedelta(days=days_ahead)
        local = _build_local(base, hour, minute)
        if local <= now_local:
            return None
        return local.astimezone(timezone.utc)

    return None


def extract_fragment(text: str) -> str:
    """Strip the recognized time phrase from text, returning the task fragment.

    Finds the earliest time phrase in text (hoy/mañana, weekday, or relative),
    removes it (and the text after it), and returns what remains stripped.
    Used to split 'llamar al banco mañana a las 10' into 'llamar al banco'.
    """
    best_start = None
    best_end = None
    for pattern in (_RELATIVE_RE, _HOY_MANANA_RE, _WEEKDAY_RE):
        m = pattern.search(text)
        if m and (best_start is None or m.start() < best_start):
            best_start = m.start()
            best_end = m.end()
    if best_start is None:
        return text.strip()
    fragment = (text[:best_start] + text[best_end:]).strip().rstrip(",").strip()
    return fragment


def parse_iso(iso_str: str, now: datetime | None = None) -> datetime | None:
    """Validate an ISO 8601 datetime from the AI classifier.

    Rejects strings that are malformed, naive without a recoverable
    offset, or resolve to a past moment.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_TZ).astimezone(timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        if dt <= now:
            return None
        return dt
    except (ValueError, TypeError):
        return None
