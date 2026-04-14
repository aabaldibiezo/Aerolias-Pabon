#!/usr/bin/env python3
# =============================================
# AEROLÍNEAS RAFAEL PABON
# load_csv.py — Carga el dataset oficial de vuelos
#
# Pasos:
#   1. Limpia datos de prueba (vuelos, asientos, pasajeros, eventos)
#   2. Inserta/actualiza los 15 aeropuertos del CSV
#   3. Inserta rutas entre todos los pares (origen, destino) del CSV
#   4. Carga los 60 000 vuelos con asientos (distribución 73/3/24)
#
# Uso dentro del contenedor:
#   docker exec arlp_nodo1 python //app/load_csv.py
#   docker exec arlp_nodo2 python //app/load_csv.py
#   docker exec arlp_nodo3 python //app/load_csv.py
# =============================================

import csv
import math
import random
import sys
import time
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import cfg

# ─────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────

CSV_PATH = "//app/VUELOS/flights.csv"

# 30 asientos por vuelo para el dataset masivo (3 clases)
PRIMERA_N   = 3
BUSINESS_N  = 6
ECONOMICA_N = 21
TOTAL_SEATS = PRIMERA_N + BUSINESS_N + ECONOMICA_N   # 30

PRECIO_PRIMERA   = 1200.0
PRECIO_BUSINESS  = 450.0
PRECIO_ECONOMICA = 150.0

P_VENTA   = 0.35
P_RESERVA = 0.03

# Nombres de pasajeros sintéticos
NOMBRES = [
    "Ana García", "Luis Martínez", "María López", "Carlos Rodríguez", "Laura Sánchez",
    "Jorge Hernández", "Isabel Pérez", "Antonio González", "Carmen Díaz", "Pablo Ruiz",
    "Sofia Chen", "Ahmed Al-Rashid", "Yuki Tanaka", "Emma Wilson", "John Smith",
    "Fatima Nakamura", "Oliver Brown", "Priya Sharma", "James Johnson", "Li Wei",
    "Amina Diallo", "Kenji Watanabe", "Nina Petrov", "Alejandro Reyes", "Aisha Okonkwo",
]

# Aeropuertos con coordenadas y metadatos
AIRPORTS = {
    "AMS": ("Amsterdam Schiphol",          "Amsterdam",   "Países Bajos",          "Europe/Amsterdam",   52.31,   4.76),
    "ATL": ("Hartsfield-Jackson Atlanta",  "Atlanta",     "Estados Unidos",        "America/New_York",   33.64, -84.43),
    "CAN": ("Guangzhou Baiyun",            "Guangzhou",   "China",                 "Asia/Shanghai",      23.39, 113.30),
    "DFW": ("Dallas/Fort Worth Intl",      "Dallas",      "Estados Unidos",        "America/Chicago",    32.90, -97.04),
    "DXB": ("Dubai International",         "Dubái",       "Emiratos Árabes",       "Asia/Dubai",         25.25,  55.36),
    "FRA": ("Frankfurt Airport",           "Frankfurt",   "Alemania",              "Europe/Berlin",      50.03,   8.57),
    "IST": ("Istanbul Airport",            "Estambul",    "Turquía",               "Europe/Istanbul",    41.27,  28.74),
    "LAX": ("Los Angeles Intl",            "Los Ángeles", "Estados Unidos",        "America/Los_Angeles",33.94,-118.41),
    "LON": ("London Heathrow",             "Londres",     "Reino Unido",           "Europe/London",      51.50,  -0.12),
    "MAD": ("Adolfo Suárez Madrid-Barajas","Madrid",      "España",                "Europe/Madrid",      40.47,  -3.56),
    "PAR": ("Charles de Gaulle",           "París",       "Francia",               "Europe/Paris",       48.85,   2.35),
    "PEK": ("Beijing Capital",             "Pekín",       "China",                 "Asia/Shanghai",      40.08, 116.60),
    "SAO": ("Guarulhos International",     "São Paulo",   "Brasil",                "America/Sao_Paulo", -23.43, -46.47),
    "SIN": ("Changi Airport",              "Singapur",    "Singapur",              "Asia/Singapore",      1.35, 103.99),
    "TYO": ("Narita International",        "Tokio",       "Japón",                 "Asia/Tokyo",         35.55, 139.78),
}

def _haversine(lat1, lon1, lat2, lon2) -> int:
    r = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return max(100, int(r * 2 * math.asin(math.sqrt(a))))

# Pre-calcular distancias entre todos los pares de aeropuertos
DISTANCES: dict[tuple, int] = {}
for o, (_, _, _, _, lat1, lon1) in AIRPORTS.items():
    for d, (_, _, _, _, lat2, lon2) in AIRPORTS.items():
        if o != d:
            DISTANCES[(o, d)] = _haversine(lat1, lon1, lat2, lon2)

def _arrival_time(dep_time: str, origin: str, destination: str) -> str:
    """Calcula hora de llegada estimada (900 km/h + 45 min overhead)."""
    h, m = map(int, dep_time.split(":"))
    km = DISTANCES.get((origin, destination), 2000)
    vuelo_min = int(km / 900 * 60) + 45
    total_min = h * 60 + m + vuelo_min
    total_min %= 1440  # ajustar si pasa medianoche
    return f"{total_min // 60:02d}:{total_min % 60:02d}"

def _aircraft_info(aircraft_id: int) -> tuple[str, int]:
    if aircraft_id <= 10: return "Boeing 737-800", 174
    if aircraft_id <= 20: return "Airbus A320", 180
    if aircraft_id <= 30: return "Boeing 787-9", 296
    if aircraft_id <= 40: return "Airbus A350-900", 315
    return "Boeing 777-300ER", 396

def _parse_date(flight_date: str) -> str:
    """MM/DD/YY → YYYY-MM-DD"""
    return datetime.strptime(flight_date.strip(), "%m/%d/%y").strftime("%Y-%m-%d")

def _gen_seats(vuelo_id: str) -> list[dict]:
    """Genera 30 asientos con distribución 73/3/24."""
    asientos = []
    for i in range(1, PRIMERA_N + 1):
        asientos.append({"num": f"{i}A", "clase": "primera",   "precio": PRECIO_PRIMERA})
    for i in range(1, PRIMERA_N + 1):
        asientos.append({"num": f"{i}B", "clase": "primera",   "precio": PRECIO_PRIMERA})
    for i in range(1, BUSINESS_N // 2 + 1):
        for col in ("C", "D"):
            asientos.append({"num": f"{i+PRIMERA_N}{col}", "clase": "business",  "precio": PRECIO_BUSINESS})
    fila = PRIMERA_N + BUSINESS_N // 2 + 1
    eco_count = 0
    for f in range(fila, 999):
        for col in ("A","B","C","D","E","F"):
            if eco_count >= ECONOMICA_N:
                break
            asientos.append({"num": f"{f}{col}", "clase": "economica", "precio": PRECIO_ECONOMICA})
            eco_count += 1
        if eco_count >= ECONOMICA_N:
            break
    # Asignar estado
    pasajeros_usados: set[str] = set()
    for a in asientos:
        r = random.random()
        if r < P_VENTA:
            a["estado"] = "Venta"
            p = f"P{random.randint(10000000, 99999999)}"
            a["pasaporte"] = p
            a["nombre"] = random.choice(NOMBRES)
        elif r < P_VENTA + P_RESERVA:
            a["estado"] = "Reserva"
            p = f"P{random.randint(10000000, 99999999)}"
            a["pasaporte"] = p
            a["nombre"] = random.choice(NOMBRES)
        else:
            a["estado"] = "Libre"
            a["pasaporte"] = None
            a["nombre"] = None
    return asientos


# ─────────────────────────────────────────
# LECTURA DEL CSV
# ─────────────────────────────────────────

def _read_csv() -> list[dict]:
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Las columnas tienen espacio al inicio
            rows.append({k.strip(): v.strip() for k, v in row.items()})
    return rows


# ─────────────────────────────────────────
# SQL SERVER
# ─────────────────────────────────────────

def _run_sqlserver(rows: list[dict]) -> None:
    import pymssql

    print(f"Conectando a SQL Server ({cfg.db_host}:{cfg.db_port}/{cfg.db_name})...")
    conn = pymssql.connect(
        server=cfg.db_host, port=cfg.db_port,
        user=cfg.db_user, password=cfg.db_password,
        database=cfg.db_name, charset="UTF-8", autocommit=False,
    )
    cur = conn.cursor()

    # ── 1. LIMPIAR DATOS ──
    print("Limpiando datos existentes...")
    for tabla in ("eventos", "asientos", "pasajeros", "vuelos"):
        cur.execute(f"DELETE FROM {tabla}")
    conn.commit()
    print("  OK — tablas vaciadas.")

    # ── 2. AEROPUERTOS ──
    print("Insertando/actualizando aeropuertos...")
    for cod, (nombre, ciudad, pais, tz, lat, lon) in AIRPORTS.items():
        cur.execute(
            "MERGE INTO aeropuertos AS target "
            "USING (SELECT %s AS codigo) AS src ON target.codigo = src.codigo "
            "WHEN NOT MATCHED THEN INSERT (codigo,nombre,ciudad,pais,timezone,latitud,longitud) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "WHEN MATCHED THEN UPDATE SET nombre=%s, ciudad=%s, pais=%s, timezone=%s, latitud=%s, longitud=%s;",
            (cod, cod, nombre, ciudad, pais, tz, lat, lon, nombre, ciudad, pais, tz, lat, lon)
        )
    conn.commit()
    print(f"  OK — {len(AIRPORTS)} aeropuertos.")

    # ── 3. RUTAS ──
    print("Insertando rutas comerciales...")
    pares = {(r["origin"], r["destination"]) for r in rows}
    rutas_insertadas = 0
    for (o, d) in pares:
        km = DISTANCES.get((o, d), 1000)
        cur.execute(
            "MERGE INTO rutas_comerciales AS target "
            "USING (SELECT %s AS origen, %s AS destino) AS src "
            "ON target.origen = src.origen AND target.destino = src.destino "
            "WHEN NOT MATCHED THEN INSERT (origen,destino,distancia_km,activa) VALUES (%s,%s,%s,1) "
            "WHEN MATCHED THEN UPDATE SET distancia_km=%s, activa=1;",
            (o, d, o, d, km, km)
        )
        rutas_insertadas += 1
    conn.commit()
    print(f"  OK — {rutas_insertadas} rutas.")

    # ── 4. VUELOS + ASIENTOS (con executemany para máxima velocidad) ──
    print(f"Cargando {len(rows):,} vuelos ({TOTAL_SEATS} asientos c/u) con executemany...")
    t0 = time.time()
    BATCH = 500   # vuelos por commit

    vuelos_buf:    list[tuple] = []
    asientos_buf:  list[tuple] = []
    pasajeros_buf: list[tuple] = []
    pasajeros_cache: set[str] = set()
    total_vuelos  = 0
    total_asientos = 0

    def _multirow_insert(cur, sql_prefix: str, rows_data: list[tuple], chunk: int = 1000):
        """Multi-row INSERT VALUES (...),(...) — mucho más rápido que executemany en pymssql."""
        for start in range(0, len(rows_data), chunk):
            chunk_data = rows_data[start:start+chunk]
            placeholders = ",".join(["(%s)" % ",".join(["%s"]*len(r)) for r in chunk_data])
            flat = [v for r in chunk_data for v in r]
            cur.execute(f"{sql_prefix} VALUES {placeholders}", flat)

    def flush_sql():
        if vuelos_buf:
            # activo omitido — DEFAULT 1 en la tabla
            _multirow_insert(cur,
                "INSERT INTO vuelos "
                "(vuelo_id,origen,destino,fecha,hora_salida,hora_llegada,aeronave,capacidad,estado)",
                vuelos_buf,
            )
            vuelos_buf.clear()
        if pasajeros_buf:
            # pasajeros_cache garantiza que no hay duplicados — INSERT directo
            _multirow_insert(cur,
                "INSERT INTO pasajeros (pasaporte, nombre)",
                [(p, n) for p, n, _ in pasajeros_buf],
            )
            pasajeros_buf.clear()
        if asientos_buf:
            _multirow_insert(cur,
                "INSERT INTO asientos "
                "(vuelo_id,numero_asiento,clase,estado,pasaporte_pasajero,precio)",
                asientos_buf,
            )
            asientos_buf.clear()
        conn.commit()

    for i, row in enumerate(rows):
        vid       = f"RP{i+1:05d}"
        dep       = row["flight_time"]
        orig      = row["origin"]
        dest      = row["destination"]
        ac_id     = int(row["aircraft_id"])
        aeronave, capacidad = _aircraft_info(ac_id)
        fecha     = _parse_date(row["flight_date"])
        hora_lleg = _arrival_time(dep, orig, dest)
        estado    = row["status"]

        vuelos_buf.append((vid, orig, dest, fecha, dep, hora_lleg, aeronave, capacidad, estado))
        total_vuelos += 1

        for a in _gen_seats(vid):
            pax = a["pasaporte"]
            if pax and pax not in pasajeros_cache:
                pasajeros_buf.append((pax, a["nombre"], pax))
                pasajeros_cache.add(pax)
            asientos_buf.append(
                (vid, a["num"], a["clase"], a["estado"], pax, a["precio"])
            )
            total_asientos += 1

        if (i + 1) % BATCH == 0:
            flush_sql()
            elapsed = time.time() - t0
            speed = total_vuelos / elapsed if elapsed > 0 else 1
            remaining = (len(rows) - total_vuelos) / speed
            print(f"  {total_vuelos:,}/{len(rows):,} vuelos | {total_asientos:,} asientos | "
                  f"{elapsed:.0f}s | ~{remaining:.0f}s restantes")

    flush_sql()   # último batch
    conn.close()

    elapsed = time.time() - t0
    print(f"\nSQL Server completado:")
    print(f"  Vuelos:   {total_vuelos:,}")
    print(f"  Asientos: {total_asientos:,}")
    print(f"  Tiempo:   {elapsed:.1f}s")


# ─────────────────────────────────────────
# MONGODB
# ─────────────────────────────────────────

def _run_mongodb(rows: list[dict]) -> None:
    from urllib.parse import quote_plus
    import pymongo

    print(f"Conectando a MongoDB ({cfg.db_host}:{cfg.db_port}/{cfg.db_name})...")
    uri = (f"mongodb://{quote_plus(cfg.db_user)}:{quote_plus(cfg.db_password)}"
           f"@{cfg.db_host}:{cfg.db_port}/{cfg.db_name}?authSource=admin")
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client[cfg.db_name]

    # ── 1. LIMPIAR DATOS ──
    print("Limpiando datos existentes...")
    db.eventos.delete_many({})
    db.asientos.delete_many({})
    db.pasajeros.delete_many({})
    db.vuelos.delete_many({})
    print("  OK — colecciones vaciadas.")

    # Actualizar validador de vuelos para incluir todos los estados del CSV
    db.command({
        "collMod": "vuelos",
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["_id","origen","destino","fecha","hora_salida",
                             "hora_llegada","aeronave","capacidad","activo"],
                "additionalProperties": False,
                "properties": {
                    "_id":          {"bsonType": "string"},
                    "origen":       {"bsonType": "string"},
                    "destino":      {"bsonType": "string"},
                    "fecha":        {"bsonType": "string"},
                    "hora_salida":  {"bsonType": "string"},
                    "hora_llegada": {"bsonType": "string"},
                    "aeronave":     {"bsonType": "string"},
                    "capacidad":    {"bsonType": "int"},
                    "activo":       {"bsonType": "bool"},
                    "estado":       {"bsonType": "string",
                                     "enum": ["SCHEDULED","BOARDING","IN_FLIGHT",
                                              "DEPARTED","LANDED","ARRIVED",
                                              "DELAYED","CANCELLED"]},
                }
            }
        },
        "validationLevel": "moderate",
        "validationAction": "error",
    })

    # ── 2. AEROPUERTOS ──
    print("Insertando/actualizando aeropuertos...")
    for cod, (nombre, ciudad, pais, tz, lat, lon) in AIRPORTS.items():
        db.aeropuertos.update_one(
            {"_id": cod},
            {"$set": {"nombre": nombre, "ciudad": ciudad, "pais": pais,
                      "timezone": tz, "latitud": float(lat), "longitud": float(lon)}},
            upsert=True,
        )
    print(f"  OK — {len(AIRPORTS)} aeropuertos.")

    # ── 3. RUTAS ──
    print("Insertando rutas comerciales...")
    pares = {(r["origin"], r["destination"]) for r in rows}
    for (o, d) in pares:
        km = DISTANCES.get((o, d), 1000)
        db.rutas_comerciales.update_one(
            {"origen": o, "destino": d},
            {"$set": {"distancia_km": km, "activa": True}},
            upsert=True,
        )
    print(f"  OK — {len(pares)} rutas.")

    # ── 4. VUELOS + ASIENTOS ──
    print(f"Cargando {len(rows):,} vuelos ({TOTAL_SEATS} asientos c/u)...")
    t0 = time.time()
    BATCH = 500
    vuelos_buf:   list[dict] = []
    asientos_buf: list[dict] = []
    pasajeros_buf: list[dict] = []
    pasajeros_cache: set[str] = set()
    total_vuelos = 0
    total_asientos = 0
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

    def flush():
        if vuelos_buf:
            try:
                db.vuelos.insert_many(vuelos_buf, ordered=False)
            except Exception:
                pass
            vuelos_buf.clear()
        if pasajeros_buf:
            try:
                db.pasajeros.insert_many(pasajeros_buf, ordered=False)
            except Exception:
                pass
            pasajeros_buf.clear()
        if asientos_buf:
            db.asientos.insert_many(asientos_buf, ordered=False)
            asientos_buf.clear()

    for i, row in enumerate(rows):
        vid = f"RP{i+1:05d}"
        dep  = row["flight_time"]
        orig = row["origin"]
        dest = row["destination"]
        ac_id = int(row["aircraft_id"])
        aeronave, capacidad = _aircraft_info(ac_id)
        fecha     = _parse_date(row["flight_date"])
        hora_lleg = _arrival_time(dep, orig, dest)
        estado    = row["status"]

        vuelos_buf.append({
            "_id": vid, "origen": orig, "destino": dest,
            "fecha": fecha, "hora_salida": dep, "hora_llegada": hora_lleg,
            "aeronave": aeronave, "capacidad": capacidad,
            "activo": True, "estado": estado,
        })
        total_vuelos += 1

        asientos = _gen_seats(vid)
        for a in asientos:
            pax = a["pasaporte"]
            if pax and pax not in pasajeros_cache:
                pasajeros_buf.append({
                    "_id": pax, "nombre": a["nombre"],
                    "email": None, "created_at": ahora,
                })
                pasajeros_cache.add(pax)
            asiento_doc = {
                "vuelo_id": vid, "numero_asiento": a["num"],
                "clase": a["clase"], "estado": a["estado"],
                "precio": a["precio"], "updated_at": ahora,
            }
            if pax:   # no incluir el campo si es None (validator solo acepta string)
                asiento_doc["pasaporte_pasajero"] = pax
            asientos_buf.append(asiento_doc)
            total_asientos += 1

        if (i + 1) % BATCH == 0:
            flush()
            elapsed = time.time() - t0
            speed = total_vuelos / elapsed
            remaining = (len(rows) - total_vuelos) / speed if speed > 0 else 0
            print(f"  {total_vuelos:,}/{len(rows):,} vuelos | {total_asientos:,} asientos | "
                  f"{elapsed:.0f}s | ~{remaining:.0f}s restantes")

    flush()
    client.close()

    elapsed = time.time() - t0
    print(f"\nMongoDB completado:")
    print(f"  Vuelos:   {total_vuelos:,}")
    print(f"  Asientos: {total_asientos:,}")
    print(f"  Tiempo:   {elapsed:.1f}s")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    print(f"=== ARLP — Carga del dataset CSV ===")
    print(f"Nodo {cfg.node_id} | Motor: {cfg.db_engine.upper()}")
    print(f"CSV: {CSV_PATH}")

    rows = _read_csv()
    print(f"Filas leídas: {len(rows):,}")

    if cfg.db_engine == "sqlserver":
        _run_sqlserver(rows)
    else:
        _run_mongodb(rows)

    print("\n=== Carga completada exitosamente ===")
