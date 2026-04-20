import json
from pathlib import Path

from scripts import run_comparison


def test_run_comparison_writes_json_and_modes(tmp_path, monkeypatch):
    out = tmp_path / "comparison_results.json"
    md = tmp_path / "comparison_results.md"
    monkeypatch.setattr(run_comparison, "BACKEND", tmp_path)

    run_comparison.main([])

    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    runs = data["runs"]
    assert len(runs) >= 12

    baseline = [r for r in runs if r["mode"] == "baseline-regex" and r["scenario"] == "single"]
    assert len(baseline) == 3
    assert all(r["final_category"] == "otros" for r in baseline)

    stub = [r for r in runs if r["mode"] == "mcp-stub" and r["scenario"] == "single"]
    assert len(stub) == 3
    assert all(r["final_category"] == "comida" for r in stub)
    assert all(r["iteration_count"] == 1 for r in stub)

    t07 = [r for r in runs if r["mode"] == "mcp-claude-t07" and r["scenario"] == "single"]
    cats = [r["final_category"] for r in t07]
    assert len(set(cats)) >= 2

    assert md.exists()
    assert "mcp-stub" in md.read_text(encoding="utf-8")
