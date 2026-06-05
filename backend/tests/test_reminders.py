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


def test_router_set_reminder_stages_confirmation():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    remind_at = _future_dt()
    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.parse_time_meta", return_value=(remind_at, False)), \
         patch("app.router.extract_fragment", return_value="banco"), \
         patch("app.router.stage_reminder", return_value="⏰ ¿Te recuerdo *banco* el 16/06 12:00?") as mock_stage:
        result = route("recuérdame: banco mañana a las 10", FAKE_USER)
    mock_stage.assert_called_once()
    assert mock_stage.call_args[0][0] == "banco"
    assert "¿Te recuerdo" in result


def test_router_set_reminder_passes_ambiguous():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    remind_at = _future_dt()
    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.parse_time_meta", return_value=(remind_at, True)), \
         patch("app.router.extract_fragment", return_value="banco"), \
         patch("app.router.stage_reminder", return_value="prompt") as mock_stage:
        route("recuérdame: banco a las 3", FAKE_USER)
    assert mock_stage.call_args.kwargs["ambiguous"] is True


def test_stage_reminder_sends_context_and_prompts():
    remind_at = _future_dt()
    with patch("app.handlers.reminders.mcp") as mock_mcp:
        mock_mcp.send_context.return_value = "ctx-1"
        from app.handlers.reminders import stage_reminder
        result = stage_reminder("dentista", remind_at, FAKE_USER, recur="mondays")
    domain, _user_id, payload = mock_mcp.send_context.call_args[0]
    assert domain == "reminder_set"
    assert payload["fragment"] == "dentista"
    assert payload["recur"] == "mondays"
    mock_mcp.request_action.assert_called_once_with("ctx-1")
    assert "dentista" in result
    assert "(se repite)" in result
    assert "sí" in result and "no" in result


def test_stage_reminder_ambiguous_pm_adds_am_hint():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Santiago")
    remind_at = datetime(2026, 6, 6, 15, 0, tzinfo=tz)
    with patch("app.handlers.reminders.mcp") as mock_mcp:
        mock_mcp.send_context.return_value = "ctx-1"
        from app.handlers.reminders import stage_reminder
        result = stage_reminder("llamar", remind_at, FAKE_USER, ambiguous=True)
    assert "3 am" in result
    assert "tarde" in result.lower()


def test_stage_reminder_ambiguous_am_adds_pm_hint():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Santiago")
    remind_at = datetime(2026, 6, 6, 9, 0, tzinfo=tz)
    with patch("app.handlers.reminders.mcp") as mock_mcp:
        mock_mcp.send_context.return_value = "ctx-1"
        from app.handlers.reminders import stage_reminder
        result = stage_reminder("gimnasio", remind_at, FAKE_USER, ambiguous=True)
    assert "9 pm" in result
    assert "noche" in result.lower()


def test_confirm_reminder_attaches_to_existing_todo():
    remind_at = _future_dt()
    ctx = {"payload": {"fragment": "banco", "remind_at": remind_at.isoformat(), "recur": None}}
    with patch("app.handlers.reminders.mcp") as mock_mcp, \
         patch("app.handlers.reminders.set_todo_reminder", return_value="⏰ ok-todo") as mock_todo, \
         patch("app.handlers.reminders.set_event_reminder") as mock_ev, \
         patch("app.handlers.reminders.create_todo_reminder") as mock_create:
        from app.handlers.reminders import confirm_reminder
        result = confirm_reminder("ctx-1", FAKE_USER, ctx)
    mock_mcp.confirm.assert_called_once_with("ctx-1")
    mock_todo.assert_called_once()
    mock_ev.assert_not_called()
    mock_create.assert_not_called()
    assert result == "⏰ ok-todo"


def test_confirm_reminder_creates_new_when_no_match():
    remind_at = _future_dt()
    ctx = {"payload": {"fragment": "comprar pan", "remind_at": remind_at.isoformat(), "recur": "daily"}}
    with patch("app.handlers.reminders.mcp"), \
         patch("app.handlers.reminders.set_todo_reminder", return_value=None), \
         patch("app.handlers.reminders.set_event_reminder", return_value=None), \
         patch("app.handlers.reminders.create_todo_reminder", return_value="⏰ nuevo") as mock_create:
        from app.handlers.reminders import confirm_reminder
        result = confirm_reminder("ctx-1", FAKE_USER, ctx)
    mock_create.assert_called_once()
    assert result == "⏰ nuevo"


def test_cancel_reminder_rolls_back():
    with patch("app.handlers.reminders.mcp") as mock_mcp:
        from app.handlers.reminders import cancel_reminder
        result = cancel_reminder("ctx-1", FAKE_USER)
    mock_mcp.rollback.assert_called_once_with("ctx-1")
    assert "cancelado" in result.lower()


def test_create_todo_reminder_inserts_new_todo():
    remind_at = _future_dt()
    db = MagicMock()
    db.table.return_value.insert.return_value.execute.return_value.data = [{}]
    with patch("app.handlers.todos.client", db):
        from app.handlers.todos import create_todo_reminder
        result = create_todo_reminder("dentista", remind_at, FAKE_USER)
    assert "⏰" in result
    assert "dentista" in result
    insert_call = db.table.return_value.insert.call_args[0][0]
    assert insert_call["task"] == "dentista"
    assert insert_call["remind_sent"] is False
    assert "remind_at" in insert_call


def test_create_todo_reminder_with_recur_appends_se_repite():
    remind_at = _future_dt()
    db = MagicMock()
    db.table.return_value.insert.return_value.execute.return_value.data = [{}]
    with patch("app.handlers.todos.client", db):
        from app.handlers.todos import create_todo_reminder
        result = create_todo_reminder("gimnasio", remind_at, FAKE_USER, recur="mondays")
    assert "(se repite)" in result
    insert_call = db.table.return_value.insert.call_args[0][0]
    assert insert_call["recur"] == "mondays"


def test_router_set_reminder_no_time():
    from app.router import route

    def patched_is_enabled(user, module):
        return True

    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.router.parse_time_meta", return_value=(None, False)):
        result = route("recuérdame: dentista el próximo martes", FAKE_USER)
    assert "No entendí la hora" in result


def test_snooze_reply_updates_correct_user_only():
    db = MagicMock()
    update_chain = db.table.return_value.update.return_value
    update_chain.eq.return_value.eq.return_value.execute.return_value.data = [{}]
    with patch("app.handlers.reminders.client", db):
        from app.handlers.reminders import handle_snooze_reply
        result = handle_snooze_reply("snooze:todos:t-abc:30", FAKE_USER)
    assert result is not None
    second_eq_calls = update_chain.eq.return_value.eq.call_args_list
    assert any(c.args == ("user_id", FAKE_USER["id"]) for c in second_eq_calls), \
        "user_id filter must be applied on snooze update"


def test_done_reply_filters_by_user_id():
    db = MagicMock()
    update_chain = db.table.return_value.update.return_value
    update_chain.eq.return_value.eq.return_value.execute.return_value.data = [{}]
    with patch("app.handlers.reminders.client", db):
        from app.handlers.reminders import handle_snooze_reply
        result = handle_snooze_reply("done:todos:t-abc", FAKE_USER)
    assert result == "✅ Listo."
    second_eq_calls = update_chain.eq.return_value.eq.call_args_list
    assert any(c.args == ("user_id", FAKE_USER["id"]) for c in second_eq_calls), \
        "user_id filter must be applied on done update"


def test_snooze_reply_rejects_out_of_range_minutes():
    from app.handlers.reminders import handle_snooze_reply
    assert handle_snooze_reply("snooze:todos:t-abc:0", FAKE_USER) is None
    assert handle_snooze_reply("snooze:todos:t-abc:1441", FAKE_USER) is None
    assert handle_snooze_reply("snooze:todos:t-abc:-10", FAKE_USER) is None


def test_snooze_reply_accepts_boundary_minutes():
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]
    with patch("app.handlers.reminders.client", db):
        from app.handlers.reminders import handle_snooze_reply
        assert handle_snooze_reply("snooze:todos:t-abc:1", FAKE_USER) is not None
        assert handle_snooze_reply("snooze:todos:t-abc:1440", FAKE_USER) is not None


def test_router_set_reminder_disabled_module():
    from app.router import route

    def patched_is_enabled(user, module):
        if module == "recordatorios":
            return False
        return True

    with patch("app.router.is_enabled", patched_is_enabled):
        result = route("recuérdame: dentista mañana a las 10", FAKE_USER)
    assert "desactivado" in result
