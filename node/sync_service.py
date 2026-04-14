# =============================================
# AEROLÍNEAS RAFAEL PABON
# sync_service.py — Servicio de sincronización entre nodos
#
# Responsabilidades:
#   1. ENVIAR: propagar eventos a los otros 2 nodos (peers)
#              tras una operación exitosa en este nodo.
#   2. RECIBIR: aplicar un evento llegado de otro nodo
#              usando la política "el primero gana".
#
# Flujo completo de una reserva en nodo1:
#   Usuario → nodo1 → apply_seat_operation() → OK
#          → tick reloj vectorial [1,0,0]
#          → propagate(evento, peers)
#               ├─► POST nodo2/sync/event  → apply_remote_event() → False (ya ocupado)
#               └─► POST nodo3/sync/event  → apply_remote_event() → False (ya ocupado)
#
# Política de conflicto:
#   Si dos nodos intentan el mismo asiento simultáneamente,
#   la operación atómica en BD acepta solo la primera que llega.
#   La segunda retorna False y se descarta (LWW via hardware clock de BD).
# =============================================

import logging
import threading
import time

import httpx

from vector_clock import VectorClock
from lamport_clock import LamportClock
from repository.base import BaseRepository
from state_machine import assert_tipo, assert_estado

logger = logging.getLogger(__name__)

# Ruta del endpoint de sincronización en cada nodo
SYNC_ENDPOINT = "/sync/event"

# Configuración de reintentos de propagación
MAX_RETRIES    = 3
RETRY_DELAY_S  = 1.5   # segundos entre reintentos


# ─────────────────────────────────────────
# ENVÍO — propagar evento a los peers
# ─────────────────────────────────────────

def propagate(evento: dict, peers: list[str]) -> None:
    """
    Envía el evento a todos los peers en hilos separados (fire-and-forget).
    Los errores de red se loggean pero nunca bloquean la respuesta al cliente.

    Args:
        evento: dict con las claves del evento (tipo, vuelo_id, etc.)
        peers:  lista de URLs base de los otros nodos, ej: ["http://nodo2:8000"]
    """
    for peer_url in peers:
        t = threading.Thread(
            target  = _send_with_retry,
            args    = (peer_url, evento),
            daemon  = True,    # no bloquea el shutdown del proceso
            name    = f"sync-{peer_url}",
        )
        t.start()


def _send_with_retry(peer_url: str, evento: dict) -> None:
    """Envía el evento a un peer con reintentos exponenciales."""
    url = f"{peer_url}{SYNC_ENDPOINT}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = httpx.post(url, json=evento, timeout=5.0)
            if resp.status_code == 200:
                logger.debug(
                    "[SYNC→] evento '%s' vuelo=%s asiento=%s → %s  OK",
                    evento.get("tipo"), evento.get("vuelo_id"),
                    evento.get("numero_asiento"), peer_url,
                )
                return
            else:
                logger.warning(
                    "[SYNC→] %s respondió HTTP %d (intento %d/%d)",
                    peer_url, resp.status_code, attempt, MAX_RETRIES,
                )
        except httpx.RequestError as exc:
            logger.warning(
                "[SYNC→] No se pudo conectar a %s: %s (intento %d/%d)",
                peer_url, exc, attempt, MAX_RETRIES,
            )

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_S * attempt)   # backoff lineal

    logger.error(
        "[SYNC→] Falló propagación a %s tras %d intentos — evento: %s",
        peer_url, MAX_RETRIES, evento,
    )


# ─────────────────────────────────────────
# RECEPCIÓN — aplicar evento de otro nodo
# ─────────────────────────────────────────

def apply_remote_event(
    evento:    dict,
    repo:      BaseRepository,
    clock:     VectorClock,
    timer_svc,              # TimerService — se tipifica como Any para evitar import circular
    lamport:   LamportClock | None = None,
) -> bool:
    """
    Procesa un evento recibido de otro nodo.

    1. Valida el payload del evento.
    2. Fusiona el reloj vectorial (merge).
    3. Aplica la operación atómica en la BD local.
       → Si ya ocurrió (conflicto), retorna False y se descarta.
    4. Gestiona timers según el tipo de evento:
       · devolucion → programa timer de 5 min en este nodo
       · liberacion → cancela el timer de este nodo (el peer ya lo liberó)

    Returns:
        True  si el evento se aplicó correctamente.
        False si fue descartado (conflicto — "el primero gana").
    """
    # ── Validación básica del payload ──
    _validate_evento(evento)

    vuelo_id       = evento["vuelo_id"]
    numero_asiento = evento["numero_asiento"]
    tipo           = evento["tipo"]

    # ── Merge del reloj vectorial ──
    nuevo_reloj = clock.merge_and_serialize(evento["reloj_vectorial"])
    logger.debug(
        "[SYNC←] Recibido '%s' de nodo%s — reloj fusionado: %s",
        tipo, evento.get("nodo_origen"), nuevo_reloj,
    )

    # ── Actualizar reloj de Lamport ──
    lamport_ts = 0
    if lamport is not None:
        lamport_ts = lamport.update(int(evento.get("lamport_timestamp") or 0))

    # ── Aplicar en BD local (operación atómica) ──
    ok = repo.apply_seat_operation(
        vuelo_id          = vuelo_id,
        numero_asiento    = numero_asiento,
        estado_anterior   = evento["estado_anterior"],
        estado_nuevo      = evento["estado_nuevo"],
        pasaporte         = evento.get("pasaporte_pasajero"),
        tipo              = tipo,
        nodo_origen       = int(evento["nodo_origen"]),
        reloj_vectorial   = evento["reloj_vectorial"],
        timestamp_epoch   = int(evento.get("timestamp_epoch") or 0),
        motivo            = evento.get("motivo"),
        lamport_timestamp = lamport_ts,
    )

    if not ok:
        logger.info(
            "[SYNC←] Descartado '%s' vuelo=%s asiento=%s — conflicto (el primero ganó)",
            tipo, vuelo_id, numero_asiento,
        )
        return False

    # ── Gestión de timers ──
    if tipo == "devolucion":
        # El peer puso este asiento en Devolución → iniciar timer local también
        timer_svc.schedule(vuelo_id, numero_asiento)
        logger.debug(
            "[SYNC←] Timer de liberación programado para %s/%s",
            vuelo_id, numero_asiento,
        )
    elif tipo == "liberacion":
        # El timer de otro nodo ya liberó el asiento → cancelar el timer local
        timer_svc.cancel(vuelo_id, numero_asiento)
        logger.debug(
            "[SYNC←] Timer cancelado para %s/%s (liberado por nodo remoto)",
            vuelo_id, numero_asiento,
        )

    logger.info(
        "[SYNC←] Aplicado '%s' vuelo=%s asiento=%s  %s→%s",
        tipo, vuelo_id, numero_asiento,
        evento["estado_anterior"], evento["estado_nuevo"],
    )
    return True


# ─────────────────────────────────────────
# VALIDACIÓN DEL PAYLOAD
# ─────────────────────────────────────────

_CAMPOS_REQUERIDOS = {
    "tipo", "vuelo_id", "numero_asiento",
    "estado_anterior", "estado_nuevo",
    "nodo_origen", "reloj_vectorial",
}


def _validate_evento(evento: dict) -> None:
    """Lanza ValueError si el payload del evento está incompleto o tiene valores inválidos."""
    faltantes = _CAMPOS_REQUERIDOS - evento.keys()
    if faltantes:
        raise ValueError(f"Payload de evento incompleto, faltan: {faltantes}")

    assert_tipo(evento["tipo"])
    assert_estado(evento["estado_anterior"])
    assert_estado(evento["estado_nuevo"])

    nodo = evento.get("nodo_origen")
    if nodo not in (1, 2, 3):
        raise ValueError(f"nodo_origen inválido: {nodo!r}")
