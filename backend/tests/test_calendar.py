from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _make_app():
    from main import app
    return TestClient(app)


def _future_iso(hours=2):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def test_ical_feed_unknown_token_returns_404():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.routes.calendar.client", db):
        resp = _make_app().get("/calendar/badtoken.ics")
    assert resp.status_code == 404


def test_ical_feed_valid_token_returns_vcal():
    db = MagicMock()

    def select_side(*args, **kwargs):
        mock = MagicMock()
        mock.eq.return_value.execute.return_value.data = [{"id": "user-1"}]
        return mock

    db.table.return_value.select.side_effect = select_side
    db.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.routes.calendar.client", db):
        resp = _make_app().get("/calendar/validtoken.ics")

    assert resp.status_code == 200
    assert "text/calendar" in resp.headers["content-type"]
    assert "BEGIN:VCALENDAR" in resp.text
    assert "END:VCALENDAR" in resp.text


def test_ical_feed_includes_events():
    user_db = MagicMock()
    starts = _future_iso(3)
    ends = _future_iso(4)

    def table_side(name):
        mock = MagicMock()
        if name == "users":
            mock.select.return_value.eq.return_value.execute.return_value.data = [{"id": "user-1"}]
        if name == "events":
            mock.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {"id": "ev-1", "title": "Dentista", "starts_at": starts, "ends_at": ends, "category": "salud"}
            ]
        return mock

    user_db.table.side_effect = table_side

    with patch("app.routes.calendar.client", user_db):
        resp = _make_app().get("/calendar/tok.ics")

    assert "Dentista" in resp.text
    assert "BEGIN:VEVENT" in resp.text
    assert "END:VEVENT" in resp.text


def test_generate_calendar_token_creates_when_missing():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"calendar_token": None}]
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]

    with patch("app.routes.calendar.client", db):
        from app.routes.calendar import generate_calendar_token
        token = generate_calendar_token("user-1")

    assert isinstance(token, str)
    assert len(token) > 10
    db.table.return_value.update.assert_called_once()


def test_generate_calendar_token_reuses_existing():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"calendar_token": "existing-tok"}]

    with patch("app.routes.calendar.client", db):
        from app.routes.calendar import generate_calendar_token
        token = generate_calendar_token("user-1")

    assert token == "existing-tok"
    db.table.return_value.update.assert_not_called()
