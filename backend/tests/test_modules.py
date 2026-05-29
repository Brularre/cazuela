from unittest.mock import MagicMock, patch

from tests.conftest import FAKE_USER


def _make_modules_db(enabled: bool | None):
    db = MagicMock()
    if enabled is None:
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    else:
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"enabled": enabled}
        ]
    return db


def test_is_enabled_no_row_defaults_true():
    db = _make_modules_db(None)
    with patch("app.handlers.modules.client", db):
        from app.handlers.modules import is_enabled
        assert is_enabled(FAKE_USER, "dinero") is True


def test_is_enabled_true_row():
    db = _make_modules_db(True)
    with patch("app.handlers.modules.client", db):
        from app.handlers.modules import is_enabled
        assert is_enabled(FAKE_USER, "dinero") is True


def test_is_enabled_false_row():
    db = _make_modules_db(False)
    with patch("app.handlers.modules.client", db):
        from app.handlers.modules import is_enabled
        assert is_enabled(FAKE_USER, "dinero") is False


def test_module_for_intent_known():
    from app.handlers.modules import module_for_intent
    assert module_for_intent("add_expense") == "dinero"
    assert module_for_intent("add_todo") == "tiempo"
    assert module_for_intent("add_to_shopping") == "despensa"
    assert module_for_intent("add_event") == "calendario"


def test_module_for_intent_unknown_returns_none():
    from app.handlers.modules import module_for_intent
    assert module_for_intent("help") is None
    assert module_for_intent("confirm") is None
    assert module_for_intent("nonexistent") is None


def _route(message, modules_enabled: dict | None = None):
    db = MagicMock()

    def module_side_effect(user_id, module):
        if modules_enabled and module in modules_enabled:
            return [{"enabled": modules_enabled[module]}]
        return []

    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    db.table.return_value.insert.return_value.execute.return_value.data = [{}]
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    def patched_is_enabled(user, module):
        if modules_enabled and module in modules_enabled:
            return modules_enabled[module]
        return True

    with patch("app.router.is_enabled", patched_is_enabled), \
         patch("app.dispatch.is_enabled", patched_is_enabled), \
         patch("app.handlers.todos.client", db), \
         patch("app.handlers.expenses.client", db), \
         patch("app.handlers.waiting_on.client", db):
        from app.router import route
        return route(message, FAKE_USER)


def test_disabled_dinero_blocks_expense():
    result = _route("gasté 5000 en almuerzo", modules_enabled={"dinero": False})
    assert "desactivado" in result


def test_enabled_dinero_allows_expense():
    with patch("app.handlers.expenses.client") as db:
        db.table.return_value.insert.return_value.execute.return_value.data = [{}]
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        result = _route("gasté 5000 en almuerzo", modules_enabled={"dinero": True})
    assert "desactivado" not in result


def test_disabled_tiempo_blocks_todo():
    result = _route("pendiente llamar al banco", modules_enabled={"tiempo": False})
    assert "desactivado" in result


def test_disabled_despensa_blocks_shopping():
    result = _route("comprar leche", modules_enabled={"despensa": False})
    assert "desactivado" in result


def test_help_never_gated():
    result = _route("ayuda", modules_enabled={"dinero": False, "tiempo": False})
    assert "desactivado" not in result


def test_no_row_allows_all():
    with patch("app.handlers.expenses.client") as db:
        db.table.return_value.insert.return_value.execute.return_value.data = [{}]
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        result = _route("gasté 5000 en almuerzo", modules_enabled=None)
    assert "desactivado" not in result
