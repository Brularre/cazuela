from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from tests.conftest import FAKE_USER


def _future_dt():
    return datetime.now(timezone.utc) + timedelta(hours=2)


def _db_todos(rows=None):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows or []
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    return db


def _db_events(rows=None):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = rows or []
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    return db


def test_set_todo_reminder_found():
    remind_at = _future_dt()
    db = _db_todos(rows=[{"id": "t-1", "task": "llamar al banco"}])
    with patch("app.handlers.todos.client", db):
        from app.handlers.todos import set_todo_reminder
        result = set_todo_reminder("banco", remind_at, FAKE_USER)
    assert result is not None
    assert "⏰" in result
    assert "banco" in result
    update_call = db.table.return_value.update.call_args[0][0]
    assert update_call["remind_sent"] is False
    assert "remind_at" in update_call


def test_set_todo_reminder_with_recur_appends_se_repite():
    remind_at = _future_dt()
    db = _db_todos(rows=[{"id": "t-1", "task": "gimnasio"}])
    with patch("app.handlers.todos.client", db):
        from app.handlers.todos import set_todo_reminder
        result = set_todo_reminder("gimnasio", remind_at, FAKE_USER, recur="mondays")
    assert result is not None
    assert "(se repite)" in result
    update_call = db.table.return_value.update.call_args[0][0]
    assert update_call["recur"] == "mondays"


def test_set_todo_reminder_recur_none_sets_null():
    remind_at = _future_dt()
    db = _db_todos(rows=[{"id": "t-1", "task": "tarea"}])
    with patch("app.handlers.todos.client", db):
        from app.handlers.todos import set_todo_reminder
        result = set_todo_reminder("tarea", remind_at, FAKE_USER, recur=None)
    assert result is not None
    assert "(se repite)" not in result
    update_call = db.table.return_value.update.call_args[0][0]
    assert update_call["recur"] is None


def test_set_todo_reminder_not_found_returns_none():
    db = _db_todos(rows=[])
    with patch("app.handlers.todos.client", db):
        from app.handlers.todos import set_todo_reminder
        result = set_todo_reminder("xyz", _future_dt(), FAKE_USER)
    assert result is None


def test_set_event_reminder_found():
    remind_at = _future_dt()
    db = _db_events(rows=[{"id": "e-1", "title": "Dentista"}])
    with patch("app.handlers.events.client", db):
        from app.handlers.events import set_event_reminder
        result = set_event_reminder("dentista", remind_at, FAKE_USER)
    assert result is not None
    assert "⏰" in result
    assert "Dentista" in result


def test_set_event_reminder_with_recur_appends_se_repite():
    remind_at = _future_dt()
    db = _db_events(rows=[{"id": "e-1", "title": "Reunión semanal"}])
    with patch("app.handlers.events.client", db):
        from app.handlers.events import set_event_reminder
        result = set_event_reminder("reunión", remind_at, FAKE_USER, recur="weekly")
    assert result is not None
    assert "(se repite)" in result
    update_call = db.table.return_value.update.call_args[0][0]
    assert update_call["recur"] == "weekly"


def test_set_event_reminder_recur_none_sets_null():
    remind_at = _future_dt()
    db = _db_events(rows=[{"id": "e-1", "title": "Dentista"}])
    with patch("app.handlers.events.client", db):
        from app.handlers.events import set_event_reminder
        result = set_event_reminder("dentista", remind_at, FAKE_USER, recur=None)
    assert result is not None
    assert "(se repite)" not in result
    update_call = db.table.return_value.update.call_args[0][0]
    assert update_call["recur"] is None


def test_set_event_reminder_not_found_returns_none():
    db = _db_events(rows=[])
    with patch("app.handlers.events.client", db):
        from app.handlers.events import set_event_reminder
        result = set_event_reminder("xyz", _future_dt(), FAKE_USER)
    assert result is None


def test_extract_fragment_strips_time():
    from app.handlers.timeparse import extract_fragment
    result = extract_fragment("llamar al banco mañana a las 10")
    assert result == "llamar al banco"


def test_extract_fragment_en_horas():
    from app.handlers.timeparse import extract_fragment
    result = extract_fragment("tomar pastilla en 2 horas")
    assert result == "tomar pastilla"


def test_extract_fragment_no_time_returns_full():
    from app.handlers.timeparse import extract_fragment
    result = extract_fragment("llamar al banco")
    assert result == "llamar al banco"


def test_reminder_router_pattern_matches():
    from app.patterns import REMINDER_SET_PATTERN
    m = REMINDER_SET_PATTERN.match("recuérdame: dentista mañana a las 10")
    assert m is not None
    assert "dentista" in m.group(1)


def test_reminder_router_pattern_no_accent():
    from app.patterns import REMINDER_SET_PATTERN
    m = REMINDER_SET_PATTERN.match("recuerdame banco en 2 horas")
    assert m is not None


def test_reminder_router_pattern_recuerda_form():
    from app.patterns import REMINDER_SET_PATTERN
    m = REMINDER_SET_PATTERN.match("recuerda: dentista mañana a las 10")
    assert m is not None


def test_router_set_reminder_todo_found():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    remind_at = _future_dt()
    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.parse_time", return_value=remind_at), \
         patch("app.router.extract_fragment", return_value="banco"), \
         patch("app.router.set_todo_reminder", return_value="⏰ Recordatorio guardado: llamar al banco (16/06 12:00)") as mock_todo, \
         patch("app.router.set_event_reminder", return_value=None):
        result = route("recuérdame: banco mañana a las 10", FAKE_USER)
    mock_todo.assert_called_once()
    assert "⏰" in result


def test_router_set_reminder_falls_back_to_event():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    remind_at = _future_dt()
    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.parse_time", return_value=remind_at), \
         patch("app.router.extract_fragment", return_value="dentista"), \
         patch("app.router.set_todo_reminder", return_value=None), \
         patch("app.router.set_event_reminder", return_value="⏰ Recordatorio guardado: Dentista (16/06 15:00)") as mock_ev:
        result = route("recuérdame: dentista viernes a las 15", FAKE_USER)
    mock_ev.assert_called_once()
    assert "⏰" in result


def test_router_set_reminder_not_found():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    remind_at = _future_dt()
    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.parse_time", return_value=remind_at), \
         patch("app.router.extract_fragment", return_value="xyz"), \
         patch("app.router.set_todo_reminder", return_value=None), \
         patch("app.router.set_event_reminder", return_value=None):
        result = route("recuérdame: xyz mañana a las 10", FAKE_USER)
    assert "No encontré" in result


def test_router_set_reminder_no_time():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.parse_time", return_value=None):
        result = route("recuérdame: dentista el próximo martes", FAKE_USER)
    assert "No entendí la hora" in result


def test_router_set_reminder_disabled_module():
    from app.router import route

    def patched_is_enabled(user, module):
        if module == "recordatorios":
            return False
        return True

    with patch("app.router.is_enabled", patched_is_enabled):
        result = route("recuérdame: dentista mañana a las 10", FAKE_USER)
    assert "desactivado" in result
