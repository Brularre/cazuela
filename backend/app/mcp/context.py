import copy
import uuid
from datetime import datetime, timezone, timedelta
from typing import TypedDict

TTL_SECONDS = 3600
MAX_HISTORY_ENTRIES = 10

SENSITIVE_KEYS = {"phone", "anthropic_key", "supabase_key", "google_tokens", "password"}

_store: dict[str, dict] = {}


class MCPContext(TypedDict):
    context_id: str
    version: str
    domain: str
    user_id: str
    created_at: str
    expires_at: str
    status: str
    payload: dict
    proposed: dict | None
    agent_model: str
    iteration_count: int


def create_context(domain: str, user_id: str, payload: dict) -> dict:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=TTL_SECONDS)

    if domain == "expense" and "user_history" in payload:
        history = payload["user_history"]
        if len(history) > MAX_HISTORY_ENTRIES:
            top = sorted(history.items(), key=lambda x: x[1], reverse=True)
            payload = {**payload, "user_history": dict(top[:MAX_HISTORY_ENTRIES])}

    context = {
        "context_id": str(uuid.uuid4()),
        "version": "1.0",
        "domain": domain,
        "user_id": user_id,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "status": "pending",
        "payload": payload,
        "proposed": None,
        "agent_model": "stub-v1",
        "iteration_count": 0,
    }
    _store[context["context_id"]] = context
    return context


def get_context(context_id: str) -> dict:
    if context_id not in _store:
        raise KeyError(f"Context not found: {context_id}")
    context = _store[context_id]
    expires_at = datetime.fromisoformat(context["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise ValueError("Context expired")
    return context


def update_context(context_id: str, **kwargs) -> dict:
    context = get_context(context_id)
    context.update(kwargs)
    return context


def confirm(context_id: str) -> dict:
    return update_context(context_id, status="confirmed")


def rollback(context_id: str) -> dict:
    return update_context(context_id, status="rolled_back")


def prune_expired() -> int:
    now = datetime.now(timezone.utc)
    expired = [
        cid for cid, c in _store.items()
        if datetime.fromisoformat(c["expires_at"]) < now
    ]
    for cid in expired:
        del _store[cid]
    return len(expired)


def _redact_dict(d: dict) -> dict:
    result = {}
    for k, v in d.items():
        if k in SENSITIVE_KEYS:
            continue
        if isinstance(v, dict):
            result[k] = _redact_dict(v)
        else:
            result[k] = v
    return result


def redact(context: dict) -> dict:
    deep = copy.deepcopy(context)
    return _redact_dict(deep)
