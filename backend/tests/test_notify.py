import warnings
from unittest.mock import MagicMock, patch


def _ok_response():
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    return r


def _fail_response():
    r = MagicMock()
    r.ok = False
    r.status_code = 400
    r.text = "Bad Request"
    return r


def _settings(token="tok", phone_id="123"):
    s = MagicMock()
    s.meta_access_token = token
    s.meta_phone_number_id = phone_id
    return s


# ---------------------------------------------------------------------------
# send_text
# ---------------------------------------------------------------------------


def test_send_text_success_returns_true():
    with patch("app.notify.requests.post", return_value=_ok_response()) as mock_post, \
         patch("app.notify.settings", _settings()):
        from app.notify import send_text
        result = send_text("+56900000000", "hola")
    assert result is True
    mock_post.assert_called_once()


def test_send_text_failure_returns_false_and_warns():
    with patch("app.notify.requests.post", return_value=_fail_response()), \
         patch("app.notify.settings", _settings()):
        from app.notify import send_text
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = send_text("+56900000000", "hola")
    assert result is False
    assert any("send failed" in str(warning.message) for warning in w)


def test_send_text_missing_credentials_returns_false():
    with patch("app.notify.settings", _settings(token="", phone_id="")):
        from app.notify import send_text
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = send_text("+56900000000", "hola")
    assert result is False
    assert any("credentials" in str(warning.message) for warning in w)


def test_send_text_strips_plus_from_phone():
    with patch("app.notify.requests.post", return_value=_ok_response()) as mock_post, \
         patch("app.notify.settings", _settings()):
        from app.notify import send_text
        send_text("+56900000000", "hola")
    payload = mock_post.call_args.kwargs["json"]
    assert payload["to"] == "56900000000"


# ---------------------------------------------------------------------------
# send_interactive
# ---------------------------------------------------------------------------


def test_send_interactive_success_returns_true():
    with patch("app.notify.requests.post", return_value=_ok_response()) as mock_post, \
         patch("app.notify.settings", _settings()):
        from app.notify import send_interactive
        result = send_interactive("+56900000000", "Buenos días", ["Continuar"])
    assert result is True
    mock_post.assert_called_once()


def test_send_interactive_failure_returns_false_and_warns():
    with patch("app.notify.requests.post", return_value=_fail_response()), \
         patch("app.notify.settings", _settings()):
        from app.notify import send_interactive
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = send_interactive("+56900000000", "body", ["Continuar"])
    assert result is False
    assert any("interactive send failed" in str(warning.message) for warning in w)


def test_send_interactive_missing_credentials_returns_false():
    with patch("app.notify.settings", _settings(token="", phone_id="")):
        from app.notify import send_interactive
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = send_interactive("+56900000000", "body", ["Continuar"])
    assert result is False


def test_send_interactive_payload_contains_continuar_button():
    with patch("app.notify.requests.post", return_value=_ok_response()) as mock_post, \
         patch("app.notify.settings", _settings()):
        from app.notify import send_interactive
        send_interactive("+56900000000", "digest body", ["Continuar"])
    payload = mock_post.call_args.kwargs["json"]
    assert payload["type"] == "interactive"
    buttons = payload["interactive"]["action"]["buttons"]
    assert len(buttons) == 1
    assert buttons[0]["reply"]["title"] == "Continuar"


def test_send_interactive_multiple_buttons():
    with patch("app.notify.requests.post", return_value=_ok_response()) as mock_post, \
         patch("app.notify.settings", _settings()):
        from app.notify import send_interactive
        send_interactive("+56900000000", "body", ["Sí", "No", "Más info"])
    payload = mock_post.call_args.kwargs["json"]
    buttons = payload["interactive"]["action"]["buttons"]
    assert len(buttons) == 3
    titles = [b["reply"]["title"] for b in buttons]
    assert titles == ["Sí", "No", "Más info"]


def test_send_interactive_body_text_preserved():
    with patch("app.notify.requests.post", return_value=_ok_response()) as mock_post, \
         patch("app.notify.settings", _settings()):
        from app.notify import send_interactive
        send_interactive("+56900000000", "☀️ Buenos días\n• tarea 1", ["Continuar"])
    payload = mock_post.call_args.kwargs["json"]
    assert payload["interactive"]["body"]["text"] == "☀️ Buenos días\n• tarea 1"


def test_send_interactive_dict_button_uses_provided_id():
    with patch("app.notify.requests.post", return_value=_ok_response()) as mock_post, \
         patch("app.notify.settings", _settings()):
        from app.notify import send_interactive
        send_interactive(
            "+56900000000",
            "⏰ Llamar al banco",
            [
                {"id": "snooze:todos:abc-123:30", "title": "Posponer 30 min"},
                {"id": "done:todos:abc-123", "title": "Listo"},
            ],
        )
    payload = mock_post.call_args.kwargs["json"]
    buttons = payload["interactive"]["action"]["buttons"]
    assert len(buttons) == 2
    assert buttons[0]["reply"]["id"] == "snooze:todos:abc-123:30"
    assert buttons[0]["reply"]["title"] == "Posponer 30 min"
    assert buttons[1]["reply"]["id"] == "done:todos:abc-123"
    assert buttons[1]["reply"]["title"] == "Listo"
