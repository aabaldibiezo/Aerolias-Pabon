# =============================================
# AEROLÍNEAS RAFAEL PABON
# vector_clock.py — Reloj Vectorial
#
# Implementa el algoritmo de Lamport generalizado a N nodos.
# El reloj es un array de 3 enteros: [t_nodo1, t_nodo2, t_nodo3]
# El índice del nodo es (node_id - 1).
#
# Reglas:
#  · Al GENERAR un evento  → incrementar propio contador
#  · Al RECIBIR un evento  → merge(local, remoto) luego incrementar propio
#  · "El primero gana"     → si dos eventos son concurrentes, gana el que
#                            llegó primero al motor de BD (resuelto en apply_seat_operation)
# =============================================

import json
import threading


NUM_NODES = 3   # nodo1, nodo2, nodo3


class VectorClock:
    """
    Reloj vectorial thread-safe para un nodo del sistema distribuido.
    Una sola instancia por nodo (singleton en main.py).
    """

    def __init__(self, node_id: int):
        if not 1 <= node_id <= NUM_NODES:
            raise ValueError(f"node_id debe estar entre 1 y {NUM_NODES}, recibido: {node_id}")
        self._node_id = node_id
        self._idx     = node_id - 1          # índice en el array
        self._clock   = [0] * NUM_NODES
        self._lock    = threading.Lock()

    # ─────────────────────────────────────────
    # OPERACIONES PRINCIPALES
    # ─────────────────────────────────────────

    def tick(self) -> list[int]:
        """
        Llama a este método ANTES de generar un evento local.
        Incrementa el propio contador y retorna una copia del reloj actualizado.
        """
        with self._lock:
            self._clock[self._idx] += 1
            return self._clock.copy()

    def merge(self, remote: list[int]) -> list[int]:
        """
        Llama a este método AL RECIBIR un evento de otro nodo.
        Fusiona tomando el máximo de cada posición y luego incrementa
        el propio contador (regla de Lamport para recepción).
        Retorna una copia del reloj resultante.
        """
        if len(remote) != NUM_NODES:
            raise ValueError(
                f"Reloj remoto tiene {len(remote)} elementos, se esperaban {NUM_NODES}"
            )
        with self._lock:
            self._clock = [max(a, b) for a, b in zip(self._clock, remote)]
            self._clock[self._idx] += 1
            return self._clock.copy()

    def get(self) -> list[int]:
        """Retorna una copia del estado actual del reloj (sin modificarlo)."""
        with self._lock:
            return self._clock.copy()

    # ─────────────────────────────────────────
    # SERIALIZACIÓN
    # ─────────────────────────────────────────

    @staticmethod
    def serialize(clock: list[int]) -> str:
        """Convierte el reloj a JSON string para almacenar en BD. Ej: '[3,1,2]'"""
        return json.dumps(clock, separators=(",", ":"))

    @staticmethod
    def deserialize(s: str) -> list[int]:
        """Parsea un JSON string y retorna la lista de enteros."""
        parsed = json.loads(s)
        if not isinstance(parsed, list) or len(parsed) != NUM_NODES:
            raise ValueError(f"Formato de reloj inválido: '{s}'")
        return [int(x) for x in parsed]

    def tick_and_serialize(self) -> str:
        """
        Atajo: tick() + serialize() en una sola llamada thread-safe.
        Uso típico: antes de guardar un evento en la BD.
        """
        return self.serialize(self.tick())

    def merge_and_serialize(self, remote_str: str) -> str:
        """
        Atajo: deserialize() + merge() + serialize() en una sola llamada.
        Uso típico: al recibir un evento de sincronización de otro nodo.
        """
        remote = self.deserialize(remote_str)
        merged = self.merge(remote)
        return self.serialize(merged)

    # ─────────────────────────────────────────
    # COMPARACIONES (para diagnóstico y logs)
    # ─────────────────────────────────────────

    @staticmethod
    def happens_before(a: list[int], b: list[int]) -> bool:
        """
        Retorna True si el evento con reloj `a` ocurrió causalmente
        ANTES del evento con reloj `b`.
        Condición: a[i] <= b[i] para todo i, y existe al menos un j con a[j] < b[j]
        """
        return (
            all(x <= y for x, y in zip(a, b))
            and any(x < y for x, y in zip(a, b))
        )

    @staticmethod
    def is_concurrent(a: list[int], b: list[int]) -> bool:
        """
        Retorna True si los eventos son concurrentes (ninguno precede al otro).
        Cuando dos eventos son concurrentes y afectan el mismo asiento,
        el sistema aplica "el primero gana" mediante la operación atómica en BD.
        """
        return (
            not VectorClock.happens_before(a, b)
            and not VectorClock.happens_before(b, a)
        )

    def __repr__(self) -> str:
        return f"VectorClock(nodo={self._node_id}, reloj={self._clock})"
