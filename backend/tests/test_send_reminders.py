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


def test_due_todo_is_sent_and_flagged():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Llamar al banco"}]
    db = _make_db(todos_due=todos_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_text", return_value=True) as mock_send, \
         patch("app.jobs.send_reminders._mark_sent") as mock_mark:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_called_once_with("+56900000001", "⏰ Llamar al banco")
    mock_mark.assert_called_once_with("todos", "t-1")


def test_due_event_is_sent_and_flagged():
    events_due = [{"id": "e-1", "user_id": "u-1", "title": "Dentista"}]
    db = _make_db(events_due=events_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_text", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_called_once_with("+56900000001", "⏰ Dentista")


def test_send_failure_leaves_remind_sent_false():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea"}]
    db = _make_db(todos_due=todos_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_text", return_value=False):
        from app.jobs.send_reminders import main
        main()
    db.table.return_value.update.assert_not_called()


def test_disabled_recordatorios_skips_row():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea"}]
    modules = [{"enabled": False}]
    db = _make_db(todos_due=todos_due, modules=modules)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_text", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_not_called()


def test_no_due_rows_nothing_sent():
    db = _make_db()
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_text", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_not_called()


def test_missing_user_phone_skips_row():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea"}]
    db = _make_db(todos_due=todos_due, user_phone=None)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_text", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    mock_send.assert_not_called()


def test_both_todos_and_events_processed():
    todos_due = [{"id": "t-1", "user_id": "u-1", "task": "Tarea A"}]
    events_due = [{"id": "e-1", "user_id": "u-1", "title": "Evento B"}]
    db = _make_db(todos_due=todos_due, events_due=events_due)
    with patch("app.jobs.send_reminders.client", db), \
         patch("app.jobs.send_reminders.send_text", return_value=True) as mock_send:
        from app.jobs.send_reminders import main
        main()
    assert mock_send.call_count == 2
    calls = [c[0][1] for c in mock_send.call_args_list]
    assert any("Tarea A" in c for c in calls)
    assert any("Evento B" in c for c in calls)
