"""Natural-language time parser for Spanish WhatsApp messages.

Public API:
  parse_time(text, now=None) -> datetime | None
    Parses a small, fixed set of Spanish time phrasings and returns
    a UTC-aware datetime. Returns None if unrecognised or in the past.

  parse_time_meta(text, now=None) -> tuple[datetime | None, bool]
    Same as parse_time, plus a flag that is True when a bare hour 1–11
    with no am/pm qualifier was parsed (12h-ambiguous).

  extract_fragment(text) -> str
    Strips the recognized time phrase from text, returning the
    task/event fragment. Used when parsing reminder commands.

  parse_iso(iso_str, now=None) -> datetime | None
    Validates an ISO 8601 datetime string (from the AI classifier).
    Ensures it is a future UTC-aware datetime. Returns None on failure.

  parse_recur(text) -> str | None
    Scans text for a "cada ..." phrase and returns the canonical recur
    value, or None if not found.

  extract_recur_fragment(text) -> str
    Like extract_fragment but also strips the "cada ..." phrase.

Supported phrasings (manual mode):
  - hoy a las HH[:MM]            today at given time
  - mañana a las HH[:MM]         tomorrow at given time
  - el WEEKDAY a las HH[:MM]     next occurrence of named weekday
  - en N horas / en N minutos    relative offset from now
  - a las HH[:MM]                next occurrence of that time (today if
                                 still future, otherwise tomorrow)

Meridiem (12h) handling:
  - explicit qualifiers win: "am"/"pm", "de la tarde"/"de la noche" (PM),
    "de la mañana"/"de la madrugada" (AM).
  - otherwise a bare hour 1–7 is assumed PM (3 → 15:00); 8–23 stay literal.

Supported recur phrasings:
  - cada día / cada dia          → "daily"
  - cada semana                  → "weekly"
  - cada lunes/martes/...        → "mondays"/"tuesdays"/etc.

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

_RECUR_MAP = {
    "lunes": "mondays",
    "martes": "tuesdays",
    "miércoles": "wednesdays",
    "miercoles": "wednesdays",
    "jueves": "thursdays",
    "viernes": "fridays",
    "sábado": "saturdays",
    "sabado": "saturdays",
    "domingo": "sundays",
}

_RECUR_WEEKDAY_RE = re.compile(
    r"\bcada\s+(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b",
    re.IGNORECASE,
)
_RECUR_DAY_RE = re.compile(r"\bcada\s+d[ií]a\b", re.IGNORECASE)
_RECUR_WEEK_RE = re.compile(r"\bcada\s+semana\b", re.IGNORECASE)
_RECUR_ANY_RE = re.compile(
    r"\bcada\s+(?:d[ií]a|semana|lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b",
    re.IGNORECASE,
)

_MERIDIEM = (
    r"(?:\s*(?P<mer>[ap])\.?\s?m\.?\b)?"
    r"(?:\s+de\s+la\s+(?:tarde|noche|ma[nñ]ana|madrugada))?"
)
_CLOCK = r"(?P<h>\d{1,2})(?::(?P<m>\d{2}))?(?:\s*hrs?)?" + _MERIDIEM
_TIME_PART = r"(?:a\s+las?\s+)?" + _CLOCK

_HOY_MANANA_RE = re.compile(
    r"\b(?P<anchor>hoy|ma[nñ]ana)\b\s*" + _TIME_PART,
    re.IGNORECASE,
)
_WEEKDAY_RE = re.compile(
    r"\b(?:el\s+)?(?P<wd>lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b\s*" + _TIME_PART,
    re.IGNORECASE,
)
_RELATIVE_RE = re.compile(
    r"\ben\s+(\d+)\s+(horas?|minutos?|mins?)\b",
    re.IGNORECASE,
)
_BARE_TIME_RE = re.compile(r"\ba\s+las?\s+" + _CLOCK, re.IGNORECASE)

_PM_PHRASE_RE = re.compile(r"\bde\s+la\s+(?:tarde|noche)\b", re.IGNORECASE)
_AM_PHRASE_RE = re.compile(r"\bde\s+la\s+(?:ma[nñ]ana|madrugada)\b", re.IGNORECASE)


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


def _resolve_hour(hour: int, merid: str | None, text: str) -> tuple[int, bool]:
    """Apply am/pm and 'de la tarde/noche/mañana' qualifiers to a raw hour.

    Returns (resolved_hour, ambiguous). ambiguous is True when no qualifier
    was given and the raw hour (1–11) could plausibly be either am or pm.
    The daytime heuristic resolves 1–7 to PM and keeps 8–11 as AM, but in
    both cases the caller may want to offer a correction.
    """
    is_pm = (merid is not None and merid.lower() == "p") or bool(_PM_PHRASE_RE.search(text))
    is_am = (merid is not None and merid.lower() == "a") or bool(_AM_PHRASE_RE.search(text))
    if is_pm:
        return (hour + 12 if 1 <= hour <= 11 else hour), False
    if is_am:
        return (0 if hour == 12 else hour), False
    ambiguous = 1 <= hour <= 11
    if 1 <= hour <= 7:
        hour += 12
    return hour, ambiguous


def parse_time(text: str, now: datetime | None = None) -> datetime | None:
    return parse_time_meta(text, now)[0]


def parse_time_meta(text: str, now: datetime | None = None) -> tuple[datetime | None, bool]:
    """Like parse_time but also reports 12h ambiguity.

    The second element is True when a bare hour 1–11 was given with no am/pm
    qualifier (so it could be either am or pm), letting callers offer the
    user a correction hint.
    """
    now_local = _as_santiago(now) if now is not None else datetime.now(_TZ)

    mt = _RELATIVE_RE.search(text)
    if mt:
        n = int(mt.group(1))
        unit = mt.group(2).lower().rstrip("s")
        delta = timedelta(hours=n) if unit.startswith("hora") else timedelta(minutes=n)
        return (now_local + delta).astimezone(timezone.utc), False

    mt = _HOY_MANANA_RE.search(text)
    if mt:
        hm = _parse_hhmm(mt.group("h"), mt.group("m"))
        if hm is None:
            return None, False
        hour, minute = hm
        hour, ambiguous = _resolve_hour(hour, mt.group("mer"), text)
        base = now_local.date()
        if mt.group("anchor").lower() in ("mañana", "manana"):
            base = base + timedelta(days=1)
        local = _build_local(base, hour, minute)
        if local <= now_local:
            return None, False
        return local.astimezone(timezone.utc), ambiguous

    mt = _WEEKDAY_RE.search(text)
    if mt:
        hm = _parse_hhmm(mt.group("h"), mt.group("m"))
        if hm is None:
            return None, False
        hour, minute = hm
        hour, ambiguous = _resolve_hour(hour, mt.group("mer"), text)
        target_wd = _WEEKDAY_MAP.get(mt.group("wd").lower())
        if target_wd is None:
            return None, False
        today_wd = now_local.weekday()
        days_ahead = (target_wd - today_wd) % 7
        if days_ahead == 0:
            candidate = _build_local(now_local.date(), hour, minute)
            if candidate <= now_local:
                days_ahead = 7
        base = now_local.date() + timedelta(days=days_ahead)
        local = _build_local(base, hour, minute)
        if local <= now_local:
            return None, False
        return local.astimezone(timezone.utc), ambiguous

    mt = _BARE_TIME_RE.search(text)
    if mt:
        hm = _parse_hhmm(mt.group("h"), mt.group("m"))
        if hm is None:
            return None, False
        hour, minute = hm
        hour, ambiguous = _resolve_hour(hour, mt.group("mer"), text)
        local = _build_local(now_local.date(), hour, minute)
        if local <= now_local:
            local = _build_local(now_local.date() + timedelta(days=1), hour, minute)
        return local.astimezone(timezone.utc), ambiguous

    return None, False


def extract_fragment(text: str) -> str:
    """Strip the recognized time phrase from text, returning the task fragment.

    Finds the earliest time phrase in text (hoy/mañana, weekday, or relative),
    removes it (and the text after it), and returns what remains stripped.
    Used to split 'llamar al banco mañana a las 10' into 'llamar al banco'.
    """
    best_start = None
    best_end = None
    for pattern in (_RELATIVE_RE, _HOY_MANANA_RE, _WEEKDAY_RE, _BARE_TIME_RE):
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


def parse_recur(text: str) -> str | None:
    """Scan text for a 'cada ...' phrase and return the canonical recur value.

    Returns None if no supported recur phrase is found.
    """
    if _RECUR_DAY_RE.search(text):
        return "daily"
    if _RECUR_WEEK_RE.search(text):
        return "weekly"
    m = _RECUR_WEEKDAY_RE.search(text)
    if m:
        return _RECUR_MAP[m.group(1).lower()]
    return None


def extract_recur_fragment(text: str) -> str:
    """Strip both the 'cada ...' phrase and the time phrase from text.

    The recur phrase is removed first so that a weekday that serves as
    both the recurrence anchor and the time anchor (e.g. "cada lunes a las 10")
    does not leave a dangling 'cada' after time stripping.
    Returns the remaining task/event fragment.
    """
    without_recur = _RECUR_ANY_RE.sub("", text).strip().rstrip(",").strip()
    return extract_fragment(without_recur)
