# =============================================
# AEROLÍNEAS RAFAEL PABON
# timer_service.py — Timer automático Devolución → Libre
#
# Cuando un asiento pasa a estado "Devolución", el sistema
# inicia un temporizador de 5 minutos (tiempo de catering).
# Al vencerse, el asiento vuelve automáticamente a "Libre".
#
# Flujo:
#   asiento → Devolución
#       └─► timer_svc.schedule(vuelo_id, numero_asiento)
#                 └─► espera 5 min
#                        └─► apply_seat_operation(Devolución → Libre)
#                               └─► propaga "liberacion" a peers
#
# Thread-safety:
#   Múltiples asientos pueden estar en Devolución simultáneamente.
#   Cada uno tiene su propio threading.Timer.
#   Un lock protege el diccionario de timers activos.
#
# Idempotencia:
#   Si el timer dispara pero el asiento ya no está en Devolución
#   (porque un peer lo liberó antes), apply_seat_operation retorna
#   False y no ocurre ningún cambio duplicado.
# =============================================

import logging
import threading
import time
from typing import Callable

from vector_clock import VectorClock
from lamport_clock import LamportClock
from repository.base import BaseRepository

logger = logging.getLogger(__name__)

# Tiempo de espera antes de liberar el asiento (segundos) — se sobreescribe con cfg
DEVOLUCION_TIMEOUT_SEG: int = 15 * 60   # 15 minutos (default)


class TimerService:
    """
    Gestiona los temporizadores de liberación automática de asientos.
    Una sola instancia por nodo (singleton en main.py).

    Args:
        repo:         Repositorio del nodo (SQL Server o MongoDB).
        clock:        Reloj vectorial del nodo.
        propagate_fn: Función para propagar eventos a los peers.
                      Firma: propagate_fn(evento: dict) -> None
                      Ejemplo: lambda e: sync_service.propagate(e, cfg.peers)
        timeout_seg:  Segundos hasta liberar. Por defecto DEVOLUCION_TIMEOUT_SEG.
                      Aceptar override facilita los tests unitarios.
    """

    def __init__(
        self,
        repo:         BaseRepository,
        clock:        VectorClock,
        propagate_fn: Callable[[dict], None],
        timeout_seg:  int = DEVOLUCION_TIMEOUT_SEG,
        lamport:      LamportClock | None = None,
    ):
        self._repo         = repo
        self._clock        = clock
        self._propagate    = propagate_fn
        self._timeout      = timeout_seg
        self._lamport      = lamport

        # {(vuelo_id, numero_asiento): threading.Timer}
        self._timers: dict[tuple[str, str], threading.Timer] = {}
        self._lock   = threading.Lock()

    # ─────────────────────────────────────────
    # API PÚBLICA
    # ─────────────────────────────────────────

    def schedule(self, vuelo_id: str, numero_asiento: str) -> None:
        """
        Programa la liberación automática del asiento en `timeout_seg` segundos.
        Si ya existía un timer para ese asiento, lo cancela y reprograma.
        """
        key = (vuelo_id, numero_asiento)

        with self._lock:
            # Cancelar timer previo si existe (caso: re-devolución)
            self._cancel_unlocked(key)

            timer = threading.Timer(
                interval = self._timeout,
                function = self._on_timer_fired,
                args     = [vuelo_id, numero_asiento],
            )
            timer.daemon = True    # no bloquea el shutdown del proceso
            timer.start()
            self._timers[key] = timer

        logger.info(
            "[TIMER] Programado: %s/%s → Libre en %d s",
            vuelo_id, numero_asiento, self._timeout,
        )

    def cancel(self, vuelo_id: str, numero_asiento: str) -> None:
        """
        Cancela el timer pendiente para un asiento.
        Llamado cuando un peer ya liberó el asiento (sincronización).
        No hace nada si no hay timer activo para ese asiento.
        """
        key = (vuelo_id, numero_asiento)
        with self._lock:
            cancelado = self._cancel_unlocked(key)

        if cancelado:
            logger.debug(
                "[TIMER] Cancelado: %s/%s (liberado por peer)",
                vuelo_id, numero_asiento,
            )

    def active_count(self) -> int:
        """Retorna el número de timers activos. Útil para diagnóstico."""
        with self._lock:
            return len(self._timers)

    def active_seats(self) -> list[tuple[str, str]]:
        """Retorna la lista de asientos con timer activo. Para diagnóstico."""
        with self._lock:
            return list(self._timers.keys())

    # ─────────────────────────────────────────
    # INTERNOS
    # ─────────────────────────────────────────

    def _cancel_unlocked(self, key: tuple[str, str]) -> bool:
        """Cancela el timer para `key` sin adquirir el lock (llamar con lock tomado)."""
        timer = self._timers.pop(key, None)
        if timer is not None:
            timer.cancel()
            return True
        return False

    def _on_timer_fired(self, vuelo_id: str, numero_asiento: str) -> None:
        """
        Callback del threading.Timer al vencerse el timeout.
        Se ejecuta en el hilo del timer (no en el hilo principal).

        1. Elimina el timer del registro.
        2. Aplica la transición Devolución → Libre en la BD local.
        3. Si se aplicó con éxito, propaga el evento a los peers.
        """
        key = (vuelo_id, numero_asiento)

        # Eliminar del registro (el timer ya disparó)
        with self._lock:
            self._timers.pop(key, None)

        logger.info(
            "[TIMER] Disparado: liberando %s/%s (Devolución → Libre)",
            vuelo_id, numero_asiento,
        )

        # Generar reloj vectorial y Lamport para este evento de sistema
        reloj      = self._clock.tick_and_serialize()
        lamport_ts = self._lamport.tick() if self._lamport is not None else 0

        try:
            ok = self._repo.apply_seat_operation(
                vuelo_id          = vuelo_id,
                numero_asiento    = numero_asiento,
                estado_anterior   = "Devolucion",
                estado_nuevo      = "Libre",
                pasaporte         = None,
                tipo              = "liberacion",
                nodo_origen       = self._clock._node_id,
                reloj_vectorial   = reloj,
                timestamp_epoch   = int(time.time()),
                lamport_timestamp = lamport_ts,
            )
        except Exception as exc:
            logger.error(
                "[TIMER] Error al liberar %s/%s: %s",
                vuelo_id, numero_asiento, exc,
            )
            return

        if not ok:
            # El asiento ya no estaba en Devolución (peer lo liberó primero)
            logger.debug(
                "[TIMER] Liberación descartada para %s/%s — ya fue liberado por un peer",
                vuelo_id, numero_asiento,
            )
            return

        # Propagar el evento de liberación a los otros nodos
        evento = {
            "tipo":               "liberacion",
            "vuelo_id":           vuelo_id,
            "numero_asiento":     numero_asiento,
            "estado_anterior":    "Devolucion",
            "estado_nuevo":       "Libre",
            "pasaporte_pasajero": None,
            "nodo_origen":        self._clock._node_id,
            "reloj_vectorial":    reloj,
            "timestamp_epoch":    int(time.time()),
            "lamport_timestamp":  lamport_ts,
        }

        try:
            self._propagate(evento)
        except Exception as exc:
            logger.error(
                "[TIMER] Error al propagar liberación de %s/%s: %s",
                vuelo_id, numero_asiento, exc,
            )

        logger.info(
            "[TIMER] Liberado y propagado: %s/%s",
            vuelo_id, numero_asiento,
        )
