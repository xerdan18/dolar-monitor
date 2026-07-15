# Monitor del dólar — Argentina

Dashboard de cotizaciones del dólar (oficial, blue, MEP, CCL, mayorista,
cripto y tarjeta) que **se actualiza solo todos los días** y publica los
resultados como página web — sin servidores, sin costo de infraestructura.

**🔗 Dashboard en vivo:** https://xerdan18.github.io/dolar-monitor/

## Cómo funciona

```
GitHub Actions (todos los días, 18:30 hora argentina)
        │
        ▼
  fetch.py      → consulta la API pública de dolarapi.com
        │         y acumula el histórico diario en data/history.csv
        ▼
  dashboard.py  → regenera docs/index.html: cotizaciones del día,
        │         variación contra la corrida anterior y gráfico
        ▼         de evolución (SVG, sin dependencias externas)
  GitHub Pages  → publica el dashboard actualizado
```

El dashboard incluye:

- **Tarjetas** con el valor de venta del día, compra y variación contra la
  corrida anterior, para las 7 cotizaciones.
- **Gráfico de evolución** de las 4 cotizaciones principales, con tooltip
  interactivo al pasar el mouse. Se completa solo con cada corrida diaria.
- **Tabla completa** del día. Modo claro y oscuro automáticos.

## Correrlo localmente

```bash
pip install -r requirements.txt
python main.py           # genera docs/index.html con los datos del día
```

## Por qué importa este diseño

Este proyecto demuestra el patrón de **monitoreo continuo**: un dato que se
mueve (precios, cotizaciones, stock, publicaciones) capturado a diario de
forma automática, con histórico acumulado y visualización siempre al día.
El mismo esquema aplica a precios de competidores, catálogos de e-commerce,
listados inmobiliarios o cualquier fuente que cambie con el tiempo.

- Extracción, histórico y presentación separados (`fetch.py`, `data/`,
  `dashboard.py`) — cambiar la fuente de datos no toca el resto.
- Cero infraestructura: GitHub Actions ejecuta, GitHub Pages publica.
- Re-ejecutar el mismo día no duplica datos (corridas idempotentes).
