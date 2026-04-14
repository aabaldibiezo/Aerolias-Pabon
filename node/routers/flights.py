# =============================================
# AEROLÍNEAS RAFAEL PABON
# routers/flights.py — Endpoints de vuelos
# =============================================

from fastapi import APIRouter, Depends, HTTPException, Query
from dependencies import get_repo
from repository.base import BaseRepository

router = APIRouter(prefix="/flights", tags=["vuelos"])


@router.get("/stats")
def global_stats(repo: BaseRepository = Depends(get_repo)):
    """
    Estadísticas globales de ocupación e ingresos de todos los vuelos activos.
    Usado por el dashboard global de Streamlit.
    """
    return repo.get_global_stats()


@router.get("")
def search_flights(
    origen:  str | None = Query(None, min_length=3, max_length=3,
                                description="Código IATA del aeropuerto de origen"),
    destino: str | None = Query(None, min_length=3, max_length=3,
                                description="Código IATA del aeropuerto de destino"),
    fecha:   str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$",
                                description="Fecha en formato YYYY-MM-DD"),
    repo: BaseRepository = Depends(get_repo),
):
    """
    Búsqueda incremental de vuelos.
    Todos los parámetros son opcionales — el frontend los va enviando
    a medida que el usuario escribe (no es un dropdown de 20k items).
    """
    vuelos = repo.search_flights(origen=origen, destino=destino, fecha=fecha)
    return {"vuelos": vuelos, "total": len(vuelos)}


@router.get("/{vuelo_id}/stats")
def flight_stats(
    vuelo_id: str,
    repo: BaseRepository = Depends(get_repo),
):
    """
    Estadísticas de ocupación e ingresos de un vuelo específico.
    Usado por el dashboard por vuelo de Streamlit.
    """
    vuelo = repo.get_flight(vuelo_id.upper())
    if not vuelo:
        raise HTTPException(status_code=404, detail=f"Vuelo '{vuelo_id}' no encontrado")
    return repo.get_flight_stats(vuelo_id.upper())


@router.get("/{vuelo_id}")
def get_flight(
    vuelo_id: str,
    repo: BaseRepository = Depends(get_repo),
):
    """Devuelve un vuelo por su ID, enriquecido con datos de aeropuertos."""
    vuelo = repo.get_flight(vuelo_id.upper())
    if not vuelo:
        raise HTTPException(status_code=404, detail=f"Vuelo '{vuelo_id}' no encontrado")
    return vuelo
