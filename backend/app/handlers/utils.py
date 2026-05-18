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

  parse_clp_amount(raw) -> float | None
    Parses a CLP amount string (dots as thousand separators).
    Returns None if the string contains a decimal point, which
    indicates a non-integer amount that shouldn't be treated as CLP.
"""
import unicodedata
from app.patterns import _DECIMAL_RE


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def find_first_substring(rows: list[dict], fragment: str, field: str) -> dict | None:
    needle = fragment.lower()
    return next((r for r in rows if r.get(field) and needle in r[field].lower()), None)


def parse_clp_amount(raw: str) -> float | None:
    if _DECIMAL_RE.search(raw):
        return None
    try:
        return float(raw.replace(".", "").replace(",", ""))
    except (ValueError, TypeError):
        return None
