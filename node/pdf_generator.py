# =============================================
# AEROLÍNEAS RAFAEL PABON
# pdf_generator.py — Generación de tarjeta de embarque en PDF
#
# Utiliza reportlab para crear un PDF con:
#   - Encabezado con logo textual de la aerolínea
#   - Datos del vuelo (origen, destino, fecha, horarios)
#   - Datos del pasajero (nombre, pasaporte)
#   - Clase y número de asiento
#   - Precio y estado del asiento
#   - Información de nodo y reloj vectorial (para contexto distribuido)
# =============================================

import io
from datetime import datetime

from reportlab.lib.pagesizes import A6, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ─────────────────────────────────────────
# PALETA DE COLORES
# ─────────────────────────────────────────

COLOR_PRIMARY   = colors.HexColor("#1A3A5C")   # Azul oscuro corporativo
COLOR_ACCENT    = colors.HexColor("#E8A020")   # Dorado para detalles
COLOR_LIGHT_BG  = colors.HexColor("#F0F4F8")   # Fondo secciones
COLOR_WHITE     = colors.white
COLOR_TEXT      = colors.HexColor("#2C3E50")


def generate_boarding_pass(
    vuelo:    dict,
    asiento:  dict,
    pasajero: dict | None,
    nodo_id:  int,
) -> bytes:
    """
    Genera un PDF de tarjeta de embarque y retorna los bytes.

    Args:
        vuelo:    dict con vuelo_id, origen, destino, fecha, hora_salida, hora_llegada,
                  aeronave, ciudad_origen, ciudad_destino
        asiento:  dict con numero_asiento, clase, estado, precio
        pasajero: dict con nombre, pasaporte, email — puede ser None
        nodo_id:  ID del nodo que emite el boarding pass (1, 2 o 3)

    Returns:
        bytes del PDF generado.
    """
    buffer = io.BytesIO()

    # Tarjeta A6 apaisada (~148 × 105 mm)
    doc = SimpleDocTemplate(
        buffer,
        pagesize  = landscape(A6),
        leftMargin  = 10*mm,
        rightMargin = 10*mm,
        topMargin   = 8*mm,
        bottomMargin = 8*mm,
    )

    styles   = getSampleStyleSheet()
    elements = []

    # ── Estilos personalizados ──
    style_title = ParagraphStyle(
        "title",
        parent    = styles["Normal"],
        fontSize  = 14,
        textColor = COLOR_WHITE,
        alignment = TA_CENTER,
        fontName  = "Helvetica-Bold",
        spaceAfter = 2,
    )
    style_subtitle = ParagraphStyle(
        "subtitle",
        parent    = styles["Normal"],
        fontSize  = 7,
        textColor = COLOR_WHITE,
        alignment = TA_CENTER,
        fontName  = "Helvetica",
    )
    style_label = ParagraphStyle(
        "label",
        parent    = styles["Normal"],
        fontSize  = 6,
        textColor = COLOR_PRIMARY,
        fontName  = "Helvetica-Bold",
        spaceAfter = 1,
    )
    style_value = ParagraphStyle(
        "value",
        parent    = styles["Normal"],
        fontSize  = 9,
        textColor = COLOR_TEXT,
        fontName  = "Helvetica-Bold",
    )
    style_small = ParagraphStyle(
        "small",
        parent    = styles["Normal"],
        fontSize  = 6,
        textColor = colors.grey,
        fontName  = "Helvetica",
        alignment = TA_CENTER,
    )

    # ── ENCABEZADO (fondo azul) ──
    header_data = [[
        Paragraph("✈  AEROLÍNEAS RAFAEL PABÓN", style_title),
        Paragraph(f"TARJETA DE EMBARQUE  |  Nodo {nodo_id}", style_subtitle),
    ]]
    header_table = Table(header_data, colWidths=[120*mm, None])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_PRIMARY),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("SPAN",       (0, 0), (-1, 0)),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3*mm))

    # ── RUTA: ORIGEN ✈ DESTINO ──
    ciudad_orig = vuelo.get("ciudad_origen",  vuelo.get("origen",  "?"))
    ciudad_dest = vuelo.get("ciudad_destino", vuelo.get("destino", "?"))
    cod_orig    = vuelo.get("origen",  "???")
    cod_dest    = vuelo.get("destino", "???")

    route_data = [[
        Paragraph(f'<font size="18"><b>{cod_orig}</b></font>', ParagraphStyle(
            "big", parent=styles["Normal"], fontSize=18, textColor=COLOR_PRIMARY,
            fontName="Helvetica-Bold", alignment=TA_CENTER)),
        Paragraph(f'<font size="14" color="#E8A020">✈</font>', ParagraphStyle(
            "arrow", parent=styles["Normal"], fontSize=14, textColor=COLOR_ACCENT,
            alignment=TA_CENTER)),
        Paragraph(f'<font size="18"><b>{cod_dest}</b></font>', ParagraphStyle(
            "big2", parent=styles["Normal"], fontSize=18, textColor=COLOR_PRIMARY,
            fontName="Helvetica-Bold", alignment=TA_CENTER)),
    ]]
    route_table = Table(route_data, colWidths=[40*mm, 20*mm, 40*mm])
    route_table.setStyle(TableStyle([
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(route_table)

    sub_data = [[
        Paragraph(ciudad_orig, ParagraphStyle("c1", parent=styles["Normal"],
            fontSize=7, textColor=colors.grey, alignment=TA_CENTER)),
        Paragraph("",     ParagraphStyle("c2", parent=styles["Normal"])),
        Paragraph(ciudad_dest, ParagraphStyle("c3", parent=styles["Normal"],
            fontSize=7, textColor=colors.grey, alignment=TA_CENTER)),
    ]]
    sub_table = Table(sub_data, colWidths=[40*mm, 20*mm, 40*mm])
    elements.append(sub_table)
    elements.append(Spacer(1, 2*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_ACCENT))
    elements.append(Spacer(1, 2*mm))

    # ── DATOS VUELO + PASAJERO (tabla de 2 columnas) ──
    pasajero_nombre = (pasajero or {}).get("nombre",    "—")
    pasajero_doc    = (pasajero or {}).get("pasaporte", "—")
    fecha_str       = vuelo.get("fecha",        "—")
    hora_sal        = vuelo.get("hora_salida",  "—")
    hora_lleg       = vuelo.get("hora_llegada", "—")
    aeronave        = vuelo.get("aeronave",     "—")
    vuelo_id        = vuelo.get("vuelo_id",     "—")
    clase           = asiento.get("clase",           "—").capitalize()
    num_asiento     = asiento.get("numero_asiento",  "—")
    precio          = asiento.get("precio",          0)

    def lbl(txt):
        return Paragraph(txt, style_label)

    def val(txt):
        return Paragraph(str(txt), style_value)

    info_data = [
        [lbl("VUELO"),         val(vuelo_id),    lbl("PASAJERO"),    val(pasajero_nombre)],
        [lbl("FECHA"),         val(fecha_str),   lbl("PASAPORTE"),   val(pasajero_doc)],
        [lbl("SALIDA"),        val(hora_sal),    lbl("CLASE"),       val(clase)],
        [lbl("LLEGADA"),       val(hora_lleg),   lbl("ASIENTO"),     val(num_asiento)],
        [lbl("AERONAVE"),      val(aeronave),    lbl("PRECIO"),      val(f"USD {precio:.2f}")],
    ]

    info_table = Table(info_data, colWidths=[22*mm, 40*mm, 22*mm, 44*mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
        ("ALIGN",  (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.lightgrey),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_PRIMARY),
        ("LINEAFTER", (1, 0), (1, -1), 0.5, COLOR_ACCENT),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 2*mm))

    # ── PIE DE PÁGINA ──
    emitido = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    elements.append(Paragraph(
        f"Emitido: {emitido}  |  Sistema distribuido ARLP — Nodo {nodo_id}  |  "
        "Por favor, presente este documento en la puerta de embarque.",
        style_small,
    ))

    doc.build(elements)
    return buffer.getvalue()
