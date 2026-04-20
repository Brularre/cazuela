#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("SESSION_SECRET", "test-secret-that-is-long-enough-for-jwt-hs256")
os.environ.setdefault("TWILIO_SKIP_VALIDATION", "true")


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
            return FakeQuery(self._store)

    return FakeClient(store)


def strip_fixture_for_insert(snapshot: dict) -> tuple[str, str, dict]:
    domain = snapshot["domain"]
    user_id = snapshot["user_id"]
    payload = copy.deepcopy(snapshot.get("payload") or {})
    return domain, user_id, payload


def default_request_actions(domain: str) -> int:
    if domain == "expense_batch":
        return 3
    return 1


def proposed_matches_categories(proposed: dict | None, domain: str, expect: dict) -> bool:
    if not proposed or not expect:
        return True
    if domain == "expense" and "category" in expect:
        return proposed.get("category") == expect["category"]
    if domain == "expense_batch" and isinstance(proposed.get("items"), list):
        by_name = {i.get("name"): i.get("category") for i in proposed["items"]}
        for name, cat in expect.items():
            if by_name.get(name) != cat:
                return False
        return True
    if domain == "reconciliation" and "categorizations" in proposed:
        return True
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay MCP context fixtures")
    parser.add_argument("fixture", type=Path, help="JSON snapshot file")
    parser.add_argument("--mode", choices=("stub", "claude"), default="stub")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--expect-final-status", default=None)
    parser.add_argument(
        "--request-actions",
        type=int,
        default=None,
        help="How many times to call request_action (default: 1, or 3 for expense_batch)",
    )
    parser.add_argument(
        "--expect-iteration-count",
        type=int,
        default=None,
        help="Assert iteration_count on the context after the last request_action",
    )
    parser.add_argument(
        "--expect-categories", default=None,
        help='JSON object e.g. {"category":"comida"} or item→category for expense_batch',
    )
    parser.add_argument("--expect-proposed-step", type=int, default=None)
    parser.add_argument(
        "--log-file",
        type=Path,
        default=BACKEND_ROOT / "mcp_interaction_log.jsonl",
    )
    args = parser.parse_args(argv)

    if args.mode == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set — skipping claude replay (hermetic mode).", file=sys.stderr)
        return 0

    if not args.fixture.is_file():
        print(f"Fixture not found: {args.fixture}", file=sys.stderr)
        return 1

    with open(args.fixture, encoding="utf-8") as f:
        raw_template = json.load(f)

    expect_cat = json.loads(args.expect_categories) if args.expect_categories else None

    import app.mcp.context as ctx_mod
    from app.mcp.client import send_context, request_action, receive_result, confirm

    runs_data = []
    errors: list[str] = []

    for run_idx in range(1, args.runs + 1):
        fake = make_fake_client()
        ctx_mod.client = fake

        if args.mode == "claude":
            from app.config import settings

            settings.use_ai_agent = True
            settings.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        else:
            from app.config import settings

            settings.use_ai_agent = False
            settings.anthropic_api_key = ""

        snapshot = copy.deepcopy(raw_template)
        domain, user_id, payload = strip_fixture_for_insert(snapshot)
        t0 = time.perf_counter()
        try:
            context_id = send_context(domain, user_id, payload)
            ctx_after_send = ctx_mod.redact(ctx_mod.get_context(context_id))
            n_actions = (
                args.request_actions
                if args.request_actions is not None
                else default_request_actions(domain)
            )
            last = None
            for _ in range(min(n_actions, 10)):
                last = request_action(context_id)

            final_ctx = receive_result(context_id)
            confirmed = confirm(context_id)
            ms = (time.perf_counter() - t0) * 1000

            proposed = (last or {}).get("proposed")
            model = (last or {}).get("agent_model", final_ctx.get("agent_model", ""))

            entry = {
                "run": run_idx,
                "fixture": str(args.fixture),
                "prompt": f"replay fixture domain={domain}",
                "context_snapshot": ctx_after_send,
                "agent_model": model,
                "proposed": proposed,
                "status_after_confirm": confirmed.get("status"),
                "iteration_count": (last or {}).get("iteration_count"),
                "decision": "accepted",
                "reason": "replay.py automated run",
                "wall_clock_ms": round(ms, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            runs_data.append(
                {
                    "proposed": proposed,
                    "iteration_count": (last or {}).get("iteration_count"),
                    "status": confirmed.get("status"),
                    "agent_model": model,
                    "wall_clock_ms": ms,
                }
            )

            with open(args.log_file, "a", encoding="utf-8") as logf:
                logf.write(json.dumps(entry, ensure_ascii=False) + "\n")

            if args.expect_final_status and confirmed.get("status") != args.expect_final_status:
                errors.append(
                    f"run {run_idx}: status {confirmed.get('status')} != {args.expect_final_status}"
                )
            if args.expect_iteration_count is not None:
                if (last or {}).get("iteration_count") != args.expect_iteration_count:
                    errors.append(
                        f"run {run_idx}: iteration_count "
                        f'{(last or {}).get("iteration_count")} != {args.expect_iteration_count}'
                    )
            if args.expect_proposed_step is not None:
                ps = (proposed or {}).get("step")
                if ps != args.expect_proposed_step:
                    errors.append(
                        f"run {run_idx}: proposed.step {ps} != {args.expect_proposed_step}"
                    )
            if expect_cat and not proposed_matches_categories(proposed, domain, expect_cat):
                errors.append(
                    f"run {run_idx}: categories mismatch expected {expect_cat} got {proposed}"
                )

        except Exception as e:
            print(f"run {run_idx} failed: {e!r}", file=sys.stderr)
            return 1

    if args.runs > 1:
        dumps = {json.dumps(r["proposed"], sort_keys=True) for r in runs_data}
        if len(dumps) > 1:
            print("variance detected: proposed outputs differ across runs", file=sys.stderr)
            return 1

    print("run\tstatus\titer\tms\tmodel")
    for i, r in enumerate(runs_data, 1):
        print(
            f"{i}\t{r['status']}\t{r['iteration_count']}\t"
            f"{r['wall_clock_ms']:.1f}\t{r['agent_model']}"
        )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
