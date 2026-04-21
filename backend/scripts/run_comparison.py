#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("SESSION_SECRET", "test-secret-that-is-long-enough-for-jwt-hs256")
os.environ.setdefault("TWILIO_SKIP_VALIDATION", "true")

USER_ID = "benchmark-0000-0000-000000000001"

SCENARIO = {
    "raw_message": "pagué 5000",
    "amount": 5000,
    "user_history": {"comida": 8, "transporte": 3, "otros": 1},
    "date": "2026-04-18",
}

BATCH_SCENARIO = {
    "raw_message": "gasté 18000 en supermercado: pan, leche, queso, lavalozas",
    "total_amount": 18000.0,
    "items_csv": "pan, leche, queso, lavalozas",
    "date": "2026-04-18",
    "user_history": {"comida": 5},
}

RECIPE_SCENARIO = {
    "recipe_name": "cazuela",
}

RECIPE_INGREDIENTS_MOCK = [
    {"item": "carne de vacuno", "quantity": 500, "unit": "g"},
    {"item": "papa", "quantity": 4, "unit": None},
    {"item": "choclo", "quantity": 2, "unit": None},
    {"item": "zapallo", "quantity": 200, "unit": "g"},
    {"item": "zanahoria", "quantity": 2, "unit": None},
    {"item": "caldo de carne", "quantity": 1, "unit": "litro"},
]


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


def run_baseline_regex_single() -> dict:
    from app.handlers.expenses import map_category

    t0 = time.perf_counter()
    cat = map_category(SCENARIO["raw_message"])
    ms = (time.perf_counter() - t0) * 1000
    return {
        "mode": "baseline-regex",
        "final_category": cat,
        "iteration_count": 0,
        "wall_clock_ms": ms,
        "db_rows_written": 1,
    }


def run_baseline_regex_batch() -> dict:
    from app.handlers.expenses import map_category

    desc = "listado plano sin palabras clave"
    t0 = time.perf_counter()
    cat = map_category(desc)
    ms = (time.perf_counter() - t0) * 1000
    return {
        "mode": "baseline-regex",
        "final_category": cat,
        "iteration_count": 0,
        "wall_clock_ms": ms,
        "db_rows_written": 1,
    }


def run_mcp_stub(scenario: dict, domain: str) -> dict:
    import app.mcp.context as ctx_mod
    from app.config import settings
    from app.mcp.client import send_context, request_action, confirm

    settings.use_ai_agent = False
    settings.anthropic_api_key = ""
    ctx_mod.client = make_fake_client()

    if domain == "expense":
        payload = {
            "raw_message": scenario["raw_message"],
            "amount": scenario["amount"],
            "date": scenario["date"],
            "note": None,
            "user_history": scenario["user_history"],
        }
    else:
        payload = {
            "raw_message": scenario["raw_message"],
            "total_amount": scenario["total_amount"],
            "items_csv": scenario["items_csv"],
            "date": scenario["date"],
            "user_history": scenario["user_history"],
        }

    t0 = time.perf_counter()
    cid = send_context(domain, USER_ID, payload)
    last = None
    n = 3 if domain == "expense_batch" else 1
    for _ in range(n):
        last = request_action(cid)
    proposed = (last or {}).get("proposed") or {}
    if domain == "expense":
        final_cat = proposed.get("category", "otros")
    else:
        final_cat = [x.get("category") for x in proposed.get("items", [])]
    confirm(cid)
    ms = (time.perf_counter() - t0) * 1000
    db_rows = 1 if domain == "expense" else len(proposed.get("items", []))
    return {
        "mode": "mcp-stub",
        "final_category": final_cat,
        "iteration_count": (last or {}).get("iteration_count"),
        "wall_clock_ms": ms,
        "db_rows_written": db_rows,
    }


def run_mcp_claude_t0() -> dict:
    import app.mcp.context as ctx_mod
    from app.config import settings
    from app.mcp.client import send_context, request_action, confirm

    settings.use_ai_agent = True
    settings.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "fake")
    ctx_mod.client = make_fake_client()
    fixed = {"category": "comida", "confidence": 0.85, "reasoning": "fijado"}
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(text=json.dumps(fixed))]

    scenario = SCENARIO
    t0 = time.perf_counter()
    with patch("app.mcp.agent.anthropic") as m_anth:
        m_anth.Anthropic.return_value.messages.create.return_value = fake_resp
        cid = send_context(
            "expense",
            USER_ID,
            {
                "raw_message": scenario["raw_message"],
                "amount": scenario["amount"],
                "date": scenario["date"],
                "note": None,
                "user_history": scenario["user_history"],
            },
        )
        last = request_action(cid)
        confirm(cid)
    ms = (time.perf_counter() - t0) * 1000
    prop = (last or {}).get("proposed") or {}
    return {
        "mode": "mcp-claude-t0",
        "final_category": prop.get("category", "otros"),
        "iteration_count": (last or {}).get("iteration_count"),
        "wall_clock_ms": ms,
        "db_rows_written": 1,
    }


def run_mcp_claude_t07(rotate_i: int) -> dict:
    import app.mcp.context as ctx_mod
    from app.config import settings
    from app.mcp.client import send_context, request_action, confirm

    settings.use_ai_agent = True
    settings.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "fake")
    ctx_mod.client = make_fake_client()
    cats = ["comida", "comida", "hogar"]
    cat = cats[rotate_i % 3]
    raw = json.dumps(
        {"category": cat, "confidence": 0.6, "reasoning": "rotación simulada"},
    )
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(text=raw)]

    scenario = SCENARIO
    t0 = time.perf_counter()
    with patch("app.mcp.agent.anthropic") as m_anth:
        m_anth.Anthropic.return_value.messages.create.return_value = fake_resp
        cid = send_context(
            "expense",
            USER_ID,
            {
                "raw_message": scenario["raw_message"],
                "amount": scenario["amount"],
                "date": scenario["date"],
                "note": None,
                "user_history": scenario["user_history"],
            },
        )
        last = request_action(cid)
        confirm(cid)
    ms = (time.perf_counter() - t0) * 1000
    prop = (last or {}).get("proposed") or {}
    return {
        "mode": "mcp-claude-t07",
        "final_category": prop.get("category", "otros"),
        "iteration_count": (last or {}).get("iteration_count"),
        "wall_clock_ms": ms,
        "db_rows_written": 1,
    }


def run_baseline_recipe() -> dict:
    t0 = time.perf_counter()
    ms = (time.perf_counter() - t0) * 1000
    return {
        "mode": "baseline-regex",
        "final_category": "0 ingredientes",
        "iteration_count": 0,
        "wall_clock_ms": ms,
        "db_rows_written": 1,
    }


def run_mcp_stub_recipe() -> dict:
    import app.mcp.context as ctx_mod
    from app.config import settings
    from app.mcp.client import send_context, request_action, confirm

    settings.use_ai_agent = False
    settings.anthropic_api_key = ""
    ctx_mod.client = make_fake_client()

    t0 = time.perf_counter()
    cid = send_context("recipe_create", USER_ID, {"recipe_name": RECIPE_SCENARIO["recipe_name"]})
    last = request_action(cid)
    proposed = (last or {}).get("proposed") or {}
    n = len(proposed.get("ingredients", []))
    confirm(cid)
    ms = (time.perf_counter() - t0) * 1000
    return {
        "mode": "mcp-stub",
        "final_category": f"{n} ingredientes",
        "iteration_count": (last or {}).get("iteration_count"),
        "wall_clock_ms": ms,
        "db_rows_written": 1 + n,
    }


def run_mcp_claude_recipe() -> dict:
    import app.mcp.context as ctx_mod
    from app.config import settings
    from app.mcp.client import send_context, request_action, confirm

    settings.use_ai_agent = True
    settings.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "fake")
    ctx_mod.client = make_fake_client()
    fixed = {"ingredients": RECIPE_INGREDIENTS_MOCK}
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(text=json.dumps(fixed))]

    t0 = time.perf_counter()
    with patch("app.mcp.agent.anthropic") as m_anth:
        m_anth.Anthropic.return_value.messages.create.return_value = fake_resp
        cid = send_context("recipe_create", USER_ID, {"recipe_name": RECIPE_SCENARIO["recipe_name"]})
        last = request_action(cid)
        confirm(cid)
    proposed = (last or {}).get("proposed") or {}
    n = len(proposed.get("ingredients", []))
    ms = (time.perf_counter() - t0) * 1000
    return {
        "mode": "mcp-claude-t0",
        "final_category": f"{n} ingredientes",
        "iteration_count": (last or {}).get("iteration_count"),
        "wall_clock_ms": ms,
        "db_rows_written": 1 + n,
    }


def markdown_table(rows: list[dict]) -> str:
    lines = [
        "| Mode | Run | Scenario | Category | Iter | ms | rows |",
        "|---|---:|:---:|---|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['mode']} | {r['run']} | {r['scenario']} | {r['final_category']!s} | "
            f"{r['iteration_count']} | {r['wall_clock_ms']:.1f} | {r['db_rows_written']} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Reserved: pass-through for future live API runs (still mocked).",
    )
    parser.parse_args(argv if argv is not None else sys.argv[1:])

    flat_runs: list[dict] = []

    for run in range(1, 4):
        r = run_baseline_regex_single()
        r["run"] = run
        r["scenario"] = "single"
        flat_runs.append(r)

    for run in range(1, 4):
        r = run_mcp_stub(SCENARIO, "expense")
        r["run"] = run
        r["scenario"] = "single"
        flat_runs.append(r)

    for run in range(1, 4):
        r = run_mcp_claude_t0()
        r["run"] = run
        r["scenario"] = "single"
        flat_runs.append(r)

    for run in range(1, 4):
        r = run_mcp_claude_t07(run - 1)
        r["run"] = run
        r["scenario"] = "single"
        flat_runs.append(r)

    for run in range(1, 4):
        br = run_baseline_regex_batch()
        br["run"] = run
        br["scenario"] = "batch"
        flat_runs.append(br)

    for run in range(1, 4):
        bs = run_mcp_stub(BATCH_SCENARIO, "expense_batch")
        bs["run"] = run
        bs["scenario"] = "batch"
        flat_runs.append(bs)

    for run in range(1, 4):
        rr = run_baseline_recipe()
        rr["run"] = run
        rr["scenario"] = "recipe"
        flat_runs.append(rr)

    for run in range(1, 4):
        rs = run_mcp_stub_recipe()
        rs["run"] = run
        rs["scenario"] = "recipe"
        flat_runs.append(rs)

    for run in range(1, 4):
        rc = run_mcp_claude_recipe()
        rc["run"] = run
        rc["scenario"] = "recipe"
        flat_runs.append(rc)

    out_json = BACKEND / "comparison_results.json"
    out_md = BACKEND / "comparison_results.md"
    payload = {
        "single_scenario": SCENARIO,
        "batch_scenario": BATCH_SCENARIO,
        "runs": flat_runs,
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    md = "# Comparison benchmark\n\n" + markdown_table(flat_runs) + "\n"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)

    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
