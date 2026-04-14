#!/usr/bin/env python3
# =============================================
# AEROLÍNEAS RAFAEL PABON
# generate_dataset.py — Generador del dataset de vuelos
#
# Genera un CSV con ~60 000 registros de vuelos sintéticos
# a partir de las rutas comerciales existentes.
#
# Uso:
#   python generate_dataset.py --output /vuelos/flights.csv
#
# El archivo CSV resultante se usa con load_flights.py.
# =============================================

import argparse
import csv
import os
import random
from datetime import date, timedelta, time


# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────

FECHA_INICIO = date(2024, 1, 1)
FECHA_FIN    = date(2026, 12, 31)   # ~3 años → ~60 000 vuelos con 60 rutas

AERONAVES = [
    "Boeing 737-800",
    "Airbus A320",
    "Boeing 787-9",
    "Airbus A350-900",
    "Embraer E195",
    "Boeing 777-300ER",
]

# Capacidad por tipo de aeronave
CAPACIDAD_POR_AERONAVE = {
    "Boeing 737-800":   174,
    "Airbus A320":      180,
    "Boeing 787-9":     296,
    "Airbus A350-900":  315,
    "Embraer E195":     124,
    "Boeing 777-300ER": 396,
}

# Rutas comerciales del sistema (origen, destino, distancia_km)
RUTAS = [
    ("MAD", "JFK", 5758), ("JFK", "MAD", 5768),
    ("MAD", "LHR", 1265), ("LHR", "MAD", 1267),
    ("MAD", "CDG", 1054), ("CDG", "MAD", 1055),
    ("MAD", "FCO", 1365), ("FCO", "MAD", 1362),
    ("MAD", "AMS", 1461), ("AMS", "MAD", 1463),
    ("JFK", "LHR", 5571), ("LHR", "JFK", 5570),
    ("JFK", "CDG", 5839), ("CDG", "JFK", 5837),
    ("JFK", "LAX", 3983), ("LAX", "JFK", 3979),
    ("JFK", "MIA", 1757), ("MIA", "JFK", 1755),
    ("JFK", "GRU", 7698), ("GRU", "JFK", 7696),
    ("LHR", "DXB", 5479), ("DXB", "LHR", 5476),
    ("LHR", "SIN", 10841), ("SIN", "LHR", 10838),
    ("LHR", "HKG", 9618), ("HKG", "LHR", 9620),
    ("LHR", "NRT", 9566), ("NRT", "LHR", 9563),
    ("CDG", "DXB", 5255), ("DXB", "CDG", 5257),
    ("CDG", "NRT", 9717), ("NRT", "CDG", 9720),
    ("DXB", "SIN", 5840), ("SIN", "DXB", 5843),
    ("DXB", "HKG", 5972), ("HKG", "DXB", 5974),
    ("DXB", "BOM", 1938), ("BOM", "DXB", 1935),
    ("DXB", "NRT", 7966), ("NRT", "DXB", 7964),
    ("SIN", "HKG", 2573), ("HKG", "SIN", 2575),
    ("SIN", "NRT", 5321), ("NRT", "SIN", 5318),
    ("SIN", "SYD", 6309), ("SYD", "SIN", 6311),
    ("HKG", "NRT", 2895), ("NRT", "HKG", 2892),
    ("NRT", "LAX", 8747), ("LAX", "NRT", 8750),
    ("LAX", "SYD", 12074), ("SYD", "LAX", 12076),
    ("GRU", "MAD", 9463), ("MAD", "GRU", 9461),
    ("GRU", "MIA", 7102), ("MIA", "GRU", 7100),
    ("MIA", "LAX", 3752), ("LAX", "MIA", 3754),
    ("VVI", "GRU", 3271), ("GRU", "VVI", 3268),
    ("VVI", "MIA", 6180), ("MIA", "VVI", 6183),
    ("FCO", "DXB", 3217), ("DXB", "FCO", 3219),
    ("AMS", "JFK", 5861), ("JFK", "AMS", 5858),
]

PREFIJO_VUELO = "RP"

HORARIOS_SALIDA = [
    (6, 0), (7, 30), (8, 45), (10, 15), (12, 0),
    (13, 30), (15, 0), (16, 45), (18, 30), (20, 0), (22, 15),
]


def generar_hora_llegada(hora_salida: time, distancia_km: int) -> time:
    """Estima la hora de llegada asumiendo 900 km/h de velocidad crucero."""
    minutos_vuelo = int(distancia_km / 900 * 60) + 45   # +45 min overhead
    total_min = hora_salida.hour * 60 + hora_salida.minute + minutos_vuelo
    total_min %= (24 * 60)   # ajuste si pasa medianoche (solo guardamos HH:MM del día)
    return time(total_min // 60, total_min % 60)


def main():
    parser = argparse.ArgumentParser(description="Genera dataset de vuelos ARLP")
    parser.add_argument(
        "--output", default="/vuelos/flights.csv",
        help="Ruta del archivo CSV de salida (default: /vuelos/flights.csv)"
    )
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)

    vuelos_generados = 0
    vuelo_counter = 1

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "vuelo_id", "origen", "destino", "fecha",
            "hora_salida", "hora_llegada", "aeronave", "capacidad",
        ])

        dia = FECHA_INICIO
        while dia <= FECHA_FIN:
            for ruta in RUTAS:
                origen, destino, distancia = ruta

                # No todos los días operan todas las rutas
                # Rutas largas: 3-4 días a la semana; cortas: diario
                if distancia > 8000:
                    if dia.weekday() not in (0, 2, 4, 6):   # lun, mié, vie, dom
                        continue
                elif distancia > 4000:
                    if dia.weekday() not in (0, 1, 2, 3, 4, 5):   # no sábado
                        continue
                # rutas <4000 km: todos los días

                aeronave  = random.choice(AERONAVES)
                capacidad = CAPACIDAD_POR_AERONAVE[aeronave]
                h, m      = random.choice(HORARIOS_SALIDA)
                hora_sal  = time(h, m)
                hora_lleg = generar_hora_llegada(hora_sal, distancia)

                vuelo_id = f"RP{vuelo_counter:05d}"
                writer.writerow([
                    vuelo_id, origen, destino,
                    dia.isoformat(),
                    hora_sal.strftime("%H:%M"),
                    hora_lleg.strftime("%H:%M"),
                    aeronave, capacidad,
                ])

                vuelo_counter   += 1
                vuelos_generados += 1

            dia += timedelta(days=1)

    print(f"Dataset generado: {vuelos_generados:,} vuelos → {args.output}")


if __name__ == "__main__":
    main()
