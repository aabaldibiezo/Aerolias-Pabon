# =============================================
# AEROLÍNEAS RAFAEL PABON
# repository/base.py — Interfaz abstracta del repositorio
#
# Define el contrato que deben implementar
# SQLServerRepository y MongoDBRepository.
# La capa de servicios y routers solo conoce esta interfaz.
# =============================================

from abc import ABC, abstractmethod
from datetime import datetime


class BaseRepository(ABC):

    # ─────────────────────────────────────────
    # AEROPUERTOS
    # ─────────────────────────────────────────

    @abstractmethod
    def get_airports(self) -> list[dict]:
        """
        Devuelve todos los aeropuertos.
        Cada dict tiene las claves:
          codigo, nombre, ciudad, pais, timezone, latitud, longitud
        """

    @abstractmethod
    def get_airport(self, codigo: str) -> dict | None:
        """Devuelve un aeropuerto por su código IATA o None si no existe."""

    # ─────────────────────────────────────────
    # RUTAS COMERCIALES (grafo para Dijkstra)
    # ─────────────────────────────────────────

    @abstractmethod
    def get_routes(self) -> list[dict]:
        """
        Devuelve todas las rutas activas del grafo dirigido.
        Cada dict tiene las claves: origen, destino, distancia_km
        """

    # ─────────────────────────────────────────
    # VUELOS
    # ─────────────────────────────────────────

    @abstractmethod
    def search_flights(
        self,
        origen:  str | None = None,
        destino: str | None = None,
        fecha:   str | None = None,   # formato: 'YYYY-MM-DD'
    ) -> list[dict]:
        """
        Búsqueda incremental de vuelos activos.
        Todos los parámetros son opcionales (filtra solo los no-None).
        Cada dict incluye ciudad_origen, ciudad_destino, timezone_origen,
        timezone_destino además de los campos del vuelo.
        """

    @abstractmethod
    def get_flight(self, vuelo_id: str) -> dict | None:
        """Devuelve un vuelo por su ID, enriquecido con datos de aeropuertos."""

    # ─────────────────────────────────────────
    # ASIENTOS
    # ─────────────────────────────────────────

    @abstractmethod
    def get_seats(self, vuelo_id: str) -> list[dict]:
        """
        Devuelve todos los asientos de un vuelo.
        Cada dict tiene: asiento_id, vuelo_id, numero_asiento,
                         clase, estado, pasaporte_pasajero, precio, updated_at
        """

    @abstractmethod
    def get_seat(self, vuelo_id: str, numero_asiento: str) -> dict | None:
        """Devuelve un asiento específico o None si no existe."""

    @abstractmethod
    def apply_seat_operation(
        self,
        vuelo_id:          str,
        numero_asiento:    str,
        estado_anterior:   str,   # estado que debe tener el asiento AHORA
        estado_nuevo:      str,   # estado al que queremos llevarlo
        pasaporte:         str | None,
        tipo:              str,   # 'reserva' | 'venta' | 'devolucion' | 'liberacion'
        nodo_origen:       int,
        reloj_vectorial:   str,   # JSON serializado, ej: "[3,1,2]"
        timestamp_epoch:   int  = 0,            # Unix timestamp UTC en segundos
        motivo:            str | None = None,   # razón de devolución u observación
        lamport_timestamp: int  = 0,            # Reloj de Lamport al momento del evento
    ) -> bool:
        """
        Operación atómica de cambio de estado de un asiento.

        Actualiza el asiento SOLO si su estado actual coincide con
        `estado_anterior` y registra el evento en el log del reloj vectorial,
        todo en la misma transacción (o con operación atómica en MongoDB).

        Retorna:
          True  → operación aplicada con éxito
          False → conflicto: el asiento ya no estaba en `estado_anterior`
                  (política "el primero gana" — este evento se descarta)
        """

    # ─────────────────────────────────────────
    # PASAJEROS
    # ─────────────────────────────────────────

    @abstractmethod
    def get_passenger(self, pasaporte: str) -> dict | None:
        """
        Devuelve un pasajero por su pasaporte.
        Dict: pasaporte, nombre, email, created_at
        """

    @abstractmethod
    def upsert_passenger(
        self,
        pasaporte: str,
        nombre:    str,
        email:     str | None = None,
    ) -> dict:
        """
        Inserta el pasajero si no existe, o lo devuelve si ya existe.
        Nunca sobreescribe un nombre ya registrado.
        Retorna el dict del pasajero (nuevo o existente).
        """

    # ─────────────────────────────────────────
    # EVENTOS (reloj vectorial)
    # ─────────────────────────────────────────

    @abstractmethod
    def get_events_since(
        self,
        timestamp_utc: datetime,
        nodo_origen:   int | None = None,
    ) -> list[dict]:
        """
        Devuelve eventos registrados desde `timestamp_utc`.
        Si `nodo_origen` se indica, filtra solo eventos de ese nodo.
        Ordenados por timestamp_utc ASC.
        Usado por el servicio de sincronización para detectar eventos perdidos.
        """

    @abstractmethod
    def get_events_since_epoch(self, epoch: int) -> list[dict]:
        """
        Devuelve todos los eventos con timestamp_epoch > epoch, ordenados ASC.
        Usado por /sync/catch-up para recuperar eventos perdidos.
        epoch debe ser Unix timestamp en segundos UTC.
        """

    # ─────────────────────────────────────────
    # ESTADÍSTICAS (dashboards)
    # ─────────────────────────────────────────

    @abstractmethod
    def get_flight_stats(self, vuelo_id: str) -> dict:
        """
        Devuelve estadísticas de ocupación e ingresos para un vuelo.
        Incluye conteo por estado (Libre/Reserva/Venta/Devolucion) y por clase.
        """

    @abstractmethod
    def get_global_stats(self) -> dict:
        """
        Devuelve estadísticas globales de todos los vuelos activos:
        ocupación total, ingresos, desglose por clase y estado.
        """

    # ─────────────────────────────────────────
    # ESTADOS DE VUELO
    # ─────────────────────────────────────────

    @abstractmethod
    def update_flight_state(self, vuelo_id: str, estado: str) -> bool:
        """
        Actualiza el estado operativo de un vuelo.
        Retorna True si el registro existía, False si no.
        """

    @abstractmethod
    def get_flights_for_state_update(self) -> list[dict]:
        """
        Devuelve vuelos activos con fecha, hora_salida, hora_llegada y estado actual.
        Usado por el background task de actualización de estados.
        """
