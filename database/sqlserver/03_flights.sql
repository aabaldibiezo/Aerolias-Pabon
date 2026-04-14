-- =============================================
-- AEROLÍNEAS RAFAEL PABON
-- 03_flights.sql — Pasajeros de prueba, vuelos y asientos
-- Motor: SQL Server 2022
-- Idempotente: seguro de ejecutar múltiples veces
--
-- Distribución de asientos por vuelo (174 total):
--   Primera clase : filas  1-3,  columnas A-D  →  12 asientos
--   Business      : filas  4-9,  columnas A-F  →  36 asientos
--   Económica     : filas 10-30, columnas A-F  → 126 asientos
-- =============================================

USE aerlonia_pabon;
GO

-- ─────────────────────────────────────────
-- PASAJEROS DE PRUEBA
-- ─────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM pasajeros WHERE pasaporte = 'US1234567')
BEGIN
    INSERT INTO pasajeros (pasaporte, nombre, email) VALUES
    ('US1234567',  'James Wilson',          'jwilson@email.com'),
    ('US9876543',  'Emily Johnson',         'ejohnson@email.com'),
    ('GB2345678',  'Oliver Smith',          'osmith@email.com'),
    ('DE3456789',  'Hans Müller',           'hmuller@email.com'),
    ('FR4567890',  'Marie Dupont',          'mdupont@email.com'),
    ('JP5678901',  'Kenji Tanaka',          'ktanaka@email.com'),
    ('CN6789012',  'Wei Zhang',             'wzhang@email.com'),
    ('BR7890123',  'Ana Paula Souza',       'apsouza@email.com'),
    ('ES8901234',  'Carlos García',         'cgarcia@email.com'),
    ('SG9012345',  'Li Wei',                'liwei@email.com'),
    ('TR0123456',  'Ayşe Kaya',             'akaya@email.com'),
    ('AE1357924',  'Mohammed Al-Rashid',    'malrashid@email.com'),
    ('AR2468013',  'Diego Fernández',       'dfernandez@email.com'),
    ('AU3579124',  'Sarah Mitchell',        'smitchell@email.com'),
    ('CA4680235',  'Pierre Tremblay',       'ptremblay@email.com');

    PRINT '15 pasajeros de prueba insertados.';
END
GO

-- ─────────────────────────────────────────
-- PROCEDIMIENTO AUXILIAR: generar asientos
-- Crea los 174 asientos de un vuelo dado
-- ─────────────────────────────────────────
IF OBJECT_ID('sp_generar_asientos', 'P') IS NOT NULL
    DROP PROCEDURE sp_generar_asientos;
GO

CREATE PROCEDURE sp_generar_asientos
    @vuelo_id       NVARCHAR(10),
    @precio_primera DECIMAL(10,2),
    @precio_business DECIMAL(10,2),
    @precio_eco      DECIMAL(10,2)
AS
BEGIN
    SET NOCOUNT ON;

    -- Solo genera si el vuelo no tiene asientos aún
    IF EXISTS (SELECT 1 FROM asientos WHERE vuelo_id = @vuelo_id)
    BEGIN
        PRINT 'Asientos de ' + @vuelo_id + ' ya existen, se omite.';
        RETURN;
    END

    -- CTE para números de fila 1-30
    -- Nota: el punto y coma es obligatorio antes de WITH en SQL Server
    ;WITH filas AS (
        SELECT  1 AS f UNION ALL SELECT  2 UNION ALL SELECT  3 UNION ALL
        SELECT  4 UNION ALL SELECT  5 UNION ALL SELECT  6 UNION ALL
        SELECT  7 UNION ALL SELECT  8 UNION ALL SELECT  9 UNION ALL
        SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL
        SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15 UNION ALL
        SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL
        SELECT 19 UNION ALL SELECT 20 UNION ALL SELECT 21 UNION ALL
        SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24 UNION ALL
        SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL
        SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
    ),
    -- Columnas disponibles por clase
    cols AS (
        SELECT 'A' AS c UNION ALL SELECT 'B' UNION ALL SELECT 'C' UNION ALL
        SELECT 'D' UNION ALL SELECT 'E' UNION ALL SELECT 'F'
    )
    INSERT INTO asientos (vuelo_id, numero_asiento, clase, precio)
    SELECT
        @vuelo_id,
        CAST(f AS NVARCHAR(3)) + c                      AS numero_asiento,
        CASE
            WHEN f <=  3 THEN 'primera'
            WHEN f <=  9 THEN 'business'
            ELSE              'economica'
        END                                             AS clase,
        CASE
            WHEN f <=  3 THEN @precio_primera
            WHEN f <=  9 THEN @precio_business
            ELSE              @precio_eco
        END                                             AS precio
    FROM filas
    CROSS JOIN cols
    -- Primera clase: solo columnas A-D (sin E ni F)
    WHERE NOT (f <= 3 AND c IN ('E', 'F'))
    ORDER BY f, c;

    PRINT 'Asientos generados para vuelo ' + @vuelo_id + '.';
END
GO

-- ─────────────────────────────────────────
-- VUELOS DE PRUEBA
-- Fechas: abril 2026 para cubrir el contexto del sistema
--
-- Formato hora: hora local del aeropuerto de origen/destino
-- ─────────────────────────────────────────

-- ── TRANSATLÁNTICOS ────────────────────────────────────────────────────

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP001')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP001', 'ATL', 'LON', '2026-04-01', '09:00', '21:30', 'Boeing 777-300ER', 174);
    EXEC sp_generar_asientos 'RP001', 2500.00, 1200.00, 420.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP002')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP002', 'LON', 'ATL', '2026-04-02', '11:00', '14:30', 'Boeing 777-300ER', 174);
    EXEC sp_generar_asientos 'RP002', 2500.00, 1200.00, 420.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP003')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP003', 'SAO', 'MAD', '2026-04-05', '01:30', '14:00', 'Airbus A350-900', 174);
    EXEC sp_generar_asientos 'RP003', 1800.00, 900.00, 380.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP004')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP004', 'MAD', 'SAO', '2026-04-06', '10:00', '18:30', 'Airbus A350-900', 174);
    EXEC sp_generar_asientos 'RP004', 1800.00, 900.00, 380.00;
END

-- ── EUROPA INTERNA ─────────────────────────────────────────────────────

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP005')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP005', 'LON', 'PAR', '2026-04-03', '07:00', '09:15', 'Airbus A320', 174);
    EXEC sp_generar_asientos 'RP005', 600.00, 300.00, 120.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP006')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP006', 'FRA', 'IST', '2026-04-04', '08:30', '12:45', 'Airbus A321', 174);
    EXEC sp_generar_asientos 'RP006', 700.00, 350.00, 140.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP007')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP007', 'MAD', 'PAR', '2026-04-07', '09:00', '11:10', 'Airbus A320', 174);
    EXEC sp_generar_asientos 'RP007', 600.00, 300.00, 110.00;
END

-- ── EUROPA → ASIA ──────────────────────────────────────────────────────

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP008')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP008', 'LON', 'DXB', '2026-04-08', '09:00', '19:00', 'Boeing 787-9', 174);
    EXEC sp_generar_asientos 'RP008', 1500.00, 750.00, 310.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP009')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP009', 'FRA', 'PEK', '2026-04-09', '11:00', '05:00', 'Boeing 747-8',  174);
    -- Nota: FRA → PEK es ruta solo ida en el grafo (PEK → FRA no existe directo)
    EXEC sp_generar_asientos 'RP009', 2200.00, 1100.00, 460.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP010')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP010', 'DXB', 'SIN', '2026-04-10', '02:00', '14:00', 'Airbus A380', 174);
    EXEC sp_generar_asientos 'RP010', 1400.00, 700.00, 290.00;
END

-- ── ASIA INTERNA ───────────────────────────────────────────────────────

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP011')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP011', 'PEK', 'TYO', '2026-04-11', '10:00', '14:30', 'Boeing 737 MAX', 174);
    EXEC sp_generar_asientos 'RP011', 1000.00, 500.00, 200.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP012')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP012', 'SIN', 'TYO', '2026-04-12', '00:30', '08:00', 'Airbus A350-900', 174);
    EXEC sp_generar_asientos 'RP012', 1100.00, 550.00, 220.00;
END

-- ── TRANSPACÍFICO ──────────────────────────────────────────────────────

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP013')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP013', 'LAX', 'TYO', '2026-04-13', '12:00', '16:30', 'Boeing 777-200LR', 174);
    EXEC sp_generar_asientos 'RP013', 3000.00, 1500.00, 600.00;
END

-- ── NORTEAMÉRICA INTERNA ───────────────────────────────────────────────

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP014')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP014', 'ATL', 'LAX', '2026-04-14', '06:00', '08:15', 'Boeing 737-800', 174);
    EXEC sp_generar_asientos 'RP014', 800.00, 400.00, 160.00;
END

IF NOT EXISTS (SELECT 1 FROM vuelos WHERE vuelo_id = 'RP015')
BEGIN
    INSERT INTO vuelos (vuelo_id, origen, destino, fecha, hora_salida, hora_llegada, aeronave, capacidad)
    VALUES ('RP015', 'DFW', 'ATL', '2026-04-15', '07:30', '10:00', 'Airbus A319', 174);
    EXEC sp_generar_asientos 'RP015', 700.00, 350.00, 140.00;
END

-- ─────────────────────────────────────────
-- RESERVAS DE PRUEBA (para ver colores en el mapa)
-- Simula algunos asientos en distintos estados
-- ─────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM asientos WHERE vuelo_id = 'RP001' AND estado <> 'Libre')
BEGIN
    -- Algunas ventas en primera clase
    UPDATE asientos
    SET estado = 'Venta', pasaporte_pasajero = 'US1234567', updated_at = GETUTCDATE()
    WHERE vuelo_id = 'RP001' AND numero_asiento IN ('1A', '1B');

    -- Algunas reservas en business
    UPDATE asientos
    SET estado = 'Reserva', pasaporte_pasajero = 'GB2345678', updated_at = GETUTCDATE()
    WHERE vuelo_id = 'RP001' AND numero_asiento IN ('4A', '4B', '5C');

    -- Una devolución en economía
    UPDATE asientos
    SET estado = 'Devolucion', pasaporte_pasajero = 'FR4567890', updated_at = GETUTCDATE()
    WHERE vuelo_id = 'RP001' AND numero_asiento = '15F';

    PRINT 'Estados de prueba aplicados al vuelo RP001.';
END

-- Limpiar procedimiento auxiliar (ya no se necesita)
DROP PROCEDURE sp_generar_asientos;
GO

PRINT '=== Vuelos y asientos listos — 15 vuelos, 2610 asientos totales ===';
GO
