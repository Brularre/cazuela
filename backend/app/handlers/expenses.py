"""
Expense handler — DINERO feature.

Public API:
  save_expense(amount, description, user) -> str
    Persists one expense row. Category is auto-detected from the
    description via CATEGORY_KEYWORDS; falls back to 'otros'.

  map_category(description) -> str
    Normalize + keyword-match to one of the fixed category strings.
    Used directly by expense_batch to categorise individual items.

  normalize(text) -> str
    Strip accents and lowercase. Re-exported to other handlers
    (recipes, pantry) for consistent fuzzy matching.
"""
from datetime import date
import unicodedata
from app.db import client

CATEGORY_KEYWORDS = {
    "comida": [
        "almuerzo", "cena", "desayuno", "cafe", "restaurant", "restaurante",
        "supermercado", "verduras", "frutas", "pan", "mercado", "delivery",
        "snack", "pizza", "pollo", "sushi", "comida", "bebida", "despensa",
        "rappi", "pedidosya",
    ],
    "transporte": [
        "uber", "taxi", "metro", "bus", "micro", "gasolina", "bencina",
        "estacionamiento", "peaje", "pasaje", "cabify", "tren", "boleto",
    ],
    "salud": [
        "farmacia", "medico", "doctor", "dentista", "medicamento", "pastilla",
        "consulta", "clinica", "hospital", "remedio", "isapre", "seguro",
    ],
    "hogar": [
        "arriendo", "luz", "agua", "gas", "internet", "limpieza", "ferreteria",
        "mueble", "renta", "condominio", "mantencion", "electrodomestico",
    ],
    "entretenimiento": [
        "cine", "teatro", "concierto", "netflix", "spotify", "juego", "bar",
        "evento", "pelicula", "serie", "suscripcion", "discoteca", "entrada",
    ],
    "ropa": [
        "ropa", "zapatos", "camisa", "pantalon", "vestido", "zapatillas",
        "accesorios", "zara", "falabella",
    ],
    "tecnologia": [
        "computador", "celular", "telefono", "apple", "samsung", "audifonos",
        "teclado", "software", "hosting", "cable",
    ],
    "educacion": [
        "universidad", "curso", "libro", "taller", "colegio", "clases",
        "capacitacion", "certificado",
    ],
    "viajes": [
        "hotel", "vuelo", "avion", "airbnb", "viaje", "turismo", "tour",
    ],
}


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )


def map_category(description: str) -> str:
    normalized = normalize(description)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in normalized for kw in keywords):
            return category
    return "otros"


def save_expense(amount: float, description: str, user: dict) -> str:
    category = map_category(description)

    client.table("expenses").insert({
        "user_id": user["id"],
        "amount": amount,
        "category": category,
        "note": description,
        "date": str(date.today()),
    }).execute()

    formatted = "$" + f"{amount:,.0f}".replace(",", ".")
    return f"✓ Gasto guardado\n{formatted} · {category} · {description}"
