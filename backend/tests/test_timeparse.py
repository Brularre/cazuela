from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.handlers.timeparse import parse_iso, parse_time, parse_recur, extract_recur_fragment

_TZ = ZoneInfo("America/Santiago")


def _now_monday_morning():
    """2025-06-16 (Monday) 10:00 Santiago — Chilean winter (UTC-4)."""
    return datetime(2025, 6, 16, 10, 0, tzinfo=_TZ)


def _utc_h(dt):
    return dt.astimezone(timezone.utc).hour


def _local_h(dt):
    return dt.astimezone(_TZ).hour


# ---------------------------------------------------------------------------
# Hoy / mañana
# ---------------------------------------------------------------------------


def test_hoy_future_time():
    now = _now_monday_morning()
    result = parse_time("reunión hoy a las 15", now=now)
    assert result is not None
    assert _local_h(result) == 15


def test_hoy_colon_minutes():
    now = _now_monday_morning()
    result = parse_time("hoy 15:30", now=now)
    assert result is not None
    local = result.astimezone(_TZ)
    assert local.hour == 15
    assert local.minute == 30


def test_hoy_past_time_returns_none():
    now = _now_monday_morning()
    result = parse_time("hoy a las 9", now=now)
    assert result is None


def test_hoy_exact_now_returns_none():
    now = _now_monday_morning()
    result = parse_time("hoy a las 10", now=now)
    assert result is None


def test_manana_no_accent():
    now = _now_monday_morning()
    result = parse_time("manana a las 10", now=now)
    assert result is not None
    local = result.astimezone(_TZ)
    assert local.hour == 10
    assert local.date() == (now.date() + timedelta(days=1))


def test_manana_accent():
    now = _now_monday_morning()
    result = parse_time("mañana a las 8", now=now)
    assert result is not None
    assert _local_h(result) == 8


def test_manana_past_time_still_tomorrow():
    now = _now_monday_morning()
    result = parse_time("mañana a las 9", now=now)
    assert result is not None
    local = result.astimezone(_TZ)
    assert local.date() == now.date() + timedelta(days=1)
    assert local.hour == 9


# ---------------------------------------------------------------------------
# Weekdays
# ---------------------------------------------------------------------------


def test_weekday_later_this_week():
    now = _now_monday_morning()
    result = parse_time("el miércoles a las 15", now=now)
    assert result is not None
    local = result.astimezone(_TZ)
    assert local.weekday() == 2
    assert local.hour == 15
    assert local.date() == now.date() + timedelta(days=2)


def test_weekday_same_day_future_time():
    now = _now_monday_morning()
    result = parse_time("el lunes a las 14", now=now)
    assert result is not None
    local = result.astimezone(_TZ)
    assert local.weekday() == 0
    assert local.hour == 14
    assert local.date() == now.date()


def test_weekday_same_day_past_time_wraps_to_next_week():
    now = _now_monday_morning()
    result = parse_time("el lunes a las 9", now=now)
    assert result is not None
    local = result.astimezone(_TZ)
    assert local.weekday() == 0
    assert local.date() == now.date() + timedelta(days=7)


def test_weekday_no_el_prefix():
    now = _now_monday_morning()
    result = parse_time("viernes 10:00", now=now)
    assert result is not None
    local = result.astimezone(_TZ)
    assert local.weekday() == 4


def test_weekday_no_time_component_returns_none():
    result = parse_time("el próximo martes")
    assert result is None


def test_weekday_sabado_no_accent():
    now = _now_monday_morning()
    result = parse_time("sabado a las 12", now=now)
    assert result is not None
    assert result.astimezone(_TZ).weekday() == 5


def test_weekday_domingo():
    now = _now_monday_morning()
    result = parse_time("domingo a las 11", now=now)
    assert result is not None
    assert result.astimezone(_TZ).weekday() == 6


# ---------------------------------------------------------------------------
# Relative (en N horas / minutos)
# ---------------------------------------------------------------------------


def test_en_horas():
    now = _now_monday_morning()
    result = parse_time("en 2 horas", now=now)
    assert result is not None
    expected = (now + timedelta(hours=2)).astimezone(timezone.utc)
    assert abs((result - expected).total_seconds()) < 1


def test_en_hora_singular():
    now = _now_monday_morning()
    result = parse_time("en 1 hora", now=now)
    assert result is not None
    expected = (now + timedelta(hours=1)).astimezone(timezone.utc)
    assert abs((result - expected).total_seconds()) < 1


def test_en_minutos():
    now = _now_monday_morning()
    result = parse_time("en 30 minutos", now=now)
    assert result is not None
    expected = (now + timedelta(minutes=30)).astimezone(timezone.utc)
    assert abs((result - expected).total_seconds()) < 1


def test_en_mins_abbreviation():
    now = _now_monday_morning()
    result = parse_time("en 15 mins", now=now)
    assert result is not None
    expected = (now + timedelta(minutes=15)).astimezone(timezone.utc)
    assert abs((result - expected).total_seconds()) < 1


# ---------------------------------------------------------------------------
# Unparseable → None
# ---------------------------------------------------------------------------


def test_empty_string():
    assert parse_time("") is None


def test_no_time_at_all():
    assert parse_time("recuérdame comprar leche") is None


def test_proximo_sin_hora():
    assert parse_time("el próximo martes") is None


def test_invalid_hour():
    now = _now_monday_morning()
    assert parse_time("hoy a las 25", now=now) is None


def test_invalid_minute():
    now = _now_monday_morning()
    assert parse_time("hoy a las 10:75", now=now) is None


# ---------------------------------------------------------------------------
# Output is UTC-aware
# ---------------------------------------------------------------------------


def test_result_is_utc_aware():
    now = _now_monday_morning()
    result = parse_time("mañana a las 10", now=now)
    assert result is not None
    assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# DST boundary sanity
# ---------------------------------------------------------------------------


def test_utc_offset_winter_utc_minus4():
    """June = Chilean winter = UTC-4."""
    now = datetime(2025, 6, 16, 10, 0, tzinfo=_TZ)
    result = parse_time("mañana a las 12", now=now)
    assert result is not None
    utc = result.astimezone(timezone.utc)
    local = result.astimezone(_TZ)
    offset_hours = (local.replace(tzinfo=None) - utc.replace(tzinfo=None)).total_seconds() / 3600
    assert offset_hours == -4


def test_utc_offset_summer_utc_minus3():
    """January = Chilean summer (DST) = UTC-3."""
    now = datetime(2025, 1, 15, 10, 0, tzinfo=_TZ)
    result = parse_time("mañana a las 12", now=now)
    assert result is not None
    utc = result.astimezone(timezone.utc)
    local = result.astimezone(_TZ)
    offset_hours = (local.replace(tzinfo=None) - utc.replace(tzinfo=None)).total_seconds() / 3600
    assert offset_hours == -3


# ---------------------------------------------------------------------------
# parse_iso
# ---------------------------------------------------------------------------


def test_parse_iso_valid_future():
    now = datetime(2025, 6, 16, 10, 0, tzinfo=timezone.utc)
    result = parse_iso("2025-06-17T15:00:00+00:00", now=now)
    assert result is not None
    assert result.astimezone(timezone.utc).hour == 15


def test_parse_iso_past_returns_none():
    now = datetime(2025, 6, 16, 10, 0, tzinfo=timezone.utc)
    result = parse_iso("2025-06-15T08:00:00+00:00", now=now)
    assert result is None


def test_parse_iso_naive_treated_as_santiago():
    now = datetime(2025, 6, 16, 10, 0, tzinfo=timezone.utc)
    result = parse_iso("2025-06-17T15:00:00", now=now)
    assert result is not None
    local = result.astimezone(_TZ)
    assert local.hour == 15


def test_parse_iso_malformed_returns_none():
    assert parse_iso("not-a-date") is None


def test_parse_iso_empty_returns_none():
    assert parse_iso("") is None


# ---------------------------------------------------------------------------
# parse_recur
# ---------------------------------------------------------------------------


def test_parse_recur_cada_dia():
    assert parse_recur("llamar cada día") == "daily"


def test_parse_recur_cada_dia_no_accent():
    assert parse_recur("llamar cada dia") == "daily"


def test_parse_recur_cada_semana():
    assert parse_recur("reunión cada semana") == "weekly"


def test_parse_recur_lunes():
    assert parse_recur("gimnasio cada lunes") == "mondays"


def test_parse_recur_martes():
    assert parse_recur("cada martes") == "tuesdays"


def test_parse_recur_miercoles_no_accent():
    assert parse_recur("cada miercoles") == "wednesdays"


def test_parse_recur_miercoles_accent():
    assert parse_recur("cada miércoles") == "wednesdays"


def test_parse_recur_jueves():
    assert parse_recur("cada jueves") == "thursdays"


def test_parse_recur_viernes():
    assert parse_recur("cada viernes") == "fridays"


def test_parse_recur_sabado_no_accent():
    assert parse_recur("cada sabado") == "saturdays"


def test_parse_recur_sabado_accent():
    assert parse_recur("cada sábado") == "saturdays"


def test_parse_recur_domingo():
    assert parse_recur("cada domingo") == "sundays"


def test_parse_recur_unknown_returns_none():
    assert parse_recur("llamar mañana a las 10") is None


def test_parse_recur_empty_returns_none():
    assert parse_recur("") is None


def test_parse_recur_case_insensitive():
    assert parse_recur("CADA DÍA") == "daily"


# ---------------------------------------------------------------------------
# extract_recur_fragment
# ---------------------------------------------------------------------------


def test_extract_recur_fragment_strips_time_and_recur():
    result = extract_recur_fragment("tomar pastilla mañana a las 9 cada día")
    assert "tomar pastilla" in result
    assert "cada" not in result
    assert "mañana" not in result


def test_extract_recur_fragment_only_recur():
    result = extract_recur_fragment("reunión cada lunes a las 10")
    assert "reunión" in result
    assert "cada" not in result


def test_extract_recur_fragment_no_time_no_recur():
    result = extract_recur_fragment("llamar al banco")
    assert result == "llamar al banco"
