from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from zoneinfo import ZoneInfo

_TZ = ZoneInfo("America/Santiago")


def _make_db(users=None, modules=None, todo_reminders=None, event_reminders=None, todos=None):
    db = MagicMock()

    def table_side_effect(name):
        t = MagicMock()
        if name == "users":
            t.select.return_value.execute.return_value.data = users or []
        elif name == "user_modules":
            t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
                modules if modules is not None else []
            )
        elif name == "todos":
            chain_r = t.select.return_value.eq.return_value.eq.return_value.eq.return_value.lte.return_value.gte.return_value.order.return_value.execute.return_value
            chain_r.data = todo_reminders or []
            t.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = todos or []
        elif name == "events":
            t.select.return_value.eq.return_value.eq.return_value.lte.return_value.gte.return_value.order.return_value.execute.return_value.data = event_reminders or []
        return t

    db.table.side_effect = table_side_effect
    return db


def _future_iso(hours=2):
    now = datetime.now(_TZ)
    dt = now + timedelta(hours=hours)
    return dt.astimezone(timezone.utc).isoformat()


def test_user_with_todos_gets_digest():
    users = [{"id": "u-1", "phone": "+56900000001"}]
    todos_data = [{"id": "t-1", "task": "Renovar seguro"}]
    db = _make_db(users=users, todos=todos_data)
    with patch("app.jobs.send_digest.client", db), \
         patch("app.jobs.send_digest.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_digest import main
        main()
    mock_send.assert_called_once()
    body = mock_send.call_args[0][1]
    assert "Renovar seguro" in body
    assert "Continuar" in mock_send.call_args[0][2]


def test_user_with_reminder_due_today_gets_digest():
    users = [{"id": "u-1", "phone": "+56900000001"}]
    todo_reminders = [{"id": "t-1", "task": "Llamar al banco", "remind_at": _future_iso(1)}]
    db = _make_db(users=users, todo_reminders=todo_reminders)
    with patch("app.jobs.send_digest.client", db), \
         patch("app.jobs.send_digest.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_digest import main
        main()
    mock_send.assert_called_once()
    body = mock_send.call_args[0][1]
    assert "Llamar al banco" in body
    assert "Recordatorios" in body


def test_todo_with_reminder_not_duplicated_in_pending():
    users = [{"id": "u-1", "phone": "+56900000001"}]
    todo_reminders = [{"id": "t-1", "task": "Llamar al banco", "remind_at": _future_iso(1)}]
    todos_data = [{"id": "t-1", "task": "Llamar al banco"}]
    db = _make_db(users=users, todo_reminders=todo_reminders, todos=todos_data)
    with patch("app.jobs.send_digest.client", db), \
         patch("app.jobs.send_digest.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_digest import main
        main()
    body = mock_send.call_args[0][1]
    assert body.count("Llamar al banco") == 1


def test_user_with_empty_lists_is_skipped():
    users = [{"id": "u-1", "phone": "+56900000001"}]
    db = _make_db(users=users)
    with patch("app.jobs.send_digest.client", db), \
         patch("app.jobs.send_digest.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_digest import main
        main()
    mock_send.assert_not_called()


def test_user_with_recordatorios_disabled_is_skipped():
    users = [{"id": "u-1", "phone": "+56900000001"}]
    todos_data = [{"id": "t-1", "task": "Algo importante"}]
    modules = [{"enabled": False}]
    db = _make_db(users=users, modules=modules, todos=todos_data)
    with patch("app.jobs.send_digest.client", db), \
         patch("app.jobs.send_digest.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_digest import main
        main()
    mock_send.assert_not_called()


def test_explanation_line_always_present():
    users = [{"id": "u-1", "phone": "+56900000001"}]
    todos_data = [{"id": "t-1", "task": "Tarea X"}]
    db = _make_db(users=users, todos=todos_data)
    with patch("app.jobs.send_digest.client", db), \
         patch("app.jobs.send_digest.send_interactive", return_value=True) as mock_send:
        from app.jobs.send_digest import main
        main()
    body = mock_send.call_args[0][1]
    assert "Cazuela te saluda cada mañana" in body


def test_false_send_does_not_abort_remaining_users():
    users = [
        {"id": "u-1", "phone": "+56900000001"},
        {"id": "u-2", "phone": "+56900000002"},
    ]
    todos_data = [{"id": "t-1", "task": "Tarea"}]

    def _table(name):
        t = MagicMock()
        if name == "users":
            t.select.return_value.execute.return_value.data = users
        elif name == "user_modules":
            t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        elif name == "todos":
            t.select.return_value.eq.return_value.eq.return_value.eq.return_value.lte.return_value.gte.return_value.order.return_value.execute.return_value.data = []
            t.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = todos_data
        elif name == "events":
            t.select.return_value.eq.return_value.eq.return_value.lte.return_value.gte.return_value.order.return_value.execute.return_value.data = []
        return t

    db = MagicMock()
    db.table.side_effect = _table

    send_results = [False, True]

    with patch("app.jobs.send_digest.client", db), \
         patch("app.jobs.send_digest.send_interactive", side_effect=send_results) as mock_send:
        from app.jobs.send_digest import main
        main()

    assert mock_send.call_count == 2


def test_digest_body_contains_greeting():
    from app.jobs.send_digest import _build_body
    body = _build_body([], [{"task": "x"} if False else "tarea"])
    assert "Buenos días" in body


def test_digest_omits_empty_sections():
    from app.jobs.send_digest import _build_body
    body = _build_body([], ["tarea"])
    assert "Recordatorios" not in body
    assert "Pendientes" in body


def test_digest_includes_both_sections():
    from app.jobs.send_digest import _build_body
    reminders = [{"title": "Dentista", "time": "10:00"}]
    todos = ["Renovar seguro"]
    body = _build_body(reminders, todos)
    assert "Dentista" in body
    assert "Renovar seguro" in body
    assert "Recordatorios" in body
    assert "Pendientes" in body
