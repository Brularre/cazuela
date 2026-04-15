from unittest.mock import MagicMock, patch

FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


def make_todo_rows(*tasks):
    return [{"id": str(i), "task": t} for i, t in enumerate(tasks)]


def make_shopping_rows(*items):
    return [{"id": str(i), "item": it} for i, it in enumerate(items)]


@patch("app.handlers.todos.client")
@patch("app.handlers.todos.mcp")
def test_complete_todo_exact_match(mock_mcp, mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_todo_rows("llamar al banco")
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.todos import complete_todo
    result = complete_todo("llamar al banco", FAKE_USER)
    assert "Listo" in result
    assert "llamar al banco" in result


@patch("app.handlers.todos.client")
@patch("app.handlers.todos.mcp")
def test_complete_todo_partial_match(mock_mcp, mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_todo_rows("llamar al banco", "pagar el gas")
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.todos import complete_todo
    result = complete_todo("banco", FAKE_USER)
    assert "llamar al banco" in result


@patch("app.handlers.todos.client")
@patch("app.handlers.todos.mcp")
def test_complete_todo_no_match(mock_mcp, mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_todo_rows("llamar al banco")
    from app.handlers.todos import complete_todo
    result = complete_todo("dentista", FAKE_USER)
    assert "No encontré" in result


@patch("app.handlers.shopping.client")
@patch("app.handlers.shopping.mcp")
def test_check_item_partial_match(mock_mcp, mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_shopping_rows("leche entera", "pan integral")
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    from app.handlers.shopping import check_item
    result = check_item("leche", FAKE_USER)
    assert "leche entera" in result


@patch("app.handlers.shopping.client")
@patch("app.handlers.shopping.mcp")
def test_check_item_no_match(mock_mcp, mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = make_shopping_rows("leche")
    from app.handlers.shopping import check_item
    result = check_item("mantequilla", FAKE_USER)
    assert "No encontré" in result
