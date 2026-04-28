"""
Shared handler utilities.

Public API:
  find_first_substring(rows, fragment, field) -> dict | None
    Returns the first row where `fragment` (case-insensitive) is a
    substring of `row[field]`. Returns None if no match.
"""


def find_first_substring(rows: list[dict], fragment: str, field: str) -> dict | None:
    needle = fragment.lower()
    return next((r for r in rows if r.get(field) and needle in r[field].lower()), None)
