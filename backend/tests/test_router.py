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


@pytest.mark.parametrize("message,expected_item", [
    ("comprar: leche", "leche"),
    ("necesito pan", "pan"),
])
def test_shopping_add_routes_to_add_to_shopping(message, expected_item):
    with patch("app.router.add_to_shopping", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item


@pytest.mark.parametrize("message,expected_item", [
    ("compré leche", "leche"),
    ("compre el pan", "el pan"),
])
def test_compre_routes_to_handle_bought(message, expected_item):
    with patch("app.router._handle_bought", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item
        assert mock.call_args[0][2] is None


@pytest.mark.parametrize("message,expected_item,expected_qty", [
    ("compré leche 3", "leche", 3),
    ("compré botellas agua 1.6 12", "botellas agua 1.6", 12),
])
def test_compre_with_qty_routes_to_handle_bought(message, expected_item, expected_qty):
    with patch("app.router._handle_bought", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item
        assert mock.call_args[0][2] == expected_qty


def test_handle_bought_both_match():
    with patch("app.dispatch.check_item", return_value="✓ Marcado: leche"), \
         patch("app.dispatch.restock_pantry_item", return_value="✓ Repuesto: leche"):
        from app.router import _handle_bought
        result = _handle_bought("leche", FAKE_USER)
        assert "✓ Marcado: leche" in result
        assert "✓ Repuesto: leche" in result


def test_handle_bought_only_shopping():
    with patch("app.dispatch.check_item", return_value="✓ Marcado: leche"), \
         patch("app.dispatch.restock_pantry_item", return_value="No encontré 'leche' en tu despensa."):
        from app.router import _handle_bought
        result = _handle_bought("leche", FAKE_USER)
        assert "✓ Marcado: leche" in result
        assert "No encontré" not in result


def test_handle_bought_only_pantry():
    with patch("app.dispatch.check_item", return_value="No encontré 'leche' en la lista."), \
         patch("app.dispatch.restock_pantry_item", return_value="✓ Repuesto: leche"):
        from app.router import _handle_bought
        result = _handle_bought("leche", FAKE_USER)
        assert "✓ Repuesto: leche" in result
        assert "No encontré" not in result


def test_handle_bought_neither_match():
    with patch("app.dispatch.check_item", return_value="No encontré 'leche' en la lista."), \
         patch("app.dispatch.restock_pantry_item", return_value="No encontré 'leche' en tu despensa."):
        from app.router import _handle_bought
        result = _handle_bought("leche", FAKE_USER)
        assert "en tu lista ni en tu despensa" in result


def test_handle_bought_pantry_suggestion_passes_through():
    suggestion = "No encontré 'leches' en tu despensa. ¿Quisiste decir _leche_?"
    with patch("app.dispatch.check_item", return_value="No encontré 'leches' en la lista."), \
         patch("app.dispatch.restock_pantry_item", return_value=suggestion):
        from app.router import _handle_bought
        result = _handle_bought("leches", FAKE_USER)
        assert "Quisiste decir" in result
        assert "leche" in result


@pytest.mark.parametrize("message,expected_item,expected_qty", [
    ("stock 3 jabón", "jabón", 3),
    ("stock 12 botella agua 1.6", "botella agua 1.6", 12),
    ("stock jabón 3", "jabón", 3),
    ("stock botella agua 1.6 3", "botella agua 1.6", 3),
])
def test_stock_routes_to_set_pantry_stock(message, expected_item, expected_qty):
    with patch("app.router.set_pantry_stock", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item
        assert mock.call_args[0][1] == expected_qty


def test_ambiguous_expense_routes_to_handle_ambiguous():
    with patch("app.router._handle_ambiguous_expense", return_value="ok") as mock:
        route("pagué 5000", FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == 5000.0
        assert mock.call_args[0][1] == "pagué 5000"
        assert mock.call_args[0][2] == FAKE_USER


def test_pague_with_description_routes_to_save_expense():
    with patch("app.router.save_expense", return_value="ok") as mock:
        route("pagué 5000 en almuerzo", FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == 5000.0
        assert "almuerzo" in mock.call_args[0][1]


def test_confirm_with_no_pending_returns_message():
    with patch("app.router.mcp.find_pending_for_user", return_value=None):
        result = route("confirmar", FAKE_USER)
    assert "pendiente" in result


def test_cancel_with_no_pending_returns_message():
    with patch("app.router.mcp.find_pending_for_user", return_value=None):
        result = route("cancelar", FAKE_USER)
    assert "pendiente" in result


@pytest.mark.parametrize("message", ["ayuda"])
def test_help_returns_command_reference(message):
    result = route(message, FAKE_USER)
    assert "Comandos disponibles" in result
    assert "gasté" in result
    assert "pendiente" in result
    assert "comprar" in result
    assert "confirmar" in result


@pytest.mark.parametrize("message,expected_item,expected_qty,expected_category", [
    ("despensa cocina: arroz 3", "arroz", 3, "cocina"),
    ("despensa baño jabón de manos 1", "jabón de manos", 1, "baño"),
])
def test_pantry_add_with_category_routes_to_add_pantry_item(message, expected_item, expected_qty, expected_category):
    with patch("app.router.add_pantry_item", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_item
        assert mock.call_args[0][1] == expected_qty
        assert mock.call_args[0][3] == expected_category


def test_pantry_add_without_category_prompts_for_category():
    with patch("app.router.mcp") as mock_mcp:
        mock_mcp.send_context.return_value = "ctx-1"
        mock_mcp.find_pending_for_user.return_value = None
        result = route("despensa: jabón 2", FAKE_USER)
        mock_mcp.send_context.assert_called_once_with(
            "pantry_add_category", FAKE_USER["id"], {"item": "jabón", "qty": 2}
        )
        assert "elegir 1" in result
        assert "elegir 2" in result
        assert "elegir 3" in result


def test_elegir_pantry_category_adds_item():
    ctx_data = {
        "domain": "pantry_add_category",
        "payload": {"item": "jabón", "qty": 2},
    }
    with patch("app.router.mcp") as mock_mcp, \
         patch("app.dispatch.mcp"), \
         patch("app.dispatch.add_pantry_item", return_value="✓ Agregado") as mock_add:
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = ctx_data
        result = route("elegir 1", FAKE_USER)
        mock_add.assert_called_once_with("jabón", 2, FAKE_USER, "cocina")
        assert "Agregado" in result


def test_elegir_out_of_range_pantry_category_returns_hint():
    ctx_data = {
        "domain": "pantry_add_category",
        "payload": {"item": "jabón", "qty": 2},
    }
    with patch("app.router.mcp") as mock_mcp:
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = ctx_data
        result = route("elegir 5", FAKE_USER)
        assert "elegir 1" in result


@pytest.mark.parametrize("message,expected_amount", [
    ("presupuesto 600.000", 600000.0),
    ("presupuesto 80000", 80000.0),
])
def test_budget_set_routes_to_set_budget(message, expected_amount):
    with patch("app.router.set_budget", return_value="ok") as mock:
        route(message, FAKE_USER)
        mock.assert_called_once()
        assert mock.call_args[0][0] == expected_amount


# ---------------------------------------------------------------------------
# _parse_clp_amount
# ---------------------------------------------------------------------------

def test_parse_clp_amount_integer_with_dot_separator():
    from app.router import _parse_clp_amount
    assert _parse_clp_amount("1.500") == 1500.0
    assert _parse_clp_amount("12.990") == 12990.0

def test_parse_clp_amount_plain_integer():
    from app.router import _parse_clp_amount
    assert _parse_clp_amount("5000") == 5000.0

def test_parse_clp_amount_decimal_returns_none():
    from app.router import _parse_clp_amount
    assert _parse_clp_amount("1500.50") is None
    assert _parse_clp_amount("1.500,50") is None


# ---------------------------------------------------------------------------
# _hint_for_message
# ---------------------------------------------------------------------------

def test_hint_digit_first_suggests_gaste():
    from app.dispatch import _hint_for_message
    result = _hint_for_message("5000 no sé")
    assert "gasté" in result


# ---------------------------------------------------------------------------
# _dashboard_reply
# ---------------------------------------------------------------------------

def test_dashboard_reply_with_url():
    from app.dispatch import _dashboard_reply
    with patch("app.dispatch.settings") as mock_settings:
        mock_settings.dashboard_url = "https://cazuela.example.com"
        result = _dashboard_reply()
    assert "cazuela.example.com" in result

def test_dashboard_reply_without_url():
    from app.dispatch import _dashboard_reply
    with patch("app.dispatch.settings") as mock_settings:
        mock_settings.dashboard_url = None
        result = _dashboard_reply()
    assert "URL" in result


# ---------------------------------------------------------------------------
# _handle_confirm — domain branches
# ---------------------------------------------------------------------------

def test_handle_confirm_expired_context():
    from app.dispatch import _handle_confirm
    with patch("app.dispatch.mcp.find_pending_for_user", return_value="ctx-1"), \
         patch("app.dispatch.mcp.receive_result", side_effect=ValueError("expired")):
        result = _handle_confirm(FAKE_USER)
    assert "expiró" in result

def test_handle_confirm_default_expense_inserts_and_confirms():
    from app.dispatch import _handle_confirm
    ctx = {
        "domain": "expense",
        "payload": {"amount": 5000, "raw_message": "pagué 5000"},
        "proposed": {"category": "comida"},
    }
    with patch("app.dispatch.mcp.find_pending_for_user", return_value="ctx-1"), \
         patch("app.dispatch.mcp.receive_result", return_value=ctx), \
         patch("app.dispatch.db") as mock_db, \
         patch("app.dispatch.mcp.confirm"):
        mock_db.table.return_value.insert.return_value.execute.return_value = None
        result = _handle_confirm(FAKE_USER)
    assert "comida" in result
    assert "5.000" in result


# ---------------------------------------------------------------------------
# _handle_cancel — domain branches
# ---------------------------------------------------------------------------

def test_handle_cancel_expired_context():
    from app.dispatch import _handle_cancel
    with patch("app.dispatch.mcp.find_pending_for_user", return_value="ctx-1"), \
         patch("app.dispatch.mcp.receive_result", side_effect=ValueError("expired")):
        result = _handle_cancel(FAKE_USER)
    assert "expiró" in result

