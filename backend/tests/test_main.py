from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_returns_twiml():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]

    with patch("app.db.users.client", mock_db):
        response = client.post(
            "/webhook",
            data={"Body": "hola", "From": "whatsapp:+56912345678"},
        )
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Response>" in response.text
    assert "<Message>" in response.text
