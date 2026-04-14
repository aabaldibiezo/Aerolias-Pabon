# =============================================
# AEROLÍNEAS RAFAEL PABON
# routers/boarding_pass.py — Endpoint de tarjeta de embarque PDF
# =============================================

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from config import cfg
from dependencies import get_repo
from pdf_generator import generate_boarding_pass
from repository.base import BaseRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/boarding-pass", tags=["tarjeta de embarque"])


@router.get("/pdf")
def get_boarding_pass_pdf(
    vuelo_id:       str = Query(..., description="ID del vuelo, ej: RP001"),
    asiento:        str = Query(..., description="Número de asiento, ej: 12A"),
    repo: BaseRepository = Depends(get_repo),
):
    """
    Genera y descarga la tarjeta de embarque en formato PDF.

    Busca el vuelo, el asiento y el pasajero asignado, y genera un PDF
    listo para imprimir con todos los datos de embarque.

    Requiere que el asiento esté en estado 'Venta' o 'Reserva' (no Libre).
    """
    vid = vuelo_id.upper()
    num = asiento.upper()

    # Obtener datos del vuelo
    vuelo = repo.get_flight(vid)
    if not vuelo:
        raise HTTPException(status_code=404, detail=f"Vuelo '{vid}' no encontrado")

    # Obtener datos del asiento
    asiento_data = repo.get_seat(vid, num)
    if not asiento_data:
        raise HTTPException(
            status_code=404,
            detail=f"Asiento '{num}' no encontrado en vuelo '{vid}'"
        )

    if asiento_data.get("estado") not in ("Venta", "Reserva"):
        raise HTTPException(
            status_code=409,
            detail=(
                f"El asiento '{num}' está en estado '{asiento_data.get('estado')}'. "
                "Solo se puede emitir tarjeta de embarque para asientos Venta o Reserva."
            )
        )

    # Obtener datos del pasajero (puede ser None para asientos sin pasajero asignado)
    pasajero = None
    pasaporte = asiento_data.get("pasaporte_pasajero")
    if pasaporte:
        pasajero = repo.get_passenger(pasaporte)

    logger.info(
        "[PDF] Generando boarding pass: vuelo=%s asiento=%s pasajero=%s nodo%d",
        vid, num, pasaporte or "—", cfg.node_id,
    )

    try:
        pdf_bytes = generate_boarding_pass(
            vuelo    = vuelo,
            asiento  = asiento_data,
            pasajero = pasajero,
            nodo_id  = cfg.node_id,
        )
    except Exception as exc:
        logger.error("[PDF] Error generando PDF: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error al generar el PDF: {exc}")

    filename = f"boarding_{vid}_{num}.pdf"

    return Response(
        content      = pdf_bytes,
        media_type   = "application/pdf",
        headers      = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length":      str(len(pdf_bytes)),
        },
    )
