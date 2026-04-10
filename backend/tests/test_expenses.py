import pytest
from app.handlers.expenses import map_category, normalize


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
