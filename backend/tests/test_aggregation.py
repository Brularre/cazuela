import pytest
from app.handlers.summary import aggregate_by_category, format_amount
from tests.fixtures.expenses import EXPENSES


# --- format_amount() ---

@pytest.mark.parametrize("amount,expected", [
    (1000, "$1.000"),
    (12990, "$12.990"),
    (1000000, "$1.000.000"),
    (500, "$500"),
    (0, "$0"),
])
def test_format_amount(amount, expected):
    assert format_amount(amount) == expected


# --- aggregate_by_category() ---

def test_empty_returns_empty_dict():
    assert aggregate_by_category([]) == {}


def test_single_expense():
    expenses = [{"amount": "5000", "category": "comida"}]
    result = aggregate_by_category(expenses)
    assert result == {"comida": 5000.0}


def test_same_category_sums_correctly():
    expenses = [
        {"amount": "5000", "category": "comida"},
        {"amount": "2000", "category": "comida"},
        {"amount": "990.5", "category": "comida"},
    ]
    result = aggregate_by_category(expenses)
    assert result["comida"] == pytest.approx(7990.5)


def test_multiple_categories_all_present():
    result = aggregate_by_category(EXPENSES)
    assert "comida" in result
    assert "transporte" in result
    assert "hogar" in result
    assert "entretenimiento" in result
    assert "salud" in result
    assert "ropa" in result


def test_sorted_descending_by_total():
    result = aggregate_by_category(EXPENSES)
    totals = list(result.values())
    assert totals == sorted(totals, reverse=True)


def test_decimal_amounts_handled():
    expenses = [
        {"amount": "990.5", "category": "comida"},
        {"amount": "9.5", "category": "comida"},
    ]
    result = aggregate_by_category(expenses)
    assert result["comida"] == pytest.approx(1000.0)


def test_category_totals_are_correct():
    result = aggregate_by_category(EXPENSES)
    # comida: 5000 + 2000 + 990.5 + 3800 = 11790.5
    assert result["comida"] == pytest.approx(11790.5)
    # transporte: 3000 + 1500 + 2500 = 7000
    assert result["transporte"] == pytest.approx(7000.0)
    # hogar: 8500 + 45000 = 53500
    assert result["hogar"] == pytest.approx(53500.0)
