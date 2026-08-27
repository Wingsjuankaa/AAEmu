# Checkpoint nativo AA10: lifecycle de items de mate v1

Fecha: 2026-08-27
Branch: `rama_10`
Baseline de código: `6256062b819dd4b92e1f20f141d118f3078c2455`

## Alcance cerrado

Este checkpoint reconstruye la frontera item -> skill `SpawnPet` -> NPC para
mounts y battle pets de ArcheAge Returns 10.0.2.13 r575. El código heredado ya
tenía spawn, mount/unmount, equipo y tabla MySQL `mates`, pero aceptaba cualquier
fila runtime, hacía casts inseguros y podía dejar estado activo obsoleto tras un
relog.

El cierre v1 incorpora:

- catálogo retail exacto, sin fallback heredado;
- validación del item físico, dueño, bolsa, skill, `impl_id` y NPC antes de
  mutar el mate activo;
- cancelación fail-closed de `SpawnPet` en relaciones desconocidas;
- exclusión mutua por personaje para doble click concurrente;
- actualización de los 20 bytes conocidos del detalle de item (EXP y nivel);
- snapshot de HP, MP, nivel, EXP, mileage y nombre al retirar o desconectar;
- eliminación correcta del registro activo por `character.Id` al relog;
- retiro del registro MySQL cuando se destruye el item;
- rechazo de destrucción mientras el mate conserva equipo persistente.

No se copiaron IDs, packets ni fórmulas desde AA8. El commit AA8
`ac631a5ef` se usó únicamente como `structural_candidate`.

## Auditoría de requisitos

| Requisito | Evidencia estática actual |
|---|---|
| Catálogo | Manifest completo de 552 relaciones y policy cerrada de 478; igualdad `itemId/skillId/npcId` probada campo por campo. |
| Adquisición | El loader materializa cada contrato promovido como `SummonMateTemplate`, cuyo `ClassType` crea `SummonMate` por el flujo normal `ItemManager.Create`; la carga aborta si la policy no coincide con ese template runtime. |
| Registro | La primera invocación crea un único `MateDb` ligado al `itemId`; una entrada existente se reutiliza. |
| Invocación/retirada | `SpawnPet` exige el mismo objeto físico de bolsa y `ToggleMate` serializa el ciclo; la segunda pulsación retira el mate activo. |
| Rechazo sin mutación | Dueño, bolsa, identidad, skill, contrato, NPC, modelo, tipo, slot pack y buffs se validan antes de retirar el mate activo o asignar IDs. Los rechazos cancelan la skill y no usan fallback. |
| Persistencia/relog | El retiro y ambos caminos de desconexión capturan HP, MP, nivel, EXP, mileage, nombre y detalle del item antes de `Character.Save`; `Load` reconstruye el registro por `item_id`. |
| Destrucción | Se rechaza si el contenedor persistente de equipo tiene piezas; si está vacío, retira el activo y agenda el borrado del `MateDb`. |
| Fronteras no demostradas | Las 74 relaciones bloqueadas permanecen fuera de la policy y generan `ItemCannotUse`, sin delegación legacy. |

Esta matriz prueba estructura, datos y orden del código. La observación retail
de spawn, retirada, mount y relog quedó cerrada dinámicamente en el despliegue
descrito al final de este checkpoint.

## Evidencia congelada

| Fuente | SHA-256 |
|---|---|
| SQLite completa AA10 | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` |
| compact retail AA10 | `F8C7A0268A26D4EFAEC47A2A2B1B525447BF16C274506CD97BF571839B5E6D29` |
| compact runtime montada | `DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD` |
| x2game operacional | `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734` |

Ghidra, sobre el x2game operacional, reancló
`FUN_39b265b0@39b265b0` y recuperó el loader nativo:

```sql
SELECT item_id, npc_id FROM item_summon_mates
```

La función incrementa un catálogo paralelo de `item_id`/`npc_id` y falla si
`sqlite3_prepare_v2` o `sqlite3_step` no terminan correctamente. El efecto
especial `SPAWN_PET` se cerró desde `skill_effects -> effects ->
special_effects`, con `special_effect_type_id=24` medido en AA10.

## Cobertura

El manifest contiene las 552 relaciones autoritativas:

| Estado primario retail | Cantidad |
|---|---:|
| `executable` | 478 |
| `compact:missing_item` | 71 |
| `compact:missing_npc` | 1 |
| `compact:missing_initial_buff` | 2 |
| **Total** | **552** |

Los bloqueos se conservan como arreglos, por lo que una fila puede registrar
además defectos de full/runtime. Entre ellos hay 3 items `use_skill_as_reagent`,
2 referencias a `mount_skills` ausentes y 5 NPC ausentes; todos pertenecen al
grupo de 71 items no publicado por retail. No se promueve ninguna fila por
parecido o por presencia exclusiva en la SQLite completa.

Casos retail visibles bloqueados:

- item `42591` -> NPC `17667`: NPC ausente en compact retail;
- item `39711` -> NPC `16458`: buff inicial `31562` ausente en compact retail;
- item `47338` -> NPC `19170`: buff inicial `31569` ausente en compact retail.

Artefactos:

- `evidence/summon_mates/aa10-summon-mate-manifest-v1.json`;
- `AAEmu.Game/Data/aa10-summon-mate-policy-v1.json`;
- `.server_files/AAEmu.Game/Data/aa10-summon-mate-policy-v1.json`;
- `scripts/audit_aa10_summon_mates.py`.

Hashes generados:

- manifest: `CEFE7FCE8F3C958C38808B5FAADA8E991E4209A1053C8D32CE7FAD09B09D16FC`;
- policy: `7BBB68611FCBC4A94FB9D98C0CCD6A8B0953D36CD1DC68B70230D5DCCD178155`.

Dos ejecuciones consecutivas produjeron los mismos hashes. Las tres SQLite
pasaron `quick_check=ok` e `integrity_check=ok` en el generador.

## Gates automatizados

La suite cubre:

- carga y hash del catálogo cerrado de 478 contratos;
- igualdad campo por campo de cada contrato de policy con su fila executable
  (`itemId`, `skillId`, `npcId`) y ausencia de promociones omitidas;
- item exacto y rechazos por dueño, slot, skill y catálogo desconocido;
- rechazo de IDs/cantidades nulas y de objetos que no pertenecen realmente al
  contenedor declarado;
- rechazo de tipo runtime incorrecto y de drift `item/skill/NPC` posterior a
  la carga de la policy;
- ausencia de fallback a una relación runtime no promovida;
- layout wire de 20 bytes y roundtrip de EXP/nivel;
- body r575 de `SCMateSpawned` de 64 bytes, incluyendo identidad, tipo y diez
  slots exactos de mount skills;
- snapshot completo de estado usado por save/relog;
- regresión completa de la solución.

Comandos canónicos:

```powershell
python reconstruccion_cliente_10\scripts\audit_aa10_summon_mates.py `
  --full E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3 `
  --compact E:\AAEmu\rama_10\data\sqlite\retail\compact.sqlite3 `
  --runtime .server_files\AAEmu.Game\Data\compact.sqlite3 `
  --x2game E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\Bin64\x2game.dll `
  --manifest reconstruccion_cliente_10\evidence\summon_mates\aa10-summon-mate-manifest-v1.json `
  --policy AAEmu.Game\Data\aa10-summon-mate-policy-v1.json
dotnet restore AAEmu.slnx
dotnet build AAEmu.slnx -c Release --no-restore
dotnet test AAEmu.UnitTests\AAEmu.UnitTests.csproj -c Release --no-build -- --no-progress --output Normal
```

Resultado del cierre estático del 2026-08-27: restore correcto, build Release
con 0 errores y suite completa `1580/1580` correcta (0 fallos, 0 omitidos). Los
avisos NU190x y de analizadores pertenecen al baseline de dependencias/código y
no introdujeron errores de compilación.

## Aceptación dinámica cerrada

La aceptación se ejecutó el 2026-08-27 sobre el cliente retail r575 y Zone 129
(`w_gweonid_forest_1`) después de la autorización explícita del usuario.

Despliegue:

- imagen previa recuperable: `aaemu-world:rollback-pre-summon-mate-20260827`;
- imagen aceptada: `sha256:908c5a647fa803079e77236bfc3403d7a2763388665c19648a18ecdc4a4d0be4`;
- Game quedó healthy y cargó 478 contratos exactos;
- el permiso temporal usado únicamente para preparar fixtures se retiró antes
  de la aceptación; `AccessLevels.json` volvió exactamente al SHA-256
  `4AF920171FB9FA33DF522F47FE35E73F680826901E91AEF20DBF1448D91ADB4A`.

Cuenta de regresión local persistente:

- usuario: `codexmate0827`;
- personaje: `Mateprobe` (character id 9, account id 3);
- credencial cifrada con DPAPI, sólo para el usuario Windows local, en
  `C:\Users\juank\AppData\Local\AAEmu\test-accounts\aa10-r575-retail.clixml`;
- la contraseña no se registra en este repositorio ni en este checkpoint.

Fixtures conservados en la bolsa de `Mateprobe`:

- item `16777486`, template `4177`, contrato executable
  `4177 -> skill 32211 -> NPC 3599` (Lilyut Horse);
- item `16777487`, template `39711`, contrato bloqueado por
  `compact:missing_initial_buff`.

Resultados observados:

1. La primera pulsación del item 4177 produjo `SCItemTaskSuccess` con
   `UpdateSummonMateItem`, `SCMateSpawned`, `SCMateState` y
   `SpawnPet ... result=Spawned`.
2. La segunda pulsación retiró el mate, emitió `WZUnitRemoved` y no consumió el
   item. Una nueva pulsación volvió a invocar la misma Lilyut Horse.
3. La interacción de mount pasó por el contrato nativo
   `CSMountMate -> SCUnitAttached`; el personaje quedó visualmente montado.
4. MySQL persistió una sola fila: `mates.id=1`,
   `item_id=16777486`, `name=Lilyut Horse`, `xp=1200`, `level=5`,
   `hp=1874`, `mp=1098`, `owner=9`. El detalle wire del item pasó de cero a
   `B004000000050000000000000000000000000000`.
5. Se salió limpiamente a selección de personaje estando montado. El servidor
   desmontó/retiró el mate, actualizó `updated_at` y guardó. Tras entrar otra
   vez, el item volvió a invocar la montura y MySQL continuó con exactamente una
   fila para ese `item_id`: no hubo duplicación ni pérdida de estado.
6. El item bloqueado 39711 mostró `You cannot use this`; el log registró
   `reason=BlockedContract`, no creó un mate y dejó ambos items sin consumo ni
   cambio de contenedor.
7. El correo auxiliar `10003` y su adjunto duplicado `16777485` se eliminaron
   mediante la API interna y el siguiente ciclo de guardado confirmó ambos en
   cero; los dos fixtures útiles permanecieron presentes.

Los guards de destrucción con/sin equipo permanecen cubiertos por pruebas
automatizadas deliberadamente no destructivas sobre la cuenta reusable. El
lifecycle requerido de adquisición, registro único, invocación, retirada,
mount y persistencia/relog queda aceptado dinámicamente.
