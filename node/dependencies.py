# =============================================
# AEROLÍNEAS RAFAEL PABON
# dependencies.py — Inyección de dependencias FastAPI
#
# Los singletons se inicializan en el startup de main.py
# y se acceden en los routers via Depends().
# =============================================

from fastapi import Request

from repository.base import BaseRepository
from vector_clock import VectorClock
from lamport_clock import LamportClock
from timer_service import TimerService


def get_repo(request: Request) -> BaseRepository:
    return request.app.state.repo


def get_clock(request: Request) -> VectorClock:
    return request.app.state.clock


def get_lamport(request: Request) -> LamportClock:
    return request.app.state.lamport


def get_timer(request: Request) -> TimerService:
    return request.app.state.timer_svc
