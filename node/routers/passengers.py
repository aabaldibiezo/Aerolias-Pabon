# =============================================
# AEROLÍNEAS RAFAEL PABON
# routers/passengers.py — Endpoints de pasajeros
# =============================================

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import get_repo
from repository.base import BaseRepository

router = APIRouter(prefix="/passengers", tags=["pasajeros"])


class PassengerUpsertRequest(BaseModel):
    pasaporte: str
    nombre:    str
    email:     str | None = None


@router.get("/{pasaporte}")
def get_passenger(
    pasaporte: str,
    repo: BaseRepository = Depends(get_repo),
):
    """
    Busca un pasajero por número de pasaporte.
    Usado en el modal del asiento para autocompletar el nombre.
    Retorna 404 si no existe (el frontend muestra campo de ingreso manual).
    """
    pasajero = repo.get_passenger(pasaporte.upper())
    if not pasajero:
        raise HTTPException(
            status_code=404,
            detail=f"Pasajero con pasaporte '{pasaporte}' no encontrado"
        )
    return pasajero


@router.post("")
def upsert_passenger(
    body: PassengerUpsertRequest,
    repo: BaseRepository = Depends(get_repo),
):
    """
    Registra un nuevo pasajero o devuelve el existente.
    Si el pasaporte ya existe, no sobreescribe el nombre.
    """
    pasajero = repo.upsert_passenger(
        pasaporte = body.pasaporte.upper(),
        nombre    = body.nombre,
        email     = body.email,
    )
    return pasajero
