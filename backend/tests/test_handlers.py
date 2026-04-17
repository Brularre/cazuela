from unittest.mock import MagicMock, patch

FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


def make_todo_rows(*tasks):
    return [{"id": str(i), "task": t} for i, t in enumerate(tasks)]


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


def make_notes_rows(*contents):
    return [{"id": str(i), "content": c} for i, c in enumerate(contents)]


@patch("app.handlers.notes.client")
def test_add_note(mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = None
    from app.handlers.notes import add_note
    result = add_note("compré flores hoy", FAKE_USER)
    assert "guardada" in result
    assert "compré flores hoy" in result


@patch("app.handlers.notes.client")
def test_list_notes_empty(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    from app.handlers.notes import list_notes
    result = list_notes(FAKE_USER)
    assert "No tienes notas" in result


@patch("app.handlers.notes.client")
def test_list_notes_with_items(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = make_notes_rows("compré flores", "llamé al médico")
    from app.handlers.notes import list_notes
    result = list_notes(FAKE_USER)
    assert "compré flores" in result


@patch("app.handlers.notes.client")
def test_search_notes_found(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = make_notes_rows("compré flores hoy", "llamé al médico")
    from app.handlers.notes import search_notes
    result = search_notes("flores", FAKE_USER)
    assert "compré flores" in result


@patch("app.handlers.notes.client")
def test_search_notes_not_found(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = []
    from app.handlers.notes import search_notes
    result = search_notes("dentista", FAKE_USER)
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
