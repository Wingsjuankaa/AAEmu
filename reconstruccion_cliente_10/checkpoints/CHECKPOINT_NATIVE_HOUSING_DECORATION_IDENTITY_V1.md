# Checkpoint nativo: dominio de propietario de vivienda AA10 r575

## Estado

Corrección reconstruida, migrada y desplegada. Aceptación funcional retail
pendiente de la prueba posterior al despliegue.

El síntoma era un `You don't have permission` local al iniciar placement dentro
de una vivienda propia. El cliente no emitía `CSDecorateHouse`; por tanto el
servidor nunca llegaba a ejecutar su política de permisos.

## Diagnóstico live y candidatos falsados

La lectura pasiva del proceso retail `archeage` con `x2game-dev.dll` mostró:

- identidad local de Dannia: `7`;
- catálogo owned del HousingManager: casas TL `16..19`, owner `7`;
- unidades de las siete casas visibles presentes en el registro cliente;
- casa TL 16: ObjId `271`, owner/co-owner `7`;
- ningún `CSDecorateHouse` tras el intento exacto.

Esto falsó dos candidatos previos: el segundo qword Character de `UnitState` y
el `buildstep` de una vivienda terminada. Ambos cambios fueron retirados del
diff final; no se conservan como supuestas correcciones.

## Autoridad nativa AA10

En `x2game-dev.dll` r575 SHA-256
`81DFABE826125D5AD4914439815AF62FDEE550DCC98B6F29C65D4228FA9F2B80`:

- `FUN_39726390`, `HousingManager::DecorateHouse`, obtiene el owner efectivo
  mediante `FUN_3971c0c0` y lo compara con la identidad local;
- `FUN_3971c0c0` devuelve literalmente el owner sólo cuando es `>= 1000`;
- un owner menor que `1000` entra al dominio especial/fallback y, salvo el
  sentinel nativo concreto, se resuelve al fallback global (cero en este flujo);
- por ello la casa contenía raw owner `7`, pero el predicado real era
  `effectiveOwner(7) == 0`, que fallaba contra la identidad local `7` y emitía
  error 2 antes de crear `CSDecorateHouse`.

La corrección previa de AA8 permitió localizar el mismo tipo de contrato, pero
el umbral, la función y el flujo se verificaron de nuevo contra AA10. No se
copiaron opcodes ni layouts de otra versión.

Evidencia Ghidra principal:

- `forensics/output/aa10-client-forensics/housing-decoration-dev-frontier/house-owner-contract.log`;
- `house-decorator-entry.log`;
- `decorator-methods.log`;
- `permission-entry.log`.

## Implementación

- `CharacterIdManager.FirstId` cambia de `1` a `1000` (`0x3E8`).
- El asignador conserva la auditoría conjunta de `characters.id` y `slaves.id`
  para evitar colisiones en el dominio persistente compartido.
- La migración transaccional e idempotente
  `SQL/updates/2026-08-30_aaemu_game_character_owner_domain.sql` mueve cada
  character ID histórico `1..999` a `old_id + 1000`.
- Todas las referencias persistentes AA10 se actualizan en la misma transacción,
  incluyendo housing, items/contenedores, quests, ArchePass, Uthstin, mail,
  friends, mates, slaves, auction, expeditions, resident points y ledger.
- `housings.co_owner` sólo se migra en permiso Private; `doodads.owner_id` sólo
  en owner type Character; `slaves.owner_id` sólo en owner type Character.

## Validación de migración

La base activa se clonó íntegramente a un schema temporal. La migración se
ejecutó dos veces sobre la copia:

- primera ejecución: personajes `1,7,8,9` a `1001,1007,1008,1009`;
- segunda ejecución: sin cambios ni errores;
- 19 viviendas preservadas, cero owners menores de 1000 y cero owners huérfanos;
- cero referencias residuales a los cuatro IDs antiguos en las superficies
  auditadas;
- el schema temporal y los archivos temporales se eliminaron después del gate.

Pruebas:

- `CharacterOwnerDomainTests`: 3/3;
- `IdManagerTests`: 103/103;
- suite completa: 1679/1680; único fallo preexistente `MoneyTest`
  (`UnableToFindRecipient`), idéntico al baseline y ajeno a housing;
- build Docker AAEmu.World/AAEmu.Game: 0 errores;
- `git diff --check`: correcto.

## Migración activa y rollback

Antes de migrar se detuvo únicamente `game` y se creó:

- backup: `E:/AAEmu/rama_10/backups/aa10-pre-character-owner-domain-20260830-153726.sql`;
- SHA-256: `B514D94D66E6526ED7E3AF8C5BBD778D63A56342F7A5FCE9BDE111DE3C654D43`.

Resultado activo:

- Wingsjuanka `1001`;
- Dannia `1007`, cuatro viviendas;
- Codexwave `1008`;
- Mateprobe `1009`;
- 19 viviendas, cero owners huérfanos.

Despliegue:

- imagen activa `aaemu-world:10.0.2.13-r575-local`:
  `sha256:b6225ddff566512ca01302ea14587f440836384d32e9ffde6f7d2aaf47923f7e`;
- rollback de imagen:
  `aaemu-world:rollback-pre-housing-owner-domain-20260830-153642`;
- `game` healthy, RestartCount `0`;
- puertos `1239`, `1240`, `1250` abiertos y registro Login correcto;
- `login` y `db` no se recrearon;
- Codex no operó el ciclo de vida de Zone.

Rollback completo: detener sólo `game`, restaurar el dump pre-migración,
retaggear la imagen rollback como tag activo y recrear sólo `game`.

No se creó commit ni se publicó push durante este despliegue.

## Follow-up: interacción RecoverItem de decoraciones

La aceptación posterior confirmó que Dannia pudo colocar el vaso decorativo,
pero el cliente no expuso ninguna acción para recuperarlo. La fila activa
identificó de forma exacta el caso: doodad `5`, template `5450`, fase `14059`,
item `98`, house `16`, owner `1007`. La full r575 define en esa fase un único
`DoodadFuncRecoverItem` (`doodad_funcs.id=11612`, next phase `-1`). Los logs no
mostraron ningún request de interacción posterior al spawn: el bloqueo era
local al cliente.

El comparador AA8 aportó la primitiva `generic_x64_compatible`: el consumer
filtra `RecoverItem` cuando `pisc[2]` conserva el sentinel cero. AA10 ya
demostraba independientemente que ese campo termina en el item del doodad y
que el tail de frescura es otro gate, limitado a `ItemBackpack.type` 3/8. El
servidor confundía ambas condiciones y sólo serializaba el item cuando era una
mochila. La corrección ahora publica `ItemTemplateId` para cualquier doodad que
lo tenga, mientras mantiene el tail de frescura exclusivamente para los tipos
3/8. La misma resolución se comparte entre `SCDoodadCreated` y
`WZCreateDoodad`.

Regresión focal: item ordinario `98` debe producir `pisc[2]=98` sin payload de
frescura; el sentinel `0` permanece cero; trade packs y mochilas no frescas
conservan sus contratos previos.

Validación y despliegue del follow-up:

- `dotnet restore AAEmu.slnx`: correcto;
- build Release: correcto, cero errores;
- suite: 1.680/1.681; único fallo preexistente `MoneyTest`
  (`UnableToFindRecipient`), igual al baseline anterior;
- `git diff --check`: correcto;
- imagen combinada activa `aaemu-world:10.0.2.13-r575-local`:
  `sha256:bce6fca8947977e633240cf48365fc836f265be85e55e597d51fdd44ff1f952e`;
- rollback: `aaemu-world:rollback-pre-decoration-recover-20260830-155518`,
  imagen
  `sha256:b6225ddff566512ca01302ea14587f440836384d32e9ffde6f7d2aaf47923f7e`;
- `game` healthy, reinicios `0`, 19 viviendas cargadas, registro Login
  correcto y puertos 1239/1240/1250 abiertos;
- el reinicio desconectó la Zone. Codex no operó su lifecycle; la aceptación
  retail queda pendiente de relanzar el perfil 142 desde Control Center y
  recuperar el vaso ya persistido.

## Aceptación retail de RecoverItem

Aceptada por el operador el 2026-08-30. Tras relanzar la Zone 142, el cliente
expuso la interacción del vaso y Dannia la ejecutó correctamente. La traza del
servidor registró `InteractionEffect, RecoverItem`, skill genérica `11361` y
`DoodadFuncRecoverItem(467)` sobre template `5450`.

El estado persistente posterior confirma cierre atómico:

- la fila `doodads.id=5` desapareció;
- el objeto original `items.id=16777465`, template `98`, sigue siendo propiedad
  de Dannia (`owner=1007`) con cantidad `1`;
- existe exactamente un item template `98` para Dannia: no hubo pérdida ni
  duplicación.

Con esto quedan aceptados dinámicamente tanto placement/owner como la
interacción y recuperación de la decoración.
