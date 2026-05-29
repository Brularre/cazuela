from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


USER = {"id": "u-1", "phone": "+56900000000"}


def _make_db():
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    return db


def test_snooze_bumps_remind_at_and_clears_remind_sent():
    db = _make_db()
    fixed_now = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)

    with patch("app.handlers.reminders.client", db), \
         patch("app.handlers.reminders.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from app.handlers.reminders import handle_snooze_reply
        result = handle_snooze_reply("snooze:todos:todo-uuid-1:30", USER)

    assert result == "⏰ Te recuerdo en 30 min."

    update_call = db.table.return_value.update.call_args
    payload = update_call[0][0]
    assert payload["remind_sent"] is False
    assert "2026-05-29T12:30:00" in payload["remind_at"]

    eq_call = db.table.return_value.update.return_value.eq.call_args
    assert eq_call[0] == ("id", "todo-uuid-1")


def test_done_todos_marks_todo_complete():
    db = _make_db()

    with patch("app.handlers.reminders.client", db):
        from app.handlers.reminders import handle_snooze_reply
        result = handle_snooze_reply("done:todos:todo-uuid-2", USER)

    assert result == "✅ Listo."

    update_call = db.table.return_value.update.call_args
    assert update_call[0][0] == {"done": True}

    eq_call = db.table.return_value.update.return_value.eq.call_args
    assert eq_call[0] == ("id", "todo-uuid-2")


def test_done_events_acknowledges_without_mutation():
    db = _make_db()

    with patch("app.handlers.reminders.client", db):
        from app.handlers.reminders import handle_snooze_reply
        result = handle_snooze_reply("done:events:event-uuid-3", USER)

    assert result == "✅ Listo."
    db.table.return_value.update.assert_not_called()


def test_unknown_button_id_returns_none():
    db = _make_db()

    with patch("app.handlers.reminders.client", db):
        from app.handlers.reminders import handle_snooze_reply
        result = handle_snooze_reply("something_random", USER)

    assert result is None


def test_snooze_unknown_table_returns_none():
    db = _make_db()

    with patch("app.handlers.reminders.client", db):
        from app.handlers.reminders import handle_snooze_reply
        result = handle_snooze_reply("snooze:unknown_table:some-id:30", USER)

    assert result is None


def test_done_unknown_table_returns_none():
    db = _make_db()

    with patch("app.handlers.reminders.client", db):
        from app.handlers.reminders import handle_snooze_reply
        result = handle_snooze_reply("done:unknown_table:some-id", USER)

    assert result is None
