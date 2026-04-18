---
name: update-comparison-report
description: Re-runs the MCP replay experiment and updates COMPARISON_REPORT.md with fresh metrics
tools: Bash, Read, Edit
---

# update-comparison-report

Re-run the MCP replay experiment and patch `COMPARISON_REPORT.md`
with up-to-date metrics. Run this after changing the agent, toggling
AI mode, or before submitting the assignment.

## Steps

1. Run the replay script in stub mode (AI disabled):
   ```
   cd backend && USE_AI_AGENT=false .venv/bin/python scripts/replay_mcp_context.py
   ```
   Capture the 3 proposed outputs.

2. If `USE_AI_AGENT=true` is set in Railway (check `.env` or ask),
   run a second pass with AI enabled by temporarily setting the env var:
   ```
   USE_AI_AGENT=true ANTHROPIC_API_KEY=<key> .venv/bin/python scripts/replay_mcp_context.py
   ```
   Capture the 3 proposed outputs. Note any variance.

3. Run the test suite and capture pass rate:
   ```
   cd backend && .venv/bin/pytest -q 2>&1 | tail -3
   ```

4. Read `COMPARISON_REPORT.md` to understand current content.

5. Update the following sections in `COMPARISON_REPORT.md`:
   - **Test pass rate table** — update passing count
   - **Output variance table** — fill in actual proposed categories
     and whether they were identical across runs
   - **Agent iteration count** — confirm still 1
   - If AI mode was run: add or update an **AI mode** subsection
     under "Output variance" with the 3 AI outputs and note any
     variance (real models are non-deterministic even at temp=0)

6. Update `mcp_interaction_log.jsonl` — the replay script appends
   automatically; no manual step needed.

## Notes

- Stub mode variance should always be 0 — if not, investigate
- AI mode at temperature=0 is mostly stable but not guaranteed
  identical; document any diff
- Do NOT rewrite the report from scratch — patch only the
  data sections that changed
- Keep line length under ~80 characters in the report
