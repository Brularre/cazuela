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


@pytest.mark.parametrize("message,expected_task", [
    ("pendiente: llamar al banco", "llamar al banco"),
    ("tarea: pagar el gas", "pagar el gas"),
    ("pendiente comprar leche", "comprar leche"),
])
def test_todo_add_routes_to_add_todo(message, expected_task):
    with patch("app.router.add_todo", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_task


@pytest.mark.parametrize("message,expected_task,expected_priority", [
    ("pendiente: hoy: llamar al banco", "llamar al banco", "hoy"),
    ("pendiente: hoy llamar al banco", "llamar al banco", "hoy"),
    ("pendiente: mes: pagar impuesto", "pagar impuesto", "mes"),
    ("pendiente: renovar seguro", "renovar seguro", "semana"),
])
def test_todo_add_extracts_priority(message, expected_task, expected_priority):
    with patch("app.router.add_todo", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_task
        assert mock.call_args[0][2] == expected_priority


@pytest.mark.parametrize("message", ["mis pendientes", "mi pendiente", "Mis Pendientes"])
def test_todo_list_routes_to_list_todos(message):
    with patch("app.router.list_todos", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


@pytest.mark.parametrize("message,expected_fragment", [
    ("listo: llamar al banco", "llamar al banco"),
    ("hice el informe", "el informe"),
    ("completé el pago", "el pago"),
])
def test_todo_done_routes_to_complete_todo(message, expected_fragment):
    with patch("app.router.complete_todo", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_fragment


@pytest.mark.parametrize("message,expected_item", [
    ("quiero: zapatillas", "zapatillas"),
    ("deseo un libro", "un libro"),
])
def test_wishlist_add_routes_to_add_to_wishlist(message, expected_item):
    with patch("app.router.add_to_wishlist", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item


@pytest.mark.parametrize("message", ["mis deseos", "mi deseo"])
def test_wishlist_list_routes_to_list_wishlist(message):
    with patch("app.router.list_wishlist", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


@pytest.mark.parametrize("message,expected_item", [
    ("comprar: leche", "leche"),
    ("necesito pan", "pan"),
])
def test_shopping_add_routes_to_add_to_shopping(message, expected_item):
    with patch("app.router.add_to_shopping", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item


@pytest.mark.parametrize("message", ["compras", "lista de compras", "Compras"])
def test_shopping_list_routes_to_list_shopping(message):
    with patch("app.router.list_shopping", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


@pytest.mark.parametrize("message,expected_item", [
    ("compré leche", "leche"),
    ("compre el pan", "el pan"),
])
def test_shopping_check_routes_to_restock_pantry_item(message, expected_item):
    with patch("app.router.restock_pantry_item", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item


def test_ambiguous_expense_routes_to_handle_ambiguous():
    with patch("app.router._handle_ambiguous_expense", return_value="ok") as mock:
        route("pagué 5000", FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == 5000.0


def test_confirm_pattern_routes_to_handle_confirm():
    with patch("app.router._handle_confirm", return_value="ok") as mock:
        route("confirmar", FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


def test_cancel_pattern_routes_to_handle_cancel():
    with patch("app.router._handle_cancel", return_value="ok") as mock:
        route("cancelar", FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


def test_confirm_with_no_pending_returns_message():
    with patch("app.router.mcp.find_pending_for_user", return_value=None):
        result = route("confirmar", FAKE_USER)
    assert "pendiente" in result


def test_cancel_with_no_pending_returns_message():
    with patch("app.router.mcp.find_pending_for_user", return_value=None):
        result = route("cancelar", FAKE_USER)
    assert "pendiente" in result


@pytest.mark.parametrize("message,expected_content", [
    ("nota: compré flores hoy", "compré flores hoy"),
    ("nota llamar al médico mañana", "llamar al médico mañana"),
])
def test_notes_add_routes_to_add_note(message, expected_content):
    with patch("app.router.add_note", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_content


@pytest.mark.parametrize("message", ["mis notas", "mi nota", "Mis Notas"])
def test_notes_list_routes_to_list_notes(message):
    with patch("app.router.list_notes", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


@pytest.mark.parametrize("message,expected_keyword", [
    ("buscar nota: flores", "flores"),
    ("buscar notas reunión", "reunión"),
    ("buscar nota médico", "médico"),
])
def test_notes_search_routes_to_search_notes(message, expected_keyword):
    with patch("app.router.search_notes", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_keyword


@pytest.mark.parametrize("message", ["ayuda", "Ayuda", "AYUDA"])
def test_help_returns_command_reference(message):
    result = route(message, FAKE_USER)
    assert "Comandos disponibles" in result
    assert "gasté" in result
    assert "pendiente" in result
    assert "comprar" in result
    assert "confirmar" in result


@pytest.mark.parametrize("message,expected_desc", [
    ("esperando: respuesta del seguro", "respuesta del seguro"),
    ("esperando respuesta del banco", "respuesta del banco"),
    ("esperando: la llamada del médico", "la llamada del médico"),
])
def test_waiting_add_routes_to_add_waiting(message, expected_desc):
    with patch("app.router.add_waiting", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_desc


@pytest.mark.parametrize("message", ["mis esperas", "mi espera", "Mis Esperas"])
def test_waiting_list_routes_to_list_waiting(message):
    with patch("app.router.list_waiting", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


@pytest.mark.parametrize("message,expected_fragment", [
    ("llegó: seguro", "seguro"),
    ("llego el banco", "el banco"),
    ("llegó la respuesta", "la respuesta"),
])
def test_waiting_resolve_routes_to_resolve_waiting(message, expected_fragment):
    with patch("app.router.resolve_waiting", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_fragment


@pytest.mark.parametrize("message,expected_item,expected_qty,expected_category", [
    ("despensa: jabón 2", "jabón", 2, "otros"),
    ("despensa cocina: arroz 3", "arroz", 3, "cocina"),
    ("despensa baño jabón de manos 1", "jabón de manos", 1, "baño"),
])
def test_pantry_add_routes_to_add_pantry_item(message, expected_item, expected_qty, expected_category):
    with patch("app.router.add_pantry_item", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item
        assert mock.call_args[0][1] == expected_qty
        assert mock.call_args[0][3] == expected_category


@pytest.mark.parametrize("message", ["mi despensa", "Mi Despensa"])
def test_pantry_list_routes_to_list_pantry(message):
    with patch("app.router.list_pantry", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


@pytest.mark.parametrize("message,expected_fragment", [
    ("usé: jabón", "jabón"),
    ("use el detergente", "el detergente"),
    ("usé shampoo", "shampoo"),
])
def test_pantry_consume_routes_to_consume_pantry_item(message, expected_fragment):
    with patch("app.router.consume_pantry_item", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_fragment


@pytest.mark.parametrize("message", ["compré todo", "compre todo", "Compré Todo"])
def test_pantry_restock_all_routes_to_restock_all_pantry(message):
    with patch("app.router.restock_all_pantry", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once_with(FAKE_USER)


@pytest.mark.parametrize("message,expected_fragment", [
    ("compré: jabón", "jabón"),
    ("compre el detergente", "el detergente"),
    ("compré shampoo", "shampoo"),
])
def test_pantry_restock_routes_to_restock_pantry_item(message, expected_fragment):
    with patch("app.router.restock_pantry_item", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_fragment
