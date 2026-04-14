#!/usr/bin/env python3
# =============================================
# AEROLÍNEAS RAFAEL PABON
# load_flights.py — Carga masiva del dataset de vuelos
#
# Lee /vuelos/flights.csv e inserta los registros en la BD del nodo.
# Para cada vuelo, genera los asientos con la distribución:
#   73% → Venta (con pasajeros sintéticos)
#    3% → Reserva (con pasajeros sintéticos)
#   24% → Libre
#
# Uso:
#   python load_flights.py [--csv /vuelos/flights.csv] [--batch 500] [--skip 0]
#
# El script carga variables de entorno desde .env si existe.
# También se puede ejecutar dentro del contenedor nodo:
#   docker exec arlp_nodo1 python /app/load_flights.py
# =============================================

import argparse
import csv
import math
import os
import random
import sys
import time
from datetime import datetime, timezone
from typing import Iterator

# Cargar .env si existe (útil fuera de Docker)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ─────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────

CLASES_CONFIG = [
    # (clase,       cantidad, precio_base, letra_cols)
    ("primera",     10,       1200.0, ["A", "B"]),
    ("business",    20,       450.0,  ["A", "B", "C", "D"]),
    ("economica",   None,     150.0,  ["A", "B", "C", "D", "E", "F"]),   # resto
]

# Probabilidades de distribución por asiento
P_VENTA    = 0.73
P_RESERVA  = 0.03
# El resto queda Libre

# Nombres de pasajeros sintéticos
NOMBRES = [
    "Ana García", "Luis Martínez", "María López", "Carlos Rodríguez", "Laura Sánchez",
    "Jorge Hernández", "Isabel Pérez", "Antonio González", "Carmen Díaz", "Pablo Ruiz",
    "Sofia Chen", "Ahmed Al-Rashid", "Yuki Tanaka", "Emma Wilson", "John Smith",
    "Fatima Nakamura", "Oliver Brown", "Priya Sharma", "James Johnson", "Li Wei",
]


def _generar_asientos(vuelo_id: str, capacidad: int) -> list[dict]:
    """
    Genera la lista de asientos para un vuelo con la distribución 73/3/24.
    Retorna lista de dicts con: numero_asiento, clase, estado, pasaporte, precio
    """
    asientos = []
    fila = 1

    # Primera clase: filas 1–N (10 asientos máx)
    primera_total = CLASES_CONFIG[0][1]
    primera_filas = math.ceil(primera_total / len(CLASES_CONFIG[0][3]))

    for f in range(1, primera_filas + 1):
        for col in CLASES_CONFIG[0][3]:
            if len([a for a in asientos if a["clase"] == "primera"]) >= primera_total:
                break
            asientos.append({
                "numero_asiento": f"{f}{col}",
                "clase":          "primera",
                "precio":         CLASES_CONFIG[0][2],
            })
        fila = f + 1

    # Business: filas siguientes (20 asientos máx)
    business_total = CLASES_CONFIG[1][1]
    business_filas = math.ceil(business_total / len(CLASES_CONFIG[1][3]))
    for f in range(fila, fila + business_filas):
        for col in CLASES_CONFIG[1][3]:
            if len([a for a in asientos if a["clase"] == "business"]) >= business_total:
                break
            asientos.append({
                "numero_asiento": f"{f}{col}",
                "clase":          "business",
                "precio":         CLASES_CONFIG[1][2],
            })
    fila += business_filas

    # Económica: filas restantes hasta completar capacidad
    economica_cols = CLASES_CONFIG[2][3]
    while len(asientos) < capacidad:
        for col in economica_cols:
            if len(asientos) >= capacidad:
                break
            asientos.append({
                "numero_asiento": f"{fila}{col}",
                "clase":          "economica",
                "precio":         CLASES_CONFIG[2][2],
            })
        fila += 1

    # Asignar estados con distribución 73/3/24
    for idx, a in enumerate(asientos):
        r = random.random()
        if r < P_VENTA:
            a["estado"]    = "Venta"
            a["pasaporte"] = f"P{random.randint(10000000, 99999999)}"
        elif r < P_VENTA + P_RESERVA:
            a["estado"]    = "Reserva"
            a["pasaporte"] = f"P{random.randint(10000000, 99999999)}"
        else:
            a["estado"]    = "Libre"
            a["pasaporte"] = None

    return asientos


def _rows_from_csv(filepath: str, skip: int = 0) -> Iterator[dict]:
    """Itera las filas del CSV a partir de `skip`."""
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i < skip:
                continue
            yield row


# ─────────────────────────────────────────
# CARGA EN SQL SERVER
# ─────────────────────────────────────────

def _load_sqlserver(rows: list[dict], batch_size: int, verbose: bool) -> None:
    import pymssql
    from config import cfg

    conn = pymssql.connect(
        server   = cfg.db_host,
        port     = cfg.db_port,
        user     = cfg.db_user,
        password = cfg.db_password,
        database = cfg.db_name,
        charset  = "UTF-8",
        autocommit = False,
    )
    cur = conn.cursor()

    # Pasajeros sintéticos a upsert (solo una vez por pasaporte)
    pasajeros_vistos: set[str] = set()
    total_vuelos = 0
    total_asientos = 0
    t0 = time.time()

    for i, row in enumerate(rows):
        vuelo_id  = row["vuelo_id"]
        capacidad = int(row["capacidad"])

        # Insertar vuelo (ignorar si ya existe)
        try:
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = %s) "
                "INSERT INTO vuelos "
                "(vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, "
                " aeronave, capacidad, activo, estado) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 'SCHEDULED')",
                (vuelo_id, vuelo_id, row["origen"], row["destino"],
                 row["fecha"], row["hora_salida"], row["hora_llegada"],
                 row["aeronave"], capacidad)
            )
        except Exception as exc:
            if verbose:
                print(f"  SKIP vuelo {vuelo_id}: {exc}")
            continue

        asientos = _generar_asientos(vuelo_id, capacidad)

        for a in asientos:
            pasaporte = a["pasaporte"]

            # Upsert pasajero sintético si aplica
            if pasaporte and pasaporte not in pasajeros_vistos:
                nombre = random.choice(NOMBRES)
                cur.execute(
                    "IF NOT EXISTS (SELECT 1 FROM pasajeros WHERE pasaporte = %s) "
                    "INSERT INTO pasajeros (pasaporte, nombre) VALUES (%s, %s)",
                    (pasaporte, pasaporte, nombre)
                )
                pasajeros_vistos.add(pasaporte)

            cur.execute(
                "INSERT INTO asientos "
                "(vuelo_id, numero_asiento, clase, estado, pasaporte_pasajero, precio) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (vuelo_id, a["numero_asiento"], a["clase"],
                 a["estado"], a["pasaporte"], a["precio"])
            )
            total_asientos += 1

        total_vuelos += 1

        if (i + 1) % batch_size == 0:
            conn.commit()
            elapsed = time.time() - t0
            if verbose:
                print(f"  Insertados {total_vuelos:,} vuelos / {total_asientos:,} asientos "
                      f"({elapsed:.1f}s)")

    conn.commit()
    conn.close()
    elapsed = time.time() - t0
    print(f"\nSQL Server: {total_vuelos:,} vuelos, {total_asientos:,} asientos "
          f"en {elapsed:.1f}s")


# ─────────────────────────────────────────
# CARGA EN MONGODB
# ─────────────────────────────────────────

def _load_mongodb(rows: list[dict], batch_size: int, verbose: bool) -> None:
    from urllib.parse import quote_plus
    import pymongo
    from config import cfg

    uri = (
        f"mongodb://{quote_plus(cfg.db_user)}:{quote_plus(cfg.db_password)}"
        f"@{cfg.db_host}:{cfg.db_port}/{cfg.db_name}?authSource=admin"
    )
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client[cfg.db_name]

    pasajeros_vistos: set[str] = set()
    vuelos_buf:   list[dict] = []
    asientos_buf: list[dict] = []
    pasajeros_buf: list[dict] = []
    total_vuelos = 0
    total_asientos = 0
    t0 = time.time()

    def flush():
        if vuelos_buf:
            try:
                db.vuelos.insert_many(vuelos_buf, ordered=False)
            except pymongo.errors.BulkWriteError:
                pass
            vuelos_buf.clear()
        if asientos_buf:
            db.asientos.insert_many(asientos_buf, ordered=False)
            asientos_buf.clear()
        if pasajeros_buf:
            try:
                db.pasajeros.insert_many(pasajeros_buf, ordered=False)
            except pymongo.errors.BulkWriteError:
                pass
            pasajeros_buf.clear()

    for i, row in enumerate(rows):
        vuelo_id  = row["vuelo_id"]
        capacidad = int(row["capacidad"])

        vuelos_buf.append({
            "_id":          vuelo_id,
            "origen":       row["origen"],
            "destino":      row["destino"],
            "fecha":        row["fecha"],
            "hora_salida":  row["hora_salida"],
            "hora_llegada": row["hora_llegada"],
            "aeronave":     row["aeronave"],
            "capacidad":    capacidad,
            "activo":       True,
            "estado":       "SCHEDULED",
        })
        total_vuelos += 1

        asientos = _generar_asientos(vuelo_id, capacidad)
        for a in asientos:
            pasaporte = a["pasaporte"]

            if pasaporte and pasaporte not in pasajeros_vistos:
                nombre = random.choice(NOMBRES)
                pasajeros_buf.append({
                    "_id":        pasaporte,
                    "nombre":     nombre,
                    "email":      None,
                    "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
                })
                pasajeros_vistos.add(pasaporte)

            asientos_buf.append({
                "vuelo_id":           vuelo_id,
                "numero_asiento":     a["numero_asiento"],
                "clase":              a["clase"],
                "estado":             a["estado"],
                "pasaporte_pasajero": pasaporte,
                "precio":             a["precio"],
                "updated_at":         datetime.now(timezone.utc).replace(tzinfo=None),
            })
            total_asientos += 1

        if (i + 1) % batch_size == 0:
            flush()
            elapsed = time.time() - t0
            if verbose:
                print(f"  Insertados {total_vuelos:,} vuelos / {total_asientos:,} asientos "
                      f"({elapsed:.1f}s)")

    flush()
    client.close()
    elapsed = time.time() - t0
    print(f"\nMongoDB: {total_vuelos:,} vuelos, {total_asientos:,} asientos "
          f"en {elapsed:.1f}s")


# ─────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Carga masiva de vuelos ARLP")
    parser.add_argument("--csv",     default="/vuelos/flights.csv",
                        help="Ruta del CSV de vuelos")
    parser.add_argument("--batch",   type=int, default=500,
                        help="Tamaño de lote para commit parcial (default: 500)")
    parser.add_argument("--skip",    type=int, default=0,
                        help="Omitir las primeras N filas (útil para reanudar)")
    parser.add_argument("--verbose", action="store_true",
                        help="Mostrar progreso detallado")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"ERROR: archivo no encontrado: {args.csv}", file=sys.stderr)
        sys.exit(1)

    from config import cfg

    print(f"Cargando {args.csv} → nodo{cfg.node_id} ({cfg.db_engine.upper()}) ...")

    # Leer todas las filas en memoria (CSV de ~10 MB, razonable)
    rows = list(_rows_from_csv(args.csv, skip=args.skip))
    print(f"Filas a procesar: {len(rows):,}")

    if cfg.db_engine == "sqlserver":
        _load_sqlserver(rows, args.batch, args.verbose)
    else:
        _load_mongodb(rows, args.batch, args.verbose)

    print("Carga completada.")


if __name__ == "__main__":
    main()
