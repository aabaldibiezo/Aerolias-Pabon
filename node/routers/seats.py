# =============================================
# AEROLÍNEAS RAFAEL PABON
# routers/seats.py — Endpoints de asientos
#
# Implementa la máquina de estados completa:
#   Libre → Reserva/Venta
#   Reserva → Venta/Devolución
#   Devolución → Libre (solo timer, no expuesto aquí)
# =============================================

import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

import sync_service
from config import cfg
from dependencies import get_clock, get_lamport, get_repo, get_timer
from lamport_clock import LamportClock
from repository.base import BaseRepository
from state_machine import TransicionInvalidaError, EstadoInvalidoError, validate_transition
from timer_service import TimerService
from vector_clock import VectorClock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flights", tags=["asientos"])


# ─────────────────────────────────────────
# MODELOS DE REQUEST / RESPONSE
# ─────────────────────────────────────────

class SeatActionRequest(BaseModel):
    pasaporte: str | None = None   # obligatorio para reservar/vender, opcional para devolver
    nombre:    str | None = None   # se guarda si es nuevo pasajero
    email:     str | None = None
    motivo:    str | None = None   # razón de devolución u observación


class SeatActionResponse(BaseModel):
    ok:              bool
    vuelo_id:        str
    numero_asiento:  str
    estado_nuevo:    str
    reloj_vectorial: str
    mensaje:         str = ""


# ─────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────

@router.get("/{vuelo_id}/seats")
def get_seats(
    vuelo_id: str,
    repo: BaseRepository = Depends(get_repo),
):
    """
    Devuelve todos los asientos de un vuelo para renderizar el mapa.
    Incluye estado y color para el frontend.
    """
    from state_machine import get_estado_color

    vuelo = repo.get_flight(vuelo_id.upper())
    if not vuelo:
        raise HTTPException(status_code=404, detail=f"Vuelo '{vuelo_id}' no encontrado")

    asientos = repo.get_seats(vuelo_id.upper())

    # Agregar color de estado para el mapa visual
    for a in asientos:
        a["color"] = get_estado_color(a["estado"])

    return {"vuelo_id": vuelo_id.upper(), "asientos": asientos}


@router.get("/{vuelo_id}/seats/{numero_asiento}")
def get_seat(
    vuelo_id:       str,
    numero_asiento: str,
    repo: BaseRepository = Depends(get_repo),
):
    """Devuelve el detalle de un asiento específico."""
    asiento = repo.get_seat(vuelo_id.upper(), numero_asiento.upper())
    if not asiento:
        raise HTTPException(
            status_code=404,
            detail=f"Asiento '{numero_asiento}' no encontrado en vuelo '{vuelo_id}'"
        )
    return asiento


@router.post("/{vuelo_id}/seats/{numero_asiento}/reservar",
             response_model=SeatActionResponse)
def reservar(
    vuelo_id:        str,
    numero_asiento:  str,
    body:            SeatActionRequest,
    background:      BackgroundTasks,
    repo:            BaseRepository = Depends(get_repo),
    clock:           VectorClock    = Depends(get_clock),
    lamport:         LamportClock   = Depends(get_lamport),
    timer_svc:       TimerService   = Depends(get_timer),
):
    """
    Transición: Libre → Reserva.
    Requiere pasaporte y nombre del pasajero.
    """
    if not body.pasaporte:
        raise HTTPException(status_code=422, detail="'pasaporte' es obligatorio para reservar")
    if not body.nombre:
        raise HTTPException(status_code=422, detail="'nombre' es obligatorio para reservar")

    return _perform_action(
        accion="reservar",
        vuelo_id=vuelo_id, numero_asiento=numero_asiento,
        body=body, background=background,
        repo=repo, clock=clock, lamport=lamport, timer_svc=timer_svc,
    )


@router.post("/{vuelo_id}/seats/{numero_asiento}/vender",
             response_model=SeatActionResponse)
def vender(
    vuelo_id:        str,
    numero_asiento:  str,
    body:            SeatActionRequest,
    background:      BackgroundTasks,
    repo:            BaseRepository = Depends(get_repo),
    clock:           VectorClock    = Depends(get_clock),
    lamport:         LamportClock   = Depends(get_lamport),
    timer_svc:       TimerService   = Depends(get_timer),
):
    """
    Transición: Libre → Venta  ó  Reserva → Venta.
    Requiere pasaporte y nombre del pasajero.
    """
    if not body.pasaporte:
        raise HTTPException(status_code=422, detail="'pasaporte' es obligatorio para vender")
    if not body.nombre:
        raise HTTPException(status_code=422, detail="'nombre' es obligatorio para vender")

    return _perform_action(
        accion="vender",
        vuelo_id=vuelo_id, numero_asiento=numero_asiento,
        body=body, background=background,
        repo=repo, clock=clock, lamport=lamport, timer_svc=timer_svc,
    )


@router.post("/{vuelo_id}/seats/{numero_asiento}/devolver",
             response_model=SeatActionResponse)
def devolver(
    vuelo_id:        str,
    numero_asiento:  str,
    body:            SeatActionRequest,
    background:      BackgroundTasks,
    repo:            BaseRepository = Depends(get_repo),
    clock:           VectorClock    = Depends(get_clock),
    lamport:         LamportClock   = Depends(get_lamport),
    timer_svc:       TimerService   = Depends(get_timer),
):
    """
    Transición: Reserva → Devolución.
    Inicia el timer configurable para volver a Libre.
    No requiere pasaporte (ya está registrado en el asiento).
    Acepta opcionalmente `motivo` para registrar la razón de la devolución.
    """
    return _perform_action(
        accion="devolver",
        vuelo_id=vuelo_id, numero_asiento=numero_asiento,
        body=body,
        background=background,
        repo=repo, clock=clock, lamport=lamport, timer_svc=timer_svc,
    )


# ─────────────────────────────────────────
# LÓGICA COMPARTIDA
# ─────────────────────────────────────────

def _perform_action(
    accion:          str,
    vuelo_id:        str,
    numero_asiento:  str,
    body:            SeatActionRequest,
    background:      BackgroundTasks,
    repo:            BaseRepository,
    clock:           VectorClock,
    timer_svc:       TimerService,
    lamport:         LamportClock | None = None,
) -> SeatActionResponse:
    """
    Flujo completo de una operación sobre un asiento:
      1. Leer estado actual del asiento
      2. Validar transición en la máquina de estados
      3. Upsert del pasajero (si aplica)
      4. Tick del reloj vectorial
      5. Operación atómica en BD (el primero gana)
      6. Programar timer si es devolución
      7. Propagar a peers en background
    """
    vid = vuelo_id.upper()
    num = numero_asiento.upper()

    # ── 1. Leer asiento ──
    asiento = repo.get_seat(vid, num)
    if not asiento:
        raise HTTPException(404, f"Asiento '{num}' no encontrado en vuelo '{vid}'")

    # ── 2. Validar máquina de estados ──
    try:
        tr = validate_transition(asiento["estado"], accion)
    except EstadoInvalidoError as e:
        raise HTTPException(500, str(e))
    except TransicionInvalidaError as e:
        raise HTTPException(409, str(e))

    # ── 3. Upsert pasajero ──
    pasaporte = body.pasaporte
    if pasaporte and body.nombre:
        repo.upsert_passenger(pasaporte, body.nombre, body.email)

    # Si es devolución, el pasaporte ya está en el asiento
    if accion == "devolver" and not pasaporte:
        pasaporte = asiento.get("pasaporte_pasajero")

    # ── 4. Tick de relojes (vectorial + Lamport) + epoch UTC ──
    lamport_ts      = lamport.tick() if lamport is not None else 0
    reloj           = clock.tick_and_serialize()
    timestamp_epoch = int(time.time())   # segundos UTC, nunca hora local

    # ── 5. Operación atómica ──
    ok = repo.apply_seat_operation(
        vuelo_id          = vid,
        numero_asiento    = num,
        estado_anterior   = tr.estado_anterior,
        estado_nuevo      = tr.estado_nuevo,
        pasaporte         = pasaporte,
        tipo              = tr.tipo,
        nodo_origen       = cfg.node_id,
        reloj_vectorial   = reloj,
        timestamp_epoch   = timestamp_epoch,
        motivo            = body.motivo or None,
        lamport_timestamp = lamport_ts,
    )

    if not ok:
        raise HTTPException(
            status_code=409,
            detail=(
                f"El asiento {num} ya no está en estado '{tr.estado_anterior}'. "
                "Fue modificado por otro usuario. Recargue el mapa."
            )
        )

    # ── 6. Timer para devolución ──
    if tr.tipo == "devolucion":
        timer_svc.schedule(vid, num)

    # ── 7. Propagar en background ──
    evento = {
        "tipo":               tr.tipo,
        "vuelo_id":           vid,
        "numero_asiento":     num,
        "estado_anterior":    tr.estado_anterior,
        "estado_nuevo":       tr.estado_nuevo,
        "pasaporte_pasajero": pasaporte,
        "nodo_origen":        cfg.node_id,
        "reloj_vectorial":    reloj,
        "timestamp_epoch":    timestamp_epoch,
        "lamport_timestamp":  lamport_ts,
        "motivo":             body.motivo or None,
    }
    background.add_task(sync_service.propagate, evento, cfg.peers)

    logger.info(
        "[SEAT] nodo%d  %s/%s  %s→%s  reloj=%s",
        cfg.node_id, vid, num,
        tr.estado_anterior, tr.estado_nuevo, reloj,
    )

    return SeatActionResponse(
        ok=True,
        vuelo_id=vid,
        numero_asiento=num,
        estado_nuevo=tr.estado_nuevo,
        reloj_vectorial=reloj,
        mensaje=f"Asiento {num} pasó a {tr.estado_nuevo}",
    )
