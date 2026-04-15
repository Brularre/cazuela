import pytest
from unittest.mock import patch
from app.router import route

FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


@pytest.mark.parametrize("message,expected_amount,expected_desc", [
    ("gasté 5000 en almuerzo", 5000.0, "almuerzo"),
    ("gaste 1.500 en taxi", 1500.0, "taxi"),
    ("gasté 12.990 en zapatillas", 12990.0, "zapatillas"),
    ("gaste 500 farmacia", 500.0, "farmacia"),
])
def test_expense_pattern_routes_to_save_expense(message, expected_amount, expected_desc):
    with patch("app.router.save_expense", return_value="ok") as mock_save:
        route(message, FAKE_USER)
        mock_save.assert_called_once()
        args = mock_save.call_args[0]
        assert args[0] == expected_amount
        assert expected_desc in args[1]


@pytest.mark.parametrize("message", [
    "resumen",
    "Resumen",
    "RESUMEN",
    "resumen de la semana",
])
def test_summary_pattern_routes_to_get_week_summary(message):
    with patch("app.router.get_week_summary", return_value="ok") as mock_summary:
        route(message, FAKE_USER)
        mock_summary.assert_called_once_with(FAKE_USER)


@pytest.mark.parametrize("message", [
    "hola",
    "qué onda",
    "123",
    "",
])
def test_unrecognized_message_returns_help_text(message):
    result = route(message, FAKE_USER)
    assert "No entendí" in result
