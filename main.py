"""Corrida completa: obtiene cotizaciones, actualiza el histórico y regenera
el dashboard. Es el script que ejecuta GitHub Actions todos los días.
"""

from dashboard import generate
from fetch import append_run, fetch_quotes


def main() -> None:
    quotes = fetch_quotes()
    today = append_run(quotes)
    print(f"{len(quotes)} cotizaciones registradas para {today}")
    output = generate(today)
    print(f"Dashboard generado: {output}")


if __name__ == "__main__":
    main()
