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
