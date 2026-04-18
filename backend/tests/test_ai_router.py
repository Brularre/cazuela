import json
import pytest
from unittest.mock import MagicMock, patch
from app.ai_router import classify

FAKE_USER = {"id": "11111111-1111-1111-1111-111111111111", "phone": "+56912345678"}


def _make_ai_response(payload: dict):
    response = MagicMock()
    response.content = [MagicMock(text=json.dumps(payload))]
    return response


def _mock_classify(message: str, intent_payload: dict) -> dict | None:
    with patch("app.ai_router.settings") as mock_settings, \
         patch("app.ai_router.anthropic") as mock_anthropic:
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value.messages.create.return_value = (
            _make_ai_response(intent_payload)
        )
        return classify(message)


def test_classify_add_expense():
    result = _mock_classify("gasté 5000 en almuerzo", {
        "intent": "add_expense", "amount": 5000, "description": "almuerzo"
    })
    assert result["intent"] == "add_expense"
    assert result["amount"] == 5000
    assert result["description"] == "almuerzo"


def test_classify_ambiguous_expense():
    result = _mock_classify("pagué 3000", {
        "intent": "ambiguous_expense", "amount": 3000
    })
    assert result["intent"] == "ambiguous_expense"
    assert result["amount"] == 3000


def test_classify_add_todo_with_priority():
    result = _mock_classify("pendiente hoy: dentista", {
        "intent": "add_todo", "task": "dentista", "priority": "hoy"
    })
    assert result["intent"] == "add_todo"
    assert result["priority"] == "hoy"


def test_classify_add_pantry_item():
    result = _mock_classify("despensa cocina: arroz 3", {
        "intent": "add_pantry_item", "item": "arroz", "qty": 3, "category": "cocina"
    })
    assert result["intent"] == "add_pantry_item"
    assert result["qty"] == 3
    assert result["category"] == "cocina"


def test_classify_unknown_returns_none():
    result = _mock_classify("bla bla bla", {"intent": "unknown"})
    assert result is None


def test_classify_invalid_intent_returns_none():
    result = _mock_classify("something", {"intent": "fly_to_moon"})
    assert result is None


def test_classify_returns_none_when_disabled():
    with patch("app.ai_router.settings") as mock_settings:
        mock_settings.use_ai_agent = False
        mock_settings.anthropic_api_key = "sk-ant-fake"
        result = classify("gasté 5000 en almuerzo")
    assert result is None


def test_classify_returns_none_on_api_error():
    with patch("app.ai_router.settings") as mock_settings, \
         patch("app.ai_router.anthropic") as mock_anthropic:
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value.messages.create.side_effect = Exception("timeout")
        result = classify("gasté 5000 en almuerzo")
    assert result is None


def test_classify_returns_none_on_malformed_json():
    with patch("app.ai_router.settings") as mock_settings, \
         patch("app.ai_router.anthropic") as mock_anthropic:
        response = MagicMock()
        response.content = [MagicMock(text="not json")]
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value.messages.create.return_value = response
        result = classify("gasté 5000 en almuerzo")
    assert result is None


def test_route_uses_ai_when_enabled():
    with patch("app.router.classify", return_value={
        "intent": "add_expense", "amount": 5000, "description": "almuerzo"
    }), patch("app.router.save_expense", return_value="ok") as mock_save:
        from app.router import route
        result = route("gasté 5000 en almuerzo", FAKE_USER)
    assert result == "ok"
    mock_save.assert_called_once_with(5000, "almuerzo", FAKE_USER)


def test_route_falls_back_to_regex_when_ai_returns_none():
    with patch("app.router.classify", return_value=None), \
         patch("app.router.save_expense", return_value="ok") as mock_save:
        from app.router import route
        result = route("gasté 5000 en almuerzo", FAKE_USER)
    assert result == "ok"
    mock_save.assert_called_once()
