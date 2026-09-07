# Integración de la comunidad AA10 — 2026-09-07

## Alcance y procedencia

Merge normal de `upstream/client_version/zone-10.0.2_r575`, hasta
`7babcb3a706c64295b5aaaeec8abe57e4d09b4da`, sobre `rama_10` en
`6c3f7e5ecf9ebc02797fc30326929da884c44902`.
Base común: `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
Se incorporan 88 commits comunitarios y se conserva la historia de 74 commits propios.
Se revisaron 74 rutas en conflicto; no se aplicó una preferencia global por un lado.

Antes del merge se respaldaron los cambios pendientes de Ipnya y localización, el diff binario,
los archivos originales y sus SHA-256. Rama de respaldo:
`backup/rama_10-pre-upstream-20260907-6c3f7e5`.
Evidencia operativa privada y rollback:
`E:\AAEmu\rama_10\backups\upstream-sync-20260907-6c3f7e5`.
Los respaldos contienen bases y configuraciones locales y no se publican en Git.

## Decisiones de integración

| Área | Resultado y motivo |
|---|---|
| Correo/subasta | Flujos comunitarios con importes largos, historial de ventas, persistencia coordinada y validación de correo; se conserva la protección de nuestros objetos bloqueados y los objetivos de quests. |
| Guardado | `PersistenceGate` comunitario combinado con `GamePersistence.Sync`, necesario para la transacción local de Ipnya. |
| Gremios/héroes/castillos | Se incorporan elección, guerras, residencia, buffs, intereses y persistencia comunitaria. La reserva de una residencia por gremio se revalida dentro del lock de colocación. |
| Viviendas | Se conservan huella exacta, binding nativo y reconstrucción propios; se añaden territorio, lodestones y residencia comunitarios. Se elimina el modelo huérfano `HousingBindingDoodad`. |
| Buffs/barcos | Se adopta el stack consolidado comunitario. La combinación con Hiram conserva `AbLevel` y `Passive`, no consume stacks si falta el destino y respeta buffs de Zone. Las retiradas se retransmiten sólo si el buff fue publicado a Zone. |
| Streaming/Zone | Se integran AOI, costuras, reseteo por instancia y barcos; se conservan la preparación del personaje y los relays nativos de equipo. |
| Doodads | Persistencia comunitaria de fases del mundo combinada con inicialización local única. No se ejecuta dos veces la fase inicial. |
| Instancias | Se incorporan matchmaking, admisión, visitas y contratos comunitarios de respuesta. Se conserva la ruta de invitación directa propia y se evita emitir la transición antes de aceptar la instancia. |
| Skills | Se conservan los objetos tipados r575 y el parser de unión nativa; no se incorpora la suposición de que todos los flags son una máscara con trece enteros. Se añade AbilitySet y los flujos comunitarios de skillsaver. |
| Equipo | Se conservan descriptor persistente, síntesis, reroll, awakening, temper y lunagem propios. Se integran regrade y catálogos comunitarios, con adaptadores a los slots nativos; no se ejecuta una segunda implementación de síntesis incompatible. |
| Item tasks | Se adopta la numeración comunitaria tras verificarla directamente en el cliente. Socketing cambia de nombre simbólico a `SkillReagents` para seguir transmitiendo 42. Se conservan `Refurbishment=127` y Bless Uthstin 153–158. |
| Configuración | Se integra la matriz ampliada de features y StreamAoi, conservando Item Lock, Ipnya, Bless Uthstin y las extensiones propias. `itemSmelting=false`, `butler=false` y `archePassMissionAccount=false`. Butler sólo tiene parsers/paquetes y no implementa los trabajos ni el estado. |
| SQL | Se incorporan 28 migraciones. Se corrige `expedition_interest`: usa la columna preexistente `notice`, porque la migración de residencia se ordena después. |

## Comprobación independiente de ItemTaskType

La función de la tabla de nombres del cliente release r575 está en RVA `0xB5A010`; cada slot
ocupa `0x28` bytes. Se extrajeron los índices desde las instrucciones que construyen cada slot,
sin modificar el cliente. El JSON de evidencia contiene SHA-256 del binario, índice, nombre y RVA
de cada llamada, en el respaldo privado `native-item-tasks.json`.

Ejemplos confirmados: QuestStart 37, SkillReagents 42, SkillEffectGainItem 44, Auction 48,
Mail 49, Trade 50, EnchantPhysical 52, ItemLock/Unlock/UnlockExcess 92/93/94,
GradeEnchant 95, Socketing 99, Evolving 100, ScaleCap 127 y BlessUthstinInitStats 153.
La denominación heredada `SkillEffectGainItem=42` de la documentación de lunagem era incorrecta;
su byte 42 sí era correcto. Las fixtures nuevas verifican 16 valores en el paquete real.

## Validación previa al despliegue

- `dotnet restore`: correcto.
- `dotnet build --configuration Release --no-restore`: 0 errores; 260 advertencias.
- `dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore`:
  **2.671/2.671**, sin omitidas, antes de restaurar el trabajo pendiente.
- Las 28 migraciones nuevas se ejecutaron en MySQL 8.0.36 aislado, sobre un dump local.
  La base original registra sólo dos migraciones antiguas; no se usa esa ausencia de registro
  para volver a ejecutar todas las migraciones históricas.
- El CLI de MySQL requiere delimitadores para la migración con procedimiento `war_is_declarer`;
  se añaden sólo en el ejecutor operativo. El SQL del repositorio conserva el formato que envía
  completo `MySqlDatabaseUpdater` mediante su conector.
- Los spawns montados se compararon por template y posición: ninguna de las 285 posiciones
  eliminadas por upstream existe en el catálogo local. Se conserva el archivo montado completo.

Las pruebas automatizadas y el arranque no constituyen aceptación visual de todas las funciones
comunitarias. Regresión retail prioritaria: correo/subasta, bloqueo y desbloqueo, intentos consecutivos
de lunagem/temper, Hiram, barcos, costuras entre Zones y acceso a instancias.
El lifecycle de las Zones sigue siendo operación exclusiva del usuario en Control Center.

## Despliegue final comprobado

Con el trabajo pendiente restaurado, la suite final pasa **2.682/2.682**, con 0 omitidas.
Game/World, Login y MySQL están healthy y sin reinicios automáticos. Game terminó el arranque
(`Server started`, 00:01:41.229), abrió 1239/1250, World escucha 1240 y Login registró
GameServerId 1. El API interno de estado responde; no hay Zones conectadas.
Los tres archivos de configuración coinciden por SHA-256 en fuente, montaje y contenedor.
El fset efectivo es:

`57 37 00 00 f4 2f 61 02 32 4e 00 fe bf cf 2d 00 00 ff bf f5 7f 9e b3 00 6c bf 00 90 79 f2 02`

Sólo aparecen los errores preexistentes de recetas Smelting 29–32; Butler y Smelting están OFF.
La configuración y los hashes de imágenes/migraciones se registran en
`reconstruccion_cliente_10/checkpoints/UPSTREAM_SYNC_20260907.manifest.json`.
La imagen local incluye los cambios pendientes restaurados, que siguen sin incorporarse a Git.

## Cierre del día: aceptación comunicada por el usuario

Después del despliegue, el usuario confirmó que completó la prueba de entrada al mundo,
movimiento, inventario/equipo y regreso desde selección de personaje sin incidencias.
También confirmó que Lunagem funciona y que pudo publicar un objeto en subasta.
Es aceptación reportada por el usuario; no se infiere de ella una venta completada,
retirada de adjuntos de correo, extracción de gemas, temper, Hiram ni todas las instancias.

Por petición explícita del usuario se incorporan ahora a Git todos los cambios pendientes:
lote Ipnya de un solo casteo, builder/aplicador Lua y sus contratos/fixtures, parches de
Dwarf/Warborn y pelo, reutilización del aplicador español y documentación de esas entregas.
El código de servidor coincide con la versión ya desplegada y validada con 2.682 unit tests.
La comprobación final de scripts da 24 pruebas aprobadas y 3 omitidas por requerir evidencia
retail extraída/configurada; no se aplicaron parches al cliente durante este cierre.
No se cambió el comportamiento del runtime para realizar el commit.
