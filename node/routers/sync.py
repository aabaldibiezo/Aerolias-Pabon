# =============================================
# AEROLÍNEAS RAFAEL PABON
# routers/sync.py — Endpoint de sincronización entre nodos
# =============================================

import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import sync_service
from config import cfg
from dependencies import get_clock, get_lamport, get_repo, get_timer
from lamport_clock import LamportClock
from repository.base import BaseRepository
from timer_service import TimerService
from vector_clock import VectorClock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sincronización"])


# ─────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────

class SyncEventPayload(BaseModel):
    tipo:               str
    vuelo_id:           str
    numero_asiento:     str
    estado_anterior:    str
    estado_nuevo:       str
    pasaporte_pasajero: str | None = None
    nodo_origen:        int
    reloj_vectorial:    str             # JSON string: "[3,1,2]"
    timestamp_epoch:    int  = 0        # Unix timestamp UTC segundos
    lamport_timestamp:  int  = 0        # Reloj de Lamport del nodo emisor
    motivo:             str | None = None


# ─────────────────────────────────────────
# POST /sync/event — Recibir evento en tiempo real
# ─────────────────────────────────────────

@router.post("/event")
def receive_event(
    payload:   SyncEventPayload,
    repo:      BaseRepository = Depends(get_repo),
    clock:     VectorClock    = Depends(get_clock),
    lamport:   LamportClock   = Depends(get_lamport),
    timer_svc: TimerService   = Depends(get_timer),
):
    """
    Recibe un evento de sincronización de otro nodo (propagación en tiempo real).
    Siempre retorna HTTP 200 para que el peer no reintente.
    """
    if payload.nodo_origen == cfg.node_id:
        logger.warning("[SYNC] Ignorando evento propio (nodo_origen=%d)", payload.nodo_origen)
        return {"aplicado": False, "razon": "eco_propio"}

    logger.info(
        "[SYNC←] tipo='%s' vuelo=%s asiento=%s de nodo%d  epoch=%d  reloj=%s",
        payload.tipo, payload.vuelo_id, payload.numero_asiento,
        payload.nodo_origen, payload.timestamp_epoch, payload.reloj_vectorial,
    )

    try:
        aplicado = sync_service.apply_remote_event(
            evento    = payload.model_dump(),
            repo      = repo,
            clock     = clock,
            timer_svc = timer_svc,
            lamport   = lamport,
        )
    except ValueError as exc:
        logger.error("[SYNC] Payload inválido: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))

    if aplicado:
        logger.info(
            "[SYNC←] ✓ Aplicado '%s' %s→%s  asiento=%s",
            payload.tipo, payload.estado_anterior, payload.estado_nuevo,
            payload.numero_asiento,
        )
    else:
        logger.info(
            "[SYNC←] ✗ Descartado '%s' asiento=%s — conflicto FWW",
            payload.tipo, payload.numero_asiento,
        )

    return {
        "aplicado":    aplicado,
        "nodo_id":     cfg.node_id,
        "reloj_local": clock.get(),
    }


# ─────────────────────────────────────────
# GET /sync/events — Exportar eventos (para catch-up de peers)
# ─────────────────────────────────────────

@router.get("/events")
def get_events(
    since: int = Query(
        ...,
        description="Unix timestamp epoch (segundos UTC). Devuelve eventos con "
                    "timestamp_epoch > since.",
        ge=0,
    ),
    repo: BaseRepository = Depends(get_repo),
):
    """
    Devuelve la lista de eventos de este nodo desde `since`.
    Un nodo reconectado llama este endpoint en sus peers para obtener
    los eventos que se perdió.
    """
    eventos = repo.get_events_since_epoch(since)
    logger.info(
        "[EVENTS] nodo%d exportando %d eventos desde epoch=%d",
        cfg.node_id, len(eventos), since,
    )
    return {
        "nodo_id":          cfg.node_id,
        "since":            since,
        "epoch_actual":     int(time.time()),
        "eventos":          eventos,
    }


# ─────────────────────────────────────────
# GET /sync/catch-up — Recuperar eventos perdidos de los peers
# ─────────────────────────────────────────

@router.get("/catch-up")
def catch_up(
    since: int = Query(
        ...,
        description="Unix timestamp epoch (segundos UTC) del último evento conocido. "
                    "Este nodo jala de sus peers todos los eventos posteriores y los aplica.",
        ge=0,
    ),
    repo:      BaseRepository = Depends(get_repo),
    clock:     VectorClock    = Depends(get_clock),
    lamport:   LamportClock   = Depends(get_lamport),
    timer_svc: TimerService   = Depends(get_timer),
):
    """
    Recuperación de eventos perdidos por desconexión temporal.

    Flujo:
      1. Nodo B (este nodo) se reconectó.
      2. Llama GET /sync/catch-up?since=<epoch_antes_de_desconexion>
      3. Este endpoint consulta a cada peer: GET <peer>/sync/events?since=<epoch>
      4. Aplica cada evento recibido contra la BD local usando apply_remote_event.
      5. Retorna un resumen de la sincronización.

    Ejemplo:
      curl http://localhost:8002/sync/catch-up?since=1700000000
    """
    logger.info(
        "[CATCH-UP] nodo%d iniciando recuperación desde epoch=%d (%s UTC)",
        cfg.node_id, since,
        time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(since)) if since else "epoch_zero",
    )

    aplicados   = 0
    descartados = 0
    errores     = 0
    detalle_peers = []

    for peer_url in cfg.peers:
        peer_eventos  = 0
        peer_aplicados = 0
        peer_descartados = 0

        try:
            resp = httpx.get(
                f"{peer_url}/sync/events",
                params={"since": since},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            eventos_peer = data.get("eventos", [])
            peer_eventos = len(eventos_peer)

            logger.info(
                "[CATCH-UP] Recibidos %d eventos de %s",
                peer_eventos, peer_url,
            )

            for ev in eventos_peer:
                logger.debug(
                    "[CATCH-UP] Aplicando tipo=%s vuelo=%s asiento=%s epoch=%d",
                    ev.get("tipo"), ev.get("vuelo_id"),
                    ev.get("numero_asiento"), ev.get("timestamp_epoch", 0),
                )
                try:
                    ok = sync_service.apply_remote_event(
                        evento    = ev,
                        repo      = repo,
                        clock     = clock,
                        timer_svc = timer_svc,
                        lamport   = lamport,
                    )
                    if ok:
                        peer_aplicados += 1
                        aplicados += 1
                        logger.info(
                            "[CATCH-UP] ✓ Aplicado tipo=%s asiento=%s  %s→%s  epoch=%d",
                            ev.get("tipo"), ev.get("numero_asiento"),
                            ev.get("estado_anterior"), ev.get("estado_nuevo"),
                            ev.get("timestamp_epoch", 0),
                        )
                    else:
                        peer_descartados += 1
                        descartados += 1
                        logger.debug(
                            "[CATCH-UP] ✗ Descartado tipo=%s asiento=%s — ya existe (FWW)",
                            ev.get("tipo"), ev.get("numero_asiento"),
                        )
                except Exception as exc:
                    errores += 1
                    logger.error(
                        "[CATCH-UP] Error aplicando evento %s/%s: %s",
                        ev.get("vuelo_id"), ev.get("numero_asiento"), exc,
                    )

        except Exception as exc:
            errores += 1
            logger.error("[CATCH-UP] No se pudo conectar a peer %s: %s", peer_url, exc)

        detalle_peers.append({
            "peer":        peer_url,
            "encontrados": peer_eventos,
            "aplicados":   peer_aplicados,
            "descartados": peer_descartados,
        })

    epoch_actual = int(time.time())

    logger.info(
        "[CATCH-UP] Completado nodo%d: aplicados=%d descartados=%d errores=%d  epoch_actual=%d",
        cfg.node_id, aplicados, descartados, errores, epoch_actual,
    )

    return {
        "nodo_id":       cfg.node_id,
        "since":         since,
        "aplicados":     aplicados,
        "descartados":   descartados,
        "errores":       errores,
        "epoch_actual":  epoch_actual,
        "peers":         detalle_peers,
    }


# ─────────────────────────────────────────
# GET /sync/status
# ─────────────────────────────────────────

@router.get("/status")
def sync_status(
    clock:     VectorClock  = Depends(get_clock),
    timer_svc: TimerService = Depends(get_timer),
):
    """Estado de sincronización del nodo: reloj, timers activos, epoch actual."""
    return {
        "nodo_id":        cfg.node_id,
        "db_engine":      cfg.db_engine,
        "peers":          cfg.peers,
        "reloj_vectorial": clock.get(),
        "timers_activos":  timer_svc.active_count(),
        "epoch_actual":    int(time.time()),
        "asientos_en_devolucion": [
            {"vuelo_id": v, "numero_asiento": a}
            for v, a in timer_svc.active_seats()
        ],
    }
