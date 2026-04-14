-- =============================================
-- AEROLÍNEAS RAFAEL PABON
-- 01_schema.sql — Creación de BD y tablas
-- Motor: SQL Server 2022
-- Idempotente: seguro de ejecutar múltiples veces
-- =============================================

-- Crear base de datos si no existe
IF NOT EXISTS (
    SELECT name FROM sys.databases WHERE name = N'aerlonia_pabon'
)
BEGIN
    CREATE DATABASE aerlonia_pabon
        COLLATE Latin1_General_CI_AS;
    PRINT 'Base de datos aerlonia_pabon creada.';
END
ELSE
    PRINT 'Base de datos aerlonia_pabon ya existe.';
GO

USE aerlonia_pabon;
GO

-- ─────────────────────────────────────────
-- TABLA: aeropuertos
-- Nodos del grafo dirigido de rutas
-- ─────────────────────────────────────────
IF NOT EXISTS (
    SELECT * FROM sys.objects
    WHERE object_id = OBJECT_ID(N'aeropuertos') AND type = N'U'
)
BEGIN
    CREATE TABLE aeropuertos (
        codigo      CHAR(3)         NOT NULL,
        nombre      NVARCHAR(120)   NOT NULL,
        ciudad      NVARCHAR(100)   NOT NULL,
        pais        NVARCHAR(100)   NOT NULL,
        -- Nombre IANA del timezone para calcular hora local y UTC
        timezone    NVARCHAR(60)    NOT NULL,
        latitud     DECIMAL(9,6)    NOT NULL,
        longitud    DECIMAL(9,6)    NOT NULL,
        CONSTRAINT PK_aeropuertos PRIMARY KEY (codigo)
    );
    PRINT 'Tabla aeropuertos creada.';
END
GO

-- ─────────────────────────────────────────
-- TABLA: rutas_comerciales
-- Aristas del grafo DIRIGIDO (no bidireccional)
-- distancia_km es el peso para el algoritmo Dijkstra
-- ─────────────────────────────────────────
IF NOT EXISTS (
    SELECT * FROM sys.objects
    WHERE object_id = OBJECT_ID(N'rutas_comerciales') AND type = N'U'
)
BEGIN
    CREATE TABLE rutas_comerciales (
        ruta_id         INT             NOT NULL IDENTITY(1,1),
        origen          CHAR(3)         NOT NULL,
        destino         CHAR(3)         NOT NULL,
        distancia_km    INT             NOT NULL,
        activa          BIT             NOT NULL DEFAULT 1,
        CONSTRAINT PK_rutas PRIMARY KEY (ruta_id),
        CONSTRAINT FK_ruta_origen  FOREIGN KEY (origen)  REFERENCES aeropuertos(codigo),
        CONSTRAINT FK_ruta_destino FOREIGN KEY (destino) REFERENCES aeropuertos(codigo),
        -- Un par origen-destino es único en el grafo dirigido
        CONSTRAINT UQ_ruta_par UNIQUE (origen, destino),
        CONSTRAINT CHK_ruta_diferente CHECK (origen <> destino),
        CONSTRAINT CHK_distancia CHECK (distancia_km > 0)
    );
    PRINT 'Tabla rutas_comerciales creada.';
END
GO

-- ─────────────────────────────────────────
-- TABLA: vuelos
-- Cada vuelo opera sobre una ruta en una fecha específica
-- ─────────────────────────────────────────
IF NOT EXISTS (
    SELECT * FROM sys.objects
    WHERE object_id = OBJECT_ID(N'vuelos') AND type = N'U'
)
BEGIN
    CREATE TABLE vuelos (
        vuelo_id        NVARCHAR(10)    NOT NULL,   -- Ej: 'RP001'
        origen          CHAR(3)         NOT NULL,
        destino         CHAR(3)         NOT NULL,
        fecha           DATE            NOT NULL,
        hora_salida     TIME(0)         NOT NULL,   -- hora local del aeropuerto origen
        hora_llegada    TIME(0)         NOT NULL,   -- hora local del aeropuerto destino
        aeronave        NVARCHAR(60)    NOT NULL    DEFAULT 'Boeing 737',
        capacidad       INT             NOT NULL    DEFAULT 174,
        activo          BIT             NOT NULL    DEFAULT 1,
        -- Estado operativo del vuelo (actualizado automáticamente por el nodo)
        estado          NVARCHAR(15)    NOT NULL    DEFAULT 'SCHEDULED',
        CONSTRAINT PK_vuelos PRIMARY KEY (vuelo_id),
        CONSTRAINT FK_vuelo_origen  FOREIGN KEY (origen)  REFERENCES aeropuertos(codigo),
        CONSTRAINT FK_vuelo_destino FOREIGN KEY (destino) REFERENCES aeropuertos(codigo),
        CONSTRAINT CHK_vuelo_diferente CHECK (origen <> destino),
        CONSTRAINT CHK_capacidad CHECK (capacidad > 0)
    );
    -- Índice para búsqueda incremental por ruta y fecha
    CREATE INDEX IX_vuelos_ruta_fecha ON vuelos(origen, destino, fecha);
    PRINT 'Tabla vuelos creada.';
END
GO

-- ─────────────────────────────────────────
-- TABLA: pasajeros
-- Se autocompleta por pasaporte en el frontend
-- ─────────────────────────────────────────
IF NOT EXISTS (
    SELECT * FROM sys.objects
    WHERE object_id = OBJECT_ID(N'pasajeros') AND type = N'U'
)
BEGIN
    CREATE TABLE pasajeros (
        pasaporte       NVARCHAR(20)    NOT NULL,
        nombre          NVARCHAR(150)   NOT NULL,
        email           NVARCHAR(150)   NULL,
        created_at      DATETIME2(0)    NOT NULL DEFAULT GETUTCDATE(),
        CONSTRAINT PK_pasajeros PRIMARY KEY (pasaporte)
    );
    -- Índice para autocompletar nombre por pasaporte
    CREATE INDEX IX_pasajeros_nombre ON pasajeros(nombre);
    PRINT 'Tabla pasajeros creada.';
END
GO

-- ─────────────────────────────────────────
-- TABLA: asientos
-- 174 asientos por vuelo con máquina de estados
-- Estados: Libre → Reserva/Venta | Reserva → Venta/Devolucion | Devolucion → Libre
-- ─────────────────────────────────────────
IF NOT EXISTS (
    SELECT * FROM sys.objects
    WHERE object_id = OBJECT_ID(N'asientos') AND type = N'U'
)
BEGIN
    CREATE TABLE asientos (
        asiento_id          INT             NOT NULL IDENTITY(1,1),
        vuelo_id            NVARCHAR(10)    NOT NULL,
        numero_asiento      NVARCHAR(4)     NOT NULL,   -- Ej: '12A', '1D'
        clase               NVARCHAR(15)    NOT NULL,
        estado              NVARCHAR(15)    NOT NULL    DEFAULT 'Libre',
        pasaporte_pasajero  NVARCHAR(20)    NULL,       -- NULL si el asiento está libre
        precio              DECIMAL(10,2)   NOT NULL,
        updated_at          DATETIME2(0)    NOT NULL    DEFAULT GETUTCDATE(),
        CONSTRAINT PK_asientos PRIMARY KEY (asiento_id),
        CONSTRAINT FK_asiento_vuelo     FOREIGN KEY (vuelo_id)           REFERENCES vuelos(vuelo_id),
        CONSTRAINT FK_asiento_pasajero  FOREIGN KEY (pasaporte_pasajero) REFERENCES pasajeros(pasaporte),
        CONSTRAINT UQ_asiento_vuelo     UNIQUE (vuelo_id, numero_asiento),
        CONSTRAINT CHK_clase  CHECK (clase  IN ('primera', 'business', 'economica')),
        CONSTRAINT CHK_estado CHECK (estado IN ('Libre', 'Reserva', 'Venta', 'Devolucion')),
        CONSTRAINT CHK_precio CHECK (precio > 0)
    );
    -- Índice para cargar el mapa de asientos de un vuelo
    CREATE INDEX IX_asientos_vuelo_estado ON asientos(vuelo_id, estado);
    PRINT 'Tabla asientos creada.';
END
GO

-- ─────────────────────────────────────────
-- TABLA: eventos
-- Log del reloj vectorial para sincronización distribuida
-- Cada operación sobre un asiento genera un evento que se
-- propaga a los otros 2 nodos
-- ─────────────────────────────────────────
IF NOT EXISTS (
    SELECT * FROM sys.objects
    WHERE object_id = OBJECT_ID(N'eventos') AND type = N'U'
)
BEGIN
    CREATE TABLE eventos (
        evento_id           INT             NOT NULL IDENTITY(1,1),
        tipo                NVARCHAR(15)    NOT NULL,   -- 'reserva','venta','devolucion','liberacion'
        vuelo_id            NVARCHAR(10)    NOT NULL,
        asiento_id          INT             NOT NULL,
        numero_asiento      NVARCHAR(4)     NOT NULL,
        estado_anterior     NVARCHAR(15)    NOT NULL,
        estado_nuevo        NVARCHAR(15)    NOT NULL,
        pasaporte_pasajero  NVARCHAR(20)    NULL,
        nodo_origen         TINYINT         NOT NULL,   -- 1, 2 o 3
        -- Reloj vectorial serializado: Ej. "[3,1,2]" (valores para nodo1, nodo2, nodo3)
        reloj_vectorial     NVARCHAR(50)    NOT NULL,
        timestamp_utc       DATETIME2(3)    NOT NULL    DEFAULT GETUTCDATE(),
        -- Indica si este nodo ya procesó/aplicó el evento recibido de otro nodo
        aplicado            BIT             NOT NULL    DEFAULT 1,
        motivo              NVARCHAR(500)   NULL,       -- Razón de devolución u observación
        timestamp_epoch     BIGINT          NOT NULL    DEFAULT 0,  -- Unix timestamp UTC (segundos)
        lamport_timestamp   BIGINT          NOT NULL    DEFAULT 0   -- Reloj de Lamport al momento del evento
        CONSTRAINT PK_eventos PRIMARY KEY (evento_id),
        CONSTRAINT CHK_evento_tipo   CHECK (tipo          IN ('reserva', 'venta', 'devolucion', 'liberacion')),
        CONSTRAINT CHK_evento_estado_ant CHECK (estado_anterior IN ('Libre', 'Reserva', 'Venta', 'Devolucion')),
        CONSTRAINT CHK_evento_estado_nvo CHECK (estado_nuevo    IN ('Libre', 'Reserva', 'Venta', 'Devolucion')),
        CONSTRAINT CHK_nodo_origen   CHECK (nodo_origen IN (1, 2, 3))
    );
    -- Índice para sincronización: buscar eventos no aplicados por nodo
    CREATE INDEX IX_eventos_nodo_tiempo  ON eventos(nodo_origen, timestamp_utc);
    CREATE INDEX IX_eventos_asiento      ON eventos(asiento_id, timestamp_utc);
    PRINT 'Tabla eventos creada.';
END
GO

PRINT '=== Schema aerlonia_pabon listo ===';
GO
