import copy
import uuid
from datetime import datetime, timezone, timedelta
from typing import TypedDict
from app.db import client

TTL_SECONDS = 3600
MAX_HISTORY_ENTRIES = 10
MAX_BATCH_SIZE = 5

SENSITIVE_KEYS = {"phone", "anthropic_key", "supabase_key", "google_tokens", "password"}


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

    if domain == "reconciliation" and "transactions" in payload:
        txns = payload["transactions"]
        if not txns:
            raise ValueError("Reconciliation batch requires at least one transaction")
        if len(txns) > MAX_BATCH_SIZE:
            payload = {**payload, "transactions": txns[:MAX_BATCH_SIZE]}

    row = {
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
    result = client.table("mcp_contexts").insert(row).execute()
    return result.data[0]


def get_context(context_id: str) -> dict:
    result = client.table("mcp_contexts").select("*").eq("context_id", context_id).execute()
    if not result.data:
        raise KeyError(f"Context not found: {context_id}")
    context = result.data[0]
    expires_at = datetime.fromisoformat(context["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise ValueError("Context expired")
    return context


def update_context(context_id: str, **kwargs) -> dict:
    get_context(context_id)
    result = client.table("mcp_contexts").update(kwargs).eq("context_id", context_id).execute()
    if not result.data:
        raise KeyError(f"Context not found: {context_id}")
    return result.data[0]


def confirm(context_id: str) -> dict:
    get_context(context_id)
    result = (
        client.table("mcp_contexts")
        .update({"status": "confirmed"})
        .eq("context_id", context_id)
        .eq("status", "staged")
        .execute()
    )
    if not result.data:
        raise ValueError("Context already confirmed or cancelled")
    return result.data[0]


def rollback(context_id: str) -> dict:
    context = get_context(context_id)
    if context["status"] in ("confirmed", "rolled_back"):
        raise ValueError(f"Cannot rollback context in status '{context['status']}'")
    return update_context(context_id, status="rolled_back")


def prune_expired() -> int:
    now = datetime.now(timezone.utc).isoformat()
    result = client.table("mcp_contexts").delete().lt("expires_at", now).execute()
    return len(result.data)


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


def find_pending_for_user(user_id: str) -> str | None:
    result = (
        client.table("mcp_contexts")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "staged")
        .execute()
    )
    staged = result.data
    if not staged:
        return None
    return max(staged, key=lambda c: datetime.fromisoformat(c["created_at"]))["context_id"]
