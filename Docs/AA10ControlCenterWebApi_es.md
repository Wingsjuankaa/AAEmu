# API local para AAEmu Control Center

Esta extensión mantiene a AAEmu como autoridad sobre el estado de personajes y `item_detail`. El Control Center no accede directamente a MySQL.

## Endpoints añadidos

### `GET /api/character/{characterId}/inventory`

Devuelve un snapshot tipado con:

- identidad, nivel, estado online y fecha de captura;
- slots equipados;
- backpack;
- template, grado, cantidad, temper, durabilidad;
- bytes de sockets y síntesis ya recuperados por AAEmu.

Si el personaje está conectado se utiliza el estado vivo de `WorldManager`; para un personaje offline se usa la caché persistida de `ItemManager`. El consumidor debe mostrar `CapturedAtUtc` para evitar presentar un snapshot offline como estado en vivo.

### `GET /api/world/chat-events?afterId={id}&limit={n}`

Devuelve eventos posteriores al identificador indicado. El journal:

- vive solamente en memoria;
- conserva un máximo de 2.000 mensajes;
- no escribe el chat en MySQL;
- excluye comandos y mensajes rechazados por nivel;
- limita cada respuesta a 500 eventos.

Al reiniciar Game el journal queda vacío y los IDs vuelven a comenzar.

## Administración existente

El Control Center reutiliza `/api/command/{characterName}` con comandos tipados y validados para teleport, entrega de items y kick. El renderer nunca recibe acceso a un comando GM libre.

## Exposición y seguridad

El puerto HTTP del API de Game no se publica al host en el override AA10. La aplicación lo consulta desde `docker compose exec -T game` contra `127.0.0.1:1280` dentro del contenedor.

No se debe publicar este API en red sin añadir autenticación, autorización por operación, restricción de origen, TLS y auditoría persistente.

## Pruebas

- `CharacterInventorySnapshotModelTests`: contrato de serialización del snapshot.
- `ChatEventJournalTests`: límite, orden y lectura incremental del journal.
- Suite completa Release: 1.292 pruebas correctas, 0 errores (2026-08-16).
