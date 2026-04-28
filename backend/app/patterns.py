"""
All compiled regex patterns used by the router.

Add a new pattern here when adding a new WhatsApp command, then
reference it in router.route() and (if AI dispatch is needed) in
dispatch._dispatch().
"""
import re

_DECIMAL_RE = re.compile(r'[.,]\d{1,2}$')

BATCH_EXPENSE_PATTERN = re.compile(
    r"^(?:gast[eé]|pagu[eé])\s+([\d.,]+)\s+en\s+(?:el\s+)?s[uú]per(?:mercado)?[:\s]+(.+)$",
    re.IGNORECASE,
)
EXPENSE_PATTERN = re.compile(
    r'^gast[eé]\s+([\d.,]+)\s+(?:en\s+)?(.+)$',
    re.IGNORECASE,
)
AMBIGUOUS_EXPENSE_PATTERN = re.compile(
    r'^pagu[eé]\s+([\d.,]+)(?:\s+(?:en\s+)?(.+))?$',
    re.IGNORECASE,
)
SUMMARY_PATTERN = re.compile(r'^resumen(?:\s+.*)?$', re.IGNORECASE)

BUDGET_SET_PATTERN = re.compile(r'^presupuesto[:\s]+([\d.,]+)$', re.IGNORECASE)

TODO_ADD_PATTERN = re.compile(r'^(?:pendiente|tarea)[:\s]+(.+)$', re.IGNORECASE)
TODO_LIST_PATTERN = re.compile(r'^mis?\s+pendientes?$', re.IGNORECASE)
TODO_DONE_PATTERN = re.compile(r'^(?:listo|hice|complet[eé])[:\s]+(.+)$', re.IGNORECASE)
TODO_DELETE_PATTERN = re.compile(r'^borrar\s+pendiente[:\s]+(.+)$', re.IGNORECASE)

NECESITO_COMPRAR_PATTERN = re.compile(r'^necesito\s+comprar\s+(.+)$', re.IGNORECASE)
SHOPPING_ADD_PATTERN = re.compile(r'^(?:comprar|necesito)[:\s]+(.+)$', re.IGNORECASE)
SHOPPING_LIST_PATTERN = re.compile(r'^(?:lista\s+de\s+)?compras?$', re.IGNORECASE)
PANTRY_RESTOCK_PATTERN = re.compile(r'^compr[eé][:\s]+(.+?)(?:\s+(\d+))?$', re.IGNORECASE)

WAITING_ADD_PATTERN = re.compile(r'^esperando[:\s]+(.+)$', re.IGNORECASE)
WAITING_LIST_PATTERN = re.compile(
    r'^(?:mis?\s+esperas?|qué\s+espero|que\s+espero|ver\s+esperas?)$', re.IGNORECASE,
)
WAITING_RESOLVE_PATTERN = re.compile(r'^lleg[oó][:\s]+(.+)$', re.IGNORECASE)

PANTRY_ADD_PATTERN = re.compile(
    r'^despensa(?:\s+(cocina|baño|otros))?[:\s]+(.+?)\s+(\d+)$',
    re.IGNORECASE,
)
PANTRY_LIST_PATTERN = re.compile(r'^mi\s+despensa$', re.IGNORECASE)
PANTRY_SET_STOCK_PATTERN = re.compile(r'^stock\s+(\d+)\s+(.+)$', re.IGNORECASE)
PANTRY_SET_STOCK_QTY_LAST_PATTERN = re.compile(r'^stock\s+(.+?)\s+(\d+)$', re.IGNORECASE)
PANTRY_CONSUME_PATTERN = re.compile(r'^us[eé][:\s]+(.+)$', re.IGNORECASE)
PANTRY_RESTOCK_ALL_PATTERN = re.compile(r'^compr[eé]\s+todo$', re.IGNORECASE)

CONFIRM_PATTERN = re.compile(r'^confirmar$', re.IGNORECASE)
CANCEL_PATTERN = re.compile(r'^cancelar$', re.IGNORECASE)
CONFIRM_SHORTCUT_PATTERN = re.compile(r'^(?:s[ií]|ok|dale|va|listo)$', re.IGNORECASE)
CANCEL_SHORTCUT_PATTERN = re.compile(r'^(?:no|nope|olvídalo|olvidalo)$', re.IGNORECASE)

HELP_PATTERN = re.compile(r'^ayuda\b', re.IGNORECASE)
TABLERO_PATTERN = re.compile(r'^(?:mi\s+)?tablero$', re.IGNORECASE)
ME_LLAMO_PATTERN = re.compile(r'^me\s+llamo\s+(.+)$', re.IGNORECASE)

RECIPE_NEW_PATTERN = re.compile(r'^nueva\s+receta[:\s]+(.+)$', re.IGNORECASE)
RECIPE_LIST_PATTERN = re.compile(r'^mis?\s+recetas?$', re.IGNORECASE)
RECIPE_SHOW_PATTERN = re.compile(r'^receta[:\s]+(.+)$', re.IGNORECASE)
RECIPE_MATCH_PATTERN = re.compile(r'^(?:qué|que)\s+puedo\s+hacer\??$', re.IGNORECASE)
RECIPE_SUGGEST_PATTERN = re.compile(
    r'^(?:(?:qué|que)\s+cocino|sugiéreme\s+recetas?|sugierme\s+recetas?)\??$',
    re.IGNORECASE,
)
RECIPE_CHOOSE_PATTERN = re.compile(r'^elegir\s+(\d+)$', re.IGNORECASE)
