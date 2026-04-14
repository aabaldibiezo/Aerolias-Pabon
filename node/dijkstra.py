# =============================================
# AEROLÍNEAS RAFAEL PABON
# dijkstra.py — Rutas más cortas en grafo dirigido
#
# Calcula la ruta de menor distancia entre dos aeropuertos
# usando el algoritmo de Dijkstra con heap binario (heapq).
#
# El grafo es DIRIGIDO: si existe ATL→SAO no implica SAO→ATL.
# El peso de cada arista es distancia_km.
#
# Ejemplo de ruta con escala obligatoria:
#   SAO → ATL  no existe directa
#   Dijkstra devuelve: SAO → MAD → ATL  (15 480 km)
#   o bien:            SAO → LON → ATL  (16 290 km)
#   → elige SAO → MAD → ATL por ser más corta.
# =============================================

import heapq
from dataclasses import dataclass, field


# ─────────────────────────────────────────
# TIPOS DE DATOS
# ─────────────────────────────────────────

# Grafo de adyacencia: {codigo_origen: {codigo_destino: distancia_km}}
Grafo = dict[str, dict[str, int]]


@dataclass(frozen=True)
class Segmento:
    """Un tramo del viaje entre dos aeropuertos consecutivos."""
    origen:       str
    destino:      str
    distancia_km: int


@dataclass(frozen=True)
class RutaResult:
    """Resultado completo de una búsqueda de ruta."""
    origen:             str
    destino:            str
    path:               tuple[str, ...]    # Ej: ("SAO", "MAD", "ATL")
    segmentos:          tuple[Segmento, ...]
    distancia_total_km: int
    num_escalas:        int                # aeropuertos intermedios (len(path) - 2)
    es_directo:         bool               # True si no hay escalas

    def __str__(self) -> str:
        ruta = " → ".join(self.path)
        if self.es_directo:
            return f"{ruta}  [{self.distancia_total_km:,} km — vuelo directo]"
        return f"{ruta}  [{self.distancia_total_km:,} km — {self.num_escalas} escala(s)]"


# ─────────────────────────────────────────
# CONSTRUCCIÓN DEL GRAFO
# ─────────────────────────────────────────

def build_graph(routes: list[dict]) -> Grafo:
    """
    Construye el grafo dirigido de adyacencia a partir de la lista
    de rutas devuelta por BaseRepository.get_routes().

    Args:
        routes: lista de dicts con claves {origen, destino, distancia_km}

    Returns:
        Grafo de adyacencia.  Los nodos sin salidas NO aparecen como claves
        (solo como destinos), lo cual es correcto para un grafo dirigido.
    """
    grafo: Grafo = {}
    for r in routes:
        origen = r["origen"]
        if origen not in grafo:
            grafo[origen] = {}
        grafo[origen][r["destino"]] = int(r["distancia_km"])
    return grafo


# ─────────────────────────────────────────
# ALGORITMO DE DIJKSTRA
# ─────────────────────────────────────────

def dijkstra(
    grafo:   Grafo,
    origen:  str,
    destino: str,
) -> RutaResult | None:
    """
    Encuentra la ruta de menor distancia entre `origen` y `destino`
    en un grafo dirigido y ponderado.

    Complejidad: O((V + E) log V) con heap binario.

    Returns:
        RutaResult si existe ruta.
        None si no hay camino posible entre los dos aeropuertos.
    """
    if origen == destino:
        return RutaResult(
            origen=origen, destino=destino,
            path=(origen,), segmentos=(),
            distancia_total_km=0, num_escalas=0, es_directo=True,
        )

    if origen not in grafo:
        # El nodo origen no tiene ninguna salida en el grafo
        return None

    # Heap: (distancia_acumulada, nodo_actual, camino_hasta_aqui)
    # Guardar el camino en el heap evita una segunda pasada para reconstruirlo.
    heap: list[tuple[int, str, list[str]]] = [(0, origen, [origen])]
    visitados: set[str] = set()

    while heap:
        dist_acum, nodo, camino = heapq.heappop(heap)

        if nodo in visitados:
            continue
        visitados.add(nodo)

        if nodo == destino:
            return _build_result(camino, dist_acum, grafo)

        for vecino, peso in grafo.get(nodo, {}).items():
            if vecino not in visitados:
                heapq.heappush(
                    heap,
                    (dist_acum + peso, vecino, camino + [vecino])
                )

    return None   # no hay camino


def _build_result(path: list[str], distancia_total: int, grafo: Grafo) -> RutaResult:
    """Construye el RutaResult desde el camino encontrado por Dijkstra."""
    segmentos = tuple(
        Segmento(
            origen       = path[i],
            destino      = path[i + 1],
            distancia_km = grafo[path[i]][path[i + 1]],
        )
        for i in range(len(path) - 1)
    )
    num_escalas = len(path) - 2   # aeropuertos intermedios (puede ser 0)

    return RutaResult(
        origen             = path[0],
        destino            = path[-1],
        path               = tuple(path),
        segmentos          = segmentos,
        distancia_total_km = distancia_total,
        num_escalas        = max(num_escalas, 0),
        es_directo         = num_escalas == 0,
    )


# ─────────────────────────────────────────
# FUNCIÓN DE ALTO NIVEL
# ─────────────────────────────────────────

def find_route(
    routes:  list[dict],
    origen:  str,
    destino: str,
) -> RutaResult | None:
    """
    Función de conveniencia: recibe la lista de rutas tal como la
    devuelve el repositorio, construye el grafo y ejecuta Dijkstra.

    Uso típico en un router FastAPI:
        routes = repo.get_routes()
        resultado = find_route(routes, "SAO", "ATL")
        if resultado is None:
            raise HTTPException(404, "No existe ruta entre estos aeropuertos")
    """
    grafo = build_graph(routes)
    return dijkstra(grafo, origen.upper(), destino.upper())


def find_top_routes(
    routes:  list[dict],
    origen:  str,
    destino: str,
    top_n:   int = 3,
) -> list[RutaResult]:
    """
    Devuelve hasta `top_n` rutas alternativas ordenadas por distancia,
    variando el número de escalas permitidas.

    Estrategia: ejecuta Dijkstra en versiones del grafo con nodos
    intermedios excluidos progresivamente para forzar caminos alternativos.
    Útil para mostrar opciones en el frontend.

    Returns:
        Lista de RutaResult (puede ser vacía si no hay ruta).
    """
    grafo_completo = build_graph(routes)
    resultados: list[RutaResult] = []
    nodos_excluidos: set[str] = set()

    # Primera ruta: la óptima
    primera = dijkstra(grafo_completo, origen.upper(), destino.upper())
    if primera is None:
        return []

    resultados.append(primera)

    # Rutas alternativas: excluir los nodos intermedios de la ruta anterior
    for _ in range(top_n - 1):
        # Excluir el primer nodo intermedio de la última ruta encontrada
        ultima = resultados[-1]
        intermedios = [p for p in ultima.path if p not in (origen.upper(), destino.upper())]

        if not intermedios:
            break   # es vuelo directo, no hay alternativa por esta estrategia

        nodos_excluidos.add(intermedios[0])

        # Construir grafo sin los nodos excluidos
        grafo_reducido: Grafo = {
            nodo: {v: d for v, d in vecinos.items() if v not in nodos_excluidos}
            for nodo, vecinos in grafo_completo.items()
            if nodo not in nodos_excluidos
        }

        alternativa = dijkstra(grafo_reducido, origen.upper(), destino.upper())
        if alternativa is None:
            break   # no quedan rutas

        # Descartar duplicados (misma secuencia de aeropuertos)
        if alternativa.path not in [r.path for r in resultados]:
            resultados.append(alternativa)

    return resultados


# ─────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────

def get_reachable(grafo: Grafo, origen: str) -> set[str]:
    """
    Devuelve el conjunto de todos los aeropuertos alcanzables
    desde `origen` en el grafo dirigido (BFS/DFS simplificado).
    Útil para filtrar destinos en el selector del frontend.
    """
    visitados: set[str] = set()
    pila = [origen.upper()]

    while pila:
        nodo = pila.pop()
        if nodo in visitados:
            continue
        visitados.add(nodo)
        pila.extend(grafo.get(nodo, {}).keys())

    visitados.discard(origen.upper())   # no incluir el origen
    return visitados
