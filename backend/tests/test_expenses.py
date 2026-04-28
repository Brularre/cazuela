import pytest
from unittest.mock import patch

from app.handlers.expenses import map_category, normalize

FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


@pytest.mark.parametrize("description,expected", [
    ("almuerzo en el mall", "comida"),
    ("Uber al aeropuerto", "transporte"),
    ("farmacia cruz verde", "salud"),
    ("arriendo de enero", "hogar"),
    ("Netflix mensual", "entretenimiento"),
    ("zapatillas nike", "ropa"),
    ("audifonos bluetooth", "tecnologia"),
    ("curso de python", "educacion"),
    ("hotel en Buenos Aires", "viajes"),
    ("algo desconocido", "otros"),
])
def test_map_category(description, expected):
    assert map_category(description) == expected


def test_map_category_accent_insensitive():
    assert map_category("médico especialista") == "salud"
    assert map_category("café con leche") == "comida"


def test_normalize_strips_accents():
    assert normalize("médico") == "medico"
    assert normalize("café") == "cafe"
    assert normalize("almuerzo") == "almuerzo"


def test_normalize_lowercases():
    assert normalize("UBER") == "uber"
    assert normalize("Netflix") == "netflix"


@patch("app.handlers.expenses.client")
def test_save_expense_inserts_and_replies(mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = None
    from app.handlers.expenses import save_expense
    result = save_expense(5000, "almuerzo en restaurante", FAKE_USER)
    assert "5.000" in result
    assert "comida" in result
    inserted = mock_client.table.return_value.insert.call_args[0][0]
    assert inserted["user_id"] == FAKE_USER["id"]
    assert inserted["amount"] == 5000
    assert inserted["category"] == "comida"
    assert "date" in inserted


@patch("app.handlers.expenses.client")
def test_expense_history_counts_by_category(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"category": "comida"},
        {"category": "comida"},
        {"category": "transporte"},
    ]
    from app.handlers.expenses import expense_history
    result = expense_history("user-1")
    assert result == {"comida": 2, "transporte": 1}
    gte_call = mock_client.table.return_value.select.return_value.eq.return_value.gte.call_args
    assert gte_call[0][0] == "date"
