from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


def _make_db(
    todos_due=None,
    events_due=None,
    modules=None,
    user_phone="+56900000001",
):
    db = MagicMock()

    def table_side_effect(name):
        t = MagicMock()
        if name == "todos":
            t.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = (
                todos_due or []
            )
            t.update.return_value.eq.return_value.execute.return_value.data = [{}]
        elif name == "events":
            t.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = (
                events_due or []
            )
            t.update.return_value.eq.return_value.execute.return_value.data = [{}]
        elif name == "user_modules":
            t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
                modules if modules is not None else []
            )
        elif name == "users":
            t.select.return_value.eq.return_value.execute.return_value.data = (
                [{"phone": user_phone}] if user_phone else []
            )
        return t

    db.table.side_effect = table_side_effect
    return db


def test_due_todo_is_sent_interactively_and_flagged():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Llamar al banco", "remind_at": "2025-06-16T14:00:00+00:00", "recur": None}]
    db = _make_db(todos_due=todos_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=True) as mock_send, \
         patch("app.jobs.send_reminders._mark_sent") as mock_mark:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args[0][0] == "+56900000001"
    assert "Llamar al banco" in call_args[0][1]
    buttons = call_args[0][2]
    assert any(b["id"] == "snooze:todos:t-1:30" for b in buttons)
    assert any(b["id"] == "done:todos:t-1" for b in buttons)
    mock_mark.assert_called_once_with("todos", "t-1")


def test_due_event_is_sent_interactively_and_flagged():
    events_due = [{"id": "e-1", "user_id": "u-1", "title": "Dentista", "remind_at": "2025-06-16T14:00:00+00:00", "recur": None}]
    db = _make_db(events_due=events_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert "Dentista" in call_args[0][1]
    buttons = call_args[0][2]
    assert any(b["id"] == "snooze:events:e-1:30" for b in buttons)
    assert any(b["id"] == "done:events:e-1" for b in buttons)


def test_send_failure_leaves_remind_sent_false():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea", "remind_at": "2025-06-16T14:00:00+00:00", "recur": None}]
    db = _make_db(todos_due=todos_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=False):
        from app.jobs.send_reminders import main
        main()
    db.table.return_value.update.assert_not_called()


def test_disabled_recordatorios_skips_row():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea", "remind_at": "2025-06-16T14:00:00+00:00", "recur": None}]
    modules = [{"enabled": False}]
    db = _make_db(todos_due=todos_due, modules=modules)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_not_called()


def test_no_due_rows_nothing_sent():
    db = _make_db()
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_not_called()


def test_missing_user_phone_skips_row():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea", "remind_at": "2025-06-16T14:00:00+00:00", "recur": None}]
    db = _make_db(todos_due=todos_due, user_phone=None)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_not_called()


def test_both_todos_and_events_processed():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea A", "remind_at": "2025-06-16T14:00:00+00:00", "recur": None}]
    events_due = [{"id": "e-1", "user_id": "u-1", "title": "Evento B", "remind_at": "2025-06-16T15:00:00+00:00", "recur": None}]
    db = _make_db(todos_due=todos_due, events_due=events_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    assert mock_send.call_count == 2
    bodies = [c[0][1] for c in mock_send.call_args_list]
    assert any("Tarea A" in b for b in bodies)
    assert any("Evento B" in b for b in bodies)


def test_recurring_row_calls_advance_recur_not_mark_sent():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Gimnasio", "remind_at": "2025-06-16T09:00:00+00:00", "recur": "mondays"}]
    db = _make_db(todos_due=todos_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=True), \
         patch("app.jobs.send_reminders._mark_sent") as mock_mark, \
         patch("app.jobs.send_reminders._advance_recur") as mock_advance:
        from app.jobs.send_reminders import main
        main()
    mock_advance.assert_called_once_with("todos", "t-1", "2025-06-16T09:00:00+00:00", "mondays")
    mock_mark.assert_not_called()


def test_non_recurring_row_calls_mark_sent_not_advance_recur():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea", "remind_at": "2025-06-16T14:00:00+00:00", "recur": None}]
    db = _make_db(todos_due=todos_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_interactive", return_value=True), \
         patch("app.jobs.send_reminders._mark_sent") as mock_mark, \
         patch("app.jobs.send_reminders._advance_recur") as mock_advance:
        from app.jobs.send_reminders import main
        main()
    mock_mark.assert_called_once_with("todos", "t-1")
    mock_advance.assert_not_called()


def test_advance_recur_daily():
    from app.jobs.send_reminders import _advance_recur
    db = MagicMock()
    with patch("app.jobs.send_reminders.client", db):
        _advance_recur("todos", "t-1", "2025-06-16T09:00:00+00:00", "daily")
    update_call = db.table.return_value.update.call_args[0][0]
    next_dt = datetime.fromisoformat(update_call["remind_at"])
    old_dt = datetime(2025, 6, 16, 9, 0, tzinfo=timezone.utc)
    assert next_dt == old_dt + timedelta(days=1)
    assert update_call["remind_sent"] is False


def test_advance_recur_weekly():
    from app.jobs.send_reminders import _advance_recur
    db = MagicMock()
    with patch("app.jobs.send_reminders.client", db):
        _advance_recur("todos", "t-1", "2025-06-16T09:00:00+00:00", "weekly")
    update_call = db.table.return_value.update.call_args[0][0]
    next_dt = datetime.fromisoformat(update_call["remind_at"])
    old_dt = datetime(2025, 6, 16, 9, 0, tzinfo=timezone.utc)
    assert next_dt == old_dt + timedelta(days=7)
    assert update_call["remind_sent"] is False


def test_advance_recur_weekday_mondays():
    from app.jobs.send_reminders import _advance_recur
    db = MagicMock()
    with patch("app.jobs.send_reminders.client", db):
        _advance_recur("todos", "t-1", "2025-06-16T09:00:00+00:00", "mondays")
    update_call = db.table.return_value.update.call_args[0][0]
    next_dt = datetime.fromisoformat(update_call["remind_at"])
    assert next_dt.weekday() == 0
    assert next_dt > datetime(2025, 6, 16, 9, 0, tzinfo=timezone.utc)
    assert update_call["remind_sent"] is False


def test_advance_recur_same_weekday_advances_full_week():
    from app.jobs.send_reminders import _advance_recur
    db = MagicMock()
    with patch("app.jobs.send_reminders.client", db):
        _advance_recur("todos", "t-1", "2025-06-16T09:00:00+00:00", "mondays")
    update_call = db.table.return_value.update.call_args[0][0]
    next_dt = datetime.fromisoformat(update_call["remind_at"])
    old_dt = datetime(2025, 6, 16, 9, 0, tzinfo=timezone.utc)
    assert (next_dt - old_dt).days == 7


def test_advance_recur_unknown_value_marks_sent_and_does_not_raise():
    from app.jobs.send_reminders import _advance_recur
    db = MagicMock()
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders._mark_sent") as mock_mark:
        _advance_recur("todos", "t-bad", "2025-06-16T09:00:00+00:00", "fortnightly")
    mock_mark.assert_called_once_with("todos", "t-bad")
    db.table.return_value.update.assert_not_called()


def test_advance_recur_weekday_uses_local_date():
    from zoneinfo import ZoneInfo
    from app.jobs.send_reminders import _advance_recur
    tz = ZoneInfo("America/Santiago")
    monday_evening_local = datetime(2025, 6, 16, 22, 0, tzinfo=tz)
    stored = monday_evening_local.astimezone(timezone.utc).isoformat()
    db = MagicMock()
    with patch("app.jobs.send_reminders.client", db):
        _advance_recur("todos", "t-1", stored, "mondays")
    update_call = db.table.return_value.update.call_args[0][0]
    next_local = datetime.fromisoformat(update_call["remind_at"]).astimezone(tz)
    assert next_local.weekday() == 0
    assert next_local.date() == monday_evening_local.date() + timedelta(days=7)
