from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


def make_mock_client(rows=None):
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = rows or []
    mock.table.return_value.insert.return_value.execute.return_value = None
    mock.table.return_value.select.return_value.eq.return_value.maybeSingle.return_value.execute.return_value.data = FAKE_USER
    return mock


@patch("app.db.users.client")
@patch("app.handlers.expenses.client")
def test_expense_saved_and_confirmed(mock_expense_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_expense_client.table.return_value.insert.return_value.execute.return_value = None

    response = client.post(
        "/webhook",
        data={"Body": "gasté 5000 en almuerzo", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "5.000" in response.text
    assert "comida" in response.text


@patch("app.db.users.client")
@patch("app.handlers.summary.client")
def test_summary_returns_weekly_totals(mock_summary_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_summary_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"amount": "5000", "category": "comida"},
        {"amount": "3000", "category": "transporte"},
        {"amount": "2000", "category": "comida"},
    ]

    response = client.post(
        "/webhook",
        data={"Body": "resumen", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "comida" in response.text
    assert "7.000" in response.text
    assert "transporte" in response.text


@patch("app.db.users.client")
def test_unrecognized_message_returns_help(mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]

    response = client.post(
        "/webhook",
        data={"Body": "hola qué tal", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "No entendí" in response.text


@patch("app.db.users.client")
@patch("app.handlers.todos.client")
def test_todos_add(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.insert.return_value.execute.return_value = None

    response = client.post(
        "/webhook",
        data={"Body": "pendiente: llamar al banco", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "llamar al banco" in response.text
    assert "✓" in response.text


@patch("app.db.users.client")
@patch("app.handlers.todos.client")
def test_todos_list_empty(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    response = client.post(
        "/webhook",
        data={"Body": "mis pendientes", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "No tienes pendientes." in response.text


@patch("app.db.users.client")
@patch("app.handlers.todos.client")
def test_todos_list_with_items(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"task": "llamar al banco"},
        {"task": "pagar arriendo"},
    ]

    response = client.post(
        "/webhook",
        data={"Body": "mis pendientes", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "Tus pendientes:" in response.text
    assert "llamar al banco" in response.text
    assert "pagar arriendo" in response.text


@patch("app.db.users.client")
@patch("app.handlers.todos.client")
def test_todos_complete(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": "t-1", "task": "llamar al banco"},
    ]
    mock_handler_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    response = client.post(
        "/webhook",
        data={"Body": "listo: llamar al banco", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "✓ Listo: llamar al banco" in response.text


@patch("app.db.users.client")
@patch("app.handlers.notes.client")
def test_notes_add(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.insert.return_value.execute.return_value = None

    response = client.post(
        "/webhook",
        data={"Body": "nota: flores en el jardín", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "✓ Nota guardada: flores en el jardín" in response.text


@patch("app.db.users.client")
@patch("app.handlers.notes.client")
def test_notes_list_empty(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

    response = client.post(
        "/webhook",
        data={"Body": "mis notas", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "No tienes notas." in response.text


@patch("app.db.users.client")
@patch("app.handlers.notes.client")
def test_notes_list_with_items(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"content": "flores en el jardín"},
        {"content": "comprar pan mañana"},
    ]

    response = client.post(
        "/webhook",
        data={"Body": "mis notas", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "Tus notas:" in response.text
    assert "flores en el jardín" in response.text
    assert "comprar pan mañana" in response.text


@patch("app.db.users.client")
@patch("app.handlers.notes.client")
def test_notes_search_found(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = [
        {"content": "flores en el jardín"},
    ]

    response = client.post(
        "/webhook",
        data={"Body": "buscar nota: flores", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "flores" in response.text
    assert "flores en el jardín" in response.text


@patch("app.db.users.client")
@patch("app.handlers.notes.client")
def test_notes_search_not_found(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = []

    response = client.post(
        "/webhook",
        data={"Body": "buscar nota: unicornio", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "No encontré notas con 'unicornio'." in response.text


@patch("app.db.users.client")
@patch("app.handlers.shopping.client")
def test_shopping_add(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.insert.return_value.execute.return_value = None

    response = client.post(
        "/webhook",
        data={"Body": "comprar: leche", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "✓ Agregado a la lista: leche" in response.text


@patch("app.db.users.client")
@patch("app.handlers.shopping.client")
def test_shopping_list_empty(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    response = client.post(
        "/webhook",
        data={"Body": "compras", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "La lista de compras está vacía." in response.text


@patch("app.db.users.client")
@patch("app.handlers.shopping.client")
def test_shopping_list_with_items(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"item": "leche", "quantity": None, "unit": None, "checked": False},
        {"item": "pan", "quantity": 2, "unit": "unidades", "checked": False},
    ]

    response = client.post(
        "/webhook",
        data={"Body": "compras", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "Lista de compras:" in response.text
    assert "leche" in response.text
    assert "pan" in response.text


@patch("app.db.users.client")
@patch("app.handlers.shopping.client")
def test_shopping_check_item(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": "s-1", "item": "leche"},
    ]
    mock_handler_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    response = client.post(
        "/webhook",
        data={"Body": "compré leche", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "✓ Marcado: leche" in response.text


@patch("app.db.users.client")
@patch("app.handlers.wishlist.client")
def test_wishlist_add(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.insert.return_value.execute.return_value = None

    response = client.post(
        "/webhook",
        data={"Body": "quiero: zapatillas", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "✓ Agregado a tu lista de deseos: zapatillas" in response.text


@patch("app.db.users.client")
@patch("app.handlers.wishlist.client")
def test_wishlist_list_empty(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

    response = client.post(
        "/webhook",
        data={"Body": "mis deseos", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "Tu lista de deseos está vacía." in response.text


@patch("app.db.users.client")
@patch("app.handlers.wishlist.client")
def test_wishlist_list_with_items(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"item": "zapatillas", "price_estimate": None},
        {"item": "auriculares", "price_estimate": 50000},
    ]

    response = client.post(
        "/webhook",
        data={"Body": "mis deseos", "From": "whatsapp:+56912345678"},
    )

    assert response.status_code == 200
    assert "Lista de deseos:" in response.text
    assert "zapatillas" in response.text
    assert "auriculares" in response.text
