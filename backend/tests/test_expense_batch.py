import json

import pytest

from app.mcp import context as ctx
from app.mcp.client import send_context, request_action
from app.handlers import expense_batch
from app.router import BATCH_EXPENSE_PATTERN, route
from app.mcp.agent import propose

FAKE_USER_ID = "11111111-1111-1111-1111-111111111111"

BATCH_PAYLOAD = {
    "raw_message": "gasté 18000 en supermercado: pan, leche, queso, detergente",
    "total_amount": 18000.0,
    "items_csv": "pan, leche, queso, detergente",
    "date": "2026-04-20",
    "user_history": {"comida": 2, "hogar": 1},
}


@pytest.fixture(autouse=True)
def db_store(monkeypatch):
    ctx_store = {}
    expense_rows = []

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
                dict(row) for row in self._store.values()
                if all(row.get(k) == v for k, v in self._eq_filters.items())
            ]
            return FakeExecute(results)

    class FakeClient:
        def __init__(self, store_ref, expense_bucket):
            self._store = store_ref
            self._expense_bucket = expense_bucket

        def table(self, name):
            return FakeQuery(self._store, name, self._expense_bucket)

    fc = FakeClient(ctx_store, expense_rows)
    monkeypatch.setattr("app.mcp.context.client", fc)
    monkeypatch.setattr("app.handlers.expense_batch.client", fc)
    return {"ctx": ctx_store, "expenses": expense_rows}


def test_batch_three_step_flow_increments_iteration_count():
    cid = send_context("expense_batch", FAKE_USER_ID, BATCH_PAYLOAD)
    for _ in range(3):
        request_action(cid)
    assert ctx.get_context(cid)["iteration_count"] == 3
    assert ctx.get_context(cid)["proposed"]["step"] == 3


def test_batch_step1_extracts_items():
    cid = send_context("expense_batch", FAKE_USER_ID, BATCH_PAYLOAD)
    r = request_action(cid)
    p = r["proposed"]
    assert p["step"] == 1
    names = [x["name"] for x in p["items"]]
    assert names == ["pan", "leche", "queso", "detergente"]


def test_batch_step2_categorizes_each_item():
    cid = send_context("expense_batch", FAKE_USER_ID, {
        **BATCH_PAYLOAD,
        "items_csv": "pan, limpieza, mercado",
    })
    request_action(cid)
    r = request_action(cid)
    p = r["proposed"]
    assert p["step"] == 2
    cats = [x["category"] for x in p["items"]]
    assert cats == ["comida", "hogar", "comida"]


def test_batch_step3_splits_total_evenly():
    cid = send_context("expense_batch", FAKE_USER_ID, {
        **BATCH_PAYLOAD,
        "total_amount": 18000.0,
        "items_csv": "a, b, c, d",
    })
    request_action(cid)
    request_action(cid)
    r = request_action(cid)
    amounts = [x["amount"] for x in r["proposed"]["items"]]
    assert amounts == [4500, 4500, 4500, 4500]


def test_batch_step3_handles_non_even_division():
    cid = send_context("expense_batch", FAKE_USER_ID, {
        **BATCH_PAYLOAD,
        "total_amount": 10000.0,
        "items_csv": "a, b, c",
    })
    request_action(cid)
    request_action(cid)
    r = request_action(cid)
    amounts = [x["amount"] for x in r["proposed"]["items"]]
    assert sum(amounts) == 10000
    assert sorted(amounts) == [3333, 3333, 3334]


def test_batch_confirm_inserts_one_row_per_item(db_store):
    user = {"id": FAKE_USER_ID}
    cid = send_context("expense_batch", FAKE_USER_ID, BATCH_PAYLOAD)
    request_action(cid)
    request_action(cid)
    request_action(cid)
    expense_batch.handle_batch_confirm(cid, user)
    rows = db_store["expenses"]
    assert len(rows) == 4
    for row in rows:
        assert row["user_id"] == FAKE_USER_ID
        assert row["date"] == "2026-04-20"
        assert "category" in row and row["category"]


def test_batch_cancel_inserts_no_rows(db_store):
    user = {"id": FAKE_USER_ID}
    cid = send_context("expense_batch", FAKE_USER_ID, BATCH_PAYLOAD)
    request_action(cid)
    request_action(cid)
    request_action(cid)
    expense_batch.handle_batch_cancel(cid, user)
    assert db_store["expenses"] == []


def test_batch_replay_yields_identical_proposed():
    out = []
    for _ in range(2):
        cid = send_context("expense_batch", FAKE_USER_ID, BATCH_PAYLOAD)
        request_action(cid)
        request_action(cid)
        r = request_action(cid)
        out.append(json.dumps(r["proposed"], sort_keys=True))
    assert out[0] == out[1]


def test_batch_empty_items_raises_validation():
    with pytest.raises(ValueError, match="non-empty"):
        send_context("expense_batch", FAKE_USER_ID, {**BATCH_PAYLOAD, "items_csv": ""})


def test_batch_whitespace_only_items_raises():
    with pytest.raises(ValueError, match="at least one"):
        send_context("expense_batch", FAKE_USER_ID, {**BATCH_PAYLOAD, "items_csv": " , , "})


@pytest.fixture
def lots_of_items_csv():
    return ",".join(f"item{i}" for i in range(15))


def test_batch_accepts_up_to_max_items(lots_of_items_csv):
    cid = send_context("expense_batch", FAKE_USER_ID, {
        **BATCH_PAYLOAD,
        "items_csv": lots_of_items_csv,
    })
    csv_stored = ctx.get_context(cid)["payload"]["items_csv"]
    assert len([p for p in csv_stored.split(",") if p.strip()]) <= ctx.MAX_ITEMS


def test_batch_route_pattern_matches_supermercado_format():
    m = BATCH_EXPENSE_PATTERN.match("gasté 18000 en supermercado: pan, leche")
    assert m is not None
    assert m.group(1) == "18000"
    assert m.group(2).strip() == "pan, leche"


def test_router_dispatches_supermercado_to_handle_batch_create(monkeypatch):
    calls = []

    def capture(msg, amount, items_csv, user):
        calls.append((msg, amount, items_csv))
        return "ctx-id", "reply-batch"

    monkeypatch.setattr("app.router.handle_batch_create", capture)
    r = route("Gasté 18000 en supermercado: pan, leche", {"id": FAKE_USER_ID})
    assert r == "reply-batch"
    assert len(calls) == 1
    assert calls[0][1] == 18000.0
    assert "pan" in calls[0][2]


def test_batch_no_sensitive_keys_in_serialized_context():
    payload = {
        **BATCH_PAYLOAD,
        "phone": "+56912345678",
        "anthropic_key": "sk-ant-xxx",
    }
    cid = send_context("expense_batch", FAKE_USER_ID, payload)
    redacted = ctx.redact(ctx.get_context(cid))

    def all_keys(d):
        keys = set(d.keys())
        for v in d.values():
            if isinstance(v, dict):
                keys |= all_keys(v)
        return keys

    assert not (all_keys(redacted) & ctx.SENSITIVE_KEYS)


def test_propose_batch_idempotent_at_step3():
    cid = send_context("expense_batch", FAKE_USER_ID, BATCH_PAYLOAD)
    request_action(cid)
    request_action(cid)
    request_action(cid)
    c3 = ctx.get_context(cid)
    p1 = propose(c3)
    p2 = propose(ctx.get_context(cid))
    assert p1 == p2
    assert p1["step"] == 3
