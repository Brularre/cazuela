import copy
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import TypedDict
from app.db import client

TTL_SECONDS = 3600
MAX_HISTORY_ENTRIES = 10
MAX_BATCH_SIZE = 5
MAX_ITEMS = 10
MAX_USER_PROFILE_JSON_CHARS = 500
MAX_CATEGORY_MAP_KEYS = 20

SENSITIVE_KEYS = {"phone", "anthropic_key", "supabase_key", "google_tokens", "password"}


def _prune_user_profile_to_budget(profile: dict) -> dict:
    keys = sorted(profile.keys())
    pruned: dict = {}
    for k in keys:
        cand = {**pruned, k: profile[k]}
        if len(json.dumps(cand, sort_keys=True, ensure_ascii=False)) <= MAX_USER_PROFILE_JSON_CHARS:
            pruned = cand
    return pruned


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

    if domain == "expense_batch":
        items_csv = (payload.get("items_csv") or "").strip()
        if not items_csv:
            raise ValueError("expense_batch requires non-empty items_csv")
        parts = [p.strip() for p in items_csv.split(",") if p.strip()]
        if not parts:
            raise ValueError("expense_batch requires at least one item")
        if len(parts) > MAX_ITEMS:
            payload = {**payload, "items_csv": ",".join(parts[:MAX_ITEMS])}

    if "category_map" in payload and isinstance(payload["category_map"], dict):
        cm = payload["category_map"]
        if len(cm) > MAX_CATEGORY_MAP_KEYS:
            payload = {**payload, "category_map": dict(list(cm.items())[:MAX_CATEGORY_MAP_KEYS])}

    if "user_profile" in payload and isinstance(payload["user_profile"], dict):
        up = payload["user_profile"]
        if len(json.dumps(up, sort_keys=True, ensure_ascii=False)) > MAX_USER_PROFILE_JSON_CHARS:
            payload = {**payload, "user_profile": _prune_user_profile_to_budget(up)}

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
