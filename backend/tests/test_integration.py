from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


def make_mock_client(rows=None):
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = rows or []
    mock.table.return_value.insert.return_value.execute.return_value = None
    mock.table.return_value.select.return_value.eq.return_value.maybeSingle.return_value.execute.return_value.data = FAKE_USER
    return mock


@patch("app.db.users.client")
@patch("app.handlers.expenses.client")
def test_expense_saved_and_confirmed(mock_expense_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_expense_client.table.return_value.insert.return_value.execute.return_value = None

    response = client.post(
        "/webhook",
        data={"Body": "gasté 5000 en almuerzo", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "5.000" in response.text
    assert "comida" in response.text


@patch("app.db.users.client")
@patch("app.handlers.summary.client")
def test_summary_returns_weekly_totals(mock_summary_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_summary_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"amount": "5000", "category": "comida"},
        {"amount": "3000", "category": "transporte"},
        {"amount": "2000", "category": "comida"},
    ]

    response = client.post(
        "/webhook",
        data={"Body": "resumen", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "comida" in response.text
    assert "7.000" in response.text
    assert "transporte" in response.text


@patch("app.db.users.client")
def test_unrecognized_message_returns_help(mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]

    response = client.post(
        "/webhook",
        data={"Body": "hola qué tal", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "No entendí" in response.text
