import pytest
from unittest.mock import patch, MagicMock

FAKE_USER = {"id": "abc-123", "phone": "+56912345678", "ai_mode": False}
FAKE_USER_AI = {"id": "abc-123", "phone": "+56912345678", "ai_mode": True}

FAKE_INGREDIENTS = [
    {"item": "pollo", "quantity": 1, "unit": None},
    {"item": "arroz", "quantity": None, "unit": "taza"},
]


def _make_mcp(ingredients):
    m = MagicMock()
    m.send_context.return_value = "ctx-1"
    m.request_action.return_value = {"proposed": {"ingredients": ingredients}}
    return m


class TestNuevaReceta:
    def test_name_too_long_rejected(self):
        from app.handlers.recipes import nueva_receta
        result = nueva_receta("a" * 101, FAKE_USER)
        assert "demasiado largo" in result

    def test_no_ai_creates_bare_recipe_with_hint(self):
        mock_mcp = _make_mcp([])
        mock_create = MagicMock(return_value={"id": "r-1", "name": "cazuela"})
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.create_recipe", mock_create):
            from app.handlers.recipes import nueva_receta
            result = nueva_receta("cazuela", FAKE_USER)
        mock_create.assert_called_once_with("abc-123", "cazuela")
        mock_mcp.confirm.assert_called_once_with("ctx-1")
        assert "cazuela" in result
        assert "modo IA" in result

    def test_ai_mode_no_ingredients_dashboard_hint(self):
        mock_mcp = _make_mcp([])
        mock_create = MagicMock(return_value={"id": "r-1", "name": "cazuela"})
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.create_recipe", mock_create):
            from app.handlers.recipes import nueva_receta
            result = nueva_receta("cazuela", FAKE_USER_AI)
        assert "dashboard" in result

    def test_ai_returns_ingredients_shows_confirmation(self):
        mock_mcp = _make_mcp(FAKE_INGREDIENTS)
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import nueva_receta
            result = nueva_receta("cazuela", FAKE_USER_AI)
        assert "pollo" in result
        assert "confirmar" in result.lower()
        mock_mcp.confirm.assert_not_called()


class TestConfirmRecipeCreate:
    def _fake_ctx(self):
        return {
            "domain": "recipe_create",
            "payload": {"recipe_name": "cazuela"},
            "proposed": {"ingredients": FAKE_INGREDIENTS},
        }

    def test_happy_path_saves_recipe_and_ingredients(self):
        mock_mcp = MagicMock()
        mock_create = MagicMock(return_value={"id": "r-1"})
        mock_replace = MagicMock(return_value=[])
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.create_recipe", mock_create), \
             patch("app.handlers.recipes.replace_ingredients", mock_replace):
            from app.handlers.recipes import confirm_recipe_create
            result = confirm_recipe_create("ctx-1", FAKE_USER, self._fake_ctx())
        mock_create.assert_called_once_with("abc-123", "cazuela")
        mock_replace.assert_called_once()
        assert "cazuela" in result
        assert "2 ingredientes" in result

    def test_expired_context_returns_graceful_message(self):
        mock_mcp = MagicMock()
        mock_mcp.confirm.side_effect = ValueError("already confirmed")
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import confirm_recipe_create
            result = confirm_recipe_create("ctx-1", FAKE_USER, self._fake_ctx())
        assert "expiró" in result


class TestCancelRecipeCreate:
    def test_cancel_success(self):
        mock_mcp = MagicMock()
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import cancel_recipe_create
            result = cancel_recipe_create("ctx-1", FAKE_USER)
        mock_mcp.rollback.assert_called_once_with("ctx-1")
        assert "cancelada" in result

    def test_cancel_already_done(self):
        mock_mcp = MagicMock()
        mock_mcp.rollback.side_effect = ValueError()
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import cancel_recipe_create
            result = cancel_recipe_create("ctx-1", FAKE_USER)
        assert "expiró" in result


class TestListRecipes:
    def test_empty_returns_create_hint(self):
        with patch("app.handlers.recipes.get_recipes", return_value=[]):
            from app.handlers.recipes import list_recipes
            result = list_recipes(FAKE_USER)
        assert "nueva receta" in result

    def test_shows_recipe_names(self):
        recipes = [{"name": "cazuela", "servings": 4}]
        with patch("app.handlers.recipes.get_recipes", return_value=recipes):
            from app.handlers.recipes import list_recipes
            result = list_recipes(FAKE_USER)
        assert "cazuela" in result
        assert "4 personas" in result


class TestShowRecipe:
    def test_not_found(self):
        with patch("app.handlers.recipes.get_recipes", return_value=[]):
            from app.handlers.recipes import show_recipe
            result = show_recipe("cazuela", FAKE_USER)
        assert "No encontré" in result

    def test_found_with_ingredients(self):
        recipes = [{"id": "r-1", "name": "cazuela", "servings": 2}]
        ingredients = [{"item": "pollo", "quantity": 1, "unit": None}]
        with patch("app.handlers.recipes.get_recipes", return_value=recipes), \
             patch("app.handlers.recipes.get_ingredients", return_value=ingredients):
            from app.handlers.recipes import show_recipe
            result = show_recipe("cazuela", FAKE_USER)
        assert "cazuela" in result
        assert "pollo" in result

    def test_found_no_ingredients_shows_dashboard_hint(self):
        recipes = [{"id": "r-1", "name": "cazuela", "servings": 2}]
        with patch("app.handlers.recipes.get_recipes", return_value=recipes), \
             patch("app.handlers.recipes.get_ingredients", return_value=[]):
            from app.handlers.recipes import show_recipe
            result = show_recipe("cazuela", FAKE_USER)
        assert "dashboard" in result


class TestCoerceQuantity:
    def test_none_returns_none(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity(None) is None

    def test_empty_string_returns_none(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity("") is None

    def test_al_gusto_returns_none(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity("al gusto") is None

    def test_un_poco_returns_none(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity("un poco") is None

    def test_range_string_returns_none(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity("2-3") is None

    def test_integer_returns_float(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity(2) == 2.0

    def test_float_returns_float(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity(2.5) == 2.5

    def test_numeric_string_returns_float(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity("2") == 2.0

    def test_decimal_string_returns_float(self):
        from app.handlers.recipes import _coerce_quantity
        assert _coerce_quantity("0.5") == 0.5


class TestAddManyToShopping:
    def test_empty_list_returns_zero(self):
        mock_client = MagicMock()
        with patch("app.handlers.shopping.client", mock_client):
            from app.handlers.shopping import add_many_to_shopping
            result = add_many_to_shopping([], FAKE_USER)
        assert result == 0
        mock_client.table.assert_not_called()

    def test_batch_inserts_with_source(self):
        mock_client = MagicMock()
        with patch("app.handlers.shopping.client", mock_client):
            from app.handlers.shopping import add_many_to_shopping
            result = add_many_to_shopping(["pollo", "romero"], FAKE_USER, "recipe")
        assert result == 2
        call_args = mock_client.table.return_value.insert.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["item"] == "pollo"
        assert call_args[0]["source"] == "recipe"
        assert call_args[1]["item"] == "romero"

    def test_default_source_is_manual(self):
        mock_client = MagicMock()
        with patch("app.handlers.shopping.client", mock_client):
            from app.handlers.shopping import add_many_to_shopping
            add_many_to_shopping(["leche"], FAKE_USER)
        call_args = mock_client.table.return_value.insert.call_args[0][0]
        assert call_args[0]["source"] == "manual"


class TestQuePuedoHacer:
    def _fake_mcp_match(self, suggestions):
        m = MagicMock()
        m.send_context.return_value = "ctx-match"
        m.request_action.return_value = {"proposed": {"suggestions": suggestions}}
        m.find_pending_for_user.return_value = "ctx-match"
        return m

    def test_no_recipes_returns_hint(self):
        with patch("app.handlers.recipes.get_recipes", return_value=[]):
            from app.handlers.recipes import que_puedo_hacer
            result = que_puedo_hacer(FAKE_USER)
        assert "nueva receta" in result

    def test_empty_pantry_shows_all_missing(self):
        mock_mcp = self._fake_mcp_match([
            {"recipe_id": "r-1", "name": "cazuela", "have": 0, "total": 3,
             "missing": ["pollo", "arroz", "zapallo"], "score": 0.0},
        ])
        recipes = [{"id": "r-1", "name": "cazuela", "servings": 2}]
        ingredients = [
            {"item": "pollo"}, {"item": "arroz"}, {"item": "zapallo"}
        ]
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        with patch("app.handlers.recipes.get_recipes", return_value=recipes), \
             patch("app.handlers.recipes.get_ingredients", return_value=ingredients), \
             patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.db", mock_db):
            from app.handlers.recipes import que_puedo_hacer
            result = que_puedo_hacer(FAKE_USER)
        assert "cazuela" in result
        assert "0/3" in result
        assert "elegir" in result

    def test_full_overlap_shows_no_missing(self):
        mock_mcp = self._fake_mcp_match([
            {"recipe_id": "r-1", "name": "tortilla", "have": 3, "total": 3,
             "missing": [], "score": 1.0},
        ])
        recipes = [{"id": "r-1", "name": "tortilla", "servings": 2}]
        ingredients = [{"item": "huevo"}, {"item": "cebolla"}, {"item": "aceite"}]
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"item": "huevo", "current_quantity": 6},
            {"item": "cebolla", "current_quantity": 2},
            {"item": "aceite", "current_quantity": 1},
        ]
        with patch("app.handlers.recipes.get_recipes", return_value=recipes), \
             patch("app.handlers.recipes.get_ingredients", return_value=ingredients), \
             patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.db", mock_db):
            from app.handlers.recipes import que_puedo_hacer
            result = que_puedo_hacer(FAKE_USER)
        assert "tortilla" in result
        assert "3/3" in result
        assert "falta" not in result

    def test_partial_overlap_shows_missing(self):
        mock_mcp = self._fake_mcp_match([
            {"recipe_id": "r-1", "name": "cazuela", "have": 2, "total": 4,
             "missing": ["pollo", "zapallo"], "score": 0.5},
        ])
        recipes = [{"id": "r-1", "name": "cazuela", "servings": 2}]
        with patch("app.handlers.recipes.get_recipes", return_value=recipes), \
             patch("app.handlers.recipes.get_ingredients", return_value=[]), \
             patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.db", MagicMock()):
            from app.handlers.recipes import que_puedo_hacer
            result = que_puedo_hacer(FAKE_USER)
        assert "pollo" in result
        assert "zapallo" in result


class TestSugerirRecetas:
    def _fake_mcp_suggest(self, suggestions):
        m = MagicMock()
        m.send_context.return_value = "ctx-suggest"
        m.request_action.return_value = {"proposed": {"suggestions": suggestions}}
        return m

    def test_ai_mode_off_returns_hint(self):
        from app.handlers.recipes import sugerir_recetas
        result = sugerir_recetas(FAKE_USER)
        assert "modo IA" in result

    def test_empty_pantry_returns_hint(self):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        with patch("app.handlers.recipes.db", mock_db):
            from app.handlers.recipes import sugerir_recetas
            result = sugerir_recetas(FAKE_USER_AI)
        assert "despensa" in result.lower()

    def test_shows_suggestions_list(self):
        suggestions = [
            {"name": "arroz con pollo", "ingredients": [], "uses_pantry": ["arroz", "cebolla"], "missing": ["pollo"]},
            {"name": "tortilla", "ingredients": [], "uses_pantry": ["huevo", "aceite"], "missing": []},
        ]
        mock_mcp = self._fake_mcp_suggest(suggestions)
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"item": "arroz", "current_quantity": 2, "desired_quantity": 2},
        ]
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.db", mock_db), \
             patch("app.handlers.recipes.get_recipes", return_value=[]):
            from app.handlers.recipes import sugerir_recetas
            result = sugerir_recetas(FAKE_USER_AI)
        assert "arroz con pollo" in result
        assert "tortilla" in result
        assert "elegir" in result

    def test_empty_suggestions_returns_error_message(self):
        mock_mcp = self._fake_mcp_suggest([])
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"item": "arroz", "current_quantity": 2, "desired_quantity": 2},
        ]
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.db", mock_db), \
             patch("app.handlers.recipes.get_recipes", return_value=[]):
            from app.handlers.recipes import sugerir_recetas
            result = sugerir_recetas(FAKE_USER_AI)
        assert "No pude" in result


class TestElegirRecetaFlavorA:
    def _staged_ctx(self, suggestions, domain="recipe_match"):
        return {
            "domain": domain,
            "payload": {"recipes": [], "pantry_in_stock": []},
            "proposed": {"suggestions": suggestions},
        }

    def test_no_staged_context_returns_hint(self):
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = None
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(1, FAKE_USER)
        assert "sugerencia" in result.lower()

    def test_expired_context_returns_message(self):
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.side_effect = ValueError("expired")
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(1, FAKE_USER)
        assert "expiraron" in result

    def test_wrong_domain_returns_hint(self):
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = {"domain": "expense", "proposed": {}}
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(1, FAKE_USER)
        assert "sugerencia" in result.lower()

    def test_out_of_range_returns_error(self):
        suggestions = [
            {"name": "tortilla", "have": 3, "total": 3, "missing": []},
            {"name": "cazuela", "have": 2, "total": 4, "missing": ["pollo", "zapallo"]},
        ]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = self._staged_ctx(suggestions)
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(9, FAKE_USER)
        assert "2 sugerencias" in result
        mock_mcp.confirm.assert_not_called()

    def test_zero_index_returns_error(self):
        suggestions = [{"name": "tortilla", "have": 3, "total": 3, "missing": []}]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = self._staged_ctx(suggestions)
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(0, FAKE_USER)
        assert "1 y 1" in result

    def test_recipe_match_no_missing_confirms_and_returns(self):
        suggestions = [{"name": "tortilla", "have": 3, "total": 3, "missing": []}]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = self._staged_ctx(suggestions)
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(1, FAKE_USER)
        mock_mcp.confirm.assert_called_once_with("ctx-1")
        mock_mcp.send_context.assert_not_called()
        assert "tortilla" in result
        assert "A cocinar" in result

    def test_all_recipes_no_ingredients_rolls_back_context(self):
        mock_mcp = MagicMock()
        mock_mcp.send_context.return_value = "ctx-match"
        mock_mcp.request_action.return_value = {"proposed": {"suggestions": [
            {"recipe_id": "r-1", "name": "misterio", "have": 0, "total": 0, "missing": [], "score": 0.0},
        ]}}
        recipes = [{"id": "r-1", "name": "misterio", "servings": 2}]
        with patch("app.handlers.recipes.get_recipes", return_value=recipes), \
             patch("app.handlers.recipes.get_ingredients", return_value=[]), \
             patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.db", MagicMock()):
            from app.handlers.recipes import que_puedo_hacer
            result = que_puedo_hacer(FAKE_USER)
        mock_mcp.rollback.assert_called_once_with("ctx-match")
        assert "ingredientes" in result
        assert "elegir" not in result

    def test_elegir_receta_db_failure_does_not_confirm_context(self):
        suggestions = [{
            "name": "tortilla",
            "ingredients": [{"item": "huevo", "quantity": 3, "unit": None}],
            "uses_pantry": [],
            "missing": [],
        }]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = {
            "domain": "recipe_suggest",
            "payload": {},
            "proposed": {"suggestions": suggestions},
        }
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.create_recipe", side_effect=RuntimeError("db down")):
            from app.handlers.recipes import elegir_receta
            try:
                elegir_receta(1, FAKE_USER)
            except RuntimeError:
                pass
        mock_mcp.confirm.assert_not_called()
        suggestions = [
            {"name": "cazuela", "have": 2, "total": 4, "missing": ["pollo", "zapallo"]}
        ]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = self._staged_ctx(suggestions)
        mock_mcp.send_context.return_value = "ctx-shop"
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(1, FAKE_USER)
        mock_mcp.send_context.assert_called_once_with(
            "shopping_add_pending", FAKE_USER["id"],
            {"items": ["pollo", "zapallo"], "source": "recipe"}
        )
        mock_mcp.request_action.assert_called_once_with("ctx-shop")
        assert "pollo" in result
        assert "zapallo" in result
        assert "lista de compras" in result


class TestElegirRecetaFlavorB:
    def _staged_suggest_ctx(self, suggestions):
        return {
            "domain": "recipe_suggest",
            "payload": {},
            "proposed": {"suggestions": suggestions},
        }

    def test_saves_recipe_and_ingredients(self):
        suggestions = [{
            "name": "tortilla de cebolla",
            "ingredients": [
                {"item": "huevo", "quantity": 3, "unit": None},
                {"item": "cebolla", "quantity": 1, "unit": None},
            ],
            "uses_pantry": ["huevo", "cebolla"],
            "missing": [],
        }]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = self._staged_suggest_ctx(suggestions)
        mock_create = MagicMock(return_value={"id": "r-new"})
        mock_replace = MagicMock(return_value=[])
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.create_recipe", mock_create), \
             patch("app.handlers.recipes.replace_ingredients", mock_replace):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(1, FAKE_USER)
        mock_create.assert_called_once_with("abc-123", "tortilla de cebolla")
        rows = mock_replace.call_args[0][1]
        assert rows[0]["item"] == "huevo"
        assert rows[0]["quantity"] == 3.0
        assert rows[1]["item"] == "cebolla"
        assert "guardada" in result

    def test_normalizes_ingredient_names(self):
        suggestions = [{
            "name": "cazuela",
            "ingredients": [{"item": "Pollo", "quantity": 500, "unit": "g"}],
            "uses_pantry": [],
            "missing": ["pollo"],
        }]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = self._staged_suggest_ctx(suggestions)
        mock_mcp.send_context.return_value = "ctx-shop"
        mock_create = MagicMock(return_value={"id": "r-new"})
        mock_replace = MagicMock(return_value=[])
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.create_recipe", mock_create), \
             patch("app.handlers.recipes.replace_ingredients", mock_replace):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(1, FAKE_USER)
        rows = mock_replace.call_args[0][1]
        assert rows[0]["item"] == "pollo"

    def test_non_numeric_quantity_becomes_none(self):
        suggestions = [{
            "name": "sopa",
            "ingredients": [{"item": "sal", "quantity": "al gusto", "unit": None}],
            "uses_pantry": ["sal"],
            "missing": [],
        }]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = self._staged_suggest_ctx(suggestions)
        mock_create = MagicMock(return_value={"id": "r-new"})
        mock_replace = MagicMock(return_value=[])
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.create_recipe", mock_create), \
             patch("app.handlers.recipes.replace_ingredients", mock_replace):
            from app.handlers.recipes import elegir_receta
            elegir_receta(1, FAKE_USER)
        rows = mock_replace.call_args[0][1]
        assert rows[0]["quantity"] is None

    def test_no_missing_skips_shopping_prompt(self):
        suggestions = [{
            "name": "tortilla",
            "ingredients": [{"item": "huevo", "quantity": 3, "unit": None}],
            "uses_pantry": ["huevo"],
            "missing": [],
        }]
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = self._staged_suggest_ctx(suggestions)
        mock_create = MagicMock(return_value={"id": "r-new"})
        mock_replace = MagicMock(return_value=[])
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.create_recipe", mock_create), \
             patch("app.handlers.recipes.replace_ingredients", mock_replace):
            from app.handlers.recipes import elegir_receta
            result = elegir_receta(1, FAKE_USER)
        mock_mcp.send_context.assert_not_called()
        assert "lista de compras" not in result


class TestConfirmShoppingAdd:
    def _fake_ctx(self, items=None, source="recipe"):
        return {
            "domain": "shopping_add_pending",
            "payload": {"items": items or ["pollo", "romero"], "source": source},
            "proposed": {"items": items or ["pollo", "romero"], "source": source},
        }

    def test_happy_path_adds_items_and_confirms(self):
        mock_mcp = MagicMock()
        mock_add = MagicMock(return_value=2)
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.add_many_to_shopping", mock_add):
            from app.handlers.recipes import confirm_shopping_add
            result = confirm_shopping_add("ctx-1", FAKE_USER, self._fake_ctx())
        mock_mcp.confirm.assert_called_once_with("ctx-1")
        mock_add.assert_called_once_with(["pollo", "romero"], FAKE_USER, "recipe")
        assert "2 ítems" in result
        assert "Buen provecho" in result

    def test_singular_noun(self):
        mock_mcp = MagicMock()
        mock_add = MagicMock(return_value=1)
        with patch("app.handlers.recipes.mcp", mock_mcp), \
             patch("app.handlers.recipes.add_many_to_shopping", mock_add):
            from app.handlers.recipes import confirm_shopping_add
            result = confirm_shopping_add("ctx-1", FAKE_USER, self._fake_ctx(["pollo"]))
        assert "1 ítem" in result

    def test_expired_context_returns_graceful_message(self):
        mock_mcp = MagicMock()
        mock_mcp.confirm.side_effect = ValueError("expired")
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import confirm_shopping_add
            result = confirm_shopping_add("ctx-1", FAKE_USER, self._fake_ctx())
        assert "expiró" in result


class TestCancelShoppingAdd:
    def test_cancel_success(self):
        mock_mcp = MagicMock()
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import cancel_shopping_add
            result = cancel_shopping_add("ctx-1", FAKE_USER)
        mock_mcp.rollback.assert_called_once_with("ctx-1")
        assert "Buen provecho" in result

    def test_cancel_already_done(self):
        mock_mcp = MagicMock()
        mock_mcp.rollback.side_effect = ValueError()
        with patch("app.handlers.recipes.mcp", mock_mcp):
            from app.handlers.recipes import cancel_shopping_add
            result = cancel_shopping_add("ctx-1", FAKE_USER)
        assert "expiró" in result


class TestRecipeRouterPatterns:
    def test_nueva_receta_routes(self):
        with patch("app.router.nueva_receta", return_value="ok") as mock_fn:
            from app.router import route
            route("nueva receta: cazuela", FAKE_USER)
            mock_fn.assert_called_once_with("cazuela", FAKE_USER)

    def test_mis_recetas_routes(self):
        with patch("app.router.list_recipes", return_value="ok") as mock_fn:
            from app.router import route
            route("mis recetas", FAKE_USER)
            mock_fn.assert_called_once_with(FAKE_USER)

    def test_receta_show_routes(self):
        with patch("app.router.show_recipe", return_value="ok") as mock_fn:
            from app.router import route
            route("receta cazuela", FAKE_USER)
            mock_fn.assert_called_once_with("cazuela", FAKE_USER)

    def test_que_puedo_hacer_routes(self):
        with patch("app.router.que_puedo_hacer", return_value="ok") as mock_fn:
            from app.router import route
            route("qué puedo hacer", FAKE_USER)
            mock_fn.assert_called_once_with(FAKE_USER)

    def test_que_puedo_hacer_without_accent_routes(self):
        with patch("app.router.que_puedo_hacer", return_value="ok") as mock_fn:
            from app.router import route
            route("que puedo hacer", FAKE_USER)
            mock_fn.assert_called_once_with(FAKE_USER)

    def test_que_cocino_routes(self):
        with patch("app.router.sugerir_recetas", return_value="ok") as mock_fn:
            from app.router import route
            route("qué cocino", FAKE_USER)
            mock_fn.assert_called_once_with(FAKE_USER)

    def test_sugiereme_recetas_routes(self):
        with patch("app.router.sugerir_recetas", return_value="ok") as mock_fn:
            from app.router import route
            route("sugiéreme recetas", FAKE_USER)
            mock_fn.assert_called_once_with(FAKE_USER)

    def test_que_cocino_with_question_mark_routes(self):
        with patch("app.router.sugerir_recetas", return_value="ok") as mock_fn:
            from app.router import route
            route("qué cocino?", FAKE_USER)
            mock_fn.assert_called_once_with(FAKE_USER)

    def test_que_puedo_hacer_with_question_mark_routes(self):
        with patch("app.router.que_puedo_hacer", return_value="ok") as mock_fn:
            from app.router import route
            route("qué puedo hacer?", FAKE_USER)
            mock_fn.assert_called_once_with(FAKE_USER)

    def test_elegir_n_routes(self):
        with patch("app.router.elegir_receta", return_value="ok") as mock_fn:
            from app.router import route
            route("elegir 3", FAKE_USER)
            mock_fn.assert_called_once_with(3, FAKE_USER)

    def test_cancelar_recipe_match_calls_rollback(self):
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = {"domain": "recipe_match", "proposed": {}}
        with patch("app.router.mcp", mock_mcp):
            from app.router import route
            result = route("cancelar", FAKE_USER)
        mock_mcp.rollback.assert_called_once_with("ctx-1")
        assert "canceladas" in result

    def test_confirm_recipe_match_prompts_elegir(self):
        mock_mcp = MagicMock()
        mock_mcp.find_pending_for_user.return_value = "ctx-1"
        mock_mcp.receive_result.return_value = {
            "domain": "recipe_match",
            "proposed": {"suggestions": [{"name": "a"}, {"name": "b"}]},
        }
        with patch("app.router.mcp", mock_mcp):
            from app.router import route
            result = route("confirmar", FAKE_USER)
        assert "elegir" in result.lower()
        mock_mcp.confirm.assert_not_called()
