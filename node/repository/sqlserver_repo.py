# =============================================
# AEROLÍNEAS RAFAEL PABON
# repository/sqlserver_repo.py — Implementación SQL Server
# Librería: pymssql
# =============================================

import pymssql
from contextlib import contextmanager
from datetime import datetime, timezone

from .base import BaseRepository
from config import cfg


class SQLServerRepository(BaseRepository):

    # ─────────────────────────────────────────
    # GESTIÓN DE CONEXIÓN
    # ─────────────────────────────────────────

    @contextmanager
    def _connect(self):
        """
        Context manager que abre una conexión, la entrega y la cierra al salir.
        autocommit=False para poder usar transacciones explícitas.
        """
        conn = pymssql.connect(
            server   = cfg.db_host,
            port     = cfg.db_port,
            user     = cfg.db_user,
            password = cfg.db_password,
            database = cfg.db_name,
            charset  = "UTF-8",
            autocommit = False,
        )
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _row_to_dict(cursor, row) -> dict:
        """Convierte una fila de pymssql en diccionario usando los nombres de columna."""
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))

    @staticmethod
    def _rows_to_dicts(cursor, rows) -> list[dict]:
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in rows]

    # ─────────────────────────────────────────
    # AEROPUERTOS
    # ─────────────────────────────────────────

    def get_airports(self) -> list[dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT codigo, nombre, ciudad, pais, timezone, "
                "CAST(latitud AS FLOAT) AS latitud, "
                "CAST(longitud AS FLOAT) AS longitud "
                "FROM aeropuertos ORDER BY ciudad"
            )
            return self._rows_to_dicts(cur, cur.fetchall())

    def get_airport(self, codigo: str) -> dict | None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT codigo, nombre, ciudad, pais, timezone, "
                "CAST(latitud AS FLOAT) AS latitud, "
                "CAST(longitud AS FLOAT) AS longitud "
                "FROM aeropuertos WHERE codigo = %s",
                (codigo.upper(),)
            )
            row = cur.fetchone()
            return self._row_to_dict(cur, row) if row else None

    # ─────────────────────────────────────────
    # RUTAS (grafo para Dijkstra)
    # ─────────────────────────────────────────

    def get_routes(self) -> list[dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT origen, destino, distancia_km "
                "FROM rutas_comerciales WHERE activa = 1"
            )
            return self._rows_to_dicts(cur, cur.fetchall())

    # ─────────────────────────────────────────
    # VUELOS
    # ─────────────────────────────────────────

    def search_flights(
        self,
        origen:  str | None = None,
        destino: str | None = None,
        fecha:   str | None = None,
    ) -> list[dict]:
        conditions = ["v.activo = 1"]
        params: list = []

        if origen:
            conditions.append("v.origen = %s")
            params.append(origen.upper())
        if destino:
            conditions.append("v.destino = %s")
            params.append(destino.upper())
        if fecha:
            conditions.append("CAST(v.fecha AS DATE) = %s")
            params.append(fecha)

        query = (
            "SELECT v.vuelo_id, v.origen, v.destino, "
            "CONVERT(VARCHAR(10), v.fecha, 120) AS fecha, "
            "CONVERT(VARCHAR(5),  v.hora_salida,  108) AS hora_salida, "
            "CONVERT(VARCHAR(5),  v.hora_llegada, 108) AS hora_llegada, "
            "v.aeronave, v.capacidad, v.activo, "
            "ao.ciudad AS ciudad_origen,  ao.timezone AS timezone_origen, "
            "ad.ciudad AS ciudad_destino, ad.timezone AS timezone_destino "
            "FROM vuelos v "
            "JOIN aeropuertos ao ON v.origen  = ao.codigo "
            "JOIN aeropuertos ad ON v.destino = ad.codigo "
            f"WHERE {' AND '.join(conditions)} "
            "ORDER BY v.fecha, v.hora_salida"
        )

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return self._rows_to_dicts(cur, cur.fetchall())

    def get_flight(self, vuelo_id: str) -> dict | None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT v.vuelo_id, v.origen, v.destino, "
                "CONVERT(VARCHAR(10), v.fecha, 120) AS fecha, "
                "CONVERT(VARCHAR(5),  v.hora_salida,  108) AS hora_salida, "
                "CONVERT(VARCHAR(5),  v.hora_llegada, 108) AS hora_llegada, "
                "v.aeronave, v.capacidad, v.activo, "
                "ao.ciudad AS ciudad_origen,  ao.timezone AS timezone_origen, "
                "ao.latitud AS lat_origen,    ao.longitud AS lon_origen, "
                "ad.ciudad AS ciudad_destino, ad.timezone AS timezone_destino, "
                "ad.latitud AS lat_destino,   ad.longitud AS lon_destino "
                "FROM vuelos v "
                "JOIN aeropuertos ao ON v.origen  = ao.codigo "
                "JOIN aeropuertos ad ON v.destino = ad.codigo "
                "WHERE v.vuelo_id = %s",
                (vuelo_id,)
            )
            row = cur.fetchone()
            return self._row_to_dict(cur, row) if row else None

    # ─────────────────────────────────────────
    # ASIENTOS
    # ─────────────────────────────────────────

    def get_seats(self, vuelo_id: str) -> list[dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT asiento_id, vuelo_id, numero_asiento, clase, estado, "
                "pasaporte_pasajero, CAST(precio AS FLOAT) AS precio, "
                "CONVERT(VARCHAR(23), updated_at, 126) AS updated_at "
                "FROM asientos WHERE vuelo_id = %s "
                "ORDER BY "
                "  CASE clase WHEN 'primera' THEN 1 WHEN 'business' THEN 2 ELSE 3 END, "
                "  CAST(LEFT(numero_asiento, LEN(numero_asiento)-1) AS INT), "
                "  RIGHT(numero_asiento, 1)",
                (vuelo_id,)
            )
            return self._rows_to_dicts(cur, cur.fetchall())

    def get_seat(self, vuelo_id: str, numero_asiento: str) -> dict | None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT asiento_id, vuelo_id, numero_asiento, clase, estado, "
                "pasaporte_pasajero, CAST(precio AS FLOAT) AS precio, "
                "CONVERT(VARCHAR(23), updated_at, 126) AS updated_at "
                "FROM asientos WHERE vuelo_id = %s AND numero_asiento = %s",
                (vuelo_id, numero_asiento)
            )
            row = cur.fetchone()
            return self._row_to_dict(cur, row) if row else None

    def apply_seat_operation(
        self,
        vuelo_id:          str,
        numero_asiento:    str,
        estado_anterior:   str,
        estado_nuevo:      str,
        pasaporte:         str | None,
        tipo:              str,
        nodo_origen:       int,
        reloj_vectorial:   str,
        timestamp_epoch:   int = 0,
        motivo:            str | None = None,
        lamport_timestamp: int = 0,
    ) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            try:
                # UPDATE atómico con OUTPUT: solo ejecuta si el estado actual
                # coincide con estado_anterior — implementa "el primero gana"
                cur.execute(
                    "UPDATE asientos "
                    "SET estado = %s, pasaporte_pasajero = %s, updated_at = GETUTCDATE() "
                    "OUTPUT INSERTED.asiento_id "
                    "WHERE vuelo_id = %s AND numero_asiento = %s AND estado = %s",
                    (estado_nuevo, pasaporte, vuelo_id, numero_asiento, estado_anterior)
                )
                row = cur.fetchone()

                if not row:
                    # El estado ya cambió (llegó otro nodo antes) → descartamos
                    conn.rollback()
                    return False

                asiento_id = row[0]

                # Registrar evento en el log del reloj vectorial
                cur.execute(
                    "INSERT INTO eventos "
                    "(tipo, vuelo_id, asiento_id, numero_asiento, "
                    " estado_anterior, estado_nuevo, pasaporte_pasajero, "
                    " nodo_origen, reloj_vectorial, aplicado, motivo, "
                    " timestamp_epoch, lamport_timestamp) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s)",
                    (tipo, vuelo_id, asiento_id, numero_asiento,
                     estado_anterior, estado_nuevo, pasaporte,
                     nodo_origen, reloj_vectorial, motivo,
                     timestamp_epoch, lamport_timestamp)
                )

                conn.commit()
                return True

            except Exception:
                conn.rollback()
                raise

    # ─────────────────────────────────────────
    # PASAJEROS
    # ─────────────────────────────────────────

    def get_passenger(self, pasaporte: str) -> dict | None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT pasaporte, nombre, email, "
                "CONVERT(VARCHAR(23), created_at, 126) AS created_at "
                "FROM pasajeros WHERE pasaporte = %s",
                (pasaporte,)
            )
            row = cur.fetchone()
            return self._row_to_dict(cur, row) if row else None

    def upsert_passenger(
        self,
        pasaporte: str,
        nombre:    str,
        email:     str | None = None,
    ) -> dict:
        with self._connect() as conn:
            cur = conn.cursor()
            try:
                # MERGE: inserta si no existe, no sobreescribe nombre ya registrado
                cur.execute(
                    "MERGE INTO pasajeros AS target "
                    "USING (SELECT %s AS pasaporte, %s AS nombre, %s AS email) AS src "
                    "ON target.pasaporte = src.pasaporte "
                    "WHEN NOT MATCHED THEN "
                    "  INSERT (pasaporte, nombre, email) "
                    "  VALUES (src.pasaporte, src.nombre, src.email);",
                    (pasaporte, nombre, email)
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        # Devuelve el pasajero (nuevo o preexistente)
        return self.get_passenger(pasaporte)

    # ─────────────────────────────────────────
    # EVENTOS (reloj vectorial)
    # ─────────────────────────────────────────

    def get_events_since(
        self,
        timestamp_utc: datetime,
        nodo_origen:   int | None = None,
    ) -> list[dict]:
        conditions = ["timestamp_utc > %s"]
        params: list = [timestamp_utc]

        if nodo_origen is not None:
            conditions.append("nodo_origen = %s")
            params.append(nodo_origen)

        query = (
            "SELECT evento_id, tipo, vuelo_id, asiento_id, numero_asiento, "
            "estado_anterior, estado_nuevo, pasaporte_pasajero, "
            "nodo_origen, reloj_vectorial, motivo, timestamp_epoch, "
            "CONVERT(VARCHAR(23), timestamp_utc, 126) AS timestamp_utc, "
            "aplicado "
            f"FROM eventos WHERE {' AND '.join(conditions)} "
            "ORDER BY timestamp_utc ASC"
        )

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return self._rows_to_dicts(cur, cur.fetchall())

    def get_events_since_epoch(self, epoch: int) -> list[dict]:
        """
        Devuelve todos los eventos con timestamp_epoch > epoch, orden ASC.
        Usado por /sync/catch-up para recuperar eventos perdidos.
        """
        query = (
            "SELECT evento_id, tipo, vuelo_id, numero_asiento, "
            "estado_anterior, estado_nuevo, pasaporte_pasajero, "
            "nodo_origen, reloj_vectorial, motivo, timestamp_epoch, lamport_timestamp, "
            "CONVERT(VARCHAR(23), timestamp_utc, 126) AS timestamp_utc "
            "FROM eventos WHERE timestamp_epoch > %s "
            "ORDER BY timestamp_epoch ASC"
        )
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, (epoch,))
            return self._rows_to_dicts(cur, cur.fetchall())

    # ─────────────────────────────────────────
    # ESTADÍSTICAS
    # ─────────────────────────────────────────

    def get_flight_stats(self, vuelo_id: str) -> dict:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT clase, estado, COUNT(*) AS cantidad, "
                "SUM(CASE WHEN estado = 'Venta' THEN precio ELSE 0 END) AS ingresos "
                "FROM asientos WHERE vuelo_id = %s "
                "GROUP BY clase, estado",
                (vuelo_id,)
            )
            rows = self._rows_to_dicts(cur, cur.fetchall())

        por_estado: dict = {}
        por_clase:  dict = {}
        ingresos_total = 0.0
        total = 0

        for r in rows:
            estado = r["estado"]
            clase  = r["clase"]
            cant   = r["cantidad"]
            ing    = float(r["ingresos"] or 0)

            por_estado[estado] = por_estado.get(estado, 0) + cant
            por_clase[clase]   = por_clase.get(clase, 0) + cant
            ingresos_total    += ing
            total             += cant

        vendidos = por_estado.get("Venta", 0)
        return {
            "vuelo_id":       vuelo_id,
            "total_asientos": total,
            "por_estado":     por_estado,
            "por_clase":      por_clase,
            "ingresos_usd":   round(ingresos_total, 2),
            "ocupacion_pct":  round(vendidos / total * 100, 1) if total else 0,
        }

    def get_global_stats(self) -> dict:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT a.clase, a.estado, COUNT(*) AS cantidad, "
                "SUM(CASE WHEN a.estado = 'Venta' THEN a.precio ELSE 0 END) AS ingresos "
                "FROM asientos a JOIN vuelos v ON a.vuelo_id = v.vuelo_id "
                "WHERE v.activo = 1 "
                "GROUP BY a.clase, a.estado"
            )
            rows = self._rows_to_dicts(cur, cur.fetchall())
            cur.execute("SELECT COUNT(*) FROM vuelos WHERE activo = 1")
            total_vuelos = cur.fetchone()[0]

        por_estado: dict = {}
        por_clase:  dict = {}
        ingresos_total = 0.0
        total = 0

        for r in rows:
            estado = r["estado"]
            clase  = r["clase"]
            cant   = r["cantidad"]
            ing    = float(r["ingresos"] or 0)
            por_estado[estado] = por_estado.get(estado, 0) + cant
            por_clase[clase]   = por_clase.get(clase, 0) + cant
            ingresos_total    += ing
            total             += cant

        vendidos = por_estado.get("Venta", 0)
        return {
            "total_vuelos":   total_vuelos,
            "total_asientos": total,
            "por_estado":     por_estado,
            "por_clase":      por_clase,
            "ingresos_usd":   round(ingresos_total, 2),
            "ocupacion_pct":  round(vendidos / total * 100, 1) if total else 0,
        }

    # ─────────────────────────────────────────
    # ESTADOS DE VUELO
    # ─────────────────────────────────────────

    def update_flight_state(self, vuelo_id: str, estado: str) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "UPDATE vuelos SET estado = %s WHERE vuelo_id = %s",
                    (estado, vuelo_id)
                )
                affected = cur.rowcount
                conn.commit()
                return affected > 0
            except Exception:
                conn.rollback()
                raise

    def get_flights_for_state_update(self) -> list[dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT vuelo_id, fecha, "
                "CONVERT(VARCHAR(5), hora_salida,  108) AS hora_salida, "
                "CONVERT(VARCHAR(5), hora_llegada, 108) AS hora_llegada, "
                "estado "
                "FROM vuelos WHERE activo = 1"
            )
            return self._rows_to_dicts(cur, cur.fetchall())
