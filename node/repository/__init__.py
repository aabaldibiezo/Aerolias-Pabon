# =============================================
# AEROLÍNEAS RAFAEL PABON
# repository/__init__.py — Factory del repositorio
#
# Instancia el repositorio correcto según DB_ENGINE.
# El resto de la aplicación importa `get_repo()` y
# nunca necesita saber si está hablando con SQL Server o MongoDB.
# =============================================

from functools import lru_cache

from .base import BaseRepository


@lru_cache(maxsize=1)
def get_repo() -> BaseRepository:
    """
    Devuelve la instancia singleton del repositorio.
    Se resuelve una sola vez al primer llamado (lru_cache).
    """
    from config import cfg

    if cfg.db_engine == "sqlserver":
        from .sqlserver_repo import SQLServerRepository
        return SQLServerRepository()

    elif cfg.db_engine == "mongodb":
        from .mongodb_repo import MongoDBRepository
        return MongoDBRepository()

    else:
        raise ValueError(f"Motor de BD no soportado: '{cfg.db_engine}'")
