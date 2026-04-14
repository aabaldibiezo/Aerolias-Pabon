// =============================================
// AEROLÍNEAS RAFAEL PABON
// 03_flights.js — Pasajeros, vuelos y asientos
// Motor: MongoDB 7
// Espejo exacto de 03_flights.sql
// Idempotente: seguro de ejecutar múltiples veces
//
// Distribución de asientos por vuelo (174 total):
//   Primera clase : filas  1-3,  columnas A-D  →  12 asientos
//   Business      : filas  4-9,  columnas A-F  →  36 asientos
//   Económica     : filas 10-30, columnas A-F  → 126 asientos
// =============================================

db = db.getSiblingDB('aerlonia_pabon');

// ─────────────────────────────────────────
// FUNCIÓN AUXILIAR: generar array de asientos
// Equivalente al sp_generar_asientos de SQL Server
// ─────────────────────────────────────────
function generarAsientos(vuelo_id, precioP, precioB, precioE) {
    const asientos = [];
    const ahora = new Date();
    // Primera clase solo columnas A-D; business y economica A-F
    const colsEstandar  = ['A', 'B', 'C', 'D', 'E', 'F'];
    const colsPrimera   = ['A', 'B', 'C', 'D'];

    for (let fila = 1; fila <= 30; fila++) {
        const cols  = fila <= 3 ? colsPrimera : colsEstandar;
        const clase = fila <= 3 ? 'primera'
                    : fila <= 9 ? 'business'
                    :             'economica';
        const precio = fila <= 3 ? precioP
                     : fila <= 9 ? precioB
                     :             precioE;

        for (const col of cols) {
            // No incluir pasaporte_pasajero cuando es null — el validador lo omite
        asientos.push({
                vuelo_id:       vuelo_id,
                numero_asiento: String(fila) + col,
                clase:          clase,
                estado:         'Libre',
                precio:         precio,
                updated_at:     ahora
            });
        }
    }
    return asientos; // 174 documentos
}

// ─────────────────────────────────────────
// PASAJEROS DE PRUEBA
// _id = número de pasaporte (clave natural)
// ─────────────────────────────────────────
if (db.pasajeros.countDocuments() === 0) {
    const ahora = new Date();
    db.pasajeros.insertMany([
        { _id: 'US1234567', nombre: 'James Wilson',         email: 'jwilson@email.com',    created_at: ahora },
        { _id: 'US9876543', nombre: 'Emily Johnson',        email: 'ejohnson@email.com',   created_at: ahora },
        { _id: 'GB2345678', nombre: 'Oliver Smith',         email: 'osmith@email.com',     created_at: ahora },
        { _id: 'DE3456789', nombre: 'Hans Müller',          email: 'hmuller@email.com',    created_at: ahora },
        { _id: 'FR4567890', nombre: 'Marie Dupont',         email: 'mdupont@email.com',    created_at: ahora },
        { _id: 'JP5678901', nombre: 'Kenji Tanaka',         email: 'ktanaka@email.com',    created_at: ahora },
        { _id: 'CN6789012', nombre: 'Wei Zhang',            email: 'wzhang@email.com',     created_at: ahora },
        { _id: 'BR7890123', nombre: 'Ana Paula Souza',      email: 'apsouza@email.com',    created_at: ahora },
        { _id: 'ES8901234', nombre: 'Carlos García',        email: 'cgarcia@email.com',    created_at: ahora },
        { _id: 'SG9012345', nombre: 'Li Wei',               email: 'liwei@email.com',      created_at: ahora },
        { _id: 'TR0123456', nombre: 'Ayşe Kaya',            email: 'akaya@email.com',      created_at: ahora },
        { _id: 'AE1357924', nombre: 'Mohammed Al-Rashid',   email: 'malrashid@email.com',  created_at: ahora },
        { _id: 'AR2468013', nombre: 'Diego Fernández',      email: 'dfernandez@email.com', created_at: ahora },
        { _id: 'AU3579124', nombre: 'Sarah Mitchell',       email: 'smitchell@email.com',  created_at: ahora },
        { _id: 'CA4680235', nombre: 'Pierre Tremblay',      email: 'ptremblay@email.com',  created_at: ahora }
    ]);
    print('15 pasajeros de prueba insertados.');
} else {
    print('Pasajeros ya existen, se omite la inserción.');
}

// ─────────────────────────────────────────
// FUNCIÓN AUXILIAR: insertar vuelo + asientos
// Verifica idempotencia antes de insertar
// ─────────────────────────────────────────
function insertarVuelo(doc, precioP, precioB, precioE) {
    if (db.vuelos.countDocuments({ _id: doc._id }) > 0) {
        print('Vuelo ' + doc._id + ' ya existe, se omite.');
        return;
    }
    db.vuelos.insertOne(doc);
    const asientos = generarAsientos(doc._id, precioP, precioB, precioE);
    db.asientos.insertMany(asientos);
    print('Vuelo ' + doc._id + ' insertado con ' + asientos.length + ' asientos.');
}

// ─────────────────────────────────────────
// VUELOS (15 vuelos, espejo de 03_flights.sql)
// ─────────────────────────────────────────

// ── TRANSATLÁNTICOS ────────────────────────────────────────────────────
insertarVuelo({
    _id: 'RP001', origen: 'ATL', destino: 'LON',
    fecha: '2026-04-01', hora_salida: '09:00', hora_llegada: '21:30',
    aeronave: 'Boeing 777-300ER', capacidad: 174, activo: true
}, 2500.00, 1200.00, 420.00);

insertarVuelo({
    _id: 'RP002', origen: 'LON', destino: 'ATL',
    fecha: '2026-04-02', hora_salida: '11:00', hora_llegada: '14:30',
    aeronave: 'Boeing 777-300ER', capacidad: 174, activo: true
}, 2500.00, 1200.00, 420.00);

insertarVuelo({
    _id: 'RP003', origen: 'SAO', destino: 'MAD',
    fecha: '2026-04-05', hora_salida: '01:30', hora_llegada: '14:00',
    aeronave: 'Airbus A350-900', capacidad: 174, activo: true
}, 1800.00, 900.00, 380.00);

insertarVuelo({
    _id: 'RP004', origen: 'MAD', destino: 'SAO',
    fecha: '2026-04-06', hora_salida: '10:00', hora_llegada: '18:30',
    aeronave: 'Airbus A350-900', capacidad: 174, activo: true
}, 1800.00, 900.00, 380.00);

// ── EUROPA INTERNA ─────────────────────────────────────────────────────
insertarVuelo({
    _id: 'RP005', origen: 'LON', destino: 'PAR',
    fecha: '2026-04-03', hora_salida: '07:00', hora_llegada: '09:15',
    aeronave: 'Airbus A320', capacidad: 174, activo: true
}, 600.00, 300.00, 120.00);

insertarVuelo({
    _id: 'RP006', origen: 'FRA', destino: 'IST',
    fecha: '2026-04-04', hora_salida: '08:30', hora_llegada: '12:45',
    aeronave: 'Airbus A321', capacidad: 174, activo: true
}, 700.00, 350.00, 140.00);

insertarVuelo({
    _id: 'RP007', origen: 'MAD', destino: 'PAR',
    fecha: '2026-04-07', hora_salida: '09:00', hora_llegada: '11:10',
    aeronave: 'Airbus A320', capacidad: 174, activo: true
}, 600.00, 300.00, 110.00);

// ── EUROPA → ASIA ──────────────────────────────────────────────────────
insertarVuelo({
    _id: 'RP008', origen: 'LON', destino: 'DXB',
    fecha: '2026-04-08', hora_salida: '09:00', hora_llegada: '19:00',
    aeronave: 'Boeing 787-9', capacidad: 174, activo: true
}, 1500.00, 750.00, 310.00);

insertarVuelo({
    // Ruta solo ida: FRA → PEK (PEK → FRA no existe directo en el grafo)
    _id: 'RP009', origen: 'FRA', destino: 'PEK',
    fecha: '2026-04-09', hora_salida: '11:00', hora_llegada: '05:00',
    aeronave: 'Boeing 747-8', capacidad: 174, activo: true
}, 2200.00, 1100.00, 460.00);

insertarVuelo({
    _id: 'RP010', origen: 'DXB', destino: 'SIN',
    fecha: '2026-04-10', hora_salida: '02:00', hora_llegada: '14:00',
    aeronave: 'Airbus A380', capacidad: 174, activo: true
}, 1400.00, 700.00, 290.00);

// ── ASIA INTERNA ───────────────────────────────────────────────────────
insertarVuelo({
    _id: 'RP011', origen: 'PEK', destino: 'TYO',
    fecha: '2026-04-11', hora_salida: '10:00', hora_llegada: '14:30',
    aeronave: 'Boeing 737 MAX', capacidad: 174, activo: true
}, 1000.00, 500.00, 200.00);

insertarVuelo({
    _id: 'RP012', origen: 'SIN', destino: 'TYO',
    fecha: '2026-04-12', hora_salida: '00:30', hora_llegada: '08:00',
    aeronave: 'Airbus A350-900', capacidad: 174, activo: true
}, 1100.00, 550.00, 220.00);

// ── TRANSPACÍFICO ──────────────────────────────────────────────────────
insertarVuelo({
    _id: 'RP013', origen: 'LAX', destino: 'TYO',
    fecha: '2026-04-13', hora_salida: '12:00', hora_llegada: '16:30',
    aeronave: 'Boeing 777-200LR', capacidad: 174, activo: true
}, 3000.00, 1500.00, 600.00);

// ── NORTEAMÉRICA INTERNA ───────────────────────────────────────────────
insertarVuelo({
    _id: 'RP014', origen: 'ATL', destino: 'LAX',
    fecha: '2026-04-14', hora_salida: '06:00', hora_llegada: '08:15',
    aeronave: 'Boeing 737-800', capacidad: 174, activo: true
}, 800.00, 400.00, 160.00);

insertarVuelo({
    _id: 'RP015', origen: 'DFW', destino: 'ATL',
    fecha: '2026-04-15', hora_salida: '07:30', hora_llegada: '10:00',
    aeronave: 'Airbus A319', capacidad: 174, activo: true
}, 700.00, 350.00, 140.00);

// ─────────────────────────────────────────
// ESTADOS DE PRUEBA en vuelo RP001
// Para ver colores distintos en el mapa de asientos desde el arranque
// ─────────────────────────────────────────
const ahora = new Date();

// Ventas en primera clase
db.asientos.updateMany(
    { vuelo_id: 'RP001', numero_asiento: { $in: ['1A', '1B'] } },
    { $set: { estado: 'Venta', pasaporte_pasajero: 'US1234567', updated_at: ahora } }
);

// Reservas en business
db.asientos.updateMany(
    { vuelo_id: 'RP001', numero_asiento: { $in: ['4A', '4B', '5C'] } },
    { $set: { estado: 'Reserva', pasaporte_pasajero: 'GB2345678', updated_at: ahora } }
);

// Una devolución en economía
db.asientos.updateOne(
    { vuelo_id: 'RP001', numero_asiento: '15F' },
    { $set: { estado: 'Devolucion', pasaporte_pasajero: 'FR4567890', updated_at: ahora } }
);

print('Estados de prueba aplicados al vuelo RP001.');
print('=== Vuelos y asientos listos — 15 vuelos, 2610 asientos totales ===');
