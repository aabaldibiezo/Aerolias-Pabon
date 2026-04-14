# =============================================
# AEROLÍNEAS RAFAEL PABON
# state_machine.py — Máquina de estados de asientos
#
# Diagrama de estados:
#
#   ┌─────────┐  reservar  ┌─────────┐
#   │         │──────────► │         │
#   │  Libre  │            │ Reserva │
#   │         │◄────────── │         │
#   └────┬────┘  liberar*  └────┬────┘
#        │                      │ vender
#        │ vender                ▼
#        │              ┌──────────────┐
#        └─────────────►│    Venta     │  ← estado final (sin devolución)
#                       └──────────────┘
#
#   Reserva ──devolver──► Devolución ──liberar*──► Libre
#
#   (*) liberar: transición automática por timer de 5 minutos
#       Solo la ejecuta timer_service.py, no el usuario.
#
# Acciones disponibles por estado:
#   Libre      → reservar, vender
#   Reserva    → vender, devolver
#   Venta      → (ninguna — estado final del cliente)
#   Devolución → liberar  (solo timer, no el usuario)
# =============================================

from dataclasses import dataclass


# ─────────────────────────────────────────
# DEFINICIÓN DE TRANSICIONES
# {estado_actual: {accion: estado_nuevo}}
# ─────────────────────────────────────────

_TRANSITIONS: dict[str, dict[str, str]] = {
    "Libre":      {"reservar": "Reserva",    "vender":  "Venta"},
    "Reserva":    {"vender":   "Venta",       "devolver": "Devolucion"},
    "Venta":      {},   # estado final para el usuario
    "Devolucion": {"liberar": "Libre"},       # solo por el timer
}

# Mapeo acción → tipo de evento (se almacena en la tabla eventos)
_ACTION_TO_TIPO: dict[str, str] = {
    "reservar": "reserva",
    "vender":   "venta",
    "devolver": "devolucion",
    "liberar":  "liberacion",
}

# Colores para el mapa visual del avión en el frontend
ESTADO_COLOR: dict[str, str] = {
    "Libre":      "#4CAF50",   # verde
    "Reserva":    "#FFC107",   # amarillo
    "Venta":      "#F44336",   # rojo
    "Devolucion": "#9E9E9E",   # gris
}

# Acciones que puede hacer el usuario (excluye 'liberar' que es del timer)
ACCIONES_USUARIO: dict[str, list[str]] = {
    "Libre":      ["reservar", "vender"],
    "Reserva":    ["vender", "devolver"],
    "Venta":      [],
    "Devolucion": [],
}


# ─────────────────────────────────────────
# EXCEPCIONES
# ─────────────────────────────────────────

class TransicionInvalidaError(ValueError):
    """Se lanza cuando se intenta una transición no permitida."""
    def __init__(self, estado_actual: str, accion: str):
        disponibles = list(_TRANSITIONS.get(estado_actual, {}).keys())
        super().__init__(
            f"Transición inválida: '{accion}' no está permitida desde el estado '{estado_actual}'. "
            f"Acciones disponibles: {disponibles}"
        )


class EstadoInvalidoError(ValueError):
    """Se lanza cuando el estado recibido no existe en el sistema."""
    def __init__(self, estado: str):
        super().__init__(
            f"Estado desconocido: '{estado}'. "
            f"Estados válidos: {list(_TRANSITIONS.keys())}"
        )


# ─────────────────────────────────────────
# DATACLASS DE RESULTADO
# ─────────────────────────────────────────

@dataclass(frozen=True)
class TransitionResult:
    estado_anterior: str
    estado_nuevo:    str
    accion:          str
    tipo:            str   # valor para la columna 'tipo' en la tabla eventos


# ─────────────────────────────────────────
# FUNCIONES PRINCIPALES
# ─────────────────────────────────────────

def validate_transition(estado_actual: str, accion: str) -> TransitionResult:
    """
    Valida si la acción es permitida desde el estado actual.

    Retorna TransitionResult con el estado nuevo y el tipo de evento.
    Lanza TransicionInvalidaError si no está permitida.
    Lanza EstadoInvalidoError si el estado no existe.

    Uso típico en un router:
        result = validate_transition(asiento["estado"], "reservar")
        repo.apply_seat_operation(..., estado_anterior=result.estado_anterior,
                                       estado_nuevo=result.estado_nuevo,
                                       tipo=result.tipo, ...)
    """
    if estado_actual not in _TRANSITIONS:
        raise EstadoInvalidoError(estado_actual)

    estado_nuevo = _TRANSITIONS[estado_actual].get(accion)
    if estado_nuevo is None:
        raise TransicionInvalidaError(estado_actual, accion)

    return TransitionResult(
        estado_anterior = estado_actual,
        estado_nuevo    = estado_nuevo,
        accion          = accion,
        tipo            = _ACTION_TO_TIPO[accion],
    )


def available_actions(estado: str, include_timer: bool = False) -> list[str]:
    """
    Retorna las acciones disponibles para un estado dado.

    Args:
        estado: estado actual del asiento
        include_timer: si True, incluye 'liberar' (solo para uso interno
                       del timer_service, nunca para el usuario)
    """
    if estado not in _TRANSITIONS:
        raise EstadoInvalidoError(estado)

    all_actions = list(_TRANSITIONS[estado].keys())

    if not include_timer:
        # 'liberar' es exclusivo del timer, no se expone al usuario
        return [a for a in all_actions if a != "liberar"]

    return all_actions


def can_perform(estado: str, accion: str) -> bool:
    """
    Versión booleana de validate_transition.
    Útil para condicionar botones en el frontend.
    """
    return accion in _TRANSITIONS.get(estado, {})


def get_estado_color(estado: str) -> str:
    """Retorna el color hex asociado al estado para el mapa visual."""
    return ESTADO_COLOR.get(estado, "#BDBDBD")


def is_terminal(estado: str) -> bool:
    """
    Retorna True si el estado no admite ninguna acción de usuario.
    'Venta' es terminal permanente; 'Devolucion' es terminal temporal
    (el timer la libera automáticamente).
    """
    return len(ACCIONES_USUARIO.get(estado, [])) == 0


# ─────────────────────────────────────────
# VALIDACIÓN DE ESTADOS Y TIPOS (para deserializar eventos de la red)
# ─────────────────────────────────────────

ESTADOS_VALIDOS = frozenset(_TRANSITIONS.keys())
TIPOS_VALIDOS   = frozenset(_ACTION_TO_TIPO.values())


def assert_estado(estado: str) -> None:
    """Lanza EstadoInvalidoError si el string no es un estado válido."""
    if estado not in ESTADOS_VALIDOS:
        raise EstadoInvalidoError(estado)


def assert_tipo(tipo: str) -> None:
    """Lanza ValueError si el string no es un tipo de evento válido."""
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(
            f"Tipo de evento desconocido: '{tipo}'. "
            f"Tipos válidos: {sorted(TIPOS_VALIDOS)}"
        )
