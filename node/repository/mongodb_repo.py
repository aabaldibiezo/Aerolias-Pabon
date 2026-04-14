# =============================================
# AEROLÍNEAS RAFAEL PABON
# repository/mongodb_repo.py — Implementación MongoDB
# Librería: pymongo
#
# Normaliza los documentos MongoDB al mismo formato de dict
# que usa SQLServerRepository, para que la capa de servicios
# sea agnóstica al motor.
# =============================================

from datetime import datetime, timezone
from urllib.parse import quote_plus

import pymongo
from pymongo import MongoClient

from .base import BaseRepository
from config import cfg


class MongoDBRepository(BaseRepository):

    def __init__(self):
        # MongoClient mantiene un pool de conexiones interno
        # quote_plus escapa caracteres especiales (@, !, etc.) en usuario/contraseña
        uri = (
            f"mongodb://{quote_plus(cfg.db_user)}:{quote_plus(cfg.db_password)}"
            f"@{cfg.db_host}:{cfg.db_port}/{cfg.db_name}"
            f"?authSource=admin"
        )
        self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self._db     = self._client[cfg.db_name]

    # ─────────────────────────────────────────
    # NORMALIZACIÓN
    # Convierte _id de MongoDB al campo nombrado
    # que usa SQL Server (codigo, vuelo_id, pasaporte)
    # ─────────────────────────────────────────

    @staticmethod
    def _norm_aeropuerto(doc: dict) -> dict:
        if doc is None:
            return None
        d = dict(doc)
        d["codigo"] = str(d.pop("_id"))
        return d

    @staticmethod
    def _norm_vuelo(doc: dict) -> dict:
        if doc is None:
            return None
        d = dict(doc)
        d["vuelo_id"] = str(d.pop("_id"))
        return d

    @staticmethod
    def _norm_pasajero(doc: dict) -> dict:
        if doc is None:
            return None
        d = dict(doc)
        d["pasaporte"] = str(d.pop("_id"))
        # Convertir datetime a string ISO para consistencia con SQL Server
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].strftime("%Y-%m-%dT%H:%M:%S")
        return d

    @staticmethod
    def _norm_asiento(doc: dict) -> dict:
        if doc is None:
            return None
        d = dict(doc)
        # ObjectId → string (equivalente al INT IDENTITY de SQL Server)
        d["asiento_id"] = str(d.pop("_id"))
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].strftime("%Y-%m-%dT%H:%M:%S")
        return d

    @staticmethod
    def _norm_evento(doc: dict) -> dict:
        if doc is None:
            return None
        d = dict(doc)
        d["evento_id"] = str(d.pop("_id"))
        if isinstance(d.get("timestamp_utc"), datetime):
            d["timestamp_utc"] = d["timestamp_utc"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        d["aplicado"] = bool(d.get("aplicado", True))
        return d

    # ─────────────────────────────────────────
    # AEROPUERTOS
    # ─────────────────────────────────────────

    def get_airports(self) -> list[dict]:
        docs = self._db.aeropuertos.find({}, {"_id": 1, "nombre": 1, "ciudad": 1,
                                              "pais": 1, "timezone": 1,
                                              "latitud": 1, "longitud": 1}
                                         ).sort("ciudad", 1)
        return [self._norm_aeropuerto(d) for d in docs]

    def get_airport(self, codigo: str) -> dict | None:
        doc = self._db.aeropuertos.find_one({"_id": codigo.upper()})
        return self._norm_aeropuerto(doc)

    # ─────────────────────────────────────────
    # RUTAS (grafo para Dijkstra)
    # ─────────────────────────────────────────

    def get_routes(self) -> list[dict]:
        docs = self._db.rutas_comerciales.find(
            {"activa": True},
            {"_id": 0, "origen": 1, "destino": 1, "distancia_km": 1}
        )
        return list(docs)

    # ─────────────────────────────────────────
    # VUELOS
    # ─────────────────────────────────────────

    def search_flights(
        self,
        origen:  str | None = None,
        destino: str | None = None,
        fecha:   str | None = None,
    ) -> list[dict]:
        filtro: dict = {"activo": True}
        if origen:
            filtro["origen"]  = origen.upper()
        if destino:
            filtro["destino"] = destino.upper()
        if fecha:
            filtro["fecha"]   = fecha

        vuelos = list(self._db.vuelos.find(filtro).sort(
            [("fecha", 1), ("hora_salida", 1)]
        ))

        # Enriquecer con datos de aeropuertos (equivalente al JOIN de SQL Server)
        codigos = {v["origen"] for v in vuelos} | {v["destino"] for v in vuelos}
        aeropuertos = {
            a["_id"]: a
            for a in self._db.aeropuertos.find({"_id": {"$in": list(codigos)}})
        }

        resultado = []
        for v in vuelos:
            d = self._norm_vuelo(v)
            ao = aeropuertos.get(d["origen"],  {})
            ad = aeropuertos.get(d["destino"], {})
            d["ciudad_origen"]    = ao.get("ciudad", "")
            d["timezone_origen"]  = ao.get("timezone", "UTC")
            d["ciudad_destino"]   = ad.get("ciudad", "")
            d["timezone_destino"] = ad.get("timezone", "UTC")
            resultado.append(d)

        return resultado

    def get_flight(self, vuelo_id: str) -> dict | None:
        v = self._db.vuelos.find_one({"_id": vuelo_id})
        if not v:
            return None

        d  = self._norm_vuelo(v)
        ao = self._db.aeropuertos.find_one({"_id": d["origen"]})  or {}
        ad = self._db.aeropuertos.find_one({"_id": d["destino"]}) or {}

        d["ciudad_origen"]    = ao.get("ciudad", "")
        d["timezone_origen"]  = ao.get("timezone", "UTC")
        d["lat_origen"]       = ao.get("latitud", 0)
        d["lon_origen"]       = ao.get("longitud", 0)
        d["ciudad_destino"]   = ad.get("ciudad", "")
        d["timezone_destino"] = ad.get("timezone", "UTC")
        d["lat_destino"]      = ad.get("latitud", 0)
        d["lon_destino"]      = ad.get("longitud", 0)
        return d

    # ─────────────────────────────────────────
    # ASIENTOS
    # ─────────────────────────────────────────

    def get_seats(self, vuelo_id: str) -> list[dict]:
        # Ordenar espejando el ORDER BY de SQL Server:
        # clase (primera→business→economica) y luego número de fila y columna
        orden_clase = {"primera": 1, "business": 2, "economica": 3}
        docs = list(self._db.asientos.find({"vuelo_id": vuelo_id}))

        def sort_key(d):
            num = d["numero_asiento"]
            col = num[-1]          # última letra
            fila = int(num[:-1])   # parte numérica
            return (orden_clase.get(d["clase"], 9), fila, col)

        docs.sort(key=sort_key)
        return [self._norm_asiento(d) for d in docs]

    def get_seat(self, vuelo_id: str, numero_asiento: str) -> dict | None:
        doc = self._db.asientos.find_one(
            {"vuelo_id": vuelo_id, "numero_asiento": numero_asiento}
        )
        return self._norm_asiento(doc)

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
        ahora = datetime.now(timezone.utc).replace(tzinfo=None)

        # find_one_and_update es atómica a nivel de documento en MongoDB.
        # El filtro incluye `estado == estado_anterior` para implementar
        # "el primero gana": si el estado ya cambió, no hay match y retorna None.
        resultado = self._db.asientos.find_one_and_update(
            {
                "vuelo_id":       vuelo_id,
                "numero_asiento": numero_asiento,
                "estado":         estado_anterior,   # condición de guarda
            },
            {
                "$set": {
                    "estado":             estado_nuevo,
                    "pasaporte_pasajero": pasaporte,
                    "updated_at":         ahora,
                }
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if resultado is None:
            # El estado ya no coincide — el primer nodo ganó, descartamos
            return False

        # Registrar evento en el log del reloj vectorial
        evento_doc = {
            "tipo":               tipo,
            "vuelo_id":           vuelo_id,
            "numero_asiento":     numero_asiento,
            "estado_anterior":    estado_anterior,
            "estado_nuevo":       estado_nuevo,
            "pasaporte_pasajero": pasaporte,
            "nodo_origen":        nodo_origen,
            "reloj_vectorial":    reloj_vectorial,
            "timestamp_utc":      ahora,
            "timestamp_epoch":    timestamp_epoch,
            "lamport_timestamp":  lamport_timestamp,
            "aplicado":           True,
        }
        if motivo:
            evento_doc["motivo"] = motivo
        self._db.eventos.insert_one(evento_doc)

        return True

    # ─────────────────────────────────────────
    # PASAJEROS
    # ─────────────────────────────────────────

    def get_passenger(self, pasaporte: str) -> dict | None:
        doc = self._db.pasajeros.find_one({"_id": pasaporte})
        return self._norm_pasajero(doc)

    def upsert_passenger(
        self,
        pasaporte: str,
        nombre:    str,
        email:     str | None = None,
    ) -> dict:
        # insert_one si no existe; si ya existe no sobreescribe el nombre
        self._db.pasajeros.update_one(
            {"_id": pasaporte},
            {
                "$setOnInsert": {
                    "_id":        pasaporte,
                    "nombre":     nombre,
                    "email":      email,
                    "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }
            },
            upsert=True,
        )
        return self.get_passenger(pasaporte)

    # ─────────────────────────────────────────
    # EVENTOS (reloj vectorial)
    # ─────────────────────────────────────────

    def get_events_since(
        self,
        timestamp_utc: datetime,
        nodo_origen:   int | None = None,
    ) -> list[dict]:
        filtro: dict = {"timestamp_utc": {"$gt": timestamp_utc}}
        if nodo_origen is not None:
            filtro["nodo_origen"] = nodo_origen

        docs = self._db.eventos.find(filtro).sort("timestamp_utc", 1)
        return [self._norm_evento(d) for d in docs]

    def get_events_since_epoch(self, epoch: int) -> list[dict]:
        """
        Devuelve todos los eventos con timestamp_epoch > epoch, orden ASC.
        Usado por /sync/catch-up para recuperar eventos perdidos.
        """
        docs = (
            self._db.eventos
            .find({"timestamp_epoch": {"$gt": epoch}})
            .sort("timestamp_epoch", 1)
        )
        return [self._norm_evento(d) for d in docs]

    # ─────────────────────────────────────────
    # ESTADÍSTICAS
    # ─────────────────────────────────────────

    def get_flight_stats(self, vuelo_id: str) -> dict:
        pipeline = [
            {"$match": {"vuelo_id": vuelo_id}},
            {"$group": {
                "_id": {"clase": "$clase", "estado": "$estado"},
                "cantidad": {"$sum": 1},
                "ingresos": {"$sum": {
                    "$cond": [{"$eq": ["$estado", "Venta"]}, "$precio", 0]
                }},
            }},
        ]
        rows = list(self._db.asientos.aggregate(pipeline))

        por_estado: dict = {}
        por_clase:  dict = {}
        ingresos_total = 0.0
        total = 0

        for r in rows:
            estado = r["_id"]["estado"]
            clase  = r["_id"]["clase"]
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
        vuelos_activos = [
            d["_id"] for d in self._db.vuelos.find({"activo": True}, {"_id": 1})
        ]
        pipeline = [
            {"$match": {"vuelo_id": {"$in": vuelos_activos}}},
            {"$group": {
                "_id": {"clase": "$clase", "estado": "$estado"},
                "cantidad": {"$sum": 1},
                "ingresos": {"$sum": {
                    "$cond": [{"$eq": ["$estado", "Venta"]}, "$precio", 0]
                }},
            }},
        ]
        rows = list(self._db.asientos.aggregate(pipeline))

        por_estado: dict = {}
        por_clase:  dict = {}
        ingresos_total = 0.0
        total = 0

        for r in rows:
            estado = r["_id"]["estado"]
            clase  = r["_id"]["clase"]
            cant   = r["cantidad"]
            ing    = float(r["ingresos"] or 0)
            por_estado[estado] = por_estado.get(estado, 0) + cant
            por_clase[clase]   = por_clase.get(clase, 0) + cant
            ingresos_total    += ing
            total             += cant

        vendidos = por_estado.get("Venta", 0)
        return {
            "total_vuelos":   len(vuelos_activos),
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
        result = self._db.vuelos.update_one(
            {"_id": vuelo_id},
            {"$set": {"estado": estado}},
        )
        return result.matched_count > 0

    def get_flights_for_state_update(self) -> list[dict]:
        docs = self._db.vuelos.find(
            {"activo": True},
            {"_id": 1, "fecha": 1, "hora_salida": 1, "hora_llegada": 1, "estado": 1},
        )
        result = []
        for d in docs:
            result.append({
                "vuelo_id":    str(d["_id"]),
                "fecha":       d.get("fecha", ""),
                "hora_salida": d.get("hora_salida", "00:00"),
                "hora_llegada": d.get("hora_llegada", "00:00"),
                "estado":      d.get("estado", "SCHEDULED"),
            })
        return result
