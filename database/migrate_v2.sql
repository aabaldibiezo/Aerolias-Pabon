-- =============================================
-- AEROLÍNEAS RAFAEL PABON
-- migrate_v2.sql — Migraciones para actualización a v2
--
-- Ejecutar en ambos SQL Server (nodo1 y nodo2):
--   docker exec arlp_sqlserver1 /opt/mssql-tools18/bin/sqlcmd \
--     -S localhost -U sa -P "$SA_PASSWORD" -No \
--     -i /init/migrate_v2.sql
--
-- Cambios:
--   1. eventos: agrega columna lamport_timestamp (si no existe)
--   2. vuelos:  agrega columna estado (si no existe)
-- =============================================

USE aerlonia_pabon;
GO

-- ─────────────────────────────────────────
-- 1. Agregar lamport_timestamp a eventos
-- ─────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID(N'eventos') AND name = N'lamport_timestamp'
)
BEGIN
    ALTER TABLE eventos
        ADD lamport_timestamp BIGINT NOT NULL DEFAULT 0;
    PRINT 'Columna lamport_timestamp agregada a eventos.';
END
ELSE
    PRINT 'Columna lamport_timestamp ya existe en eventos.';
GO

-- ─────────────────────────────────────────
-- 2. Agregar estado a vuelos
-- ─────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID(N'vuelos') AND name = N'estado'
)
BEGIN
    ALTER TABLE vuelos
        ADD estado NVARCHAR(15) NOT NULL DEFAULT 'SCHEDULED';
    PRINT 'Columna estado agregada a vuelos.';
END
ELSE
    PRINT 'Columna estado ya existe en vuelos.';
GO

PRINT '=== Migración v2 completada ===';
GO
