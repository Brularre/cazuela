from datetime import datetime
from unittest.mock import MagicMock, patch
import jwt
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_SECRET = "test-secret"
TEST_PHONE = "+56912345678"
TEST_USER_ID = "user-1"
TEST_TOKEN = jwt.encode(
    {"phone": TEST_PHONE, "user_id": TEST_USER_ID, "exp": datetime(2099, 1, 1)},
    TEST_SECRET,
    algorithm="HS256",
)


def _authed_cookies():
    return {"session": TEST_TOKEN}


def test_dashboard_unauthenticated():
    response = client.get("/dashboard")
    assert response.status_code == 401


def test_dashboard_expired_session():
    expired_token = jwt.encode(
        {"phone": TEST_PHONE, "user_id": TEST_USER_ID, "exp": datetime(2000, 1, 1)},
        TEST_SECRET,
        algorithm="HS256",
    )
    with patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        response = client.get("/dashboard", cookies={"session": expired_token})
    assert response.status_code == 401
    assert response.json()["detail"] == "session_expired"


def test_dashboard_returns_all_sections():
    db = MagicMock()

    def table_side_effect(name):
        mock = MagicMock()
        if name == "expenses":
            mock.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
                {"amount": "1500", "category": "comida", "date": "2024-01-15"},
            ]
        elif name == "todos":
            mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": "todo-1", "task": "llamar al banco", "priority": None},
            ]
        elif name == "waiting_on":
            mock.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {"id": "w-1", "description": "respuesta del banco", "created_at": "2024-01-10T10:00:00"},
            ]
        elif name == "pantry":
            mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {"id": "p-1", "item": "jabón", "current_quantity": 0, "desired_quantity": 2, "category": "baño"},
            ]
        return mock

    db.table.side_effect = table_side_effect

    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as mock_settings:
        mock_settings.session_secret = TEST_SECRET

        response = client.get("/dashboard", cookies=_authed_cookies())

    assert response.status_code == 200
    data = response.json()
    assert "gastos" in data
    assert "pendientes" in data
    assert "esperando" in data
    assert "weekly_total" in data["gastos"]
    assert "by_day" in data["gastos"]
    assert "by_category" in data["gastos"]
    assert "compras" in data
    assert "despensa" in data
    assert len(data["compras"]) == 1
    assert data["compras"][0]["item"] == "jabón"


def test_complete_todo():
    db = MagicMock()
    db.table.side_effect = lambda name: MagicMock()

    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as mock_settings:
        mock_settings.session_secret = TEST_SECRET

        response = client.patch(
            "/dashboard/todos/todo-1/complete",
            cookies=_authed_cookies(),
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    update_calls = [
        call for call in db.table.call_args_list
        if call.args[0] == "todos"
    ]
    assert len(update_calls) > 0


def test_resolve_waiting():
    db = MagicMock()
    db.table.side_effect = lambda name: MagicMock()

    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as mock_settings:
        mock_settings.session_secret = TEST_SECRET

        response = client.patch(
            "/dashboard/waiting_on/w-1/resolve",
            cookies=_authed_cookies(),
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    update_calls = [
        call for call in db.table.call_args_list
        if call.args[0] == "waiting_on"
    ]
    assert len(update_calls) > 0


def _pantry_db(pantry_mock=None):
    db = MagicMock()
    def table_side_effect(name):
        if name == "pantry" and pantry_mock:
            return pantry_mock
        return MagicMock()
    db.table.side_effect = table_side_effect
    return db


def test_create_pantry_item_returns_id():
    pantry = MagicMock()
    pantry.upsert.return_value.execute.return_value.data = [{"id": "item-456"}]
    db = _pantry_db(pantry)
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        res = client.post(
            "/dashboard/pantry",
            json={"item": "jabón", "desired_quantity": 3, "category": "baño"},
            cookies=_authed_cookies(),
        )
    assert res.status_code == 200
    assert res.json()["id"] == "item-456"


def test_create_pantry_item_normalizes_item_name():
    pantry = MagicMock()
    pantry.upsert.return_value.execute.return_value.data = [{"id": "item-789"}]
    db = _pantry_db(pantry)
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        client.post(
            "/dashboard/pantry",
            json={"item": "Jabón de manos", "desired_quantity": 2, "category": "baño"},
            cookies=_authed_cookies(),
        )
    upserted = pantry.upsert.call_args[0][0]
    assert upserted["item"] == "jabon de manos"


def test_create_pantry_item_upsert_passes_on_conflict():
    pantry = MagicMock()
    pantry.upsert.return_value.execute.return_value.data = [{"id": "item-999"}]
    db = _pantry_db(pantry)
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        client.post(
            "/dashboard/pantry",
            json={"item": "arroz", "desired_quantity": 5, "category": "cocina"},
            cookies=_authed_cookies(),
        )
    _, kwargs = pantry.upsert.call_args
    assert kwargs.get("on_conflict") == "user_id,item"


def test_create_pantry_item_invalid_category():
    db = _pantry_db()
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        res = client.post(
            "/dashboard/pantry",
            json={"item": "jabón", "desired_quantity": 3, "category": "invalido"},
            cookies=_authed_cookies(),
        )
    assert res.status_code == 422


def test_update_pantry_item():
    db = _pantry_db()
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        res = client.patch(
            "/dashboard/pantry/item-123",
            json={"desired_quantity": 5},
            cookies=_authed_cookies(),
        )
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_update_pantry_item_current_quantity():
    pantry = MagicMock()
    db = _pantry_db(pantry)
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        res = client.patch(
            "/dashboard/pantry/item-123",
            json={"current_quantity": 2},
            cookies=_authed_cookies(),
        )
    assert res.status_code == 200
    pantry.update.assert_called_once_with({"current_quantity": 2})


def test_delete_pantry_item():
    db = _pantry_db()
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        res = client.delete("/dashboard/pantry/item-123", cookies=_authed_cookies())
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_restock_pantry_item():
    pantry = MagicMock()
    pantry.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"desired_quantity": 3}]
    db = _pantry_db(pantry)
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        res = client.patch("/dashboard/pantry/item-123/restock", cookies=_authed_cookies())
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_restock_all_pantry():
    pantry = MagicMock()
    pantry.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "current_quantity": 0, "desired_quantity": 2},
        {"id": "2", "current_quantity": 3, "desired_quantity": 3},
    ]
    db = _pantry_db(pantry)
    with patch("app.routes.dashboard.client", db), \
         patch("app.middleware.auth.settings") as s:
        s.session_secret = TEST_SECRET
        res = client.patch("/dashboard/pantry/restock-all", cookies=_authed_cookies())
    assert res.status_code == 200
    assert res.json()["ok"] is True


def _authed_db():
    db = MagicMock()
    db.table.side_effect = lambda name: MagicMock()
    return db


class TestMealPlanRoutes:
    def test_get_meal_plan_invalid_week(self):
        db = _authed_db()
        with patch("app.routes.dashboard.client", db), \
             patch("app.middleware.auth.settings") as s:
            s.session_secret = TEST_SECRET
            res = client.get("/dashboard/meal-plan?week=not-a-date", cookies=_authed_cookies())
        assert res.status_code == 422

    def test_upsert_entry_invalid_day(self):
        db = _authed_db()
        with patch("app.routes.dashboard.client", db), \
             patch("app.middleware.auth.settings") as s:
            s.session_secret = TEST_SECRET
            res = client.post(
                "/dashboard/meal-plan/entries",
                json={"week_start": "2026-04-21", "day_of_week": "monday", "slot_name": "almuerzo", "recipe_id": None},
                cookies=_authed_cookies(),
            )
        assert res.status_code == 422

    def test_upsert_entry_invalid_week_start(self):
        db = _authed_db()
        with patch("app.routes.dashboard.client", db), \
             patch("app.middleware.auth.settings") as s:
            s.session_secret = TEST_SECRET
            res = client.post(
                "/dashboard/meal-plan/entries",
                json={"week_start": "not-a-date", "day_of_week": "lunes", "slot_name": "almuerzo", "recipe_id": None},
                cookies=_authed_cookies(),
            )
        assert res.status_code == 422

    def test_upsert_entry_recipe_not_owned_returns_404(self):
        db = MagicMock()
        def table_side_effect(name):
            m = MagicMock()
            if name == "recipes":
                m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            return m
        db.table.side_effect = table_side_effect
        with patch("app.routes.dashboard.client", db), \
             patch("app.middleware.auth.settings") as s:
            s.session_secret = TEST_SECRET
            res = client.post(
                "/dashboard/meal-plan/entries",
                json={"week_start": "2026-04-21", "day_of_week": "lunes", "slot_name": "almuerzo", "recipe_id": "other-recipe"},
                cookies=_authed_cookies(),
            )
        assert res.status_code == 404

    def test_update_slots_plan_not_owned_returns_404(self):
        db = MagicMock()
        def table_side_effect(name):
            m = MagicMock()
            if name == "meal_plans":
                m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            return m
        db.table.side_effect = table_side_effect
        with patch("app.routes.dashboard.client", db), \
             patch("app.middleware.auth.settings") as s:
            s.session_secret = TEST_SECRET
            res = client.patch(
                "/dashboard/meal-plan/other-plan/slots",
                json={"slots": ["almuerzo"]},
                cookies=_authed_cookies(),
            )
        assert res.status_code == 404

    def test_get_meal_plan_returns_plan_and_entries(self):
        db = MagicMock()
        def table_side_effect(name):
            m = MagicMock()
            if name == "meal_plans":
                m.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                    {"id": "plan-1", "slots": ["almuerzo", "cena"]}
                ]
            elif name == "meal_plan_entries":
                m.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": "e-1", "day_of_week": "lunes", "slot_name": "almuerzo",
                     "recipe_id": "r-1", "recipes": {"name": "Cazuela"}},
                ]
            return m
        db.table.side_effect = table_side_effect
        with patch("app.routes.dashboard.client", db), \
             patch("app.middleware.auth.settings") as s:
            s.session_secret = TEST_SECRET
            res = client.get("/dashboard/meal-plan?week=2026-04-21", cookies=_authed_cookies())
        assert res.status_code == 200
        data = res.json()
        assert data["plan_id"] == "plan-1"
        assert data["slots"] == ["almuerzo", "cena"]
        assert len(data["entries"]) == 1
        assert data["entries"][0]["recipe_name"] == "Cazuela"

    def test_generate_shopping_adds_missing_items(self):
        db = MagicMock()
        def table_side_effect(name):
            m = MagicMock()
            if name == "meal_plans":
                m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": "plan-1"}
                ]
            elif name == "meal_plan_entries":
                m.select.return_value.eq.return_value.not_.is_.return_value.execute.return_value.data = [
                    {"recipe_id": "r-1"}
                ]
            elif name == "recipe_ingredients":
                m.select.return_value.in_.return_value.execute.return_value.data = [
                    {"item": "pollo"},
                    {"item": "papa"},
                ]
            elif name == "pantry":
                m.select.return_value.eq.return_value.execute.return_value.data = []
            elif name == "shopping_list":
                m.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
                m.insert.return_value.execute.return_value.data = [{}]
            return m
        db.table.side_effect = table_side_effect
        with patch("app.routes.dashboard.client", db), \
             patch("app.middleware.auth.settings") as s:
            s.session_secret = TEST_SECRET
            res = client.post("/dashboard/meal-plan/plan-1/shopping", cookies=_authed_cookies())
        assert res.status_code == 200
        data = res.json()
        added_items = [a["item"] for a in data["added"]]
        assert "pollo" in added_items
        assert "papa" in added_items
        assert data["confirm"] == []

    def test_generate_shopping_skips_stocked_pantry_items(self):
        db = MagicMock()
        def table_side_effect(name):
            m = MagicMock()
            if name == "meal_plans":
                m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": "plan-1"}
                ]
            elif name == "meal_plan_entries":
                m.select.return_value.eq.return_value.not_.is_.return_value.execute.return_value.data = [
                    {"recipe_id": "r-1"}
                ]
            elif name == "recipe_ingredients":
                m.select.return_value.in_.return_value.execute.return_value.data = [
                    {"item": "pollo"},
                ]
            elif name == "pantry":
                m.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": "p-1", "item": "pollo", "current_quantity": 2}
                ]
            return m
        db.table.side_effect = table_side_effect
        with patch("app.routes.dashboard.client", db), \
             patch("app.middleware.auth.settings") as s:
            s.session_secret = TEST_SECRET
            res = client.post("/dashboard/meal-plan/plan-1/shopping", cookies=_authed_cookies())
        assert res.status_code == 200
        data = res.json()
        assert data["added"] == []
        assert len(data["confirm"]) == 1
        assert data["confirm"][0]["item"] == "pollo"
