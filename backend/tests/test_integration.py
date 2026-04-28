from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from main import app
from tests.conftest import meta_payload, FAKE_USER

client = TestClient(app)



@patch("app.db.users.client")
@patch("app.handlers.expenses.client")
def test_expense_saved_and_confirmed(mock_expense_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_expense_client.table.return_value.insert.return_value.execute.return_value = None

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("gasté 5000 en almuerzo"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "5.000" in text
    assert "comida" in text


@patch("app.db.users.client")
@patch("app.handlers.summary.client")
def test_summary_returns_weekly_totals(mock_summary_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    d = date.today().isoformat()
    mock_summary_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"amount": "5000", "category": "comida", "date": d},
        {"amount": "3000", "category": "transporte", "date": d},
        {"amount": "2000", "category": "comida", "date": d},
    ]

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("resumen"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "comida" in text
    assert "7.000" in text
    assert "transporte" in text


@patch("app.db.users.client")
def test_unrecognized_message_returns_help(mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("hola qué tal"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "No entendí" in text


@patch("main.get_or_create_user")
def test_new_user_receives_welcome(mock_get_user):
    mock_get_user.return_value = (FAKE_USER, True)

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("hola"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "Cazuela" in text
    assert "me llamo" in text


@patch("app.db.users.client")
def test_me_llamo_saves_name(mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_users_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("me llamo Bruno"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "Bruno" in text


@patch("app.db.users.client")
def test_me_llamo_empty_name_rejected(mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("me llamo   "))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "No entendí ese mensaje" in text


@patch("app.db.users.client")
@patch("app.handlers.todos.client")
def test_todos_add(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.insert.return_value.execute.return_value = None

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("pendiente: llamar al banco"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "llamar al banco" in text
    assert "✓" in text


@patch("app.db.users.client")
@patch("app.handlers.todos.client")
def test_todos_list_empty(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("mis pendientes"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "No tienes pendientes." in text


@patch("app.db.users.client")
@patch("app.handlers.todos.client")
def test_todos_list_with_items(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"task": "llamar al banco", "priority": "hoy"},
        {"task": "pagar arriendo", "priority": "semana"},
    ]

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("mis pendientes"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "llamar al banco" in text
    assert "pagar arriendo" in text


@patch("app.db.users.client")
@patch("app.handlers.todos.client")
def test_todos_complete(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": "t-1", "task": "llamar al banco"},
    ]
    mock_handler_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("listo: llamar al banco"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "✓ Listo: llamar al banco" in text


@patch("app.db.users.client")
@patch("app.handlers.shopping.client")
def test_shopping_add(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.insert.return_value.execute.return_value = None

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("comprar: leche"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "✓ Agregado a la lista: leche" in text


@patch("app.db.users.client")
@patch("app.handlers.shopping.client")
def test_shopping_list_empty(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("compras"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "La lista de compras está vacía." in text


@patch("app.db.users.client")
@patch("app.handlers.shopping.client")
def test_shopping_list_with_items(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"item": "leche", "quantity": None, "unit": None, "checked": False},
        {"item": "pan", "quantity": 2, "unit": "unidades", "checked": False},
    ]

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("compras"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "Lista de compras:" in text
    assert "leche" in text
    assert "pan" in text


@patch("app.db.users.client")
@patch("app.handlers.pantry.client")
def test_shopping_check_item(mock_handler_client, mock_users_client):
    mock_users_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_USER]
    mock_handler_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "p-1", "item": "leche", "desired_quantity": 2},
    ]
    mock_handler_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    with patch("main._send_whatsapp") as mock_send:
        response = client.post("/webhook", json=meta_payload("compré leche"))

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "Repuesto" in text
    assert "leche" in text


def _make_mcp_expense_fake_client(ctx_store, expense_rows):
    class FakeExecute:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, store_ref, table_name, expense_bucket):
            self._store = store_ref
            self._table = table_name
            self._expense_bucket = expense_bucket
            self._eq_filters = {}
            self._lt_filter = None
            self._pending_insert = None
            self._pending_update = None
            self._do_delete = False

        def select(self, *args):
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

        def eq(self, field, value):
            self._eq_filters[field] = value
            return self

        def lt(self, field, value):
            self._lt_filter = (field, value)
            return self

        def gte(self, field, value):
            return self

        def execute(self):
            if self._pending_insert is not None:
                if self._table == "expenses":
                    row = dict(self._pending_insert)
                    self._expense_bucket.append(row)
                    return FakeExecute([row])
                self._store[self._pending_insert["context_id"]] = dict(self._pending_insert)
                return FakeExecute([self._store[self._pending_insert["context_id"]]])

            if self._pending_update is not None:
                results = []
                for row in self._store.values():
                    if all(row.get(k) == v for k, v in self._eq_filters.items()):
                        row.update(self._pending_update)
                        results.append(dict(row))
                return FakeExecute(results)

            if self._do_delete:
                to_del = []
                for cid, row in self._store.items():
                    if self._lt_filter:
                        field, val = self._lt_filter
                        if row.get(field, "") < val:
                            to_del.append(cid)
                deleted = [self._store.pop(cid) for cid in to_del]
                return FakeExecute(deleted)

            if self._table == "expenses":
                return FakeExecute([])

            results = [
                dict(row)
                for row in self._store.values()
                if all(row.get(k) == v for k, v in self._eq_filters.items())
            ]
            return FakeExecute(results)

    class FakeClient:
        def __init__(self, store_ref, expense_bucket):
            self._store = store_ref
            self._expense_bucket = expense_bucket

        def table(self, name):
            return FakeQuery(self._store, name, self._expense_bucket)

    return FakeClient(ctx_store, expense_rows)


@patch("main.get_or_create_user")
def test_supermercado_batch_webhook_reply(mock_get_user, monkeypatch):
    mock_get_user.return_value = (FAKE_USER, False)
    fc = _make_mcp_expense_fake_client({}, [])
    monkeypatch.setattr("app.mcp.context.client", fc)
    monkeypatch.setattr("app.handlers.expense_batch.client", fc)

    with patch("main._send_whatsapp") as mock_send:
        response = client.post(
            "/webhook",
            json=meta_payload("gasté 18000 en supermercado: pan, leche, jabón"),
        )

    assert response.status_code == 200
    text = mock_send.call_args[0][1]
    assert "confirmar" in text.lower() or "Confirmar" in text
    assert "pan" in text
    assert "comida" in text
