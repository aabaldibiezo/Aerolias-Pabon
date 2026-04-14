# =============================================
# AEROLÍNEAS RAFAEL PABON
# main.py — Punto de entrada del nodo FastAPI
#
# Mismo código para los 3 nodos.
# El motor de BD y el ID se configuran por variables de entorno.
# =============================================

import asyncio
import logging
import logging.config

from contextlib import asynccontextmanager
from datetime import datetime, timezone, date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import cfg
from repository import get_repo
from vector_clock import VectorClock
from lamport_clock import LamportClock
from timer_service import TimerService
import sync_service

from routers import flights, seats, passengers, routes, sync, boarding_pass


# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  [nodo%(node_id)s]  %(levelname)-8s  %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
)

# Añadir node_id a todos los mensajes del logger raíz
_old_factory = logging.getLogRecordFactory()

def _record_factory(*args, **kwargs):
    record = _old_factory(*args, **kwargs)
    record.node_id = cfg.node_id
    return record

logging.setLogRecordFactory(_record_factory)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# LÓGICA DE ESTADOS DE VUELO
# ─────────────────────────────────────────

_FLIGHT_STATE_LOG = logging.getLogger("flight_states")


def _compute_flight_state(fecha: str, hora_salida: str, hora_llegada: str) -> str:
    """
    Calcula el estado operativo de un vuelo basándose en la hora UTC actual.

    Estados posibles:
      SCHEDULED  → salida en más de 30 minutos
      BOARDING   → falta ≤30 min para salida
      IN_FLIGHT  → entre hora_salida y hora_llegada
      ARRIVED    → hora_llegada ya pasó
    """
    try:
        now  = datetime.now(timezone.utc).replace(tzinfo=None)
        base = datetime.strptime(fecha, "%Y-%m-%d")
        dep  = datetime.combine(base.date(), datetime.strptime(hora_salida,  "%H:%M").time())
        arr  = datetime.combine(base.date(), datetime.strptime(hora_llegada, "%H:%M").time())

        # Manejar vuelos que llegan pasada la medianoche
        if arr <= dep:
            from datetime import timedelta
            arr += timedelta(days=1)

        if now >= arr:
            return "ARRIVED"
        if now >= dep:
            return "IN_FLIGHT"
        from datetime import timedelta
        if now >= dep - timedelta(minutes=30):
            return "BOARDING"
        return "SCHEDULED"
    except Exception:
        return "SCHEDULED"


def _compute_and_update_flight_states(repo) -> None:
    """Lee todos los vuelos activos y actualiza sus estados si cambiaron."""
    vuelos = repo.get_flights_for_state_update()
    updated = 0
    for v in vuelos:
        nuevo = _compute_flight_state(v["fecha"], v["hora_salida"], v["hora_llegada"])
        if nuevo != v.get("estado"):
            repo.update_flight_state(v["vuelo_id"], nuevo)
            updated += 1
    if updated:
        _FLIGHT_STATE_LOG.info("Estados de vuelo actualizados: %d vuelos", updated)


# ─────────────────────────────────────────
# CICLO DE VIDA (startup / shutdown)
# ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    logger.info("Iniciando nodo%d  motor=%s  host=%s",
                cfg.node_id, cfg.db_engine, cfg.db_host)

    # Repositorio (singleton — resuelve motor por DB_ENGINE)
    repo         = get_repo()
    clock        = VectorClock(cfg.node_id)
    lamport      = LamportClock(cfg.node_id)

    # TimerService recibe la función de propagación como callback
    # para evitar imports circulares entre timer_service y sync_service
    timer_svc = TimerService(
        repo         = repo,
        clock        = clock,
        propagate_fn = lambda evento: sync_service.propagate(evento, cfg.peers),
        timeout_seg  = cfg.refund_timeout_seconds,
        lamport      = lamport,
    )

    # Exponer singletons via app.state para inyección de dependencias
    app.state.repo      = repo
    app.state.clock     = clock
    app.state.lamport   = lamport
    app.state.timer_svc = timer_svc

    logger.info("Nodo%d listo — peers: %s", cfg.node_id, cfg.peers)

    # ── Tarea de fondo: actualizar estados de vuelo cada 60 segundos ──
    stop_event = asyncio.Event()

    async def _update_flight_states():
        while not stop_event.is_set():
            try:
                _compute_and_update_flight_states(repo)
            except Exception as exc:
                logger.warning("Error actualizando estados de vuelo: %s", exc)
            await asyncio.sleep(60)

    flight_state_task = asyncio.create_task(_update_flight_states())

    yield   # ← la aplicación corre aquí

    # ── SHUTDOWN ──
    stop_event.set()
    flight_state_task.cancel()
    logger.info("Apagando nodo%d — timers activos: %d",
                cfg.node_id, timer_svc.active_count())


# ─────────────────────────────────────────
# APLICACIÓN
# ─────────────────────────────────────────

app = FastAPI(
    title       = f"Aerolíneas Rafael Pabon — Nodo {cfg.node_id}",
    description = (
        f"Motor: **{cfg.db_engine.upper()}** | "
        f"Nodo ID: **{cfg.node_id}** | "
        "Sistema distribuido de reservas con Relojes Vectoriales"
    ),
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# CORS — permite que Streamlit (puerto 8501) llame a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ─────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────

app.include_router(flights.router)
app.include_router(seats.router)
app.include_router(passengers.router)
app.include_router(routes.router)
app.include_router(sync.router)
app.include_router(boarding_pass.router)


# ─────────────────────────────────────────
# ENDPOINTS RAÍZ
# ─────────────────────────────────────────

@app.get("/", tags=["info"])
def root():
    """Info básica del nodo. Usado como health check por docker-compose."""
    return {
        "nodo_id":   cfg.node_id,
        "db_engine": cfg.db_engine,
        "db_host":   cfg.db_host,
        "peers":     cfg.peers,
        "status":    "ok",
    }


@app.get("/health", tags=["info"])
def health(request_app = None):
    """Health check detallado con estado del reloj vectorial."""
    from fastapi import Request
    return {"status": "ok", "nodo_id": cfg.node_id}
