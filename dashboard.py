"""Genera docs/index.html: dashboard estático con las cotizaciones del día,
variación contra la corrida anterior y evolución histórica en un gráfico de
líneas SVG. Sin dependencias de JavaScript externas — todo inline, apto para
GitHub Pages.
"""

import json
from pathlib import Path

from fetch import load_history

OUTPUT = Path(__file__).parent / "docs" / "index.html"

# Series del gráfico (máx. 4 para que se lea) y paleta categórica validada
CHART_CASAS = ["oficial", "blue", "bolsa", "tarjeta"]
SERIES_COLORS = {  # (claro, oscuro)
    "oficial": ("#2a78d6", "#3987e5"),
    "blue": ("#1baf7a", "#199e70"),
    "bolsa": ("#eda100", "#c98500"),
    "tarjeta": ("#008300", "#008300"),
}

# Geometría del gráfico
W, H = 920, 340
M_LEFT, M_RIGHT, M_TOP, M_BOTTOM = 64, 120, 16, 36


def fmt(value: float, decimals: int = 2) -> str:
    """Formato argentino: 1.562,61"""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "@").replace(".", ",").replace("@", ".")


def fmt_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}/{m}"


def build_series(history: list[dict]) -> tuple[list[str], dict]:
    dates = sorted({r["date"] for r in history})
    series = {}
    for casa in CHART_CASAS:
        by_date = {r["date"]: float(r["venta"]) for r in history if r["casa"] == casa}
        points = [by_date.get(d) for d in dates]
        if any(v is not None for v in points):
            nombre = next(r["nombre"] for r in history if r["casa"] == casa)
            series[casa] = {"nombre": nombre, "values": points}
    return dates, series


def nice_ticks(lo: float, hi: float, count: int = 5) -> list[float]:
    span = (hi - lo) or 1
    raw = span / (count - 1)
    mag = 10 ** len(str(int(raw))) / 10
    step = max(round(raw / mag) * mag, mag)
    start = int(lo / step) * step
    ticks = []
    t = start
    while t <= hi + step:
        if t >= lo - step / 2:
            ticks.append(t)
        t += step
    return ticks


def svg_chart(dates: list[str], series: dict) -> str:
    values = [v for s in series.values() for v in s["values"] if v is not None]
    lo, hi = min(values) * 0.995, max(values) * 1.005
    ticks = nice_ticks(lo, hi)
    lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])
    plot_w = W - M_LEFT - M_RIGHT
    plot_h = H - M_TOP - M_BOTTOM

    def x(i: int) -> float:
        if len(dates) == 1:
            return M_LEFT + plot_w / 2
        return M_LEFT + plot_w * i / (len(dates) - 1)

    def y(v: float) -> float:
        return M_TOP + plot_h * (1 - (v - lo) / (hi - lo))

    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" '
             f'aria-label="Evolución de la cotización de venta">']
    for t in ticks:
        parts.append(f'<line x1="{M_LEFT}" y1="{y(t):.1f}" x2="{W - M_RIGHT}" '
                     f'y2="{y(t):.1f}" class="grid"/>')
        parts.append(f'<text x="{M_LEFT - 8}" y="{y(t):.1f}" class="tick" '
                     f'text-anchor="end" dy="0.32em">${fmt(t, 0)}</text>')
    for i, d in enumerate(dates):
        parts.append(f'<text x="{x(i):.1f}" y="{H - M_BOTTOM + 20}" class="tick" '
                     f'text-anchor="middle">{fmt_date(d)}</text>')
    labels = []
    for casa, s in series.items():
        pts = [(x(i), y(v)) for i, v in enumerate(s["values"]) if v is not None]
        color = f"var(--c-{casa})"
        if len(pts) > 1:
            path = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
            parts.append(f'<polyline points="{path}" fill="none" '
                         f'stroke="{color}" stroke-width="2"/>')
        for px, py in pts:
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" '
                         f'fill="{color}" stroke="var(--surface-1)" '
                         f'stroke-width="2"/>')
        labels.append([pts[-1][0], pts[-1][1], color, s["nombre"]])

    # separar etiquetas que quedarían superpuestas (mín. 16px entre sí)
    labels.sort(key=lambda l: l[1])
    for i in range(1, len(labels)):
        if labels[i][1] - labels[i - 1][1] < 16:
            labels[i][1] = labels[i - 1][1] + 16
    for lx, ly, color, nombre in labels:
        parts.append(f'<rect x="{lx + 10}" y="{ly - 5}" width="10" height="10" '
                     f'rx="2" fill="{color}"/>')
        parts.append(f'<text x="{lx + 25}" y="{ly}" class="label" '
                     f'dy="0.32em">{nombre}</text>')
    parts.append(f'<line id="crosshair" x1="0" y1="{M_TOP}" x2="0" '
                 f'y2="{H - M_BOTTOM}" class="crosshair" visibility="hidden"/>')
    parts.append("</svg>")
    return "".join(parts)


def render(history: list[dict], today: str) -> str:
    dates, series = build_series(history)
    latest = {r["casa"]: r for r in history if r["date"] == dates[-1]}
    prev_date = dates[-2] if len(dates) > 1 else None
    prev = {r["casa"]: r for r in history if r["date"] == prev_date}

    tiles = []
    for casa, row in latest.items():
        venta = float(row["venta"])
        delta_html = '<span class="delta">— sin corrida previa</span>'
        if casa in prev:
            d = venta - float(prev[casa]["venta"])
            pct = d / float(prev[casa]["venta"]) * 100
            arrow = "▲" if d > 0 else ("▼" if d < 0 else "=")
            sign = "+" if d > 0 else ""
            delta_html = (f'<span class="delta">{arrow} {sign}{fmt(d)} '
                          f'({sign}{fmt(pct)}%) vs {fmt_date(prev_date)}</span>')
        tiles.append(f"""
      <div class="tile">
        <h3>{row['nombre']}</h3>
        <p class="value">${fmt(venta)}</p>
        <p class="sub">Compra: ${fmt(float(row['compra']))}</p>
        {delta_html}
      </div>""")

    table_rows = "".join(
        f"<tr><td>{r['nombre']}</td><td>${fmt(float(r['compra']))}</td>"
        f"<td>${fmt(float(r['venta']))}</td></tr>"
        for r in latest.values()
    )

    chart_data = {
        "dates": dates,
        "geom": {"w": W, "left": M_LEFT, "right": M_RIGHT},
        "series": [
            {"nombre": s["nombre"], "casa": casa, "values": s["values"]}
            for casa, s in series.items()
        ],
    }

    legend = "".join(
        f'<span class="chip"><span class="swatch" '
        f'style="background:var(--c-{casa})"></span>{s["nombre"]}</span>'
        for casa, s in series.items()
    )

    single_note = ("<p class='note'>El gráfico se completa automáticamente con "
                   "cada corrida diaria.</p>" if len(dates) < 3 else "")

    light_colors = "".join(f"--c-{c}: {v[0]};" for c, v in SERIES_COLORS.items())
    dark_colors = "".join(f"--c-{c}: {v[1]};" for c, v in SERIES_COLORS.items())

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitor del dólar — Argentina</title>
<style>
  :root {{
    color-scheme: light;
    --page: #f9f9f7; --surface-1: #fcfcfb;
    --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
    --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
    {light_colors}
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      color-scheme: dark;
      --page: #0d0d0d; --surface-1: #1a1a19;
      --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
      --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
      {dark_colors}
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{
    background: var(--page); color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 32px 20px; max-width: 1000px; margin: 0 auto;
  }}
  header h1 {{ font-size: 1.5rem; }}
  header p {{ color: var(--ink-2); margin-top: 4px; }}
  .tiles {{
    display: grid; gap: 12px; margin: 24px 0;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }}
  .tile {{
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 12px; padding: 16px;
  }}
  .tile h3 {{ font-size: 0.85rem; font-weight: 600; color: var(--ink-2); }}
  .tile .value {{ font-size: 1.6rem; font-weight: 700; margin: 6px 0 2px; }}
  .tile .sub {{ font-size: 0.8rem; color: var(--muted); }}
  .tile .delta {{ font-size: 0.8rem; color: var(--ink-2); display: block;
                  margin-top: 8px; }}
  .card {{
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px; margin-bottom: 24px;
    position: relative;
  }}
  .card h2 {{ font-size: 1.05rem; margin-bottom: 12px; }}
  .legend {{ display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 8px; }}
  .chip {{ font-size: 0.8rem; color: var(--ink-2); display: inline-flex;
           align-items: center; gap: 6px; }}
  .swatch {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; }}
  svg {{ width: 100%; height: auto; display: block; }}
  svg .grid {{ stroke: var(--grid); stroke-width: 1; }}
  svg .tick {{ fill: var(--muted); font-size: 12px;
               font-variant-numeric: tabular-nums; }}
  svg .label {{ fill: var(--ink); font-size: 12px; font-weight: 600; }}
  svg .crosshair {{ stroke: var(--muted); stroke-dasharray: 3 3; }}
  .note {{ color: var(--muted); font-size: 0.8rem; margin-top: 8px; }}
  #tooltip {{
    position: absolute; pointer-events: none; visibility: hidden;
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 12px; font-size: 0.8rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10;
  }}
  #tooltip strong {{ display: block; margin-bottom: 4px; }}
  #tooltip .row {{ display: flex; align-items: center; gap: 6px;
                   color: var(--ink-2); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th, td {{ text-align: left; padding: 8px 12px;
            border-bottom: 1px solid var(--grid); }}
  td:nth-child(n+2), th:nth-child(n+2) {{ text-align: right;
            font-variant-numeric: tabular-nums; }}
  th {{ color: var(--ink-2); font-weight: 600; font-size: 0.8rem; }}
  footer {{ color: var(--muted); font-size: 0.8rem; text-align: center;
            margin-top: 8px; }}
  footer a {{ color: inherit; }}
</style>
</head>
<body>
<header>
  <h1>Monitor del dólar — Argentina</h1>
  <p>Última actualización: {fmt_date(today)}/{today[:4]} · Se actualiza solo,
     todos los días</p>
</header>

<section class="tiles">{"".join(tiles)}
</section>

<section class="card">
  <h2>Evolución — precio de venta</h2>
  <div class="legend">{legend}</div>
  {svg_chart(dates, series)}
  <div id="tooltip"></div>
  {single_note}
</section>

<section class="card">
  <h2>Todas las cotizaciones de hoy</h2>
  <table>
    <thead><tr><th>Cotización</th><th>Compra</th><th>Venta</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table>
</section>

<footer>
  Datos: <a href="https://dolarapi.com">dolarapi.com</a> · Actualizado a diario
  con GitHub Actions · Hecho por
  <a href="https://github.com/xerdan18">Bruno (xerdan18)</a>
</footer>

<script>
const DATA = {json.dumps(chart_data, ensure_ascii=False)};
const svg = document.querySelector("svg");
const cross = document.getElementById("crosshair");
const tip = document.getElementById("tooltip");
const card = tip.parentElement;
const fmtAr = v => "$" + v.toLocaleString("es-AR",
  {{minimumFractionDigits: 2, maximumFractionDigits: 2}});

svg.addEventListener("mousemove", ev => {{
  const rect = svg.getBoundingClientRect();
  const scale = DATA.geom.w / rect.width;
  const mx = (ev.clientX - rect.left) * scale;
  const plotW = DATA.geom.w - DATA.geom.left - DATA.geom.right;
  const n = DATA.dates.length;
  const i = n === 1 ? 0 : Math.max(0, Math.min(n - 1,
    Math.round((mx - DATA.geom.left) / plotW * (n - 1))));
  const cx = n === 1 ? DATA.geom.left + plotW / 2
                     : DATA.geom.left + plotW * i / (n - 1);
  cross.setAttribute("x1", cx); cross.setAttribute("x2", cx);
  cross.setAttribute("visibility", "visible");
  const [y, m, d] = DATA.dates[i].split("-");
  tip.innerHTML = "<strong>" + d + "/" + m + "/" + y + "</strong>" +
    DATA.series.map(s => s.values[i] == null ? "" :
      '<div class="row"><span class="swatch" style="background:var(--c-' +
      s.casa + ')"></span>' + s.nombre + ": " + fmtAr(s.values[i]) + "</div>"
    ).join("");
  const cardRect = card.getBoundingClientRect();
  let left = ev.clientX - cardRect.left + 16;
  if (left + 180 > cardRect.width) left -= 200;
  tip.style.left = left + "px";
  tip.style.top = (ev.clientY - cardRect.top + 8) + "px";
  tip.style.visibility = "visible";
}});
svg.addEventListener("mouseleave", () => {{
  cross.setAttribute("visibility", "hidden");
  tip.style.visibility = "hidden";
}});
</script>
</body>
</html>
"""


def generate(today: str) -> Path:
    history = load_history()
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(render(history, today), encoding="utf-8")
    return OUTPUT
