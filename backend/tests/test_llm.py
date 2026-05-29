import json
import pytest
from unittest.mock import patch

from app.llm import classify, _StubProvider, _parse_intent_json, _user_profile_prefix
from tests.conftest import FAKE_USER


@pytest.fixture(autouse=True)
def clear_stub():
    _StubProvider.clear()
    yield
    _StubProvider.clear()


def _register(message: str, payload: dict):
    _StubProvider.register(message, json.dumps(payload))


def test_classify_add_expense():
    _register("gasté 5000 en almuerzo", {"intent": "add_expense", "amount": 5000, "description": "almuerzo"})
    result = classify("gasté 5000 en almuerzo", FAKE_USER)
    assert result["intent"] == "add_expense"
    assert result["amount"] == 5000
    assert result["description"] == "almuerzo"


def test_classify_ambiguous_expense():
    _register("pagué 3000", {"intent": "ambiguous_expense", "amount": 3000})
    result = classify("pagué 3000", FAKE_USER)
    assert result["intent"] == "ambiguous_expense"
    assert result["amount"] == 3000


def test_classify_add_todo_with_priority():
    _register("pendiente hoy: dentista", {"intent": "add_todo", "task": "dentista", "priority": "hoy"})
    result = classify("pendiente hoy: dentista", FAKE_USER)
    assert result["intent"] == "add_todo"
    assert result["priority"] == "hoy"


def test_classify_add_pantry_item():
    _register(
        "despensa cocina: arroz 3",
        {"intent": "add_pantry_item", "item": "arroz", "qty": 3, "category": "cocina"},
    )
    result = classify("despensa cocina: arroz 3", FAKE_USER)
    assert result["intent"] == "add_pantry_item"
    assert result["qty"] == 3
    assert result["category"] == "cocina"


def test_classify_unknown_returns_none():
    _register("bla bla bla", {"intent": "unknown"})
    assert classify("bla bla bla", FAKE_USER) is None


def test_classify_invalid_intent_returns_none():
    _register("something", {"intent": "fly_to_moon"})
    assert classify("something", FAKE_USER) is None


def test_classify_returns_none_when_disabled():
    user = {**FAKE_USER, "ai_mode": False}
    _register("gasté 5000 en almuerzo", {"intent": "add_expense", "amount": 5000, "description": "almuerzo"})
    assert classify("gasté 5000 en almuerzo", user) is None


def test_classify_returns_none_when_no_provider():
    with patch("app.llm.settings") as mock_settings:
        mock_settings.classifier_provider = "none"
        result = classify("gasté 5000 en almuerzo", FAKE_USER)
    assert result is None


def test_classify_returns_none_on_api_error():
    with patch("app.llm._provider_for") as mock_provider:
        mock_provider.return_value.complete.side_effect = Exception("timeout")
        result = classify("gasté 5000 en almuerzo", FAKE_USER)
    assert result is None


def test_classify_long_message_returns_none():
    assert classify("a" * 1001, FAKE_USER) is None


def test_parse_intent_json_strips_markdown():
    raw = "```json\n{\"intent\": \"list_todos\"}\n```"
    result = _parse_intent_json(raw)
    assert result == {"intent": "list_todos"}


def test_parse_intent_json_rejects_unknown_intent():
    assert _parse_intent_json(json.dumps({"intent": "unknown"})) is None


def test_parse_intent_json_rejects_invalid_intent():
    assert _parse_intent_json(json.dumps({"intent": "fly_to_moon"})) is None


def test_parse_intent_json_returns_none_on_bad_json():
    assert _parse_intent_json("not json at all") is None


def test_parse_intent_json_returns_none_on_empty():
    assert _parse_intent_json("") is None


def test_user_profile_prefix_includes_name_and_currency():
    user = {**FAKE_USER, "name": "Blas", "currency": "USD"}
    prefix = _user_profile_prefix(user)
    assert "Blas" in prefix
    assert "USD" in prefix


def test_user_profile_prefix_defaults_currency_to_clp():
    prefix = _user_profile_prefix(FAKE_USER)
    assert "CLP" in prefix


def test_user_profile_prefix_omits_name_when_missing():
    prefix = _user_profile_prefix(FAKE_USER)
    assert "name" not in prefix.lower() or "User's name" not in prefix


def test_route_uses_ai_when_regex_misses():
    _register("que hago con esto", {"intent": "add_expense", "amount": 5000, "description": "almuerzo"})
    with patch("app.dispatch.save_expense", return_value="ok") as mock_save:
        from app.router import route
        result = route("que hago con esto", FAKE_USER)
    assert result == "ok"
    mock_save.assert_called_once_with(5000, "almuerzo", FAKE_USER)


def test_route_falls_back_to_regex_when_ai_returns_none():
    with patch("app.router.save_expense", return_value="ok") as mock_save:
        from app.router import route
        result = route("gasté 5000 en almuerzo", FAKE_USER)
    assert result == "ok"
    mock_save.assert_called_once()


def test_route_falls_back_to_regex_when_dispatch_raises():
    _register("gasté 5000 en almuerzo", {"intent": "add_expense", "amount": 5000, "description": "almuerzo"})
    with patch("app.dispatch.save_expense", side_effect=Exception("db error")), \
         patch("app.router.save_expense", return_value="✓ Gasto guardado\n$5.000 · comida · almuerzo") as mock_save:
        from app.router import route
        result = route("gasté 5000 en almuerzo", FAKE_USER)
    assert isinstance(result, str)
    assert len(result) > 0
    mock_save.assert_called_once()


def test_dispatch_returns_none_on_missing_required_fields():
    from app.router import _dispatch
    assert _dispatch({"intent": "add_expense", "amount": 5000}, "msg", FAKE_USER) is None
    assert _dispatch({"intent": "add_todo"}, "msg", FAKE_USER) is None
    assert _dispatch({"intent": "add_pantry_item", "item": "arroz"}, "msg", FAKE_USER) is None


def test_dispatch_ambiguous_expense_uses_raw_message():
    from app.router import _dispatch
    with patch("app.dispatch._handle_ambiguous_expense", return_value="ok") as mock:
        _dispatch({"intent": "ambiguous_expense", "amount": 3000}, "pagué 3000", FAKE_USER)
    mock.assert_called_once_with(3000, "pagué 3000", FAKE_USER)
