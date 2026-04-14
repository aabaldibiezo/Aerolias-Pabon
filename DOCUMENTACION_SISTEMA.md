# Aerolíneas Rafael Pabón — Documentación del Sistema
## Sistema Distribuido de Reservas Aéreas

---

## Tabla de Contenidos

1. [Arquitectura General](#1-arquitectura-general)
2. [Componentes del Sistema](#2-componentes-del-sistema)
3. [Algoritmos Implementados](#3-algoritmos-implementados)
   - 3.1 [Reloj de Lamport](#31-reloj-de-lamport)
   - 3.2 [Reloj Vectorial](#32-reloj-vectorial)
   - 3.3 [Algoritmo de Dijkstra](#33-algoritmo-de-dijkstra)
   - 3.4 [TSP — Vecino más Cercano](#34-tsp--vecino-más-cercano)
   - 3.5 [Fórmula de Haversine](#35-fórmula-de-haversine)
   - 3.6 [Máquina de Estados de Vuelos](#36-máquina-de-estados-de-vuelos)
   - 3.7 [Máquina de Estados de Asientos](#37-máquina-de-estados-de-asientos)
4. [Mecanismo de Sincronización](#4-mecanismo-de-sincronización)
5. [Servicio de Temporizador](#5-servicio-de-temporizador)
6. [Esquema de Base de Datos](#6-esquema-de-base-de-datos)
7. [API REST — Endpoints](#7-api-rest--endpoints)
8. [Frontend](#8-frontend)
9. [Flujo Completo de una Operación](#9-flujo-completo-de-una-operación)

---

## 1. Arquitectura General

El sistema es una plataforma distribuida de reservas aéreas compuesta por **tres nodos independientes**, cada uno con su propio motor de base de datos y una API REST propia. No existe un coordinador central — los nodos se sincronizan entre sí de forma peer-to-peer.

```
┌──────────────────────────────────────────────────────────────┐
│                      CLIENTE (Streamlit)                      │
│                      http://localhost:8501                    │
└─────────────────────────────┬────────────────────────────────┘
                              │ HTTP
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   NODO 1         │ │   NODO 2         │ │   NODO 3         │
│   Europa/FRA     │ │   Asia/TYO       │ │   Sudamérica/LAP │
│   FastAPI :8001  │ │   FastAPI :8002  │ │   FastAPI :8003  │
│   SQL Server     │ │   SQL Server     │ │   MongoDB        │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                    Red Docker: arlp_network
                    Sync peer-to-peer via HTTP
```

### Tecnologías

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| API Backend | FastAPI + Uvicorn | Python 3.11 |
| BD Nodos 1 y 2 | Microsoft SQL Server | 2022 |
| BD Nodo 3 | MongoDB | 7 |
| Frontend | Streamlit | — |
| Contenerización | Docker Compose | — |
| PDF | ReportLab | 4.2.5 |

---

## 2. Componentes del Sistema

### Nodos de la API (`node/`)

Cada nodo corre el mismo código Python pero con configuración diferente:

```
node/
├── main.py               # Arranque, ciclo de vida, tarea de estados de vuelo
├── config.py             # Variables de entorno (nodo, motor BD, timeouts)
├── dependencies.py       # Inyección de dependencias FastAPI
├── lamport_clock.py      # Reloj de Lamport
├── vector_clock.py       # Reloj Vectorial
├── state_machine.py      # Transiciones de estados de asientos
├── sync_service.py       # Propagación y recepción de eventos entre nodos
├── timer_service.py      # Temporizador de devoluciones
├── tsp.py                # TSP vecino más cercano
├── dijkstra.py           # Algoritmo de Dijkstra
├── pdf_generator.py      # Generación de pase de abordar PDF
├── load_csv.py           # Cargador del dataset CSV
├── repository/
│   ├── base.py           # Interfaz abstracta del repositorio
│   ├── sqlserver_repo.py # Implementación SQL Server
│   └── mongodb_repo.py   # Implementación MongoDB
└── routers/
    ├── flights.py        # Endpoints de vuelos y estadísticas
    ├── seats.py          # Endpoints de asientos (reservar, vender, devolver)
    ├── passengers.py     # Endpoints de pasajeros
    ├── routes.py         # Endpoints de rutas, Dijkstra, TSP
    ├── sync.py           # Endpoints de sincronización
    └── boarding_pass.py  # Endpoint de pase de abordar PDF
```

### Frontend (`frontend/`)

```
frontend/
├── streamlit_app.py             # Página principal: selector de nodo e idioma
├── utils/
│   ├── i18n.py                  # Traducciones ES/EN
│   └── node_client.py           # Cliente HTTP hacia los nodos
└── pages/
    ├── 1_buscar_vuelo.py        # Búsqueda de vuelos + Dijkstra
    ├── 2_mapa_asientos.py       # Mapa interactivo de asientos
    ├── 3_boarding_pass.py       # Pase de abordar PDF
    ├── 4_dashboard_vuelo.py     # Estadísticas por vuelo
    └── 5_dashboard_global.py    # Dashboard global del sistema
```

---

## 3. Algoritmos Implementados

### 3.1 Reloj de Lamport

**Archivo:** `node/lamport_clock.py`

**Propósito:** Asignar un orden total a todos los eventos del sistema distribuido. Garantiza que si el evento A ocurre antes que el evento B, entonces `L(A) < L(B)`.

**Reglas del algoritmo:**
1. Cuando un nodo genera un evento local → incrementa su contador en 1
2. Cuando un nodo recibe un evento remoto → `tiempo = max(tiempo_local, tiempo_recibido) + 1`
3. El timestamp se adjunta a cada evento propagado

**Implementación:**

```python
class LamportClock:
    def __init__(self, node_id: int):
        self._time = 0
        self._lock = threading.Lock()   # thread-safe

    def tick(self) -> int:
        """Evento local: incrementa y devuelve el tiempo actual."""
        with self._lock:
            self._time += 1
            return self._time

    def update(self, received_time: int) -> int:
        """Recibe evento remoto: sincroniza y avanza el reloj."""
        with self._lock:
            self._time = max(self._time, received_time) + 1
            return self._time

    def get_time(self) -> int:
        with self._lock:
            return self._time
```

**Uso en el sistema:**
- Al **enviar** una operación de asiento → `lamport.tick()` genera un timestamp
- Al **recibir** un evento de otro nodo → `lamport.update(evento.lamport_timestamp)` sincroniza
- El valor se persiste en la columna `lamport_timestamp` de la tabla `eventos`

---

### 3.2 Reloj Vectorial

**Archivo:** `node/vector_clock.py`

**Propósito:** Detectar relaciones causales y concurrencia entre operaciones en los 3 nodos. A diferencia del reloj de Lamport, permite determinar si dos eventos son concurrentes o si uno causó al otro.

**Representación:** Array de 3 enteros `[t1, t2, t3]`, uno por nodo.

**Implementación:**

```python
class VectorClock:
    def __init__(self, node_id: int):
        self._clock = [0, 0, 0]       # [nodo1, nodo2, nodo3]
        self._idx   = node_id - 1     # índice propio (0, 1 o 2)

    def tick(self) -> list[int]:
        """Evento local: incrementa la posición propia."""
        with self._lock:
            self._clock[self._idx] += 1
            return self._clock.copy()

    def merge(self, remote: list[int]) -> list[int]:
        """
        Recibe evento remoto:
        1. Toma el máximo componente a componente
        2. Incrementa la posición propia
        """
        with self._lock:
            self._clock = [max(a, b) for a, b in zip(self._clock, remote)]
            self._clock[self._idx] += 1
            return self._clock.copy()

    @staticmethod
    def happens_before(a: list[int], b: list[int]) -> bool:
        """a → b si a[i] ≤ b[i] para todo i, y existe j tal que a[j] < b[j]"""
        return (
            all(x <= y for x, y in zip(a, b)) and
            any(x <  y for x, y in zip(a, b))
        )

    @staticmethod
    def is_concurrent(a: list[int], b: list[int]) -> bool:
        """Concurrentes si ninguno precede causalmente al otro."""
        return (
            not VectorClock.happens_before(a, b) and
            not VectorClock.happens_before(b, a)
        )
```

**Serialización:** Se almacena como string JSON en la BD: `"[3,1,2]"`

**Resolución de conflictos:** Cuando dos eventos concurrentes modifican el mismo asiento, gana el primero en escribir en la BD ("first-write-wins") mediante una operación atómica `UPDATE ... WHERE estado = estado_anterior`.

---

### 3.3 Algoritmo de Dijkstra

**Archivo:** `node/dijkstra.py`

**Propósito:** Encontrar la ruta más corta entre dos aeropuertos en el grafo dirigido de rutas comerciales.

**Estructura del grafo:**
- **Nodos:** 15 aeropuertos (ATL, PEK, DXB, TYO, LON, LAX, PAR, FRA, IST, SIN, MAD, AMS, DFW, CAN, SAO)
- **Aristas:** Rutas comerciales dirigidas con peso = distancia en km
- **Dirigido:** La ruta SAO→MAD puede existir sin que exista MAD→SAO

**Implementación (heap mínimo):**

```python
def dijkstra(grafo, origen, destino):
    """Complejidad: O((V + E) log V)"""
    heap = [(0, origen, [origen])]   # (distancia, nodo_actual, camino)
    visitados = set()

    while heap:
        dist_acum, nodo, camino = heapq.heappop(heap)

        if nodo in visitados:
            continue
        visitados.add(nodo)

        if nodo == destino:
            return _build_result(camino, dist_acum, grafo)

        for vecino, peso in grafo.get(nodo, {}).items():
            if vecino not in visitados:
                heapq.heappush(heap, (dist_acum + peso, vecino, camino + [vecino]))

    return None   # no existe ruta
```

**Endpoints disponibles:**
- `GET /routes/shortest?origen=SAO&destino=ATL` → mejor ruta única
- `GET /routes/alternatives?origen=SAO&destino=ATL&top_n=3` → hasta 3 rutas alternativas
- `GET /routes/reachable?origen=FRA` → todos los aeropuertos alcanzables

---

### 3.4 TSP — Vecino más Cercano

**Archivo:** `node/tsp.py`

**Propósito:** Calcular un circuito que visite todos los aeropuertos alcanzables desde un origen, minimizando la distancia total (o el tiempo de vuelo).

**Heurística del Vecino más Cercano:**
> Desde el nodo actual, ir siempre al aeropuerto no visitado más cercano. Continuar hasta visitar todos y cerrar el circuito.

**Complejidad:** O(n² × Dijkstra) donde n = número de aeropuertos

**Implementación:**

```python
def nearest_neighbor_tsp(routes, origen, criterio="costo"):
    # Construir grafo con pesos según criterio
    # criterio="costo"  → peso = distancia_km
    # criterio="tiempo" → peso = distancia_km / 900  (horas a 900 km/h)
    grafo = _build_graph(routes, criterio)

    # Obtener todos los aeropuertos alcanzables desde el origen
    alcanzables = set(_dijkstra(grafo, origen).keys())

    visitados  = [origen]
    actual     = origen
    costo_total = 0.0

    while len(visitados) < len(alcanzables):
        # Distancias mínimas desde el nodo actual (Dijkstra)
        distancias = _dijkstra(grafo, actual)

        # Seleccionar el aeropuerto no visitado más cercano
        siguiente = min(
            (a for a in alcanzables if a not in visitados),
            key=lambda x: distancias.get(x, math.inf)
        )

        costo_total += distancias[siguiente]
        visitados.append(siguiente)
        actual = siguiente

    # Intentar cerrar el circuito regresando al origen
    regreso = _dijkstra(grafo, actual).get(origen)
    if regreso:
        visitados.append(origen)
        costo_total += regreso

    return {
        "orden_visita":      visitados,
        "distancia_total_km": distancia_km,
        "tiempo_total_h":    tiempo_h,
        "circuito_cerrado":  bool(regreso),
    }
```

**Endpoint:** `GET /routes/tsp?origen=FRA&criterio=costo`

**Criterios:**
- `costo` → minimiza kilómetros totales
- `tiempo` → minimiza horas de vuelo (velocidad crucero 900 km/h)

---

### 3.5 Fórmula de Haversine

**Archivo:** `node/load_csv.py`

**Propósito:** Calcular la distancia real entre dos aeropuertos usando sus coordenadas GPS, considerando la curvatura de la Tierra (gran círculo).

**Fórmula:**

```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
d = 2R × arcsin(√a)     donde R = 6,371 km
```

**Implementación:**

```python
def _haversine(lat1, lon1, lat2, lon2) -> int:
    R = 6371   # Radio terrestre en km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return max(100, int(R * 2 * math.asin(math.sqrt(a))))
```

**Uso:** Se pre-computa una matriz de distancias para los 15×14 = 210 pares de aeropuertos al cargar el dataset. Esta matriz alimenta el grafo de Dijkstra y el TSP.

**Aeropuertos del sistema (15 nodos):**

| Código | Ciudad | País |
|--------|--------|------|
| ATL | Atlanta | USA |
| PEK | Pekín | China |
| DXB | Dubái | EAU |
| TYO | Tokio | Japón |
| LON | Londres | UK |
| LAX | Los Ángeles | USA |
| PAR | París | Francia |
| FRA | Frankfurt | Alemania |
| IST | Estambul | Turquía |
| SIN | Singapur | Singapur |
| MAD | Madrid | España |
| AMS | Ámsterdam | Países Bajos |
| DFW | Dallas | USA |
| CAN | Cantón | China |
| SAO | São Paulo | Brasil |

---

### 3.6 Máquina de Estados de Vuelos

**Archivo:** `node/main.py`

**Propósito:** Mantener el estado operativo de cada vuelo actualizado en tiempo real, basándose en la hora UTC actual.

**Diagrama de estados:**

```
SCHEDULED ──(30 min antes de salida)──► BOARDING
BOARDING  ──(hora de salida)──────────► IN_FLIGHT
IN_FLIGHT ──(hora de llegada)─────────► ARRIVED

Adicionalmente: DELAYED, CANCELLED (asignados manualmente)
```

**Cálculo del estado:**

```python
def _compute_flight_state(fecha, hora_salida, hora_llegada) -> str:
    now = datetime.now(timezone.utc)
    dep = datetime.combine(fecha, hora_salida, tzinfo=timezone.utc)
    arr = datetime.combine(fecha, hora_llegada, tzinfo=timezone.utc)

    # Vuelos que llegan al día siguiente (ej: 23:00 → 02:00)
    if arr <= dep:
        arr += timedelta(days=1)

    if now >= arr:
        return "ARRIVED"
    if now >= dep:
        return "IN_FLIGHT"
    if now >= dep - timedelta(minutes=30):
        return "BOARDING"
    return "SCHEDULED"
```

**Tarea de fondo (asyncio):** Se ejecuta cada 60 segundos y actualiza el estado de todos los vuelos activos (no ARRIVED, no CANCELLED) en la base de datos local.

```python
async def _background_flight_states():
    while True:
        await asyncio.sleep(60)
        await _compute_and_update_flight_states()
```

---

### 3.7 Máquina de Estados de Asientos

**Archivo:** `node/state_machine.py`

**Propósito:** Definir y validar las transiciones permitidas del estado de un asiento.

**Diagrama de estados:**

```
        reservar         vender
  Libre ────────► Reserva ────────► Venta (terminal)
    ▲                │
    │    devolver    │
    │ ◄──────────────┘
    │
  Libre ◄─────── Devolucion
       (por temporizador: "liberar")
```

**Definición de transiciones:**

```python
_TRANSITIONS = {
    "Libre":      { "reservar":  "Reserva",
                    "vender":    "Venta"    },
    "Reserva":    { "vender":    "Venta",
                    "devolver":  "Devolucion" },
    "Venta":      { },                       # Estado terminal
    "Devolucion": { "liberar":   "Libre" },  # Solo por temporizador
}
```

**Colores en UI:**

| Estado | Color | Hex |
|--------|-------|-----|
| Libre | Verde | `#4CAF50` |
| Reserva | Amarillo | `#FFC107` |
| Venta | Rojo | `#F44336` |
| Devolucion | Gris | `#9E9E9E` |

**Atomicidad:** La transición se aplica con un `UPDATE ... WHERE estado = estado_anterior`. Si el estado cambió entre la lectura y la escritura (concurrencia), el UPDATE afecta 0 filas y la operación es rechazada.

---

## 4. Mecanismo de Sincronización

**Archivo:** `node/sync_service.py`

El sistema usa **replicación optimista peer-to-peer**: cada nodo aplica la operación localmente y luego la propaga a sus pares de forma asíncrona.

### Flujo de Envío (Propagación)

```
Usuario → Nodo1 → aplica operación en BD local
                → genera evento con vector clock
                → propaga a Nodo2 (HTTP POST /sync/event)
                → propaga a Nodo3 (HTTP POST /sync/event)
                     [fire-and-forget, 3 reintentos con backoff 1.5s]
```

### Flujo de Recepción

```python
def apply_remote_event(evento, repo, clock, timer_svc, lamport):
    # 1. Fusionar relojes vectoriales
    nuevo_reloj = clock.merge(evento["reloj_vectorial"])

    # 2. Actualizar reloj de Lamport
    lamport_ts = lamport.update(evento["lamport_timestamp"])

    # 3. Aplicar operación atómica en BD local
    #    Solo tiene éxito si estado_actual == estado_anterior esperado
    ok = repo.apply_seat_operation(
        vuelo_id        = evento["vuelo_id"],
        numero_asiento  = evento["numero_asiento"],
        estado_anterior = evento["estado_anterior"],
        estado_nuevo    = evento["estado_nuevo"],
        reloj_vectorial = nuevo_reloj,
        lamport_timestamp = lamport_ts,
    )

    # 4. Gestionar temporizadores si aplica
    if ok:
        if evento["tipo"] == "devolucion":
            timer_svc.schedule(vuelo_id, numero_asiento)
        elif evento["tipo"] == "liberacion":
            timer_svc.cancel(vuelo_id, numero_asiento)

    return ok
```

### Resolución de Conflictos (First-Write-Wins)

Cuando dos nodos modifican el mismo asiento simultáneamente:

1. Ambos ven el asiento como `Libre` y generan `reservar`
2. El primer evento en llegar a cada BD hace el UPDATE exitoso
3. El segundo evento falla (estado actual ya no es `Libre`)
4. El segundo evento se descarta silenciosamente

### Mecanismo de Catch-up (Recuperación)

Cuando un nodo regresa tras una desconexión:

```
Nodo reconectado → GET /sync/catch-up?since=<epoch>
                 → Consulta a Nodo1: GET /sync/events?since=<epoch>
                 → Consulta a Nodo2: GET /sync/events?since=<epoch>
                 → Aplica todos los eventos faltantes en orden cronológico
```

### Estructura de un Evento Propagado

```json
{
    "tipo":               "reserva",
    "vuelo_id":           "RP00001",
    "numero_asiento":     "12A",
    "estado_anterior":    "Libre",
    "estado_nuevo":       "Reserva",
    "pasaporte_pasajero": "P12345678",
    "nodo_origen":        1,
    "reloj_vectorial":    "[3,1,2]",
    "timestamp_epoch":    1700000000,
    "lamport_timestamp":  42,
    "motivo":             null
}
```

---

## 5. Servicio de Temporizador

**Archivo:** `node/timer_service.py`

**Propósito:** Liberar automáticamente los asientos en estado `Devolucion` después de un timeout configurable.

**Funcionamiento:**

```
Asiento pasa a "Devolucion"
         │
         ▼
  TimerService.schedule(vuelo_id, numero_asiento)
         │
         ▼  (espera REFUND_TIMEOUT_SECONDS — por defecto 900s = 15 min)
         │
         ▼
  _on_timer_fired():
    → aplica "Devolucion → Libre" en BD local
    → propaga evento "liberacion" a los otros 2 nodos
```

**Configuración:** Variable de entorno `REFUND_TIMEOUT_SECONDS` (configurable en `docker-compose.yml`).

**Thread-safety:**
- Un `threading.Timer` independiente por asiento
- Lock para acceso concurrente al diccionario de timers
- Si el timer dispara pero otro nodo ya liberó el asiento → `apply_seat_operation` devuelve `False` y no se genera evento duplicado

**Cancelación:** Si una operación cancela la devolución (ej. el sistema recibe un evento de liberación del peer primero), `timer_svc.cancel(vuelo_id, numero_asiento)` anula el timer pendiente.

---

## 6. Esquema de Base de Datos

### SQL Server (Nodos 1 y 2)

```sql
-- Aeropuertos (15 filas)
CREATE TABLE aeropuertos (
    codigo   CHAR(3)      PRIMARY KEY,
    nombre   NVARCHAR(100) NOT NULL,
    ciudad   NVARCHAR(100) NOT NULL,
    pais     NVARCHAR(100) NOT NULL,
    timezone NVARCHAR(50)  NOT NULL,
    latitud  FLOAT         NOT NULL,
    longitud FLOAT         NOT NULL
);

-- Rutas comerciales (grafo dirigido)
CREATE TABLE rutas_comerciales (
    ruta_id      INT           PRIMARY KEY IDENTITY,
    origen       CHAR(3)       NOT NULL REFERENCES aeropuertos(codigo),
    destino      CHAR(3)       NOT NULL REFERENCES aeropuertos(codigo),
    distancia_km INT           NOT NULL,
    activa       BIT           NOT NULL DEFAULT 1,
    CONSTRAINT uq_ruta_par UNIQUE (origen, destino)
);

-- Vuelos (60,000 filas)
CREATE TABLE vuelos (
    vuelo_id     NVARCHAR(10)  PRIMARY KEY,
    origen       CHAR(3)       NOT NULL REFERENCES aeropuertos(codigo),
    destino      CHAR(3)       NOT NULL REFERENCES aeropuertos(codigo),
    fecha        DATE          NOT NULL,
    hora_salida  TIME          NOT NULL,
    hora_llegada TIME          NOT NULL,
    aeronave     NVARCHAR(50)  NOT NULL,
    capacidad    INT           NOT NULL,
    activo       BIT           NOT NULL DEFAULT 1,
    estado       NVARCHAR(15)  NOT NULL DEFAULT 'SCHEDULED'
    -- estado ∈ {SCHEDULED, BOARDING, IN_FLIGHT, ARRIVED, DELAYED, CANCELLED}
);
CREATE INDEX ix_vuelos_ruta_fecha ON vuelos(origen, destino, fecha);

-- Pasajeros
CREATE TABLE pasajeros (
    pasaporte  NVARCHAR(20)  PRIMARY KEY,
    nombre     NVARCHAR(200) NOT NULL,
    email      NVARCHAR(200) NULL,
    created_at DATETIME2     NOT NULL DEFAULT GETUTCDATE()
);

-- Asientos (1,980,000 filas)
CREATE TABLE asientos (
    asiento_id         INT           PRIMARY KEY IDENTITY,
    vuelo_id           NVARCHAR(10)  NOT NULL REFERENCES vuelos(vuelo_id),
    numero_asiento     NVARCHAR(5)   NOT NULL,
    clase              NVARCHAR(20)  NOT NULL,
    -- clase ∈ {primera, business, economica}
    estado             NVARCHAR(20)  NOT NULL DEFAULT 'Libre',
    -- estado ∈ {Libre, Reserva, Venta, Devolucion}
    pasaporte_pasajero NVARCHAR(20)  NULL REFERENCES pasajeros(pasaporte),
    precio             DECIMAL(10,2) NOT NULL,
    updated_at         DATETIME2     NOT NULL DEFAULT GETUTCDATE(),
    CONSTRAINT uq_asiento_vuelo UNIQUE (vuelo_id, numero_asiento)
);
CREATE INDEX ix_asientos_vuelo_estado ON asientos(vuelo_id, estado);

-- Eventos (log del reloj vectorial)
CREATE TABLE eventos (
    evento_id           INT           PRIMARY KEY IDENTITY,
    tipo                NVARCHAR(20)  NOT NULL,
    -- tipo ∈ {reserva, venta, devolucion, liberacion}
    vuelo_id            NVARCHAR(10)  NOT NULL,
    numero_asiento      NVARCHAR(5)   NOT NULL,
    estado_anterior     NVARCHAR(20)  NOT NULL,
    estado_nuevo        NVARCHAR(20)  NOT NULL,
    pasaporte_pasajero  NVARCHAR(20)  NULL,
    nodo_origen         INT           NOT NULL,  -- 1, 2 o 3
    reloj_vectorial     NVARCHAR(50)  NOT NULL,  -- "[3,1,2]"
    timestamp_utc       DATETIME2     NOT NULL,
    aplicado            BIT           NOT NULL DEFAULT 1,
    motivo              NVARCHAR(500) NULL,
    timestamp_epoch     BIGINT        NOT NULL,
    lamport_timestamp   BIGINT        NOT NULL DEFAULT 0
);
CREATE INDEX ix_eventos_nodo_tiempo ON eventos(nodo_origen, timestamp_utc);
```

### MongoDB (Nodo 3)

Misma estructura como colecciones con validación `$jsonSchema`. Diferencias notables:
- `_id` reemplaza a la PK relacional (código IATA para aeropuertos, vuelo_id para vuelos, pasaporte para pasajeros)
- `asientos` usa `ObjectId` automático como `_id`
- Los mismos índices únicos se replican con `createIndex({ ... }, { unique: true })`

### Distribución de Asientos por Vuelo

Cada vuelo tiene **30 asientos** distribuidos así:

| Clase | Cantidad | Precio | Asientos |
|-------|----------|--------|---------|
| Primera | 3 | $1,200 | 1A, 1B, 2A |
| Business | 6 | $450 | 2C, 2D, 3C, 3D, 4C, 4D |
| Económica | 21 | $150 | 5A–5F, 6A–6F, 7A–7F |

**Distribución inicial de estados (dataset):**

| Estado | Probabilidad | Descripción |
|--------|-------------|-------------|
| Venta | 35% | Asiento vendido con pasajero asignado |
| Reserva | 3% | Asiento reservado con pasajero asignado |
| Libre | 62% | Disponible para reservar o comprar |

---

## 7. API REST — Endpoints

### Vuelos

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/flights` | Buscar vuelos (origen, destino, fecha — todos opcionales) |
| GET | `/flights/stats` | Estadísticas globales: ocupación, ingresos, distribución |
| GET | `/flights/{vuelo_id}` | Detalle de un vuelo con info de aeropuertos |
| GET | `/flights/{vuelo_id}/stats` | Estadísticas por vuelo y clase |

### Asientos

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/flights/{vuelo_id}/seats` | Mapa completo de asientos con estado y color |
| GET | `/flights/{vuelo_id}/seats/{numero}` | Detalle de un asiento específico |
| POST | `/flights/{vuelo_id}/seats/{numero}/reservar` | Reservar asiento |
| POST | `/flights/{vuelo_id}/seats/{numero}/vender` | Vender asiento |
| POST | `/flights/{vuelo_id}/seats/{numero}/devolver` | Devolver asiento |

**Body de reserva/venta:**
```json
{ "pasaporte": "P12345678", "nombre": "Ana García", "email": "ana@mail.com" }
```

**Respuesta de operación:**
```json
{
    "ok": true,
    "estado_nuevo": "Reserva",
    "reloj_vectorial": "[3,1,2]",
    "lamport_timestamp": 42
}
```

### Pasajeros

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/passengers/{pasaporte}` | Buscar pasajero por pasaporte |
| POST | `/passengers` | Crear/actualizar pasajero |

### Rutas y Algoritmos

| Método | Endpoint | Descripción | Algoritmo |
|--------|---------|-------------|-----------|
| GET | `/routes/airports` | Listar los 15 aeropuertos | — |
| GET | `/routes/shortest` | Ruta más corta entre dos aeropuertos | Dijkstra |
| GET | `/routes/alternatives` | Top N rutas alternativas | Dijkstra |
| GET | `/routes/reachable` | Aeropuertos alcanzables desde origen | BFS |
| GET | `/routes/tsp` | Circuito TSP desde un origen | Nearest-Neighbor + Dijkstra |

### Sincronización

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| POST | `/sync/event` | Recibir evento de un nodo par |
| GET | `/sync/events` | Exportar eventos desde un epoch (para catch-up) |
| GET | `/sync/catch-up` | Recuperar eventos perdidos de todos los pares |
| GET | `/sync/status` | Estado del nodo: reloj vectorial, timers activos |

### Pase de Abordar

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/boarding-pass/pdf` | Generar PDF del pase de abordar |

---

## 8. Frontend

Aplicación Streamlit multilingüe (Español / Inglés) que se comunica con cualquiera de los 3 nodos.

### Página Principal
- Selector de idioma (ES/EN)
- Selector de nodo regional (Europa/Frankfurt, Asia/Tokio, Sudamérica/La Paz)
- Estado de salud del sistema (los 3 nodos)

### Página 1 — Buscar Vuelo
- Búsqueda incremental por origen, destino y fecha (todos opcionales)
- Muestra sugerencia de ruta Dijkstra (directa o con escalas)
- Lista de vuelos con estado actual (SCHEDULED, BOARDING, IN_FLIGHT, ARRIVED)

### Página 2 — Mapa de Asientos
- Grilla interactiva con un botón por asiento
- Colores según estado del asiento
- Panel lateral con detalle: clase, precio, pasajero asignado
- Formulario de acción: ingresar pasaporte, nombre, email
- Actualización en tiempo real del estado y reloj vectorial

### Página 3 — Pase de Abordar
- Descarga de PDF A6 (tarjeta de embarque) generado con ReportLab
- Incluye: nombre del pasajero, vuelo, ruta, fecha, asiento, clase, node_id

### Página 4 — Dashboard por Vuelo
- KPIs: porcentaje de ocupación, ingreso total
- Barras horizontales: distribución por estado y por clase

### Página 5 — Dashboard Global
- Totales consolidados de los 3 nodos
- Ingreso total del sistema, ocupación media, vuelos por estado

---

## 9. Flujo Completo de una Operación

**Escenario:** Usuario reserva el asiento 12A del vuelo RP00001 en Nodo1.

```
1. Frontend envía:
   POST http://nodo1:8001/flights/RP00001/seats/12A/reservar
   Body: { "pasaporte": "P12345678", "nombre": "Ana García" }

2. Router (seats.py) en Nodo1:
   a. lamport_ts  = lamport.tick()          → 43
   b. reloj       = clock.tick_and_serialize() → "[4,1,2]"
   c. repo.apply_seat_operation(
          estado_anterior="Libre", estado_nuevo="Reserva",
          reloj_vectorial="[4,1,2]", lamport_timestamp=43
      )
      → Ejecuta: UPDATE asientos SET estado='Reserva' WHERE vuelo_id='RP00001'
                 AND numero_asiento='12A' AND estado='Libre'
      → Inserta en eventos: tipo='reserva', reloj='[4,1,2]', lamport=43

3. Nodo1 responde inmediatamente al Frontend:
   { "ok": true, "estado_nuevo": "Reserva", "reloj_vectorial": "[4,1,2]" }

4. En background, Nodo1 propaga a los pares:
   POST nodo2:8002/sync/event  ─────────────────► Nodo2
   POST nodo3:8003/sync/event  ─────────────────► Nodo3

5. Nodo2 (al recibir el evento):
   a. clock.merge("[4,1,2]")   → "[4,2,2]"  (incrementa su propio índice)
   b. lamport.update(43)       → 44
   c. UPDATE asientos... WHERE estado='Libre'  → éxito (asiento estaba Libre)
   d. INSERT en eventos locales

6. Nodo3 (al recibir el evento):
   a. clock.merge("[4,1,2]")   → "[4,1,3]"  (incrementa su propio índice)
   b. lamport.update(43)       → 44
   c. updateOne en asientos... donde estado='Libre'  → éxito
   d. insertOne en eventos

7. Los 3 nodos ahora tienen el asiento 12A en estado "Reserva".
   Consistencia eventual alcanzada.
```

---

*Aerolíneas Rafael Pabón — Sistema Distribuido de Reservas v2*
*Tecnologías: FastAPI · SQL Server · MongoDB · Streamlit · Docker*
