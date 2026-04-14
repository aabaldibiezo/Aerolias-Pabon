# =============================================
# AEROLÍNEAS RAFAEL PABON
# utils/seat_renderer.py — Mapa visual del avión en HTML
#
# Genera una tabla HTML con los 174 asientos coloreados
# por estado. Se inyecta con st.markdown(unsafe_allow_html=True).
#
# Layout estándar:
#   Primera  (filas 1-3):   columnas A B C | D        (4 por fila)
#   Business (filas 4-9):   columnas A B C | D E F    (6 por fila)
#   Económica (filas 10-30): columnas A B C | D E F   (6 por fila)
#   El pasillo está entre C y D.
# =============================================

COLORES = {
    "Libre":      "#4CAF50",
    "Reserva":    "#FFC107",
    "Venta":      "#EF5350",
    "Devolucion": "#9E9E9E",
}

TEXTO_COLOR = {
    "Libre":      "#fff",
    "Reserva":    "#333",
    "Venta":      "#fff",
    "Devolucion": "#fff",
}

CSS = """
<style>
.arlp-map-wrap { overflow-x: auto; }
.arlp-map {
    border-collapse: separate;
    border-spacing: 3px;
    font-family: 'Courier New', monospace;
    margin: 0 auto;
}
.arlp-map th {
    width: 34px; text-align: center; font-size: 12px;
    color: #555; padding-bottom: 4px;
}
.arlp-map td.seat {
    width: 34px; height: 30px; text-align: center;
    border-radius: 5px 5px 2px 2px;
    font-size: 9px; font-weight: bold;
    vertical-align: middle; cursor: default;
    border-top: 3px solid rgba(0,0,0,0.2);
}
.arlp-map td.aisle { width: 18px; }
.arlp-map td.row-num {
    width: 24px; text-align: right; color: #999;
    font-size: 10px; padding-right: 4px;
}
.arlp-map tr.class-header td {
    font-size: 10px; font-weight: bold; color: #1B3A6B;
    text-align: center; padding: 6px 0 2px 0;
    letter-spacing: 1px;
}
.arlp-legend { display: flex; gap: 14px; margin: 8px 0 4px 0; flex-wrap: wrap; }
.arlp-legend-item { display: flex; align-items: center; gap: 5px; font-size: 12px; }
.arlp-legend-box {
    width: 16px; height: 16px; border-radius: 3px;
    border-top: 3px solid rgba(0,0,0,0.2);
}
</style>
"""

LEGEND = """
<div class="arlp-legend">
  <div class="arlp-legend-item">
    <div class="arlp-legend-box" style="background:#4CAF50"></div> Libre
  </div>
  <div class="arlp-legend-item">
    <div class="arlp-legend-box" style="background:#FFC107"></div> Reserva
  </div>
  <div class="arlp-legend-item">
    <div class="arlp-legend-box" style="background:#EF5350"></div> Vendido
  </div>
  <div class="arlp-legend-item">
    <div class="arlp-legend-box" style="background:#9E9E9E"></div> Devolución
  </div>
</div>
"""


def render_seat_map(asientos: list[dict], resaltado: str | None = None) -> str:
    """
    Genera el HTML del mapa de asientos del avión.

    Args:
        asientos:  lista de dicts del endpoint GET /flights/{id}/seats
        resaltado: número de asiento a resaltar (ej: '12A'), o None

    Returns:
        String HTML listo para st.markdown(unsafe_allow_html=True)
    """
    # Indexar por número de asiento para acceso O(1)
    idx: dict[str, dict] = {a["numero_asiento"]: a for a in asientos}

    filas_primera   = range(1, 4)       # filas 1-3
    filas_business  = range(4, 10)      # filas 4-9
    filas_eco       = range(10, 31)     # filas 10-30

    html = [CSS, '<div class="arlp-map-wrap">', LEGEND,
            '<table class="arlp-map">']

    # Encabezado de columnas
    html.append(
        "<tr>"
        "<th></th>"
        "<th>A</th><th>B</th><th>C</th>"
        "<th></th>"   # pasillo
        "<th>D</th><th>E</th><th>F</th>"
        "</tr>"
    )

    def seat_td(num: str) -> str:
        a      = idx.get(num)
        estado = a["estado"] if a else "Libre"
        bg     = COLORES.get(estado, "#ccc")
        fg     = TEXTO_COLOR.get(estado, "#fff")
        border = "3px solid #FFD700" if num == resaltado else "none"
        label  = num[:-1]  # solo número de fila, sin letra (la letra está en th)
        return (
            f'<td class="seat" title="{num}" '
            f'style="background:{bg}; color:{fg}; outline:{border};">'
            f'{num}</td>'
        )

    def fila_row(f: int, cols: list[str]) -> str:
        cells = [f'<td class="row-num">{f}</td>']
        for c in ['A', 'B', 'C']:
            num = f"{f}{c}"
            cells.append(seat_td(num) if c in cols else '<td class="seat" style="background:#eee;opacity:.3;"></td>')
        cells.append('<td class="aisle"></td>')
        for c in ['D', 'E', 'F']:
            num = f"{f}{c}"
            cells.append(seat_td(num) if c in cols else '<td class="seat" style="background:#eee;opacity:.3;"></td>')
        return "<tr>" + "".join(cells) + "</tr>"

    # ── Primera clase ──
    html.append('<tr class="class-header"><td></td>'
                '<td colspan="7">✦ PRIMERA CLASE ✦</td></tr>')
    for f in filas_primera:
        html.append(fila_row(f, ['A', 'B', 'C', 'D']))   # sin E ni F

    # ── Business ──
    html.append('<tr class="class-header"><td></td>'
                '<td colspan="7">◆ BUSINESS ◆</td></tr>')
    for f in filas_business:
        html.append(fila_row(f, ['A', 'B', 'C', 'D', 'E', 'F']))

    # ── Económica ──
    html.append('<tr class="class-header"><td></td>'
                '<td colspan="7">· ECONÓMICA ·</td></tr>')
    for f in filas_eco:
        html.append(fila_row(f, ['A', 'B', 'C', 'D', 'E', 'F']))

    html.append("</table></div>")
    return "\n".join(html)


def resumen_disponibilidad(asientos: list[dict]) -> dict:
    """Cuenta asientos por estado. Útil para el header de la página."""
    conteo = {"Libre": 0, "Reserva": 0, "Venta": 0, "Devolucion": 0}
    for a in asientos:
        estado = a.get("estado", "Libre")
        conteo[estado] = conteo.get(estado, 0) + 1
    return conteo
