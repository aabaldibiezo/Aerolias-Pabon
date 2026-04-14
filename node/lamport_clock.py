# =============================================
# AEROLÍNEAS RAFAEL PABON
# lamport_clock.py — Reloj de Lamport
#
# Complemento al Reloj Vectorial. Proporciona un orden total
# parcial de eventos en el sistema distribuido.
#
# Reglas de Lamport:
#   1. Al GENERAR un evento local  → tiempo += 1
#   2. Al RECIBIR un evento remoto → tiempo = max(local, recibido) + 1
#
# A diferencia del Reloj Vectorial (que detecta causalidad),
# el Reloj de Lamport garantiza que si A → B entonces L(A) < L(B).
# =============================================

import threading


class LamportClock:
    """
    Reloj de Lamport thread-safe para un nodo del sistema distribuido.
    Una sola instancia por nodo (singleton en main.py).
    """

    def __init__(self, node_id: int):
        self._node_id = node_id
        self._time    = 0
        self._lock    = threading.Lock()

    def tick(self) -> int:
        """
        Incrementa el reloj al generar un evento local.
        Retorna el nuevo timestamp.
        Llamar ANTES de registrar cualquier evento propio.
        """
        with self._lock:
            self._time += 1
            return self._time

    def update(self, received_time: int) -> int:
        """
        Actualiza el reloj al recibir un evento de otro nodo.
        Aplica: tiempo = max(local, recibido) + 1
        Retorna el nuevo timestamp.
        """
        with self._lock:
            self._time = max(self._time, received_time) + 1
            return self._time

    def get_time(self) -> int:
        """Retorna el valor actual sin modificarlo."""
        with self._lock:
            return self._time

    def __repr__(self) -> str:
        return f"LamportClock(nodo={self._node_id}, t={self._time})"
