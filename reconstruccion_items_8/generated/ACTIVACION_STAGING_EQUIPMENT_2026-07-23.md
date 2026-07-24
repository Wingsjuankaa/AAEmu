# Activación controlada del runtime de equipamiento AA8

Fecha: 2026-07-23  
Estado: staging activo, pendiente de pruebas manuales en el cliente

## Artefactos activos

- Compact:
  `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-v1.sqlite3`
- SHA-256:
  `566236160A50A5B77CE9640EF40D492BF925A8132591717FDE61E6692F2A8C98`
- Imagen `game`:
  `sha256:170ee7e23ea19214a023f3e09a4d29bc0d90fefc829454b3fbd437c55b44d94c`
- Excepción de staging:
  `AAEMU_ITEM8_STAGING_ALLOW_CANDIDATES=1`

Dos construcciones independientes produjeron el mismo hash. `quick_check` e
`integrity_check` devolvieron `ok`. La caché nativa de fórmulas de `game11`
quedó resuelta desde la referencia confirmada `157353`; no quedan referencias
`<ref:...>` en fórmulas de equipamiento.

## Respaldo y migración

- Respaldo completo de `aaemu_game` y `aaemu_login`:
  `E:\AAEmu-Research\backups\aa8-native-equipment\aaemu8-pre-native-equipment-2026-07-23.sql`
- SHA-256:
  `49A08D28543E96B285D493AB6F188074120EB517A69C54981167DE7753FD3585`
- Exportación previa de las 59 instancias:
  `E:\AAEmu-Research\migration\aa8-native-equipment\items-before-aa8.tsv`
- SQL transaccional aplicado:
  `E:\AAEmu-Research\migration\aa8-native-equipment\quarantine-aa8.sql`
- Informe:
  `E:\AAEmu-Research\migration\aa8-native-equipment\quarantine-aa8.json`

Resultado inicial:

- 2 instancias AA8 candidatas retenidas.
- 57 instancias movidas a `quarantined_items`.
- 46 porque su ID no existe en AA8.
- 11 porque aún falta recuperar su definición concreta AA8.

Después de la primera entrada al mundo se corrigió la clausura:

- `item_body_parts` es un resultado AA8 independiente; se conservan sus 718
  filas, incluidas 405 sin fila en el resultado general `items`.
- `impl_id=0` representa el objeto genérico nativo, no una familia faltante.
- Se restauraron transaccionalmente 5 body parts y 11 instancias genéricas.
- Permanecen 41 instancias retiradas del catálogo activo AA8. Su clasificación
  está en `QUARANTINE_RECONSTRUCTION_2026-07-23.md`.

## Validación técnica

- 100/100 pruebas .NET superadas con `DOTNET_ROLL_FORWARD=Major`.
- Compilador dinámico: 0 errores.
- Inicio de `game`: 0 errores y 0 excepciones.
- Puertos activos: 2239 y 2250.
- Registro en Login correcto.
- El loot de doodads ignora casters NPC en lugar de lanzar
  `InvalidCastException`.

## Rollback

El rollback es una operación de mantenimiento y se realiza con el cliente
cerrado:

1. Detener únicamente `game`.
2. Restaurar el respaldo SQL completo indicado arriba.
3. Restaurar en `.env`:
   `COMPACT_DB=D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-native-combat-passives-v1.sqlite3`
4. Eliminar la excepción
   `AAEMU_ITEM8_STAGING_ALLOW_CANDIDATES` del servicio `game`.
5. Recrear únicamente `game` y validar Login, mundo e inventario.

No se deben copiar manualmente filas desde `quarantined_items` a `items`: la
restauración debe conservar de forma atómica inventarios y equipamiento.
