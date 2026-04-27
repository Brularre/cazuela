import json
import threading
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from app.mcp import context as ctx
from app.mcp.client import send_context, request_action, receive_result, confirm, rollback
from app.mcp.agent import propose

FAKE_USER_ID = "11111111-1111-1111-1111-111111111111"

EXPENSE_PAYLOAD = {
    "raw_message": "pagué 5000 ayer",
    "amount": 5000.0,
    "date": "2026-04-14",
    "note": None,
    "user_history": {"comida": 8, "transporte": 3, "otros": 1},
}


@pytest.fixture(autouse=True)
def db_store(monkeypatch):
    store = {}

    class FakeExecute:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, store_ref, table):
            self._store = store_ref
            self._table = table
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
        def __init__(self, store_ref):
            self._store = store_ref

        def table(self, name):
            return FakeQuery(self._store, name)

    monkeypatch.setattr("app.mcp.context.client", FakeClient(store))
    return store


def test_round_trip_status_transitions():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    assert ctx.get_context(context_id)["status"] == "pending"

    result = request_action(context_id)
    assert result["status"] == "staged"

    final = confirm(context_id)
    assert final["status"] == "confirmed"


def test_rollback():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    request_action(context_id)
    result = rollback(context_id)
    assert result["status"] == "rolled_back"


def test_receive_result_returns_current_state():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    request_action(context_id)
    result = receive_result(context_id)
    assert result["status"] == "staged"
    assert result["proposed"] is not None


def test_reproducibility():
    payload = {**EXPENSE_PAYLOAD, "user_history": {"comida": 8, "transporte": 3}}
    id1 = send_context("expense", FAKE_USER_ID, payload)
    id2 = send_context("expense", FAKE_USER_ID, payload)
    r1 = request_action(id1)
    r2 = request_action(id2)
    assert r1["proposed"]["category"] == r2["proposed"]["category"]


def test_stub_picks_highest_history():
    context = ctx.create_context("expense", FAKE_USER_ID, {
        **EXPENSE_PAYLOAD,
        "user_history": {"comida": 8, "transporte": 3},
    })
    result = propose(context)
    assert result["category"] == "comida"


def test_stub_empty_history_returns_otros():
    context = ctx.create_context("expense", FAKE_USER_ID, {
        **EXPENSE_PAYLOAD,
        "user_history": {},
    })
    result = propose(context)
    assert result["category"] == "otros"


def test_ttl_expiry():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    ctx.update_context(context_id, expires_at=past)
    with pytest.raises(ValueError, match="expired"):
        ctx.get_context(context_id)


def test_prune_expired():
    id1 = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    id2 = send_context("todo", FAKE_USER_ID, {"task": "llamar banco", "due_date": None})
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    ctx.update_context(id1, expires_at=past)
    removed = ctx.prune_expired()
    assert removed == 1
    with pytest.raises((ValueError, KeyError)):
        ctx.get_context(id1)
    assert ctx.get_context(id2) is not None


def test_history_pruned_to_max():
    big_history = {f"cat_{i}": i for i in range(15)}
    context_id = send_context("expense", FAKE_USER_ID, {
        **EXPENSE_PAYLOAD,
        "user_history": big_history,
    })
    stored = ctx.get_context(context_id)["payload"]["user_history"]
    assert len(stored) <= ctx.MAX_HISTORY_ENTRIES


def test_iteration_count_increments():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    request_action(context_id)
    assert ctx.get_context(context_id)["iteration_count"] == 1


def test_context_id_returned_as_string():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    assert isinstance(context_id, str)


def test_find_pending_for_user_returns_staged_context():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    request_action(context_id)
    from app.mcp.client import find_pending_for_user
    found = find_pending_for_user(FAKE_USER_ID)
    assert found == context_id


def test_find_pending_for_user_returns_none_when_no_staged():
    send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    from app.mcp.client import find_pending_for_user
    assert find_pending_for_user(FAKE_USER_ID) is None


def test_no_sensitive_keys_in_serialized_context():
    payload_with_pii = {
        **EXPENSE_PAYLOAD,
        "phone": "+56912345678",
        "anthropic_key": "sk-ant-xxx",
    }
    context_id = send_context("expense", FAKE_USER_ID, payload_with_pii)
    raw = ctx.get_context(context_id)
    redacted = ctx.redact(raw)

    def all_keys(d):
        keys = set(d.keys())
        for v in d.values():
            if isinstance(v, dict):
                keys |= all_keys(v)
        return keys

    found = all_keys(redacted) & ctx.SENSITIVE_KEYS
    assert found == set(), f"Sensitive keys leaked into context: {found}"


def test_confirm_already_confirmed_raises():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    request_action(context_id)
    confirm(context_id)
    with pytest.raises(ValueError, match="Context already confirmed or cancelled"):
        confirm(context_id)


def test_two_concurrent_confirms_raises_on_second(monkeypatch):
    """
    Confirms that only one caller can move status staged→confirmed.

    FakeClient here wraps execute() with a threading.Lock so only one
    UPDATE ... WHERE status='staged' can observe a matching row at a time.
    Postgres provides the real guarantee via row-level locking; we cannot
    run that without a live database.
    """
    store = {}
    exec_lock = threading.Lock()

    class FakeExecute:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, store_ref):
            self._store = store_ref
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
            with exec_lock:
                if self._pending_insert is not None:
                    self._store[self._pending_insert["context_id"]] = dict(
                        self._pending_insert
                    )
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
        def __init__(self, store_ref):
            self._store = store_ref

        def table(self, name):
            return FakeQuery(self._store)

    monkeypatch.setattr("app.mcp.context.client", FakeClient(store))

    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    request_action(context_id)
    barrier = threading.Barrier(2)
    out: list[tuple[str, Exception | None]] = []

    def worker():
        barrier.wait()
        try:
            confirm(context_id)
            out.append(("ok", None))
        except ValueError as e:
            out.append(("err", e))

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    oks = [x for x in out if x[0] == "ok"]
    errs = [x for x in out if x[0] == "err"]
    assert len(oks) == 1 and len(errs) == 1
    assert "already confirmed" in str(errs[0][1])


def test_rollback_already_rolled_back_raises():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    rollback(context_id)
    with pytest.raises(ValueError, match="Cannot rollback"):
        rollback(context_id)


def test_stub_non_expense_domain_returns_confirmed():
    from app.mcp.agent import propose
    result = propose({"domain": "todo", "payload": {}})
    assert result == {"confirmed": True}
    assert "category" not in result


def test_ai_agent_propose_called_when_enabled():
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text=json.dumps({
        "category": "transporte",
        "confidence": 0.9,
        "reasoning": "parece un gasto de transporte",
    }))]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    context = {
        "domain": "expense",
        "payload": {**EXPENSE_PAYLOAD, "user_history": {"comida": 8}},
    }

    with patch("app.mcp.agent.settings") as mock_settings, \
         patch("app.mcp.agent.anthropic") as mock_anthropic:
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value = fake_client
        result = propose(context)

    assert result["category"] == "transporte"
    assert result["confidence"] == 0.9
    fake_client.messages.create.assert_called_once()


def test_ai_agent_falls_back_to_stub_on_error():
    context = {
        "domain": "expense",
        "payload": {**EXPENSE_PAYLOAD, "user_history": {"comida": 8}},
    }

    with patch("app.mcp.agent.settings") as mock_settings, \
         patch("app.mcp.agent.anthropic") as mock_anthropic:
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value.messages.create.side_effect = Exception("API error")
        result = propose(context)

    assert result["category"] == "comida"


def test_ai_agent_invalid_category_falls_back_to_otros():
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text=json.dumps({
        "category": "pizza",
        "confidence": 0.7,
        "reasoning": "es una pizza",
    }))]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    context = {
        "domain": "expense",
        "payload": {**EXPENSE_PAYLOAD, "user_history": {"comida": 8}},
    }

    with patch("app.mcp.agent.settings") as mock_settings, \
         patch("app.mcp.agent.anthropic") as mock_anthropic:
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value = fake_client
        result = propose(context)

    assert result["category"] == "otros"


def test_ai_agent_malformed_json_falls_back_to_stub():
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="not json at all")]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    context = {
        "domain": "expense",
        "payload": {**EXPENSE_PAYLOAD, "user_history": {"transporte": 5}},
    }

    with patch("app.mcp.agent.settings") as mock_settings, \
         patch("app.mcp.agent.anthropic") as mock_anthropic:
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value = fake_client
        result = propose(context)

    assert result["category"] == "transporte"


def test_ai_agent_missing_fields_get_defaults():
    from app.mcp.agent import _parse_ai_response
    result = _parse_ai_response(json.dumps({"category": "comida"}))
    assert result["category"] == "comida"
    assert result["confidence"] == 0.5
    assert result["reasoning"] == "categorizado por IA"  # default when missing


def test_ai_agent_disabled_uses_stub():
    context = {
        "domain": "expense",
        "payload": {**EXPENSE_PAYLOAD, "user_history": {"salud": 3}},
    }
    with patch("app.mcp.agent.settings") as mock_settings:
        mock_settings.use_ai_agent = False
        mock_settings.anthropic_api_key = "sk-ant-fake"
        result = propose(context)
    assert result["category"] == "salud"


def test_verify_refine_loop():
    payload_v1 = {
        **EXPENSE_PAYLOAD,
        "user_history": {"otros": 5, "comida": 1},
    }
    id1 = send_context("expense", FAKE_USER_ID, payload_v1)
    result1 = request_action(id1)
    assert result1["proposed"]["category"] == "otros"

    rollback(id1)
    assert ctx.get_context(id1)["status"] == "rolled_back"

    payload_v2 = {**payload_v1, "user_history": {"comida": 8, "otros": 2}}
    id2 = send_context("expense", FAKE_USER_ID, payload_v2)
    result2 = request_action(id2)
    assert result2["proposed"]["category"] == "comida"

    confirm(id2)
    assert ctx.get_context(id2)["status"] == "confirmed"


BATCH_PAYLOAD = {
    "transactions": [
        {"raw_message": "pagué 5000", "amount": 5000, "date": "2026-04-18"},
        {"raw_message": "compré pan", "amount": 1500, "date": "2026-04-18"},
        {"raw_message": "taxi al trabajo", "amount": 3000, "date": "2026-04-18"},
    ],
    "user_history": {"comida": 8, "transporte": 3},
}


def test_reconciliation_batch_round_trip():
    context_id = send_context("reconciliation", FAKE_USER_ID, BATCH_PAYLOAD)
    assert ctx.get_context(context_id)["status"] == "pending"

    result = request_action(context_id)
    assert result["status"] == "staged"
    cats = result["proposed"]["categorizations"]
    assert len(cats) == 3
    assert all("category" in c and "confidence" in c for c in cats)

    final = confirm(context_id)
    assert final["status"] == "confirmed"


def test_reconciliation_batch_reproducibility():
    ids = [send_context("reconciliation", FAKE_USER_ID, BATCH_PAYLOAD) for _ in range(3)]
    outputs = [json.dumps(request_action(ctx_id)["proposed"], sort_keys=True) for ctx_id in ids]
    assert outputs[0] == outputs[1] == outputs[2], f"Variance detected: {outputs}"


def test_reconciliation_batch_pruned_to_max():
    big_batch = [
        {"raw_message": f"gasto {i}", "amount": i * 1000, "date": "2026-04-18"}
        for i in range(8)
    ]
    context_id = send_context("reconciliation", FAKE_USER_ID, {
        **BATCH_PAYLOAD, "transactions": big_batch,
    })
    stored = ctx.get_context(context_id)["payload"]["transactions"]
    assert len(stored) <= ctx.MAX_BATCH_SIZE


def test_reconciliation_verify_refine_loop():
    payload_v1 = {**BATCH_PAYLOAD, "user_history": {"otros": 5}}
    id1 = send_context("reconciliation", FAKE_USER_ID, payload_v1)
    result1 = request_action(id1)
    assert all(c["category"] == "otros"
               for c in result1["proposed"]["categorizations"])
    rollback(id1)
    assert ctx.get_context(id1)["status"] == "rolled_back"

    payload_v2 = {**BATCH_PAYLOAD, "user_history": {"comida": 8, "otros": 2}}
    id2 = send_context("reconciliation", FAKE_USER_ID, payload_v2)
    result2 = request_action(id2)
    assert all(c["category"] == "comida"
               for c in result2["proposed"]["categorizations"])
    confirm(id2)
    assert ctx.get_context(id2)["status"] == "confirmed"


def test_reconciliation_empty_history_returns_otros():
    payload = {**BATCH_PAYLOAD, "user_history": {}}
    context_id = send_context("reconciliation", FAKE_USER_ID, payload)
    result = request_action(context_id)
    assert all(c["category"] == "otros"
               for c in result["proposed"]["categorizations"])


def test_reconciliation_empty_transactions_raises():
    with pytest.raises(ValueError, match="at least one"):
        send_context("reconciliation", FAKE_USER_ID, {
            **BATCH_PAYLOAD, "transactions": [],
        })


def test_agent_model_updated_to_ai_when_ai_mode_enabled():
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text=json.dumps({
        "category": "transporte",
        "confidence": 0.9,
        "reasoning": "parece un gasto de transporte",
    }))]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    with patch("app.mcp.agent.settings") as mock_settings, \
         patch("app.mcp.agent.anthropic") as mock_anthropic:
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value = fake_client
        result = request_action(context_id)

    assert result["agent_model"] == "claude-haiku-4-5-20251001"


def test_agent_model_stays_stub_when_ai_disabled():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    with patch("app.mcp.agent.settings") as mock_settings:
        mock_settings.use_ai_agent = False
        mock_settings.anthropic_api_key = ""
        result = request_action(context_id)
    assert result["agent_model"] == "stub-v1"


def test_ai_reproducibility_across_3_mocked_runs():
    fixed = {"category": "comida", "confidence": 0.9,
             "reasoning": "historial frecuente"}
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text=json.dumps(fixed))]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    context = {
        "domain": "expense",
        "payload": {**EXPENSE_PAYLOAD, "user_history": {"comida": 8}},
    }

    results = []
    with patch("app.mcp.agent.settings") as mock_settings, \
         patch("app.mcp.agent.anthropic") as mock_anthropic:
        mock_settings.use_ai_agent = True
        mock_settings.anthropic_api_key = "sk-ant-fake"
        mock_anthropic.Anthropic.return_value = fake_client
        for _ in range(3):
            results.append(propose(context))

    serialized = [json.dumps(r, sort_keys=True) for r in results]
    assert serialized[0] == serialized[1] == serialized[2], \
        f"AI output varied across runs: {serialized}"


def test_context_accepts_user_profile_field():
    profile = {"name": "Ana", "currency": "CLP", "preferred_categories": ["comida", "transporte"]}
    payload = {**EXPENSE_PAYLOAD, "user_profile": profile}
    context_id = send_context("expense", FAKE_USER_ID, payload)
    stored = ctx.get_context(context_id)["payload"]["user_profile"]
    assert stored == profile


def test_stub_uses_category_map_when_present():
    payload = {
        **EXPENSE_PAYLOAD,
        "raw_message": "pagué 5000 por almuerzo",
        "category_map": {"almuerzo": "comida"},
    }
    context = ctx.create_context("expense", FAKE_USER_ID, payload)
    result = propose(context)
    assert result["category"] == "comida"
    assert result["confidence"] == 0.9


def test_user_profile_redacted_for_sensitive_keys():
    payload = {
        **EXPENSE_PAYLOAD,
        "user_profile": {"name": "Ana", "anthropic_key": "sk-secret"},
    }
    context_id = send_context("expense", FAKE_USER_ID, payload)
    redacted = ctx.redact(ctx.get_context(context_id))

    def collect(d):
        s = set(d.keys())
        for v in d.values():
            if isinstance(v, dict):
                s |= collect(v)
        return s

    assert "anthropic_key" not in collect(redacted.get("payload", {}))


def test_category_map_pruned_to_max_keys():
    cmap = {f"k{i}": "comida" for i in range(50)}
    context_id = send_context("expense", FAKE_USER_ID, {**EXPENSE_PAYLOAD, "category_map": cmap})
    stored = ctx.get_context(context_id)["payload"]["category_map"]
    assert len(stored) <= ctx.MAX_CATEGORY_MAP_KEYS
