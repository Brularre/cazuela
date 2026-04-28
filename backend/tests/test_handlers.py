from unittest.mock import MagicMock, patch

FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


def make_todo_rows(*tasks):
    return [{"id": str(i), "task": t} for i, t in enumerate(tasks)]


def make_todo_priority_rows(*pairs):
    return [{"id": str(i), "task": t, "priority": p} for i, (t, p) in enumerate(pairs)]


@patch("app.handlers.todos.client")
def test_add_todo_default_priority(mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = None
    from app.handlers.todos import add_todo
    result = add_todo("llamar al banco", FAKE_USER)
    assert "llamar al banco" in result
    inserted = mock_client.table.return_value.insert.call_args[0][0]
    assert inserted["priority"] == "semana"


@patch("app.handlers.todos.client")
def test_add_todo_explicit_priority(mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = None
    from app.handlers.todos import add_todo
    result = add_todo("llamar al banco", FAKE_USER, priority="hoy")
    assert "llamar al banco" in result
    inserted = mock_client.table.return_value.insert.call_args[0][0]
    assert inserted["priority"] == "hoy"


@patch("app.handlers.todos.client")
def test_list_todos_grouped_by_priority(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_todo_priority_rows(
        ("llamar al banco", "hoy"),
        ("renovar seguro", "semana"),
    )
    from app.handlers.todos import list_todos
    result = list_todos(FAKE_USER)
    assert "Hoy" in result
    assert "Esta semana" in result
    assert result.index("llamar al banco") < result.index("renovar seguro")


@patch("app.handlers.todos.client")
def test_list_todos_null_priority_falls_back_to_semana(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"task": "tarea sin prioridad", "priority": None},
    ]
    from app.handlers.todos import list_todos
    result = list_todos(FAKE_USER)
    assert "tarea sin prioridad" in result
    assert "Esta semana" in result


@patch("app.handlers.pantry.client")
def test_consume_pantry_item_accent_insensitive(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabon", "current_quantity": 2}
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import consume_pantry_item
    result = consume_pantry_item("jabón", FAKE_USER)
    assert "jabon" in result
    assert "quedan 1" in result


def make_shopping_rows(*items):
    return [{"id": str(i), "item": it} for i, it in enumerate(items)]


@patch("app.handlers.todos.client")
def test_complete_todo_exact_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_todo_rows("llamar al banco")
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.todos import complete_todo
    result = complete_todo("llamar al banco", FAKE_USER)
    assert "Listo" in result
    assert "llamar al banco" in result


@patch("app.handlers.todos.client")
def test_complete_todo_partial_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_todo_rows("llamar al banco", "pagar el gas")
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.todos import complete_todo
    result = complete_todo("banco", FAKE_USER)
    assert "llamar al banco" in result


@patch("app.handlers.todos.client")
def test_complete_todo_no_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_todo_rows("llamar al banco")
    from app.handlers.todos import complete_todo
    result = complete_todo("dentista", FAKE_USER)
    assert "No encontré" in result


@patch("app.handlers.shopping.client")
def test_add_to_shopping(mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = None
    from app.handlers.shopping import add_to_shopping
    result = add_to_shopping("papel higiénico", FAKE_USER)
    assert "papel higiénico" in result
    assert "✓" in result


@patch("app.handlers.shopping.client")
def test_list_shopping_with_items(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"item": "leche", "quantity": None, "unit": None, "checked": False},
        {"item": "pan", "quantity": None, "unit": None, "checked": False},
    ]
    from app.handlers.shopping import list_shopping
    result = list_shopping(FAKE_USER)
    assert "leche" in result
    assert "pan" in result


@patch("app.handlers.shopping.client")
def test_list_shopping_empty(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    from app.handlers.shopping import list_shopping
    result = list_shopping(FAKE_USER)
    assert "vacía" in result


@patch("app.handlers.shopping.client")
def test_check_item_partial_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_shopping_rows("leche entera", "pan integral")
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.shopping import check_item
    result = check_item("leche", FAKE_USER)
    assert "leche entera" in result


@patch("app.handlers.shopping.client")
def test_check_item_no_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_shopping_rows("leche")
    from app.handlers.shopping import check_item
    result = check_item("mantequilla", FAKE_USER)
    assert "No encontré" in result


def make_waiting_rows(*descriptions):
    return [{"id": str(i), "description": d} for i, d in enumerate(descriptions)]


@patch("app.handlers.waiting_on.client")
def test_add_waiting(mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = None
    from app.handlers.waiting_on import add_waiting
    result = add_waiting("respuesta del seguro", FAKE_USER)
    assert "Guardado" in result
    assert "respuesta del seguro" in result


@patch("app.handlers.waiting_on.client")
def test_list_waiting_empty(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    from app.handlers.waiting_on import list_waiting
    result = list_waiting(FAKE_USER)
    assert "No tienes nada esperando" in result


@patch("app.handlers.waiting_on.client")
def test_list_waiting_with_items(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = make_waiting_rows(
        "respuesta del seguro", "llamada del banco"
    )
    from app.handlers.waiting_on import list_waiting
    result = list_waiting(FAKE_USER)
    assert "respuesta del seguro" in result


@patch("app.handlers.waiting_on.client")
def test_resolve_waiting_partial_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_waiting_rows(
        "respuesta del seguro", "llamada del banco"
    )
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.waiting_on import resolve_waiting
    result = resolve_waiting("seguro", FAKE_USER)
    assert "respuesta del seguro" in result


@patch("app.handlers.waiting_on.client")
def test_resolve_waiting_no_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_waiting_rows(
        "respuesta del seguro"
    )
    from app.handlers.waiting_on import resolve_waiting
    result = resolve_waiting("dentista", FAKE_USER)
    assert "No encontré" in result


def make_pantry_rows(*triples):
    return [
        {"id": str(i), "item": item, "current_quantity": cur, "desired_quantity": des}
        for i, (item, cur, des) in enumerate(triples)
    ]


@patch("app.handlers.pantry.client")
def test_add_pantry_item_new(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = []
    mock_client.table.return_value.insert.return_value.execute.return_value = None
    from app.handlers.pantry import add_pantry_item
    result = add_pantry_item("jabón", 3, FAKE_USER)
    assert "Agregado" in result
    assert "jabon" in result
    inserted = mock_client.table.return_value.insert.call_args[0][0]
    assert inserted["item"] == "jabon"
    assert inserted["desired_quantity"] == 3
    assert inserted["current_quantity"] == 3
    assert inserted["category"] == "otros"


@patch("app.handlers.pantry.client")
def test_add_pantry_item_with_category(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = []
    mock_client.table.return_value.insert.return_value.execute.return_value = None
    from app.handlers.pantry import add_pantry_item
    add_pantry_item("arroz", 3, FAKE_USER, "cocina")
    inserted = mock_client.table.return_value.insert.call_args[0][0]
    assert inserted["category"] == "cocina"


@patch("app.handlers.pantry.client")
def test_add_pantry_item_existing_updates_desired(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = [{"id": "x"}]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import add_pantry_item
    result = add_pantry_item("jabón", 5, FAKE_USER)
    assert "actualizada" in result


@patch("app.handlers.pantry.client")
def test_add_pantry_item_existing_resets_current_qty(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = [{"id": "x"}]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import add_pantry_item
    add_pantry_item("jabón", 5, FAKE_USER)
    updated = mock_client.table.return_value.update.call_args[0][0]
    assert updated["current_quantity"] == 5
    assert updated["desired_quantity"] == 5


@patch("app.handlers.pantry.client")
def test_list_pantry_empty(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    from app.handlers.pantry import list_pantry
    result = list_pantry(FAKE_USER)
    assert "vacía" in result


@patch("app.handlers.pantry.client")
def test_list_pantry_marks_low_stock(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"item": "jabón", "current_quantity": 1, "desired_quantity": 3, "category": "baño"},
        {"item": "papel", "current_quantity": 2, "desired_quantity": 2, "category": "otros"},
    ]
    from app.handlers.pantry import list_pantry
    result = list_pantry(FAKE_USER)
    assert "jabón" in result
    assert "reponer" in result
    assert "papel" in result


@patch("app.handlers.pantry.client")
def test_list_pantry_groups_by_category_in_order(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"item": "arroz", "current_quantity": 2, "desired_quantity": 2, "category": "cocina"},
        {"item": "jabón", "current_quantity": 0, "desired_quantity": 2, "category": "baño"},
        {"item": "pilas", "current_quantity": 1, "desired_quantity": 3, "category": "otros"},
    ]
    from app.handlers.pantry import list_pantry
    result = list_pantry(FAKE_USER)
    assert result.index("Cocina") < result.index("Baño") < result.index("Otros")
    assert "arroz" in result
    assert "jabón" in result
    assert "pilas" in result


@patch("app.handlers.pantry.client")
def test_consume_pantry_item_partial_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón de manos", "current_quantity": 2}
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import consume_pantry_item
    result = consume_pantry_item("jabón", FAKE_USER)
    assert "jabón de manos" in result
    assert "quedan 1" in result


@patch("app.handlers.pantry.client")
def test_consume_pantry_item_hits_zero(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "current_quantity": 1}
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import consume_pantry_item
    result = consume_pantry_item("jabón", FAKE_USER)
    assert "sin stock" in result


@patch("app.handlers.pantry.client")
def test_consume_pantry_item_no_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "current_quantity": 2}
    ]
    from app.handlers.pantry import consume_pantry_item
    result = consume_pantry_item("detergente", FAKE_USER)
    assert "No encontré" in result


@patch("app.handlers.pantry.client")
def test_restock_pantry_item(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "current_quantity": 0, "desired_quantity": 3}
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import restock_pantry_item
    result = restock_pantry_item("jabón", FAKE_USER)
    assert "Repuesto" in result
    assert "jabón" in result
    assert "3 disponibles" in result


@patch("app.handlers.pantry.client")
def test_restock_pantry_item_with_qty(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "botella agua 1.6", "current_quantity": 0, "desired_quantity": 12}
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import restock_pantry_item
    result = restock_pantry_item("botella agua 1.6", FAKE_USER, qty=6)
    assert "Repuesto" in result
    assert "6 disponibles" in result


@patch("app.handlers.pantry.client")
def test_restock_pantry_item_plural_suggests_stored_name(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "botella agua 1.6", "current_quantity": 0, "desired_quantity": 12}
    ]
    from app.handlers.pantry import restock_pantry_item
    result = restock_pantry_item("botellas agua 1.6", FAKE_USER)
    assert "No encontré" in result
    assert "botella agua 1.6" in result
    assert "Quisiste decir" in result


@patch("app.handlers.pantry.client")
def test_restock_pantry_item_no_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "current_quantity": 1, "desired_quantity": 3}
    ]
    from app.handlers.pantry import restock_pantry_item
    result = restock_pantry_item("detergente", FAKE_USER)
    assert "No encontré" in result


@patch("app.handlers.pantry.client")
def test_restock_all_pantry_some_low(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "current_quantity": 0, "desired_quantity": 2},
        {"id": "2", "item": "papel", "current_quantity": 3, "desired_quantity": 3},
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import restock_all_pantry
    result = restock_all_pantry(FAKE_USER)
    assert "1 ítem repuesto" in result


@patch("app.handlers.pantry.client")
def test_restock_all_pantry_plural(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "current_quantity": 0, "desired_quantity": 2},
        {"id": "2", "item": "papel", "current_quantity": 1, "desired_quantity": 3},
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import restock_all_pantry
    result = restock_all_pantry(FAKE_USER)
    assert "2 ítems repuestos" in result


@patch("app.handlers.pantry.client")
def test_restock_all_pantry_already_stocked(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "current_quantity": 2, "desired_quantity": 2},
    ]
    from app.handlers.pantry import restock_all_pantry
    result = restock_all_pantry(FAKE_USER)
    assert "al día" in result


@patch("app.handlers.pantry.client")
def test_set_pantry_stock(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "desired_quantity": 3}
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import set_pantry_stock
    result = set_pantry_stock("jabón", 2, FAKE_USER)
    assert "Stock actualizado" in result
    assert "2 disponibles" in result
    updated = mock_client.table.return_value.update.call_args[0][0]
    assert updated["current_quantity"] == 2


@patch("app.handlers.pantry.client")
def test_set_pantry_stock_no_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "desired_quantity": 3}
    ]
    from app.handlers.pantry import set_pantry_stock
    result = set_pantry_stock("detergente", 2, FAKE_USER)
    assert "No encontré" in result


@patch("app.handlers.pantry.client")
def test_set_pantry_stock_caps_at_9999(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "desired_quantity": 3}
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import set_pantry_stock
    result = set_pantry_stock("jabón", 99999, FAKE_USER)
    updated = mock_client.table.return_value.update.call_args[0][0]
    assert updated["current_quantity"] == 9999


@patch("app.handlers.summary.client")
def test_week_summary_shows_budget_remaining(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"amount": "50000", "category": "comida"}
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"amount": "150000"}
    ]
    from app.handlers.summary import get_week_summary
    result = get_week_summary(FAKE_USER)
    assert "te quedan" in result
    assert "150.000" in result


@patch("app.handlers.summary.client")
def test_week_summary_shows_budget_exceeded(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"amount": "200000", "category": "comida"}
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"amount": "150000"}
    ]
    from app.handlers.summary import get_week_summary
    result = get_week_summary(FAKE_USER)
    assert "excedido" in result
    assert "⚠" in result


@patch("app.handlers.summary.client")
def test_week_summary_no_budget_line_when_unset(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"amount": "50000", "category": "comida"}
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    from app.handlers.summary import get_week_summary
    result = get_week_summary(FAKE_USER)
    assert "Presupuesto" not in result


@patch("app.handlers.summary.client")
def test_week_summary_no_expenses_this_week(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = []
    from app.handlers.summary import get_week_summary
    result = get_week_summary(FAKE_USER)
    assert "No hay gastos registrados esta semana." in result


@patch("app.handlers.summary.client")
def test_week_summary_shows_user_name(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"amount": "5000", "category": "comida"}
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    user = {**FAKE_USER, "name": "Ana"}
    from app.handlers.summary import get_week_summary
    result = get_week_summary(user)
    assert "¡Hola Ana!" in result


@patch("app.handlers.budget.client")
def test_set_budget(mock_client):
    mock_client.table.return_value.upsert.return_value.execute.return_value = None
    from app.handlers.budget import set_budget
    result = set_budget(600000, FAKE_USER)
    assert "mensual" in result
    assert "600.000" in result


# ---------------------------------------------------------------------------
# End-to-end: full Flavor B flow via router.route()
# Seed pantry → qué cocino → mocked AI → elegir 2 → sí
# ---------------------------------------------------------------------------

import json
import pytest
from unittest.mock import patch

E2E_USER = {"id": "e2e-user-1111", "phone": "+56911111111", "ai_mode": True}

FAKE_SUGGESTIONS = [
    {
        "name": "sopa de verduras",
        "ingredients": [
            {"item": "cebolla", "quantity": 1, "unit": None},
            {"item": "zanahoria", "quantity": 2, "unit": None},
        ],
        "uses_pantry": ["cebolla", "zanahoria"],
        "missing": [],
    },
    {
        "name": "arroz con pollo",
        "ingredients": [
            {"item": "arroz", "quantity": 2, "unit": "tazas"},
            {"item": "pollo", "quantity": 500, "unit": "g"},
        ],
        "uses_pantry": ["arroz"],
        "missing": ["pollo"],
    },
]


@pytest.fixture()
def e2e_store(monkeypatch):
    ctx_store = {}
    pantry_rows = [
        {"item": "cebolla", "current_quantity": 2, "desired_quantity": 2, "user_id": E2E_USER["id"]},
        {"item": "zanahoria", "current_quantity": 1, "desired_quantity": 2, "user_id": E2E_USER["id"]},
        {"item": "arroz", "current_quantity": 3, "desired_quantity": 3, "user_id": E2E_USER["id"]},
    ]
    recipes_rows = []
    ingredients_rows = []
    shopping_rows = []

    class FakeExecute:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, table, store, pantry, recipes, ingredients, shopping):
            self._table = table
            self._store = store
            self._pantry = pantry
            self._recipes = recipes
            self._ingredients = ingredients
            self._shopping = shopping
            self._eq = {}
            self._pending_insert = None
            self._pending_update = None
            self._do_delete = False
            self._lt = None

        def select(self, *a):
            return self

        def insert(self, data):
            self._pending_insert = data
            return self

        def update(self, data):
            self._pending_update = data
            return self

        def delete(self):
            self._do_delete = True
            return self

        def eq(self, f, v):
            self._eq[f] = v
            return self

        def lt(self, f, v):
            self._lt = (f, v)
            return self

        def execute(self):
            if self._pending_insert is not None:
                rows = self._pending_insert if isinstance(self._pending_insert, list) else [self._pending_insert]
                rows = [dict(r) for r in rows]
                if self._table == "mcp_contexts":
                    self._store[rows[0]["context_id"]] = rows[0]
                    return FakeExecute([rows[0]])
                if self._table == "recipes":
                    row = {**rows[0], "id": f"recipe-{len(self._recipes)+1}"}
                    self._recipes.append(row)
                    return FakeExecute([row])
                if self._table == "recipe_ingredients":
                    self._ingredients.extend(rows)
                    return FakeExecute(rows)
                if self._table == "shopping_list":
                    self._shopping.extend(rows)
                    return FakeExecute(rows)
                return FakeExecute(rows)

            if self._pending_update is not None:
                results = []
                for row in self._store.values():
                    if all(row.get(k) == v for k, v in self._eq.items()):
                        row.update(self._pending_update)
                        results.append(dict(row))
                return FakeExecute(results)

            if self._do_delete:
                if self._lt:
                    f, v = self._lt
                    to_del = [k for k, row in self._store.items() if row.get(f, "") < v]
                    deleted = [self._store.pop(k) for k in to_del]
                    return FakeExecute(deleted)
                if self._table == "recipe_ingredients":
                    recipe_id = self._eq.get("recipe_id")
                    before = [r for r in self._ingredients if r.get("recipe_id") == recipe_id]
                    self._ingredients[:] = [r for r in self._ingredients if r.get("recipe_id") != recipe_id]
                    return FakeExecute(before)
                return FakeExecute([])

            if self._table == "mcp_contexts":
                results = [dict(r) for r in self._store.values()
                           if all(r.get(k) == v for k, v in self._eq.items())]
                return FakeExecute(results)
            if self._table == "pantry":
                results = [r for r in self._pantry if all(r.get(k) == v for k, v in self._eq.items())]
                return FakeExecute(results)
            if self._table == "recipes":
                results = [r for r in self._recipes if all(r.get(k) == v for k, v in self._eq.items())]
                return FakeExecute(results)
            if self._table == "recipe_ingredients":
                results = [r for r in self._ingredients if all(r.get(k) == v for k, v in self._eq.items())]
                return FakeExecute(results)
            if self._table == "shopping_list":
                results = [r for r in self._shopping if all(r.get(k) == v for k, v in self._eq.items())]
                return FakeExecute(results)
            return FakeExecute([])

    class FakeClient:
        def __init__(self):
            pass
        def table(self, name):
            return FakeQuery(name, ctx_store, pantry_rows, recipes_rows, ingredients_rows, shopping_rows)

    fc = FakeClient()
    monkeypatch.setattr("app.mcp.context.client", fc)
    monkeypatch.setattr("app.handlers.recipes.db", fc)
    monkeypatch.setattr("app.handlers.shopping.client", fc)
    monkeypatch.setattr("app.router.classify", lambda m: None)

    # Patch create_recipe and replace_ingredients to write to our in-memory stores
    def fake_create_recipe(uid, name, servings=2):
        row = {"id": f"recipe-{len(recipes_rows)+1}", "name": name, "servings": servings, "user_id": uid}
        recipes_rows.append(row)
        return row

    def fake_replace_ingredients(recipe_id, rows):
        ingredients_rows[:] = [r for r in ingredients_rows if r.get("recipe_id") != recipe_id]
        for r in rows:
            ingredients_rows.append({**r, "recipe_id": recipe_id})
        return rows

    monkeypatch.setattr("app.handlers.recipes.create_recipe", fake_create_recipe)
    monkeypatch.setattr("app.handlers.recipes.replace_ingredients", fake_replace_ingredients)

    return {
        "ctx": ctx_store,
        "pantry": pantry_rows,
        "recipes": recipes_rows,
        "ingredients": ingredients_rows,
        "shopping": shopping_rows,
        "client": fc,
    }


def test_e2e_que_cocino_elegir_si(e2e_store, monkeypatch):
    """Full Flavor B flow: qué cocino → mocked AI → elegir 2 → sí."""
    from app.router import route

    # Patch AI so we don't call Haiku
    monkeypatch.setattr(
        "app.mcp.agent._propose_recipe_suggest",
        lambda ctx: {"suggestions": FAKE_SUGGESTIONS},
    )
    monkeypatch.setattr(
        "app.handlers.recipes.get_recipes",
        lambda uid: [],
    )

    # Step 1: request suggestions
    reply1 = route("qué cocino", E2E_USER)
    assert "sopa de verduras" in reply1
    assert "arroz con pollo" in reply1
    assert "elegir" in reply1

    # Step 2: pick option 2 (arroz con pollo — has missing: pollo)
    reply2 = route("elegir 2", E2E_USER)
    assert "arroz con pollo" in reply2
    assert "guardada" in reply2
    assert "pollo" in reply2
    assert "lista de compras" in reply2

    # recipe was inserted
    assert len(e2e_store["recipes"]) == 1
    assert e2e_store["recipes"][0]["name"] == "arroz con pollo"
    # ingredients were inserted
    ingredient_items = {r["item"] for r in e2e_store["ingredients"]}
    assert "arroz" in ingredient_items
    assert "pollo" in ingredient_items

    # Step 3: confirm shopping add
    reply3 = route("sí", E2E_USER)
    assert "Buen provecho" in reply3

    # shopping_list should have the missing item
    assert len(e2e_store["shopping"]) == 1
    assert e2e_store["shopping"][0]["item"] == "pollo"
    assert e2e_store["shopping"][0]["source"] == "recipe"


def test_e2e_que_puedo_hacer_elegir_no_missing(e2e_store, monkeypatch):
    """Flavor A: qué puedo hacer → elegir 1 (no missing) → no shopping prompt."""
    from app.router import route
    from unittest.mock import patch as upatch

    SUGGESTIONS_A = [
        {"recipe_id": "r-saved", "name": "sopa de verduras", "have": 2, "total": 2, "missing": [], "score": 1.0},
    ]

    def mock_get_recipes(uid):
        return [{"id": "r-saved", "name": "sopa de verduras", "servings": 2}]

    def mock_get_ingredients(rid):
        return [{"item": "cebolla"}, {"item": "zanahoria"}]

    monkeypatch.setattr("app.handlers.recipes.get_recipes", mock_get_recipes)
    monkeypatch.setattr("app.handlers.recipes.get_ingredients", mock_get_ingredients)
    monkeypatch.setattr(
        "app.mcp.agent._propose_recipe_match",
        lambda ctx: {"suggestions": SUGGESTIONS_A},
    )

    reply1 = route("qué puedo hacer", E2E_USER)
    assert "sopa de verduras" in reply1
    assert "2/2" in reply1

    reply2 = route("elegir 1", E2E_USER)
    assert "sopa de verduras" in reply2
    assert "A cocinar" in reply2
    assert "lista de compras" not in reply2
    assert len(e2e_store["shopping"]) == 0
