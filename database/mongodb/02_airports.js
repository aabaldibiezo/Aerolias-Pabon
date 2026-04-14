// =============================================
// AEROLÍNEAS RAFAEL PABON
// 02_airports.js — Aeropuertos y grafo dirigido de rutas
// Motor: MongoDB 7
// Espejo exacto de 02_airports.sql
// Idempotente: seguro de ejecutar múltiples veces
// =============================================

db = db.getSiblingDB('aerlonia_pabon');

// ─────────────────────────────────────────
// AEROPUERTOS (15 nodos del grafo)
// _id = código IATA (clave natural, igual que SQL Server)
// ─────────────────────────────────────────
const aeropuertosExistentes = db.aeropuertos.countDocuments();

if (aeropuertosExistentes === 0) {
    db.aeropuertos.insertMany([
        { _id: 'ATL', nombre: 'Hartsfield-Jackson Atlanta International', ciudad: 'Atlanta',      pais: 'Estados Unidos', timezone: 'America/New_York',    latitud:  33.636719, longitud:  -84.428067 },
        { _id: 'PEK', nombre: 'Beijing Capital International',            ciudad: 'Pekín',        pais: 'China',          timezone: 'Asia/Shanghai',       latitud:  40.080111, longitud:  116.584556 },
        { _id: 'DXB', nombre: 'Dubai International Airport',              ciudad: 'Dubái',        pais: 'Emiratos Árabes',timezone: 'Asia/Dubai',          latitud:  25.252778, longitud:   55.364444 },
        { _id: 'TYO', nombre: 'Tokyo Haneda Airport',                     ciudad: 'Tokio',        pais: 'Japón',          timezone: 'Asia/Tokyo',          latitud:  35.553333, longitud:  139.781113 },
        { _id: 'LON', nombre: 'London Heathrow Airport',                  ciudad: 'Londres',      pais: 'Reino Unido',    timezone: 'Europe/London',       latitud:  51.477500, longitud:   -0.461389 },
        { _id: 'LAX', nombre: 'Los Angeles International Airport',        ciudad: 'Los Ángeles',  pais: 'Estados Unidos', timezone: 'America/Los_Angeles', latitud:  33.942536, longitud: -118.408075 },
        { _id: 'PAR', nombre: 'Charles de Gaulle Airport',                ciudad: 'París',        pais: 'Francia',        timezone: 'Europe/Paris',        latitud:  49.009722, longitud:    2.547778 },
        { _id: 'FRA', nombre: 'Frankfurt Airport',                        ciudad: 'Fráncfort',    pais: 'Alemania',       timezone: 'Europe/Berlin',       latitud:  50.026421, longitud:    8.543125 },
        { _id: 'IST', nombre: 'Istanbul Airport',                         ciudad: 'Estambul',     pais: 'Turquía',        timezone: 'Europe/Istanbul',     latitud:  41.275278, longitud:   28.751944 },
        { _id: 'SIN', nombre: 'Singapore Changi Airport',                 ciudad: 'Singapur',     pais: 'Singapur',       timezone: 'Asia/Singapore',      latitud:   1.359167, longitud:  103.989441 },
        { _id: 'MAD', nombre: 'Adolfo Suárez Madrid-Barajas Airport',     ciudad: 'Madrid',       pais: 'España',         timezone: 'Europe/Madrid',       latitud:  40.471926, longitud:   -3.560833 },
        { _id: 'AMS', nombre: 'Amsterdam Airport Schiphol',               ciudad: 'Ámsterdam',    pais: 'Países Bajos',   timezone: 'Europe/Amsterdam',    latitud:  52.308056, longitud:    4.764167 },
        { _id: 'DFW', nombre: 'Dallas/Fort Worth International Airport',  ciudad: 'Dallas',       pais: 'Estados Unidos', timezone: 'America/Chicago',     latitud:  32.896800, longitud:  -97.038000 },
        { _id: 'CAN', nombre: 'Guangzhou Baiyun International Airport',   ciudad: 'Cantón',       pais: 'China',          timezone: 'Asia/Shanghai',       latitud:  23.392356, longitud:  113.299064 },
        { _id: 'SAO', nombre: 'São Paulo/Guarulhos International Airport',ciudad: 'São Paulo',    pais: 'Brasil',         timezone: 'America/Sao_Paulo',   latitud: -23.432075, longitud:  -46.469511 }
    ]);
    print('15 aeropuertos insertados.');
} else {
    print('Aeropuertos ya existen (' + aeropuertosExistentes + '), se omite la inserción.');
}

// ─────────────────────────────────────────
// RUTAS COMERCIALES — Grafo DIRIGIDO
// Espejo exacto de 02_airports.sql
// El índice único (origen, destino) ya está creado en 01_init.js
// ─────────────────────────────────────────
const rutasExistentes = db.rutas_comerciales.countDocuments();

if (rutasExistentes === 0) {
    db.rutas_comerciales.insertMany([

        // ── NORTEAMÉRICA ↔ EUROPA ──────────────────────────────────────
        { origen: 'ATL', destino: 'LON', distancia_km: 6750, activa: true },
        { origen: 'LON', destino: 'ATL', distancia_km: 6750, activa: true },
        { origen: 'ATL', destino: 'MAD', distancia_km: 7200, activa: true },
        { origen: 'MAD', destino: 'ATL', distancia_km: 7200, activa: true },
        { origen: 'DFW', destino: 'MAD', distancia_km: 8150, activa: true },
        { origen: 'DFW', destino: 'FRA', distancia_km: 8390, activa: true },
        { origen: 'LAX', destino: 'LON', distancia_km: 8755, activa: true },
        { origen: 'LON', destino: 'LAX', distancia_km: 8755, activa: true },

        // ── NORTEAMÉRICA INTERNA ───────────────────────────────────────
        { origen: 'ATL', destino: 'LAX', distancia_km: 3380, activa: true },
        { origen: 'LAX', destino: 'ATL', distancia_km: 3380, activa: true },
        { origen: 'ATL', destino: 'DFW', distancia_km: 1150, activa: true },
        { origen: 'DFW', destino: 'ATL', distancia_km: 1150, activa: true },
        { origen: 'DFW', destino: 'LAX', distancia_km: 1990, activa: true },
        { origen: 'LAX', destino: 'DFW', distancia_km: 1990, activa: true },

        // ── NORTEAMÉRICA → SUDAMÉRICA (solo ida) ──────────────────────
        // SAO → ATL NO existe directo: hay que hacer SAO → MAD → ATL
        { origen: 'ATL', destino: 'SAO', distancia_km:  7600, activa: true },
        { origen: 'DFW', destino: 'SAO', distancia_km:  8510, activa: true },

        // ── SUDAMÉRICA ↔ EUROPA ────────────────────────────────────────
        { origen: 'SAO', destino: 'MAD', distancia_km:  8280, activa: true },
        { origen: 'MAD', destino: 'SAO', distancia_km:  8280, activa: true },
        { origen: 'SAO', destino: 'LON', distancia_km:  9540, activa: true },
        { origen: 'LON', destino: 'SAO', distancia_km:  9540, activa: true },
        { origen: 'SAO', destino: 'PAR', distancia_km:  9350, activa: true },
        { origen: 'PAR', destino: 'SAO', distancia_km:  9350, activa: true },

        // ── EUROPA INTERNA ─────────────────────────────────────────────
        { origen: 'LON', destino: 'PAR', distancia_km:   340, activa: true },
        { origen: 'PAR', destino: 'LON', distancia_km:   340, activa: true },
        { origen: 'LON', destino: 'FRA', distancia_km:   650, activa: true },
        { origen: 'FRA', destino: 'LON', distancia_km:   650, activa: true },
        { origen: 'LON', destino: 'AMS', distancia_km:   360, activa: true },
        { origen: 'AMS', destino: 'LON', distancia_km:   360, activa: true },
        { origen: 'LON', destino: 'MAD', distancia_km:  1260, activa: true },
        { origen: 'MAD', destino: 'LON', distancia_km:  1260, activa: true },
        { origen: 'PAR', destino: 'MAD', distancia_km:  1050, activa: true },
        { origen: 'MAD', destino: 'PAR', distancia_km:  1050, activa: true },
        { origen: 'PAR', destino: 'FRA', distancia_km:   480, activa: true },
        { origen: 'FRA', destino: 'PAR', distancia_km:   480, activa: true },
        { origen: 'AMS', destino: 'FRA', distancia_km:   360, activa: true },
        { origen: 'FRA', destino: 'AMS', distancia_km:   360, activa: true },
        { origen: 'FRA', destino: 'IST', distancia_km:  2230, activa: true },
        { origen: 'IST', destino: 'FRA', distancia_km:  2230, activa: true },

        // ── EUROPA → ASIA (algunas solo ida) ───────────────────────────
        { origen: 'LON', destino: 'DXB', distancia_km:  5490, activa: true },
        { origen: 'DXB', destino: 'LON', distancia_km:  5490, activa: true },
        // FRA → PEK solo ida: la vuelta es PEK → IST → FRA
        { origen: 'FRA', destino: 'PEK', distancia_km:  7820, activa: true },
        { origen: 'IST', destino: 'DXB', distancia_km:  2680, activa: true },
        { origen: 'DXB', destino: 'IST', distancia_km:  2680, activa: true },

        // ── MEDIO ORIENTE / ASIA ───────────────────────────────────────
        { origen: 'DXB', destino: 'SIN', distancia_km:  5840, activa: true },
        { origen: 'SIN', destino: 'DXB', distancia_km:  5840, activa: true },
        // DXB → PEK solo ida
        { origen: 'DXB', destino: 'PEK', distancia_km:  5990, activa: true },

        // ── ASIA INTERNA ───────────────────────────────────────────────
        { origen: 'PEK', destino: 'TYO', distancia_km:  2100, activa: true },
        { origen: 'TYO', destino: 'PEK', distancia_km:  2100, activa: true },
        { origen: 'PEK', destino: 'SIN', distancia_km:  4470, activa: true },
        { origen: 'SIN', destino: 'PEK', distancia_km:  4470, activa: true },
        { origen: 'PEK', destino: 'CAN', distancia_km:  1900, activa: true },
        { origen: 'CAN', destino: 'PEK', distancia_km:  1900, activa: true },
        { origen: 'TYO', destino: 'SIN', distancia_km:  5310, activa: true },
        { origen: 'SIN', destino: 'TYO', distancia_km:  5310, activa: true },
        { origen: 'CAN', destino: 'SIN', distancia_km:  2480, activa: true },
        { origen: 'SIN', destino: 'CAN', distancia_km:  2480, activa: true },

        // ── TRANSPACÍFICO ──────────────────────────────────────────────
        { origen: 'LAX', destino: 'TYO', distancia_km:  8800, activa: true },
        { origen: 'TYO', destino: 'LAX', distancia_km:  8800, activa: true },
        // LAX → SIN solo ida
        { origen: 'LAX', destino: 'SIN', distancia_km: 14100, activa: true },

        // ── ASIA → EUROPA (rutas de regreso por escala) ────────────────
        // Permite: PEK → IST → FRA (ya que PEK → FRA directo no existe)
        { origen: 'PEK', destino: 'IST', distancia_km:  6800, activa: true }
    ]);
    print('Rutas comerciales del grafo dirigido insertadas.');
} else {
    print('Rutas ya existen (' + rutasExistentes + '), se omite la inserción.');
}

print('=== Aeropuertos y rutas listos ===');
