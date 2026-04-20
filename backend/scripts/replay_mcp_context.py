#!/usr/bin/env python3
"""
Deprecated. Use from the backend directory:

    .venv/bin/python replay.py fixtures/mcp_snapshots/<name>.json --mode stub ...
"""
import sys


def main() -> int:
    print(
        "replay_mcp_context.py is deprecated. Use: "
        "cd backend && .venv/bin/python replay.py <fixture.json> [options]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
