---
name: expense-aggregator-gen
description: >
  Given a time boundary and optional category filter, generate an
  aggregation function, edge-case unit tests, and a sample data fixture.
  Use when adding a new summary or reporting view for expenses.
argument-hint: "[daily|weekly|monthly] [category filter — optional]"
---

DO NOT write any files. Output the code as markdown code blocks
for the developer to review before applying.

Given a time boundary and optional category filter, generate:
1. An aggregation function in `backend/app/handlers/`
2. Edge-case unit tests in `backend/tests/`
3. A sample data fixture for use in tests

## Steps

1. Read `backend/app/handlers/summary.py` to understand the existing
   aggregation pattern and `format_amount` helper
2. Read `backend/tests/test_expenses.py` and
   `backend/tests/test_integration.py` to match the existing test style
3. Based on `$ARGUMENTS`, determine:
   - **Time boundary:** daily | weekly (default) | monthly | custom range
   - **Grouping:** by category (default) | by day | by both
   - **Filter:** specific category, or all (default)
4. Generate the aggregation function — add it to `summary.py`
   if it fits naturally, or create a new file if it's a distinct concern
5. Generate edge-case unit tests covering:
   - Empty result set
   - Single expense
   - Multiple expenses in same category (should sum correctly)
   - Multiple categories sorted by total descending
   - Amounts with decimals
   - Boundary dates (first and last day of period)
6. Generate a sample data fixture as a plain list of dicts
   matching the `expenses` table schema:
   `[{"amount": "5000", "category": "comida", "note": "...",
   "date": "..."}]`
   Save it to `backend/tests/fixtures/expenses.py`

## Output contract

- Aggregation function must accept `(user: dict, ...)` and return a str
- Use `format_amount` from `summary.py` for all currency formatting
- Tests must use `@pytest.mark.parametrize` where multiple cases apply
- No external calls in unit tests — mock `client` where needed
- Fixture data must cover at least 3 categories and 2 weeks of dates

## Rules

- **Line length:** break long lines at natural clause or sentence
  boundaries. Prefer multiple short lines over one long line.
  Aim for ~80 characters max.
- Follow existing code style — no docstrings, no type annotations on
  variables, no comments unless logic is non-obvious
- Do not add features beyond what the time boundary + filter requires
- If `$ARGUMENTS` is empty, default to weekly aggregation by category
  (mirrors the existing `get_week_summary`)
