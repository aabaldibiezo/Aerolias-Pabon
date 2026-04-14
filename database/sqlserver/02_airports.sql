-- =============================================
-- AEROLÍNEAS RAFAEL PABON
-- 02_airports.sql — Aeropuertos y grafo dirigido de rutas
-- Motor: SQL Server 2022
-- Idempotente: seguro de ejecutar múltiples veces
-- =============================================

USE aerlonia_pabon;
GO

-- ─────────────────────────────────────────
-- AEROPUERTOS (15 nodos del grafo)
-- ─────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM aeropuertos WHERE codigo = 'ATL')
BEGIN
    INSERT INTO aeropuertos (codigo, nombre, ciudad, pais, timezone, latitud, longitud) VALUES
    ('ATL', 'Hartsfield-Jackson Atlanta International', 'Atlanta',       'Estados Unidos', 'America/New_York',    33.636719, -84.428067),
    ('PEK', 'Beijing Capital International',             'Pekín',         'China',          'Asia/Shanghai',       40.080111,  116.584556),
    ('DXB', 'Dubai International Airport',               'Dubái',         'Emiratos Árabes','Asia/Dubai',          25.252778,   55.364444),
    ('TYO', 'Tokyo Haneda Airport',                      'Tokio',         'Japón',          'Asia/Tokyo',          35.553333,  139.781113),
    ('LON', 'London Heathrow Airport',                   'Londres',       'Reino Unido',    'Europe/London',       51.477500,   -0.461389),
    ('LAX', 'Los Angeles International Airport',         'Los Ángeles',   'Estados Unidos', 'America/Los_Angeles', 33.942536, -118.408075),
    ('PAR', 'Charles de Gaulle Airport',                 'París',         'Francia',        'Europe/Paris',        49.009722,    2.547778),
    ('FRA', 'Frankfurt Airport',                         'Fráncfort',     'Alemania',       'Europe/Berlin',       50.026421,    8.543125),
    ('IST', 'Istanbul Airport',                          'Estambul',      'Turquía',        'Europe/Istanbul',     41.275278,   28.751944),
    ('SIN', 'Singapore Changi Airport',                  'Singapur',      'Singapur',       'Asia/Singapore',       1.359167,  103.989441),
    ('MAD', 'Adolfo Suárez Madrid-Barajas Airport',      'Madrid',        'España',         'Europe/Madrid',       40.471926,   -3.560833),
    ('AMS', 'Amsterdam Airport Schiphol',                'Ámsterdam',     'Países Bajos',   'Europe/Amsterdam',    52.308056,    4.764167),
    ('DFW', 'Dallas/Fort Worth International Airport',   'Dallas',        'Estados Unidos', 'America/Chicago',     32.896800,  -97.038000),
    ('CAN', 'Guangzhou Baiyun International Airport',    'Cantón',        'China',          'Asia/Shanghai',       23.392356,  113.299064),
    ('SAO', 'São Paulo/Guarulhos International Airport', 'São Paulo',     'Brasil',         'America/Sao_Paulo',  -23.432075,  -46.469511);

    PRINT '15 aeropuertos insertados.';
END
ELSE
    PRINT 'Aeropuertos ya existen, se omite la inserción.';
GO

-- ─────────────────────────────────────────
-- RUTAS COMERCIALES — Grafo DIRIGIDO
--
-- Notación:  A → B  significa que existe vuelo de A a B
--            A ↔ B  significa que existe en ambas direcciones
--
-- No todas las rutas son bidireccionales.
-- Ejemplo: SAO → MAD existe, pero MAD → SAO también existe.
--          ATL → SAO existe, pero SAO → ATL NO existe directamente
--          (hay que hacer escala: SAO → MAD → ATL o SAO → LON → ATL)
--
-- distancia_km = peso para el algoritmo Dijkstra
-- ─────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM rutas_comerciales WHERE origen = 'ATL' AND destino = 'LON')
BEGIN
    INSERT INTO rutas_comerciales (origen, destino, distancia_km) VALUES

    -- ── NORTEAMÉRICA ↔ EUROPA ──────────────────────────────────────────
    ('ATL', 'LON',  6750),  -- Atlanta → Londres
    ('LON', 'ATL',  6750),  -- Londres → Atlanta  (bidireccional)
    ('ATL', 'MAD',  7200),  -- Atlanta → Madrid
    ('MAD', 'ATL',  7200),  -- Madrid → Atlanta   (bidireccional)
    ('DFW', 'MAD',  8150),  -- Dallas → Madrid
    ('DFW', 'FRA',  8390),  -- Dallas → Fráncfort
    ('LAX', 'LON',  8755),  -- Los Ángeles → Londres
    ('LON', 'LAX',  8755),  -- Londres → Los Ángeles (bidireccional)

    -- ── NORTEAMÉRICA INTERNA ───────────────────────────────────────────
    ('ATL', 'LAX',  3380),  -- Atlanta → Los Ángeles
    ('LAX', 'ATL',  3380),  -- Los Ángeles → Atlanta (bidireccional)
    ('ATL', 'DFW',  1150),  -- Atlanta → Dallas
    ('DFW', 'ATL',  1150),  -- Dallas → Atlanta       (bidireccional)
    ('DFW', 'LAX',  1990),  -- Dallas → Los Ángeles
    ('LAX', 'DFW',  1990),  -- Los Ángeles → Dallas   (bidireccional)

    -- ── NORTEAMÉRICA → SUDAMÉRICA (solo ida) ──────────────────────────
    ('ATL', 'SAO',  7600),  -- Atlanta → São Paulo  (NO hay SAO → ATL directo)
    ('DFW', 'SAO',  8510),  -- Dallas → São Paulo   (NO hay SAO → DFW directo)

    -- ── SUDAMÉRICA ↔ EUROPA ────────────────────────────────────────────
    ('SAO', 'MAD',  8280),  -- São Paulo → Madrid
    ('MAD', 'SAO',  8280),  -- Madrid → São Paulo  (bidireccional)
    ('SAO', 'LON',  9540),  -- São Paulo → Londres
    ('LON', 'SAO',  9540),  -- Londres → São Paulo (bidireccional)
    ('SAO', 'PAR',  9350),  -- São Paulo → París
    ('PAR', 'SAO',  9350),  -- París → São Paulo   (bidireccional)

    -- ── EUROPA INTERNA ─────────────────────────────────────────────────
    ('LON', 'PAR',   340),  -- Londres ↔ París
    ('PAR', 'LON',   340),
    ('LON', 'FRA',   650),  -- Londres ↔ Fráncfort
    ('FRA', 'LON',   650),
    ('LON', 'AMS',   360),  -- Londres ↔ Ámsterdam
    ('AMS', 'LON',   360),
    ('LON', 'MAD',  1260),  -- Londres ↔ Madrid
    ('MAD', 'LON',  1260),
    ('PAR', 'MAD',  1050),  -- París ↔ Madrid
    ('MAD', 'PAR',  1050),
    ('PAR', 'FRA',   480),  -- París ↔ Fráncfort
    ('FRA', 'PAR',   480),
    ('AMS', 'FRA',   360),  -- Ámsterdam ↔ Fráncfort
    ('FRA', 'AMS',   360),
    ('FRA', 'IST',  2230),  -- Fráncfort ↔ Estambul
    ('IST', 'FRA',  2230),

    -- ── EUROPA → ASIA (algunas solo ida para demostrar Dijkstra) ───────
    ('LON', 'DXB',  5490),  -- Londres ↔ Dubái
    ('DXB', 'LON',  5490),
    ('FRA', 'PEK',  7820),  -- Fráncfort → Pekín (NO hay PEK → FRA directo)
    ('IST', 'DXB',  2680),  -- Estambul ↔ Dubái
    ('DXB', 'IST',  2680),

    -- ── MEDIO ORIENTE / ASIA ───────────────────────────────────────────
    ('DXB', 'SIN',  5840),  -- Dubái ↔ Singapur
    ('SIN', 'DXB',  5840),
    ('DXB', 'PEK',  5990),  -- Dubái → Pekín (NO hay PEK → DXB directo)

    -- ── ASIA INTERNA ───────────────────────────────────────────────────
    ('PEK', 'TYO',  2100),  -- Pekín ↔ Tokio
    ('TYO', 'PEK',  2100),
    ('PEK', 'SIN',  4470),  -- Pekín ↔ Singapur
    ('SIN', 'PEK',  4470),
    ('PEK', 'CAN',  1900),  -- Pekín ↔ Cantón
    ('CAN', 'PEK',  1900),
    ('TYO', 'SIN',  5310),  -- Tokio ↔ Singapur
    ('SIN', 'TYO',  5310),
    ('CAN', 'SIN',  2480),  -- Cantón ↔ Singapur
    ('SIN', 'CAN',  2480),

    -- ── TRANSPACÍFICO ──────────────────────────────────────────────────
    ('LAX', 'TYO',  8800),  -- Los Ángeles ↔ Tokio
    ('TYO', 'LAX',  8800),
    ('LAX', 'SIN', 14100),  -- Los Ángeles → Singapur (NO hay SIN → LAX directo)

    -- ── ASIA → EUROPA (ruta de regreso por escala) ─────────────────────
    ('PEK', 'IST',  6800);  -- Pekín → Estambul (permite regresar PEK → IST → FRA)
    -- SIN → DXB ya insertado en línea 113 (Dubái ↔ Singapur)

    PRINT 'Rutas comerciales del grafo dirigido insertadas.';
END
ELSE
    PRINT 'Rutas ya existen, se omite la inserción.';
GO

PRINT '=== Aeropuertos y rutas listos ===';
GO
