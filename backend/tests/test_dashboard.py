from datetime import datetime
from unittest.mock import MagicMock, patch
import jwt
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_SECRET = "test-secret"
TEST_PHONE = "+56912345678"
TEST_TOKEN = jwt.encode(
    {"phone": TEST_PHONE, "exp": datetime(2099, 1, 1)},
    TEST_SECRET,
    algorithm="HS256",
)


def _authed_cookies():
    return {"session": TEST_TOKEN}


def test_dashboard_unauthenticated():
    response = client.get("/dashboard")
    assert response.status_code == 401


def test_dashboard_returns_all_sections():
    db = MagicMock()

    def table_side_effect(name):
        mock = MagicMock()
        if name == "users":
            mock.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": "user-1"}
            ]
        elif name == "expenses":
            mock.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
                {"amount": "1500", "category": "comida", "date": "2024-01-15"},
            ]
        elif name == "todos":
            mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": "todo-1", "task": "llamar al banco", "priority": None},
            ]
        elif name == "waiting_on":
            mock.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {"id": "w-1", "description": "respuesta del banco", "created_at": "2024-01-10T10:00:00"},
            ]
        return mock

    db.table.side_effect = table_side_effect

    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as mock_settings:
        mock_settings.session_secret = TEST_SECRET

        response = client.get("/dashboard", cookies=_authed_cookies())

    assert response.status_code == 200
    data = response.json()
    assert "gastos" in data
    assert "pendientes" in data
    assert "esperando" in data
    assert "weekly_total" in data["gastos"]
    assert "by_day" in data["gastos"]
    assert "by_category" in data["gastos"]


def test_complete_todo():
    db = MagicMock()

    def table_side_effect(name):
        mock = MagicMock()
        if name == "users":
            mock.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": "user-1"}
            ]
        return mock

    db.table.side_effect = table_side_effect

    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as mock_settings:
        mock_settings.session_secret = TEST_SECRET

        response = client.patch(
            "/dashboard/todos/todo-1/complete",
            cookies=_authed_cookies(),
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    update_calls = [
        call for call in db.table.call_args_list
        if call.args[0] == "todos"
    ]
    assert len(update_calls) > 0


def test_resolve_waiting():
    db = MagicMock()

    def table_side_effect(name):
        mock = MagicMock()
        if name == "users":
            mock.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": "user-1"}
            ]
        return mock

    db.table.side_effect = table_side_effect

    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as mock_settings:
        mock_settings.session_secret = TEST_SECRET

        response = client.patch(
            "/dashboard/waiting_on/w-1/resolve",
            cookies=_authed_cookies(),
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    update_calls = [
        call for call in db.table.call_args_list
        if call.args[0] == "waiting_on"
    ]
    assert len(update_calls) > 0
