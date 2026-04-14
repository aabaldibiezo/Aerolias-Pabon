# =============================================
# AEROLÍNEAS RAFAEL PABON
# routers/routes.py — Endpoints de rutas (Dijkstra)
# =============================================

from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import get_repo
from repository.base import BaseRepository
from dijkstra import build_graph, find_route, find_top_routes, get_reachable
from tsp import nearest_neighbor_tsp

router = APIRouter(prefix="/routes", tags=["rutas"])


@router.get("/airports")
def list_airports(repo: BaseRepository = Depends(get_repo)):
    """Lista todos los aeropuertos del sistema."""
    return {"aeropuertos": repo.get_airports()}


@router.get("/shortest")
def shortest_route(
    origen:  str = Query(..., min_length=3, max_length=3),
    destino: str = Query(..., min_length=3, max_length=3),
    repo: BaseRepository = Depends(get_repo),
):
    """
    Calcula la ruta más corta (por distancia km) entre dos aeropuertos
    en el grafo dirigido usando el algoritmo de Dijkstra.

    Si no existe vuelo directo, devuelve la ruta con escalas.
    Si no hay ningún camino posible, retorna 404.
    """
    routes  = repo.get_routes()
    result  = find_route(routes, origen.upper(), destino.upper())

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No existe ruta entre {origen.upper()} y {destino.upper()} "
                "en el grafo de rutas comerciales actuales."
            )
        )

    return {
        "origen":              result.origen,
        "destino":             result.destino,
        "path":                list(result.path),
        "segmentos":           [
            {"origen": s.origen, "destino": s.destino, "distancia_km": s.distancia_km}
            for s in result.segmentos
        ],
        "distancia_total_km":  result.distancia_total_km,
        "num_escalas":         result.num_escalas,
        "es_directo":          result.es_directo,
        "descripcion":         str(result),
    }


@router.get("/alternatives")
def alternative_routes(
    origen:  str = Query(..., min_length=3, max_length=3),
    destino: str = Query(..., min_length=3, max_length=3),
    top_n:   int = Query(3, ge=1, le=5),
    repo: BaseRepository = Depends(get_repo),
):
    """
    Devuelve hasta `top_n` rutas alternativas ordenadas por distancia.
    Útil para mostrar opciones de escalas en el frontend.
    """
    routes   = repo.get_routes()
    results  = find_top_routes(routes, origen.upper(), destino.upper(), top_n=top_n)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No existe ninguna ruta entre {origen.upper()} y {destino.upper()}"
        )

    return {
        "origen":  origen.upper(),
        "destino": destino.upper(),
        "rutas": [
            {
                "path":               list(r.path),
                "distancia_total_km": r.distancia_total_km,
                "num_escalas":        r.num_escalas,
                "es_directo":         r.es_directo,
                "descripcion":        str(r),
            }
            for r in results
        ],
    }


@router.get("/reachable")
def reachable_from(
    origen: str = Query(..., min_length=3, max_length=3),
    repo: BaseRepository = Depends(get_repo),
):
    """
    Devuelve todos los aeropuertos alcanzables desde `origen`
    en el grafo dirigido (sin importar el número de escalas).
    Usado para filtrar el selector de destino en el frontend:
    si el aeropuerto no es alcanzable, no aparece en la lista.
    """
    routes  = repo.get_routes()
    grafo   = build_graph(routes)
    destinos = get_reachable(grafo, origen.upper())

    # Enriquecer con nombre y ciudad
    todos = {a["codigo"]: a for a in repo.get_airports()}
    return {
        "origen":   origen.upper(),
        "destinos": [
            todos[cod] for cod in sorted(destinos) if cod in todos
        ],
    }


@router.get("/tsp")
def tsp_tour(
    origen:   str = Query(..., min_length=3, max_length=3,
                          description="Aeropuerto de inicio del recorrido"),
    criterio: str = Query("costo", pattern=r"^(costo|tiempo)$",
                          description="'costo' minimiza km, 'tiempo' minimiza horas"),
    repo: BaseRepository = Depends(get_repo),
):
    """
    Calcula un recorrido TSP (Problema del Viajero) usando la heurística
    del vecino más cercano sobre el grafo dirigido de rutas comerciales.

    Visita todos los aeropuertos alcanzables desde `origen` intentando
    minimizar la distancia total (criterio='costo') o el tiempo de vuelo
    total (criterio='tiempo', asumiendo velocidad crucero de 900 km/h).

    El resultado incluye el orden de visita, distancia total y tiempo total.
    """
    routes = repo.get_routes()

    if not routes:
        raise HTTPException(status_code=404, detail="No hay rutas comerciales registradas")

    try:
        resultado = nearest_neighbor_tsp(
            routes   = routes,
            origen   = origen.upper(),
            criterio = criterio,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Enriquecer la lista de visitas con nombres de ciudades
    todos = {a["codigo"]: a for a in repo.get_airports()}
    resultado["detalle_visitas"] = [
        {
            "codigo": cod,
            "ciudad": todos.get(cod, {}).get("ciudad", cod),
            "pais":   todos.get(cod, {}).get("pais",   ""),
        }
        for cod in resultado["orden_visita"]
    ]

    return resultado
