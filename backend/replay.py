#!/usr/bin/env python
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_file")
    parser.add_argument("--expected-category", default=None)
    args = parser.parse_args()

    with open(args.snapshot_file) as f:
        snapshot = json.load(f)

    from app.mcp.agent import propose

    result = propose(snapshot)
    print(f"Agent output:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

    if args.expected_category:
        actual = result.get("category")
        if actual == args.expected_category:
            print(f"\nPASS: category == '{actual}'")
            sys.exit(0)
        else:
            print(f"\nFAIL: expected '{args.expected_category}', got '{actual}'")
            sys.exit(1)


if __name__ == "__main__":
    main()
