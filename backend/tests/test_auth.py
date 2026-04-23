from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import jwt
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_PHONE = "+56912345678"


def test_request_otp_throttled_when_recent_exists():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "user-1"}
    ]
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.execute.return_value.data = [
        {"id": "otp-recent"}
    ]

    with patch("app.routes.auth.client", db), \
         patch("app.routes.auth.requests") as mock_requests:
        response = client.post("/auth/request-otp", json={"phone": TEST_PHONE})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    db.table.return_value.insert.assert_not_called()
    mock_requests.post.assert_not_called()


def test_request_otp_unknown_phone():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("app.routes.auth.client", db):
        response = client.post("/auth/request-otp", json={"phone": TEST_PHONE})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    db.table.return_value.insert.assert_not_called()


def test_request_otp_known_phone():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "user-1"}
    ]
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.execute.return_value.data = []
    db.table.return_value.insert.return_value.execute.return_value.data = [{}]

    with patch("app.routes.auth.client", db), \
         patch("app.routes.auth.requests") as mock_requests, \
         patch("app.routes.auth.settings") as mock_settings:
        mock_settings.meta_access_token = "fake-token"
        mock_settings.meta_phone_number_id = "12345"
        mock_settings.session_secret = "test-secret"

        response = client.post("/auth/request-otp", json={"phone": TEST_PHONE})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    db.table.return_value.insert.assert_called_once()
    mock_requests.post.assert_called_once()


def _otp_select_chain(db):
    return (
        db.table.return_value
        .select.return_value
        .eq.return_value   # phone
        .eq.return_value   # used
        .gt.return_value   # expires_at
    )


def test_verify_otp_valid():
    db = MagicMock()
    otp_row = {"id": "otp-1", "code": "123456", "attempts": 0}
    _otp_select_chain(db).execute.return_value.data = [otp_row]
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "user-1"}
    ]

    with patch("app.routes.auth.client", db), \
         patch("app.routes.auth.settings") as mock_settings:
        mock_settings.session_secret = "test-secret"

        response = client.post(
            "/auth/verify-otp",
            json={"phone": TEST_PHONE, "code": "123456"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "session" in response.cookies
    decoded = jwt.decode(response.cookies["session"], "test-secret", algorithms=["HS256"])
    assert decoded["user_id"] == "user-1"


def test_verify_otp_invalid_code():
    db = MagicMock()
    otp_row = {"id": "otp-1", "code": "123456", "attempts": 0}
    _otp_select_chain(db).execute.return_value.data = [otp_row]

    with patch("app.routes.auth.client", db), \
         patch("app.routes.auth.settings") as mock_settings:
        mock_settings.session_secret = "test-secret"

        response = client.post(
            "/auth/verify-otp",
            json={"phone": TEST_PHONE, "code": "000000"},
        )

    assert response.status_code == 401
    db.table.return_value.update.assert_called()


def test_verify_otp_expired():
    db = MagicMock()
    _otp_select_chain(db).execute.return_value.data = []

    with patch("app.routes.auth.client", db), \
         patch("app.routes.auth.settings") as mock_settings:
        mock_settings.session_secret = "test-secret"

        response = client.post(
            "/auth/verify-otp",
            json={"phone": TEST_PHONE, "code": "999999"},
        )

    assert response.status_code == 401


def test_verify_otp_brute_force_blocked():
    db = MagicMock()
    otp_row = {"id": "otp-1", "code": "123456", "attempts": 5}
    _otp_select_chain(db).execute.return_value.data = [otp_row]

    with patch("app.routes.auth.client", db), \
         patch("app.routes.auth.settings") as mock_settings:
        mock_settings.session_secret = "test-secret"

        response = client.post(
            "/auth/verify-otp",
            json={"phone": TEST_PHONE, "code": "999999"},
        )

    assert response.status_code == 429
