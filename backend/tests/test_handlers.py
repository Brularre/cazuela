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
        {"id": "1", "item": "jabón", "desired_quantity": 3}
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.pantry import restock_pantry_item
    result = restock_pantry_item("jabón", FAKE_USER)
    assert "Repuesto" in result
    assert "jabón" in result


@patch("app.handlers.pantry.client")
def test_restock_pantry_item_no_match(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "item": "jabón", "desired_quantity": 3}
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


@patch("app.handlers.budget.client")
def test_set_budget(mock_client):
    mock_client.table.return_value.upsert.return_value.execute.return_value = None
    from app.handlers.budget import set_budget
    result = set_budget(600000, FAKE_USER)
    assert "mensual" in result
    assert "600.000" in result
