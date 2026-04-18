#!/usr/bin/env python3
"""
Replay script: runs the MCP propose→confirm cycle N times with an
identical context payload and asserts reproducible output.

Usage (from backend/):
    .venv/bin/python scripts/replay_mcp_context.py

Writes each run to mcp_interaction_log.jsonl.
"""
import os
import sys
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ.setdefault("TWILIO_SKIP_VALIDATION", "true")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.mcp.context as ctx_module
from app.mcp.client import send_context, request_action, receive_result, confirm

REPLAY_PAYLOAD = {
    "raw_message": "pagué 5000",
    "amount": 5000.0,
    "date": "2026-04-18",
    "note": None,
    "user_history": {"comida": 8, "transporte": 3, "otros": 1},
}

USER_ID = "replay-user-0000-0000-000000000001"
RUNS = 3
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp_interaction_log.jsonl")


def make_fake_client():
    store = {}

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

        def select(self, *args): return self
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

    return FakeClient(store)


def run_once(fake_client, run_number: int) -> dict:
    import app.mcp.context as ctx_mod
    import app.mcp.client as client_mod
    original = ctx_mod.client
    ctx_mod.client = fake_client
    client_mod  # ensure same module
    try:
        context_id = send_context("expense", USER_ID, REPLAY_PAYLOAD)
        context_after_send = ctx_mod.get_context(context_id)

        result = request_action(context_id)
        proposed = result.get("proposed", {})

        final = confirm(context_id)

        entry = {
            "run": run_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": f"Categorize ambiguous expense: {REPLAY_PAYLOAD['raw_message']}",
            "context_snapshot": ctx_mod.redact(context_after_send),
            "agent_model": result.get("agent_model", "stub-v1"),
            "proposed": proposed,
            "status_after_confirm": final.get("status"),
            "iteration_count": result.get("iteration_count", 1),
            "decision": "accepted",
            "reason": "automated replay — deterministic stub",
        }
        return entry
    finally:
        ctx_mod.client = original


def main():
    fake_client = make_fake_client()
    results = []

    print(f"Running {RUNS} replay(s) of scenario: \"{REPLAY_PAYLOAD['raw_message']}\"")
    print(f"User history: {REPLAY_PAYLOAD['user_history']}\n")

    for i in range(1, RUNS + 1):
        entry = run_once(make_fake_client(), i)
        results.append(entry)
        print(f"Run {i}/{RUNS}: proposed={json.dumps(entry['proposed'])}")

    proposed_outputs = [json.dumps(r["proposed"], sort_keys=True) for r in results]
    all_identical = len(set(proposed_outputs)) == 1

    print()
    if all_identical:
        print(f"✓ All {RUNS} runs produced identical output — reproducibility confirmed")
    else:
        print(f"✗ Output variance detected across {RUNS} runs:")
        for i, out in enumerate(proposed_outputs, 1):
            print(f"  Run {i}: {out}")

    with open(LOG_FILE, "a") as f:
        for entry in results:
            f.write(json.dumps(entry) + "\n")

    print(f"\nInteractions logged to mcp_interaction_log.jsonl")
    return 0 if all_identical else 1


if __name__ == "__main__":
    sys.exit(main())
