import json
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
    assert result["reasoning"] == "categorizado por IA"


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
