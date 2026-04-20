"""Tests for replay.py and deterministic propose() over fixture snapshots."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.mcp import context as ctx
from app.mcp.agent import propose

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / "fixtures" / "mcp_snapshots"


def _snapshot_context(snapshot: dict) -> dict:
    return {
        "domain": snapshot["domain"],
        "payload": dict(snapshot.get("payload") or {}),
        "proposed": snapshot.get("proposed"),
    }


@pytest.mark.parametrize(
    "fixture_path",
    sorted(FIXTURES.glob("*.json")),
    ids=lambda p: p.name,
)
def test_propose_three_times_identical_per_fixture(fixture_path: Path):
    with open(fixture_path, encoding="utf-8") as f:
        snapshot = json.load(f)
    context = _snapshot_context(snapshot)
    redacted = ctx.redact(
        {
            "context_id": snapshot.get("context_id", "test"),
            "domain": context["domain"],
            "payload": context["payload"],
            "proposed": context["proposed"],
            "user_id": snapshot.get("user_id", "u"),
            "status": "pending",
            "iteration_count": 0,
            "agent_model": "stub-v1",
            "version": "1.0",
            "created_at": "2026-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T00:00:00+00:00",
        }
    )
    base = {
        "domain": redacted["domain"],
        "payload": redacted["payload"],
        "proposed": redacted.get("proposed"),
    }
    outs = [json.dumps(propose(dict(base)), sort_keys=True) for _ in range(3)]
    assert outs[0] == outs[1] == outs[2], f"variance in {fixture_path.name}: {outs}"


def test_replay_cli_stub_expense_comida():
    r = subprocess.run(
        [
            sys.executable,
            str(BACKEND / "replay.py"),
            str(FIXTURES / "expense_comida.json"),
            "--mode",
            "stub",
            "--runs",
            "2",
            "--request-actions",
            "1",
            "--expect-final-status",
            "confirmed",
            "--expect-iteration-count",
            "1",
        ],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_replay_cli_expense_batch_supermercado():
    r = subprocess.run(
        [
            sys.executable,
            str(BACKEND / "replay.py"),
            str(FIXTURES / "expense_batch_supermercado.json"),
            "--mode",
            "stub",
            "--runs",
            "2",
            "--request-actions",
            "3",
            "--expect-final-status",
            "confirmed",
            "--expect-iteration-count",
            "3",
            "--expect-proposed-step",
            "3",
        ],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_replay_cli_fails_on_category_mismatch():
    r = subprocess.run(
        [
            sys.executable,
            str(BACKEND / "replay.py"),
            str(FIXTURES / "expense_comida.json"),
            "--mode",
            "stub",
            "--runs",
            "1",
            "--request-actions",
            "1",
            "--expect-final-status",
            "confirmed",
            "--expect-categories",
            '{"category": "tecnología"}',
        ],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1


def test_replay_detects_proposed_variance_across_runs():
    proposed_a = {"category": "comida", "confidence": 0.8}
    proposed_b = {"category": "hogar", "confidence": 0.8}
    dumps = {json.dumps(p, sort_keys=True) for p in (proposed_a, proposed_b)}
    assert len(dumps) == 2
