import pytest
from app.mcp import context as ctx_mod
from app.mcp.client import send_context, request_action, confirm, rollback
from app.mcp.agent import _infer_pantry_category, _propose_pantry_add_batch
from app.handlers import pantry_shopping
from app.router import NECESITO_COMPRAR_PATTERN, route

FAKE_USER_ID = "22222222-2222-2222-2222-222222222222"
FAKE_USER = {"id": FAKE_USER_ID, "phone": "+56900000000"}


@pytest.fixture(autouse=True)
def db_store(monkeypatch):
    ctx_store = {}
    pantry_rows = []
    shopping_rows = []

    class FakeExecute:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, store_ref, table_name, pantry_bucket, shopping_bucket):
            self._store = store_ref
            self._table = table_name
            self._pantry = pantry_bucket
            self._shopping = shopping_bucket
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

        def execute(self):
            if self._pending_insert is not None:
                inserts = (
                    self._pending_insert
                    if isinstance(self._pending_insert, list)
                    else [self._pending_insert]
                )
                if self._table == "pantry":
                    rows = [dict(r) for r in inserts]
                    self._pantry.extend(rows)
                    return FakeExecute(rows)
                if self._table == "shopping_list":
                    rows = [dict(r) for r in inserts]
                    self._shopping.extend(rows)
                    return FakeExecute(rows)
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

            results = [
                dict(row) for row in self._store.values()
                if all(row.get(k) == v for k, v in self._eq_filters.items())
            ]
            return FakeExecute(results)

    class FakeClient:
        def __init__(self, store_ref, pantry_bucket, shopping_bucket):
            self._store = store_ref
            self._pantry = pantry_bucket
            self._shopping = shopping_bucket

        def table(self, name):
            return FakeQuery(self._store, name, self._pantry, self._shopping)

    fc = FakeClient(ctx_store, pantry_rows, shopping_rows)
    monkeypatch.setattr("app.mcp.context.client", fc)
    monkeypatch.setattr("app.handlers.pantry_shopping.client", fc)
    return {"ctx": ctx_store, "pantry": pantry_rows, "shopping": shopping_rows}


def test_create_proposes_items_with_categories(db_store):
    reply = pantry_shopping.handle_pantry_add_create("shampoo y balsamo", FAKE_USER)
    assert "shampoo" in reply
    assert "baño" in reply
    assert "despensa" in reply.lower()
    assert "lista" in reply.lower()


def test_confirm_despensa_writes_pantry_rows(db_store):
    pantry_shopping.handle_pantry_add_create("shampoo, balsamo", FAKE_USER)
    cid = list(db_store["ctx"].keys())[0]
    pantry_shopping.handle_pantry_add_confirm_despensa(cid, FAKE_USER)
    assert len(db_store["pantry"]) == 2
    for row in db_store["pantry"]:
        assert row["current_quantity"] == 0
        assert row["desired_quantity"] == 1
        assert row["user_id"] == FAKE_USER_ID
        assert row["category"] in {"cocina", "baño", "otros"}


def test_confirm_despensa_infers_baño_category(db_store):
    pantry_shopping.handle_pantry_add_create("shampoo", FAKE_USER)
    cid = list(db_store["ctx"].keys())[0]
    pantry_shopping.handle_pantry_add_confirm_despensa(cid, FAKE_USER)
    assert db_store["pantry"][0]["category"] == "baño"


def test_confirm_lista_writes_shopping_rows(db_store):
    pantry_shopping.handle_pantry_add_create("shampoo, balsamo", FAKE_USER)
    cid = list(db_store["ctx"].keys())[0]
    pantry_shopping.handle_pantry_add_confirm_lista(cid, FAKE_USER)
    assert len(db_store["shopping"]) == 2
    assert db_store["pantry"] == []


def test_cancel_rolls_back(db_store):
    pantry_shopping.handle_pantry_add_create("shampoo", FAKE_USER)
    cid = list(db_store["ctx"].keys())[0]
    reply = pantry_shopping.handle_pantry_add_cancel(cid, FAKE_USER)
    assert "cancelad" in reply.lower()
    assert db_store["ctx"][cid]["status"] == "rolled_back"
    assert db_store["pantry"] == []


def test_double_confirm_is_safe(db_store):
    pantry_shopping.handle_pantry_add_create("shampoo", FAKE_USER)
    cid = list(db_store["ctx"].keys())[0]
    pantry_shopping.handle_pantry_add_confirm_despensa(cid, FAKE_USER)
    reply = pantry_shopping.handle_pantry_add_confirm_despensa(cid, FAKE_USER)
    assert "expiró" in reply or "confirmada" in reply


def test_confirm_despensa_invalid_category_falls_back_to_otros(db_store, monkeypatch):
    from app.mcp.agent import _propose_pantry_add_batch as real_propose

    def propose_with_bad_category(ctx):
        result = real_propose(ctx)
        for item in result.get("items", []):
            item["category"] = "comida"
        return result

    monkeypatch.setattr("app.mcp.agent._propose_pantry_add_batch", propose_with_bad_category)
    pantry_shopping.handle_pantry_add_create("jabón", FAKE_USER)
    cid = list(db_store["ctx"].keys())[0]
    pantry_shopping.handle_pantry_add_confirm_despensa(cid, FAKE_USER)
    assert db_store["pantry"][0]["category"] == "otros"


def test_infer_category_baño():
    assert _infer_pantry_category("shampoo") == "baño"
    assert _infer_pantry_category("balsamo") == "baño"
    assert _infer_pantry_category("jabón") == "baño"
    assert _infer_pantry_category("desodorante") == "baño"


def test_infer_category_cocina():
    assert _infer_pantry_category("arroz") == "cocina"
    assert _infer_pantry_category("café") == "cocina"
    assert _infer_pantry_category("leche") == "cocina"


def test_infer_category_otros():
    assert _infer_pantry_category("pilas AA") == "otros"
    assert _infer_pantry_category("regalo") == "otros"


def test_propose_splits_on_y(db_store):
    ctx = {"domain": "pantry_add_batch", "payload": {"items_raw": "shampoo y balsamo"}}
    result = _propose_pantry_add_batch(ctx)
    assert len(result["items"]) == 2
    assert result["items"][0]["name"] == "shampoo"
    assert result["items"][1]["name"] == "balsamo"


def test_propose_splits_on_comma(db_store):
    ctx = {"domain": "pantry_add_batch", "payload": {"items_raw": "arroz, sal, aceite"}}
    result = _propose_pantry_add_batch(ctx)
    assert len(result["items"]) == 3


def test_context_prunes_excess_items(db_store):
    from app.mcp.context import create_context, MAX_ITEMS
    import re
    many = ", ".join(f"item{i}" for i in range(MAX_ITEMS + 3))
    ctx = create_context("pantry_add_batch", FAKE_USER_ID, {"items_raw": many})
    parts = [
        p.strip()
        for p in re.split(r",\s*|\s+y\s+", ctx["payload"]["items_raw"])
        if p.strip()
    ]
    assert len(parts) == MAX_ITEMS


def test_router_pattern_matches():
    assert NECESITO_COMPRAR_PATTERN.match("necesito comprar shampoo y balsamo")
    assert NECESITO_COMPRAR_PATTERN.match("Necesito Comprar jabón")
    assert not NECESITO_COMPRAR_PATTERN.match("necesito: jabón")
    assert not NECESITO_COMPRAR_PATTERN.match("comprar: jabón")


def test_router_necesito_comprar_triggers_mcp(db_store, monkeypatch):
    monkeypatch.setattr("app.router.classify", lambda m: None)
    monkeypatch.setattr("app.router.db", type("DB", (), {"table": lambda self, n: type("Q", (), {
        "select": lambda s, *a: s,
        "eq": lambda s, *a: s,
        "gte": lambda s, *a: s,
        "execute": lambda s: type("R", (), {"data": []})(),
    })()})())
    reply = route("necesito comprar shampoo", FAKE_USER)
    assert "shampoo" in reply
    assert "despensa" in reply.lower() or "lista" in reply.lower()
