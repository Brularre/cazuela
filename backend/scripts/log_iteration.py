#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = REPO_ROOT / "agent_iteration_log.md"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", default="stub-v1")
    p.add_argument("--settings", default="")
    p.add_argument("--output", default="")
    p.add_argument("--diff", default="")
    p.add_argument("--decision", choices=("accepted", "rejected"), required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--context-snapshot", type=Path, default=None)
    p.add_argument("--log-file", type=Path, default=DEFAULT_LOG)
    args = p.parse_args(argv)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ctx_line = (
        f"`{args.context_snapshot}`"
        if args.context_snapshot
        else "(none)"
    )
    block = f"""
---

## {ts} — {args.task}

**Prompt:**
```
{args.prompt.strip()}
```

**Context snapshot:** {ctx_line}

**Model:** {args.model}
**Settings:** {args.settings or "(n/a)"}

**Agent output:**
```
{args.output.strip() or "(n/a)"}
```

**Diff applied:**
```
{args.diff.strip() or "(n/a)"}
```

**Decision:** {args.decision.capitalize()}
**Reason:** {args.reason.strip()}

""".lstrip()

    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(args.log_file, "a", encoding="utf-8") as f:
        f.write(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
