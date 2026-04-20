import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_log_iteration_appends(tmp_path):
    log = tmp_path / "log.md"
    r = subprocess.run(
        [
            sys.executable,
            str(BACKEND / "scripts" / "log_iteration.py"),
            "--task",
            "unit test",
            "--prompt",
            "TASK: verify CLI\nACCEPT: file grows",
            "--model",
            "stub-v1",
            "--decision",
            "accepted",
            "--reason",
            "automated test",
            "--log-file",
            str(log),
        ],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    text = log.read_text(encoding="utf-8")
    assert "unit test" in text
    assert "verify CLI" in text
    assert "accepted" in text.lower()
