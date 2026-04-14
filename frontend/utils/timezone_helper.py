# =============================================
# AEROLÍNEAS RAFAEL PABON
# utils/timezone_helper.py — Conversión de horas a UTC
# Usa zoneinfo (stdlib Python 3.9+) + tzdata
# =============================================

from datetime import datetime
from zoneinfo import ZoneInfo


UTC = ZoneInfo("UTC")


def local_to_utc(fecha: str, hora: str, timezone: str) -> datetime:
    """
    Convierte una fecha y hora local de un aeropuerto a UTC.

    Args:
        fecha:    'YYYY-MM-DD'
        hora:     'HH:MM'
        timezone: nombre IANA, ej: 'America/New_York'

    Returns:
        datetime con tzinfo=UTC
    """
    tz    = ZoneInfo(timezone)
    dt    = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    return dt.astimezone(UTC)


def format_utc(dt_utc: datetime) -> str:
    """Formatea un datetime UTC como 'HH:MM UTC'."""
    return dt_utc.strftime("%H:%M UTC")


def format_local(fecha: str, hora: str, timezone: str) -> str:
    """
    Devuelve la hora local con el offset UTC.
    Ej: '09:00 (UTC-4)'
    """
    tz     = ZoneInfo(timezone)
    dt     = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    offset = dt.utcoffset()
    total  = int(offset.total_seconds() // 3600)
    sign   = "+" if total >= 0 else "-"
    return f"{hora} (UTC{sign}{abs(total)})"


def flight_times(vuelo: dict) -> dict:
    """
    Calcula las horas UTC de salida y llegada de un vuelo.

    Args:
        vuelo: dict devuelto por get_flight() — incluye timezone_origen y timezone_destino

    Returns:
        dict con salida_local, salida_utc, llegada_local, llegada_utc (strings)
    """
    fecha = vuelo["fecha"]

    salida_utc  = local_to_utc(fecha, vuelo["hora_salida"],  vuelo["timezone_origen"])
    llegada_utc = local_to_utc(fecha, vuelo["hora_llegada"], vuelo["timezone_destino"])

    return {
        "salida_local":  format_local(fecha, vuelo["hora_salida"],  vuelo["timezone_origen"]),
        "salida_utc":    format_utc(salida_utc),
        "llegada_local": format_local(fecha, vuelo["hora_llegada"], vuelo["timezone_destino"]),
        "llegada_utc":   format_utc(llegada_utc),
    }
