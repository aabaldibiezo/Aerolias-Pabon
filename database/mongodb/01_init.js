// =============================================
// AEROLÍNEAS RAFAEL PABON
// 01_init.js — Colecciones, validadores e índices
// Motor: MongoDB 7
// Espejo de la estructura SQL Server (colecciones separadas)
// Idempotente: seguro de ejecutar múltiples veces
// =============================================

// Cambiar al contexto de la base de datos del sistema
db = db.getSiblingDB('aerlonia_pabon');

const colecciones = db.getCollectionNames();
print('=== Inicializando colecciones de aerlonia_pabon ===');

// ─────────────────────────────────────────
// COLECCIÓN: aeropuertos
// _id = código IATA (equivalente a PK codigo CHAR(3))
// ─────────────────────────────────────────
if (!colecciones.includes('aeropuertos')) {
    db.createCollection('aeropuertos', {
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['_id', 'nombre', 'ciudad', 'pais', 'timezone', 'latitud', 'longitud'],
                additionalProperties: false,
                properties: {
                    _id:       { bsonType: 'string',  minLength: 3, maxLength: 3,
                                 description: 'Código IATA de 3 caracteres' },
                    nombre:    { bsonType: 'string',  minLength: 1 },
                    ciudad:    { bsonType: 'string',  minLength: 1 },
                    pais:      { bsonType: 'string',  minLength: 1 },
                    timezone:  { bsonType: 'string',  minLength: 1,
                                 description: 'Nombre IANA del timezone (ej: America/New_York)' },
                    latitud:   { bsonType: 'double'  },
                    longitud:  { bsonType: 'double'  }
                }
            }
        },
        validationLevel:  'strict',
        validationAction: 'error'
    });
    print('Colección aeropuertos creada.');
} else {
    print('Colección aeropuertos ya existe.');
}

// ─────────────────────────────────────────
// COLECCIÓN: rutas_comerciales
// Grafo DIRIGIDO — par (origen, destino) es único
// distancia_km es el peso para Dijkstra
// ─────────────────────────────────────────
if (!colecciones.includes('rutas_comerciales')) {
    db.createCollection('rutas_comerciales', {
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['origen', 'destino', 'distancia_km', 'activa'],
                properties: {
                    origen:        { bsonType: 'string', minLength: 3, maxLength: 3 },
                    destino:       { bsonType: 'string', minLength: 3, maxLength: 3 },
                    distancia_km:  { bsonType: 'int',    minimum: 1 },
                    activa:        { bsonType: 'bool' }
                }
            }
        },
        validationLevel:  'strict',
        validationAction: 'error'
    });
    // Índice único sobre el par dirigido (espejo del UNIQUE SQL Server)
    db.rutas_comerciales.createIndex(
        { origen: 1, destino: 1 },
        { unique: true, name: 'uq_ruta_par' }
    );
    print('Colección rutas_comerciales creada.');
} else {
    print('Colección rutas_comerciales ya existe.');
}

// ─────────────────────────────────────────
// COLECCIÓN: vuelos
// _id = vuelo_id (equivalente a PK NVARCHAR(10))
// ─────────────────────────────────────────
if (!colecciones.includes('vuelos')) {
    db.createCollection('vuelos', {
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['_id', 'origen', 'destino', 'fecha', 'hora_salida',
                           'hora_llegada', 'aeronave', 'capacidad', 'activo'],
                additionalProperties: false,
                properties: {
                    _id:          { bsonType: 'string', minLength: 1,
                                    description: 'ID del vuelo, ej: RP001' },
                    origen:       { bsonType: 'string', minLength: 3, maxLength: 3 },
                    destino:      { bsonType: 'string', minLength: 3, maxLength: 3 },
                    // Fecha como string ISO YYYY-MM-DD para compatibilidad con SQL Server
                    fecha:        { bsonType: 'string',
                                    pattern: '^\\d{4}-\\d{2}-\\d{2}$' },
                    // Horas locales como string HH:MM (hora local del aeropuerto)
                    hora_salida:  { bsonType: 'string',
                                    pattern: '^\\d{2}:\\d{2}$' },
                    hora_llegada: { bsonType: 'string',
                                    pattern: '^\\d{2}:\\d{2}$' },
                    aeronave:     { bsonType: 'string', minLength: 1 },
                    capacidad:    { bsonType: 'int',    minimum: 1 },
                    activo:       { bsonType: 'bool' },
                    // Estado operativo del vuelo (actualizado por background task)
                    estado:       { bsonType: 'string',
                                    enum: ['SCHEDULED','BOARDING','IN_FLIGHT',
                                           'ARRIVED','DELAYED','CANCELLED'] }
                }
            }
        },
        validationLevel:  'strict',
        validationAction: 'error'
    });
    // Índice para búsqueda incremental por ruta y fecha (espejo del IX SQL Server)
    db.vuelos.createIndex(
        { origen: 1, destino: 1, fecha: 1 },
        { name: 'ix_vuelos_ruta_fecha' }
    );
    print('Colección vuelos creada.');
} else {
    print('Colección vuelos ya existe.');
}

// ─────────────────────────────────────────
// COLECCIÓN: pasajeros
// _id = pasaporte (equivalente a PK NVARCHAR(20))
// ─────────────────────────────────────────
if (!colecciones.includes('pasajeros')) {
    db.createCollection('pasajeros', {
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['_id', 'nombre', 'created_at'],
                additionalProperties: false,
                properties: {
                    _id:        { bsonType: 'string', minLength: 1,
                                  description: 'Número de pasaporte' },
                    nombre:     { bsonType: 'string', minLength: 1 },
                    email:      { bsonType: ['string', 'null'] },
                    created_at: { bsonType: 'date' }
                }
            }
        },
        validationLevel:  'strict',
        validationAction: 'error'
    });
    // Índice para autocompletar por nombre
    db.pasajeros.createIndex(
        { nombre: 1 },
        { name: 'ix_pasajeros_nombre' }
    );
    print('Colección pasajeros creada.');
} else {
    print('Colección pasajeros ya existe.');
}

// ─────────────────────────────────────────
// COLECCIÓN: asientos
// _id = ObjectId automático
// Par (vuelo_id, numero_asiento) es único
// ─────────────────────────────────────────
if (!colecciones.includes('asientos')) {
    db.createCollection('asientos', {
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['vuelo_id', 'numero_asiento', 'clase',
                           'estado', 'precio', 'updated_at'],
                properties: {
                    vuelo_id:           { bsonType: 'string' },
                    numero_asiento:     { bsonType: 'string',
                                         description: 'Ej: 12A, 1D' },
                    clase:              { bsonType: 'string',
                                         enum: ['primera', 'business', 'economica'] },
                    estado:             { bsonType: 'string',
                                         enum: ['Libre', 'Reserva', 'Venta', 'Devolucion'] },
                    // null cuando el asiento está libre — se omite el campo en ese caso
                    pasaporte_pasajero: { bsonType: 'string' },
                    // ['int','double']: mongosh 2.x guarda números enteros como Int32
                    precio:             { bsonType: ['int', 'double'], minimum: 0 },
                    updated_at:         { bsonType: 'date' }
                }
            }
        },
        validationLevel:  'strict',
        validationAction: 'error'
    });
    // Índice único equivalente al UNIQUE SQL Server (vuelo_id, numero_asiento)
    db.asientos.createIndex(
        { vuelo_id: 1, numero_asiento: 1 },
        { unique: true, name: 'uq_asiento_vuelo' }
    );
    // Índice para cargar el mapa de asientos de un vuelo filtrado por estado
    db.asientos.createIndex(
        { vuelo_id: 1, estado: 1 },
        { name: 'ix_asientos_vuelo_estado' }
    );
    print('Colección asientos creada.');
} else {
    print('Colección asientos ya existe.');
}

// ─────────────────────────────────────────
// COLECCIÓN: eventos
// Log del reloj vectorial para sincronización distribuida
// _id = ObjectId automático
// ─────────────────────────────────────────
if (!colecciones.includes('eventos')) {
    db.createCollection('eventos', {
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['tipo', 'vuelo_id', 'numero_asiento',
                           'estado_anterior', 'estado_nuevo',
                           'nodo_origen', 'reloj_vectorial', 'timestamp_utc', 'aplicado'],
                properties: {
                    tipo:               { bsonType: 'string',
                                         enum: ['reserva', 'venta', 'devolucion', 'liberacion'] },
                    vuelo_id:           { bsonType: 'string' },
                    // Se guarda el número de asiento en lugar del ObjectId
                    // para compatibilidad con la clave natural de SQL Server
                    numero_asiento:     { bsonType: 'string' },
                    estado_anterior:    { bsonType: 'string',
                                         enum: ['Libre', 'Reserva', 'Venta', 'Devolucion'] },
                    estado_nuevo:       { bsonType: 'string',
                                         enum: ['Libre', 'Reserva', 'Venta', 'Devolucion'] },
                    pasaporte_pasajero: { bsonType: ['string', 'null'] },
                    nodo_origen:        { bsonType: 'int', enum: [1, 2, 3] },
                    // Reloj vectorial serializado: Ej. "[3,1,2]"
                    reloj_vectorial:    { bsonType: 'string' },
                    timestamp_utc:      { bsonType: 'date' },
                    // true = este nodo ya procesó/aplicó el evento
                    aplicado:           { bsonType: 'bool' }
                }
            }
        },
        validationLevel:  'strict',
        validationAction: 'error'
    });
    // Índice para sincronización: buscar eventos por nodo y tiempo
    db.eventos.createIndex(
        { nodo_origen: 1, timestamp_utc: 1 },
        { name: 'ix_eventos_nodo_tiempo' }
    );
    // Índice para detectar conflictos en un asiento específico
    db.eventos.createIndex(
        { vuelo_id: 1, numero_asiento: 1, timestamp_utc: 1 },
        { name: 'ix_eventos_asiento' }
    );
    print('Colección eventos creada.');
} else {
    print('Colección eventos ya existe.');
}

print('=== Colecciones e índices listos ===');
