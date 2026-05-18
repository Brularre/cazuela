"""
Shared handler utilities.

Public API:
  normalize(text) -> str
    NFKD decomposition + ASCII encode + lowercase. Canonical form used
    for all fuzzy matching and DB storage of user-supplied text (pantry
    items, recipe ingredients). Single source of truth — do not define
    a local normalize() in individual handlers.

  find_first_substring(rows, fragment, field) -> dict | None
    Returns the first row where `fragment` (case-insensitive) is a
    substring of `row[field]`. Returns None if no match.
"""
import unicodedata


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def find_first_substring(rows: list[dict], fragment: str, field: str) -> dict | None:
    needle = fragment.lower()
    return next((r for r in rows if r.get(field) and needle in r[field].lower()), None)
