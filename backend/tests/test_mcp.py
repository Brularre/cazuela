import pytest
from datetime import datetime, timezone, timedelta
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
def clear_store():
    ctx._store.clear()
    yield
    ctx._store.clear()


def test_round_trip_status_transitions():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    assert ctx._store[context_id]["status"] == "pending"

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
    ctx._store[context_id]["expires_at"] = past
    with pytest.raises(ValueError, match="expired"):
        ctx.get_context(context_id)


def test_prune_expired():
    id1 = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    id2 = send_context("todo", FAKE_USER_ID, {"task": "llamar banco", "due_date": None})
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    ctx._store[id1]["expires_at"] = past
    removed = ctx.prune_expired()
    assert removed == 1
    assert id1 not in ctx._store
    assert id2 in ctx._store


def test_history_pruned_to_max():
    big_history = {f"cat_{i}": i for i in range(15)}
    context_id = send_context("expense", FAKE_USER_ID, {
        **EXPENSE_PAYLOAD,
        "user_history": big_history,
    })
    stored = ctx._store[context_id]["payload"]["user_history"]
    assert len(stored) <= ctx.MAX_HISTORY_ENTRIES


def test_iteration_count_increments():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    request_action(context_id)
    assert ctx._store[context_id]["iteration_count"] == 1


def test_context_id_returned_as_string():
    context_id = send_context("expense", FAKE_USER_ID, EXPENSE_PAYLOAD)
    assert isinstance(context_id, str)


def test_no_sensitive_keys_in_serialized_context():
    payload_with_pii = {
        **EXPENSE_PAYLOAD,
        "phone": "+56912345678",
        "anthropic_key": "sk-ant-xxx",
    }
    context_id = send_context("expense", FAKE_USER_ID, payload_with_pii)
    raw = ctx._store[context_id]
    redacted = ctx.redact(raw)

    def all_keys(d):
        keys = set(d.keys())
        for v in d.values():
            if isinstance(v, dict):
                keys |= all_keys(v)
        return keys

    found = all_keys(redacted) & ctx.SENSITIVE_KEYS
    assert found == set(), f"Sensitive keys leaked into context: {found}"
