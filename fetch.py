"""Obtiene las cotizaciones del dólar desde dolarapi.com (API pública y
gratuita) y las registra en el histórico diario.
"""

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API_URL = "https://dolarapi.com/v1/dolares"
HISTORY_FILE = Path(__file__).parent / "data" / "history.csv"
FIELDS = ["date", "casa", "nombre", "compra", "venta"]

# Argentina no tiene horario de verano: UTC-3 fijo
AR_TZ = timezone(timedelta(hours=-3))


def fetch_quotes() -> list[dict]:
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    return [
        {
            "casa": q["casa"],
            "nombre": q["nombre"],
            "compra": q["compra"],
            "venta": q["venta"],
        }
        for q in response.json()
    ]


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_run(quotes: list[dict]) -> str:
    """Registra la corrida de hoy (hora argentina). Reemplaza si ya existía."""
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    today = datetime.now(AR_TZ).date().isoformat()
    rows = [r for r in load_history() if r["date"] != today]
    rows.extend({"date": today, **q} for q in quotes)
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return today
