Create an entry in `agent_log.txt` documenting a recent AI suggestion and the decision made about it.

## Steps

1. Run `git diff HEAD` and `git status` to see what changed recently (if anything)
2. Read `agent_log.txt` to understand the existing format and avoid duplicates
3. Based on the recent conversation and/or changes, identify:
   - What Claude Code suggested
   - Whether it was **Accepted**, **Modified**, or **Rejected**
   - The rationale behind the decision
4. Append a new entry to `agent_log.txt` using exactly this format:

```
## YYYY-MM-DD — <short topic, e.g. "Expense handler structure">

**Suggested:** <what Claude Code proposed — be specific, 1-2 sentences>
**Decision:** Accepted | Modified | Rejected
**Rationale:** <why — focus on the non-obvious reasoning, 1-3 sentences>

---
```

## Rules

- If `$ARGUMENTS` were provided, use them as the topic/context hint
- Keep each field concise — this is a log, not an essay
- One entry per invocation — don't batch multiple decisions into one entry
- Only log decisions with actual rationale — skip trivial formatting or typo fixes
- Date format: YYYY-MM-DD
- Append at the **bottom** of the file, after the last `---`
- **Line length:** break long lines at natural clause or sentence boundaries.
  Prefer multiple short lines over one long line. Aim for ~80 characters max per line.
