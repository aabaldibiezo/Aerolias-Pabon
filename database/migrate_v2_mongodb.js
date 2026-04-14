// =============================================
// AEROLÍNEAS RAFAEL PABON
// migrate_v2_mongodb.js — Migración MongoDB a v2
//
// Ejecutar en el contenedor mongodb3:
//   docker exec arlp_mongodb3 mongosh \
//     -u "$MONGO_ROOT_USER" -p "$MONGO_ROOT_PASSWORD" \
//     --authenticationDatabase admin \
//     aerlonia_pabon /migrate_v2_mongodb.js
//
// Cambios:
//   1. vuelos:  actualiza validador para permitir campo 'estado'
//               e inicializa a 'SCHEDULED' en documentos existentes
//   2. eventos: el campo lamport_timestamp ya es flexible (no necesita migración)
// =============================================

db = db.getSiblingDB('aerlonia_pabon');
print('=== Iniciando migración v2 MongoDB ===');

// ─────────────────────────────────────────
// 1. Actualizar validador de vuelos para incluir 'estado'
// ─────────────────────────────────────────
db.runCommand({
    collMod: 'vuelos',
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['_id', 'origen', 'destino', 'fecha', 'hora_salida',
                       'hora_llegada', 'aeronave', 'capacidad', 'activo'],
            additionalProperties: false,
            properties: {
                _id:          { bsonType: 'string', minLength: 1 },
                origen:       { bsonType: 'string', minLength: 3, maxLength: 3 },
                destino:      { bsonType: 'string', minLength: 3, maxLength: 3 },
                fecha:        { bsonType: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$' },
                hora_salida:  { bsonType: 'string', pattern: '^\\d{2}:\\d{2}$' },
                hora_llegada: { bsonType: 'string', pattern: '^\\d{2}:\\d{2}$' },
                aeronave:     { bsonType: 'string', minLength: 1 },
                capacidad:    { bsonType: 'int',    minimum: 1 },
                activo:       { bsonType: 'bool' },
                estado:       { bsonType: 'string',
                                enum: ['SCHEDULED','BOARDING','IN_FLIGHT',
                                       'ARRIVED','DELAYED','CANCELLED'] }
            }
        }
    },
    validationLevel:  'moderate',   // moderate: solo valida docs nuevos/modificados
    validationAction: 'error'
});
print('Validador de vuelos actualizado.');

// ─────────────────────────────────────────
// 2. Inicializar campo 'estado' en vuelos existentes
// ─────────────────────────────────────────
const result = db.vuelos.updateMany(
    { estado: { $exists: false } },
    { $set: { estado: 'SCHEDULED' } }
);
print(`Campo 'estado' inicializado en ${result.modifiedCount} vuelos.`);

print('=== Migración v2 MongoDB completada ===');
