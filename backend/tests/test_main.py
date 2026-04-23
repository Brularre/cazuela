from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from tests.conftest import meta_payload, FAKE_USER

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_sends_reply():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]

    with patch("app.db.users.client", mock_db), \
         patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("hola"))

    assert response.status_code == 200
    mock_send.assert_called_once()
    _, text = mock_send.call_args[0]
    assert len(text) > 0


def test_webhook_ignores_non_text_messages():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [{"from": "56912345678", "type": "image"}]}}]}],
    }
    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    mock_send.assert_not_called()


def test_webhook_verify_valid_token():
    with patch("main.settings") as s:
        s.meta_webhook_verify_token = "my-secret"
        s.meta_skip_validation = True
        response = client.get("/webhook?hub.mode=subscribe&hub.verify_token=my-secret&hub.challenge=abc123")
    assert response.status_code == 200
    assert response.text == "abc123"


def test_webhook_verify_wrong_token():
    with patch("main.settings") as s:
        s.meta_webhook_verify_token = "my-secret"
        response = client.get("/webhook?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=abc123")
    assert response.status_code == 403


def test_webhook_verify_empty_token_rejected():
    with patch("main.settings") as s:
        s.meta_webhook_verify_token = ""
        response = client.get("/webhook?hub.mode=subscribe&hub.verify_token=&hub.challenge=abc123")
    assert response.status_code == 403


def test_webhook_ignores_delivery_receipts():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"statuses": [{"id": "msg-1", "status": "delivered"}]}}]}],
    }
    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    mock_send.assert_not_called()


def test_webhook_bad_signature_rejected():
    with patch("main.settings") as s:
        s.meta_skip_validation = False
        s.meta_app_secret = "real-secret"
        response = client.post(
            "/webhook",
            json=meta_payload("hola"),
            headers={"X-Hub-Signature-256": "sha256=badsignature"},
        )
    assert response.status_code == 403
