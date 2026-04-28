"""
Public handler API — one import per feature.

Agents working on a new handler can read this file to understand the
full surface area without opening every module.

DINERO
  expenses.py   : save_expense, expense_history, map_category, normalize
  budget.py     : set_budget
  summary.py    : get_week_summary, aggregate_by_category, format_amount
  expense_batch : handle_batch_create, handle_batch_confirm, handle_batch_cancel

TIEMPO
  todos.py      : add_todo, list_todos, complete_todo, delete_todo
  waiting_on.py : add_waiting, list_waiting, resolve_waiting

COMIDA
  pantry.py           : add_pantry_item, list_pantry, consume_pantry_item,
                        restock_pantry_item, set_pantry_stock, restock_all_pantry
  pantry_shopping.py  : handle_pantry_add_create, handle_pantry_add_confirm_despensa,
                        handle_pantry_add_confirm_lista, handle_pantry_add_cancel
  shopping.py         : add_to_shopping, add_many_to_shopping, list_shopping, check_item
  recipes.py          : nueva_receta, confirm_recipe_create, cancel_recipe_create,
                        list_recipes, show_recipe, que_puedo_hacer,
                        sugerir_recetas, elegir_receta,
                        confirm_shopping_add, cancel_shopping_add

SHARED
  utils.py      : find_first_substring
"""
from app.handlers.expenses import save_expense, expense_history, map_category, normalize
from app.handlers.budget import set_budget
from app.handlers.summary import get_week_summary, aggregate_by_category, format_amount
from app.handlers.expense_batch import handle_batch_create, handle_batch_confirm, handle_batch_cancel
from app.handlers.todos import add_todo, list_todos, complete_todo, delete_todo
from app.handlers.waiting_on import add_waiting, list_waiting, resolve_waiting
from app.handlers.pantry import (
    add_pantry_item, list_pantry, consume_pantry_item,
    restock_pantry_item, set_pantry_stock, restock_all_pantry,
)
from app.handlers.pantry_shopping import (
    handle_pantry_add_create, handle_pantry_add_confirm_despensa,
    handle_pantry_add_confirm_lista, handle_pantry_add_cancel,
)
from app.handlers.shopping import add_to_shopping, add_many_to_shopping, list_shopping, check_item
from app.handlers.recipes import (
    nueva_receta, confirm_recipe_create, cancel_recipe_create,
    list_recipes, show_recipe, que_puedo_hacer,
    sugerir_recetas, elegir_receta,
    confirm_shopping_add, cancel_shopping_add,
)
from app.handlers.utils import find_first_substring

__all__ = [
    "save_expense", "expense_history", "map_category", "normalize",
    "set_budget",
    "get_week_summary", "aggregate_by_category", "format_amount",
    "handle_batch_create", "handle_batch_confirm", "handle_batch_cancel",
    "add_todo", "list_todos", "complete_todo", "delete_todo",
    "add_waiting", "list_waiting", "resolve_waiting",
    "add_pantry_item", "list_pantry", "consume_pantry_item",
    "restock_pantry_item", "set_pantry_stock", "restock_all_pantry",
    "handle_pantry_add_create", "handle_pantry_add_confirm_despensa",
    "handle_pantry_add_confirm_lista", "handle_pantry_add_cancel",
    "add_to_shopping", "add_many_to_shopping", "list_shopping", "check_item",
    "nueva_receta", "confirm_recipe_create", "cancel_recipe_create",
    "list_recipes", "show_recipe", "que_puedo_hacer",
    "sugerir_recetas", "elegir_receta",
    "confirm_shopping_add", "cancel_shopping_add",
    "find_first_substring",
]
