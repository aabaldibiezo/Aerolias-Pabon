# =============================================
# AEROLÍNEAS RAFAEL PABON
# config.py — Configuración del nodo
# Lee variables de entorno inyectadas por docker-compose
# =============================================

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    # Identidad del nodo (1, 2 o 3)
    node_id: int

    # Motor de base de datos: 'sqlserver' o 'mongodb'
    db_engine: str

    # Conexión a la base de datos
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # URLs de los otros 2 nodos para propagación de eventos
    peers: list[str]

    # Puerto en el que escucha este nodo
    app_port: int

    # Segundos antes de liberar un asiento en Devolución (default 15 min)
    refund_timeout_seconds: int = 900


def load_config() -> Config:
    """
    Carga la configuración desde variables de entorno.
    Lanza ValueError si falta alguna variable obligatoria.
    """
    def require(key: str) -> str:
        val = os.environ.get(key, "").strip()
        if not val:
            raise ValueError(f"Variable de entorno obligatoria no definida: {key}")
        return val

    node_id  = int(require("NODE_ID"))
    db_engine = require("DB_ENGINE").lower()

    if db_engine not in ("sqlserver", "mongodb"):
        raise ValueError(f"DB_ENGINE debe ser 'sqlserver' o 'mongodb', recibido: '{db_engine}'")

    # PEERS: "http://nodo2:8000,http://nodo3:8000"
    peers_raw = require("PEERS")
    peers = [p.strip() for p in peers_raw.split(",") if p.strip()]

    return Config(
        node_id   = node_id,
        db_engine = db_engine,
        db_host   = require("DB_HOST"),
        db_port   = int(require("DB_PORT")),
        db_name   = require("DB_NAME"),
        db_user   = require("DB_USER"),
        db_password = require("DB_PASSWORD"),
        peers     = peers,
        app_port  = int(os.environ.get("APP_PORT", "8000")),
        refund_timeout_seconds = int(os.environ.get("REFUND_TIMEOUT_SECONDS", "900")),
    )


# Instancia global — se carga una sola vez al arrancar el nodo
cfg: Config = load_config()
