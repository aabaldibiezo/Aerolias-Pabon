# =============================================
# AEROLÍNEAS RAFAEL PABON
# tsp.py — Algoritmo del Viajero (TSP) con heurística del vecino más cercano
#
# Dado un aeropuerto de origen, calcula un recorrido que visita todos los
# aeropuertos alcanzables minimizando el costo total (km) o tiempo (horas).
#
# Heurística: Vecino más cercano (Nearest Neighbor)
#   1. Partir del origen.
#   2. En cada paso, ir al aeropuerto no visitado más cercano
#      (usando Dijkstra cuando no hay arista directa).
#   3. Repetir hasta visitar todos los alcanzables.
#   4. Intentar regresar al origen (circuito).
#
# Criterios:
#   'costo'  → peso = distancia_km
#   'tiempo' → peso = distancia_km / 900  (horas, velocidad crucero 900 km/h)
# =============================================

import heapq


def _dijkstra(graph: dict[str, dict[str, float]], start: str) -> dict[str, float]:
    """
    Distancias mínimas desde `start` a todos los nodos alcanzables.
    graph[u][v] = peso de la arista u→v.
    """
    dist: dict[str, float] = {start: 0.0}
    heap = [(0.0, start)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float("inf")):
            continue
        for v, w in graph.get(u, {}).items():
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))

    return dist


def nearest_neighbor_tsp(
    routes:   list[dict],
    origen:   str,
    criterio: str = "costo",
) -> dict:
    """
    Heurística del vecino más cercano para TSP en el grafo dirigido de rutas.

    Args:
        routes:   lista de dicts con claves 'origen', 'destino', 'distancia_km'
        origen:   código IATA del aeropuerto de partida
        criterio: 'costo' (minimiza km) o 'tiempo' (minimiza horas a 900 km/h)

    Returns:
        dict con orden_visita, distancia_total_km, tiempo_total_h y metadatos.

    Raises:
        ValueError si el criterio es inválido o el origen no existe en el grafo.
    """
    if criterio not in ("costo", "tiempo"):
        raise ValueError(f"criterio debe ser 'costo' o 'tiempo', recibido: {criterio!r}")

    # ── Construir grafo con pesos según criterio ──
    graph: dict[str, dict[str, float]] = {}
    todos: set[str] = set()

    for r in routes:
        o   = r["origen"]
        d   = r["destino"]
        km  = r["distancia_km"]
        peso = float(km) if criterio == "costo" else float(km) / 900.0
        todos.add(o)
        todos.add(d)
        graph.setdefault(o, {})[d] = peso

    if origen not in todos:
        raise ValueError(f"Aeropuerto '{origen}' no existe en el grafo de rutas")

    # ── Aeropuertos alcanzables desde el origen (primer Dijkstra) ──
    alcanzables: set[str] = set(_dijkstra(graph, origen).keys())

    # ── Heurística del vecino más cercano ──
    visitados: list[str] = [origen]
    visitados_set: set[str] = {origen}
    costo_total = 0.0

    actual = origen
    while len(visitados_set) < len(alcanzables):
        dist_actual = _dijkstra(graph, actual)

        mejor_costo   = float("inf")
        mejor_destino = None

        for aeropuerto in alcanzables:
            if aeropuerto not in visitados_set:
                d = dist_actual.get(aeropuerto, float("inf"))
                if d < mejor_costo:
                    mejor_costo   = d
                    mejor_destino = aeropuerto

        if mejor_destino is None:
            break   # sin destinos alcanzables restantes

        visitados.append(mejor_destino)
        visitados_set.add(mejor_destino)
        costo_total += mejor_costo
        actual = mejor_destino

    # ── Intentar regreso al origen (circuito) ──
    dist_final    = _dijkstra(graph, actual)
    costo_regreso = dist_final.get(origen)
    circuito      = False

    if costo_regreso is not None:
        costo_total += costo_regreso
        visitados.append(origen)
        circuito = True

    # ── Convertir costo a km y horas ──
    if criterio == "costo":
        distancia_total_km = costo_total
        tiempo_total_h     = costo_total / 900.0
    else:
        tiempo_total_h     = costo_total
        distancia_total_km = costo_total * 900.0

    return {
        "origen":                   origen,
        "criterio":                 criterio,
        "orden_visita":             visitados,
        "aeropuertos_visitados":    len(visitados_set),
        "aeropuertos_alcanzables":  len(alcanzables),
        "distancia_total_km":       round(distancia_total_km, 1),
        "tiempo_total_h":           round(tiempo_total_h, 2),
        "circuito_cerrado":         circuito,
    }
