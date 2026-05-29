from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from tests.conftest import FAKE_USER


def _db(rows=None):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = rows or []
    db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = rows or []
    db.table.return_value.insert.return_value.execute.return_value.data = [{}]
    db.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [{}]
    return db


def _future_iso():
    return (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()


def test_add_event():
    starts_at = datetime.now(timezone.utc) + timedelta(hours=2)
    db = _db()
    with patch("app.handlers.events.client", db):
        from app.handlers.events import add_event
        result = add_event("Dentista", starts_at, FAKE_USER)
    assert "Dentista" in result
    assert "📅" in result
    inserted = db.table.return_value.insert.call_args[0][0]
    assert inserted["user_id"] == FAKE_USER["id"]
    assert inserted["title"] == "Dentista"


def test_list_events_empty():
    db = _db(rows=[])
    with patch("app.handlers.events.client", db):
        from app.handlers.events import list_events
        result = list_events(FAKE_USER)
    assert "No tienes eventos" in result


def test_list_events_shows_items():
    starts_at = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    db = _db(rows=[{"title": "Reunión", "starts_at": starts_at, "category": "trabajo"}])
    with patch("app.handlers.events.client", db):
        from app.handlers.events import list_events
        result = list_events(FAKE_USER)
    assert "Reunión" in result
    assert "Próximos eventos" in result


def test_delete_event_found():
    db = _db(rows=[{"id": "ev-1", "title": "Dentista"}])
    with patch("app.handlers.events.client", db):
        from app.handlers.events import delete_event
        result = delete_event("dentista", FAKE_USER)
    assert "Dentista" in result
    assert "✓" in result


def test_delete_event_not_found():
    db = _db(rows=[])
    with patch("app.handlers.events.client", db):
        from app.handlers.events import delete_event
        result = delete_event("dentista", FAKE_USER)
    assert "No encontré" in result


def test_parse_event_time_tomorrow():
    from zoneinfo import ZoneInfo
    from app.handlers.events import parse_event_time
    result = parse_event_time("evento: reunión mañana a las 10")
    assert result is not None
    local = result.astimezone(ZoneInfo("America/Santiago"))
    assert local.hour == 10


def test_parse_event_time_today():
    from zoneinfo import ZoneInfo
    from app.handlers.events import parse_event_time
    result = parse_event_time("evento: reunión hoy a las 15")
    assert result is not None
    local = result.astimezone(ZoneInfo("America/Santiago"))
    assert local.hour == 15


def test_parse_event_time_unrecognised_returns_none():
    from app.handlers.events import parse_event_time
    result = parse_event_time("evento: dentista el próximo martes")
    assert result is None


def test_disabled_calendario_blocks_event():
    from app.router import route

    def patched_is_enabled(user, module):
        if module == "calendario":
            return False
        return True

    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.dispatch.is_enabled", patched_is_enabled):
        result = route("evento: dentista mañana a las 10", FAKE_USER)
    assert "desactivado" in result


def test_event_list_router_pattern():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.list_events", return_value="ok") as mock_list:
        route("mis eventos", FAKE_USER)
    mock_list.assert_called_once_with(FAKE_USER)


def test_event_delete_router_pattern():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.delete_event", return_value="ok") as mock_del:
        route("borrar evento dentista", FAKE_USER)
    mock_del.assert_called_once_with("dentista", FAKE_USER)
