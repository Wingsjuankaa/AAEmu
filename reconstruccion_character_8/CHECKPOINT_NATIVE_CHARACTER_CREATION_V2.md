# Checkpoint — creación nativa de personajes AA8 v2

Fecha: 2026-07-25
Cliente: Kakao 8.0.3.12 r558734
Base validada: B14 Explorer/Hiram T1

## Resultado

La creación de personajes nuevos está habilitada para las 12 plantillas
jugables (seis razas y ambos géneros) y las ocho habilidades ofrecidas por la
pantalla de login: 96 combinaciones.

El runtime resuelve antes de asignar IDs:

- raza, género, modelo, facción, distritos y zona inicial;
- transformación inicial;
- siete piezas corporales compatibles con el modelo solicitado;
- pack de equipo por
  `ability_id -> login_stage_abilities.start_equip_pack_id`;
- cuatro suministros nativos;
- habilidad de nivel 1 y habilidades predeterminadas relacionadas;
- snapshot persistente de 217 acciones.

Una combinación, referencia, ranura, grado, cantidad o modelo inválido rechaza
la creación completa. La escritura de personaje, posición, habilidades,
acciones y objetos iniciales comparte una transacción MySQL. El éxito se envía
después del commit; nombre, IDs y objetos en memoria se liberan si falla.

No se migran ni reinterpretan personajes preexistentes.

## Autoridad y decisiones aceptadas

El baseline forense estricto permanece en:

- `generated/native-character-creation-v1-data.json`;
- `generated/native-character-creation-v1-manifest.json`;
- `generated/global-client-creation-sweep-v1-manifest.json`.

La política explícitamente aceptada está versionada en
`accepted-character-bootstrap-v2-policy.json`. No se mezcla con filas
clasificadas como nativas.

### Transformación inicial

`characters`, `district_return_points` y `return_points` prueban zona, distrito,
facción e identidad lógica del punto inicial:

| Raza | Zona | Return point | Editor name |
|---|---:|---:|---|
| Nuian | 179 | 243 | `system_nuian_start` |
| Dwarf | 328 | 239 | `dwarf_start` |
| Elf | 129 | 245 | `Gwe_start` |
| Hariharan | 187 | 240 | `rain_system` |
| Ferre | 184 | 241 | `start_fp` |
| Warborn | 157 | 717 | `start_warborn` |

El cliente no transporta XYZ de `return_points`; el loader confirmado consulta
solo `id, editor_name, name, use_additional`. Por decisión del operador se
conservan las transformaciones funcionales del servidor para las razas legado
y las transformaciones de la rama AAEmu 8 para Dwarf/Warborn, vinculadas a los
IDs y zonas nativos. Los grados de `CharTemplates.json` se convierten a radianes
antes de entrar en `WorldSpawnPosition`.

### Barra de acciones

El resultado nativo `default_action_bar_actions` es exactamente vacío. El
cliente AA8 sí prueba el algoritmo:

`SCSkillLearned -> FUN_395fb5a0 -> FUN_39690860 -> FUN_39690340`.

Para un personaje menor a nivel 21 busca la primera ranura base libre entre
1..12. La política aceptada persiste:

- ranura 1: tipo `Spell` (2), habilidad inicial elegida;
- las otras 216 ranuras: tipo `None` (0), acción 0.

Esto produce 20.832 filas, 217 por cada una de las 96 combinaciones. Aprender
habilidades posteriores continúa usando la autorregistración ya reconstruida.

### Suministros

Las filas nativas son:

- 87: item 4045, cantidad 1;
- 88: item 18791, cantidad 3;
- 89: item 18792, cantidad 3;
- 90: item 417, cantidad 3.

Como el orden no forma parte de la aceptación, se asignan de manera
determinista a mochila 0..3 por ID ascendente.

### Capacidad y expansión

La capacidad inicial aceptada permanece en 50 mochila / 50 banco. El protocolo
de expansión usa `CSExpandSlotsPacket` (`0x0A5`, int32 contenedor + bool).
Solo se aceptan mochila y banco, capacidades 50..140 y límites de diez ranuras.

El loader nativo de `bag_expands` es `x2game.dll FUN_39a077c0`. El resultado
Kakao contiene 20 filas:

- pasos 0..4: 5.000, 10.000, 30.000, 100.000 y 250.000;
- pasos 5..9: item 49000 en cantidades 1, 3, 6, 10 y 10;
- la misma secuencia para mochila y banco.

B14 usaba históricamente el item 8000025 y una unidad por paso. Esa relación
fue reemplazada; el runtime activo no conserva ninguna fila
`bag_expands.item_id=8000025`.

## Cierre de objetos

Los 16 objetos iniciales tienen fila `items` nativa y cierre concreto:

- 9 `item_weapons`;
- 3 `item_armors`;
- 4 objetos genéricos persistibles.

El item 4045 es el Teleport Book (`impl_id=14`). El backend no implementa un
subtipo persistente para ese impl y lo materializa como `Item`, respaldado por
su fila nativa. Armas y armaduras validan sus holdables, wearables, tipo,
ranura y set antes de marcarse `complete`.

El resultado nativo completo `default_skills` contiene una anomalía:
`skill_id=44214` no existe en el resultado nativo completo `skills`. Ninguna
relación `character_default_skills` la consume. El loader registra y omite esa
fila global; las habilidades realmente usadas por creación siguen siendo
obligatorias.

## Protocolo

- creación: nombre, raza, género, 7 uint32 corporales, modelo 0x128, 3 bytes de
  habilidad, nivel 1, `introZoneId=-1`;
- respuesta: opcode `0x2DD`, serializer de lista AA8;
- snapshot: 217 acciones con payload variable por tipo;
- actualización individual: índice byte, tipo byte y uint32/uint64 según tipo;
- `0x0AE`: ordenamiento de inventario, excluido de barra.

Una actualización de acción inválida no muta el personaje y provoca
resincronización autoritativa.

La validación visible contra el cliente AA8 también confirmó:

- `CSDeleteCharacterPacket 0x09A` responde con
  `SCCharacterDeleteResponsePacket 0x03D`;
- el largo exacto de plaintext C2G se obtiene del `msgKey`; el padding AES no
  forma parte del payload entregado a los parsers;
- las habilidades segunda y tercera de creación usan el sentinel nativo
  `AbilityType.None = 30`;
- las piezas de cuerpo nativas no usan las reglas de cantidad/grado de
  `ItemTemplate`;
- una identidad interna de modelo cero se normaliza con la plantilla
  raza/género/modelo ya validada;
- `CSSelectCharacterPacket 0x061` consume exactamente cinco bytes:
  `uint32 characterId + byte skipClientDriven`. El sexto byte histórico era
  padding AES y fue eliminado. Esto coincide con la firma de `x2game.dll`
  `SelectCharacter(index, skipClientDriven)` y con el frame local observado;
- el retorno desde el mundo a la lista de personajes reutiliza las claves de
  sesión y envía `CSAesXorKey_05_Packet 0x176` con un payload exacto de cuatro
  bytes: el sentinel `uint32 0`. El frame se observó localmente como
  `00-00-00-00`; el `int16` histórico posterior pertenecía al padding;
- la validación visible posterior al despliegue completó
  `CSLeaveWorld -> SCPrepareLeaveWorld -> SCLeaveWorldGranted` con la espera
  normal de diez segundos. A continuación `CSAesXorKey_05 0x176` fue aceptado y
  el servidor envió `SCGetSlotCount 0x011`, `SCAccountAttendance 0x31E`,
  `SCRaceCongestion 0x173` y `SCCharacterList 0x170`, sin rechazo del
  handshake ni cierre del cliente;
- el `world_id=1` conservado en la política de transformación es la
  identificación externa heredada. Antes de asignar IDs se normaliza al
  `WorldManager.DefaultWorldId` resuelto desde los mundos del cliente
  (`main_world=0` en este runtime), igual que hacía el cargador funcional
  anterior. XYZ, zona y rotación permanecen intactos.

La prueba visible detectó esta última diferencia porque el personaje nuevo
quedó inicialmente en el mundo lógico 1 mientras los 28.334 spawners de NPC
estaban en `main_world=0`. La reconstrucción de creación no eliminó ni
deshabilitó plantillas o archivos de spawn históricos.

## Artefactos reproducibles

- política:
  `accepted-character-bootstrap-v2-policy.json`;
- generador:
  `derive_accepted_character_bootstrap_v2.py`;
- datos:
  `generated/native-character-creation-v2-data.json`;
- manifiesto:
  `generated/native-character-creation-v2-manifest.json`;
- verificador:
  `verify_native_character_creation_v2.py`;
- runtime no versionado:
  `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-character-creation-v2.sqlite3`.

Hashes:

- datos v2:
  `E9E11F0923456EBB85A82E9A879AB1B681483D09D89C9622587FFA377E972B06`;
- manifiesto v2:
  `00835393C2ECA94A65F7CEA87B5FF2176A5FFC100AA65822F5078BF4BACE8408`;
- runtime v2:
  `A062929C8FEAE4B7796018083AD5B0FEC8FF5A5985032E62AEED3F57343AA973`.

Dos generaciones y dos builds produjeron hashes idénticos.
`quick_check=ok`, `integrity_check=ok`, 96 combinaciones, 20.832 acciones y
cero referencias huérfanas dentro del cierre de creación.

## Retirada nativa al cambiar de región

La prueba visible con el elfo detectó un cierre iniciado por el cliente al
cruzar de `Elf Starting Area` a `Harpa's Camp`. El servidor no produjo
excepción ni kick y la posición del personaje se guardó correctamente. Justo
antes del cierre se enviaban los opcodes históricos `0x231` y `0x24F`.

La revisión byte por byte de `x2game.dll` Kakao 8.0.3.12 demostró:

- `0x231` no es retirada de unidades en esta build. Su objeto contiene
  `zoneId`, `zoneOrigin`, `spawnerId` y posiciones;
- `0x24F` no es retirada de doodads. Su serializer consume entradas de
  ranking;
- el handler nativo de retirada de unidades es `FUN_392f9090`. Está registrado
  por `FUN_393665c0` en `param_1 + 0x1190`, que resuelve al opcode `0x230`;
- su objeto usa la vtable `PTR_FUN_39cf9f00`; `FUN_399a9eb0` consume
  `ushort count`, limita a 500 entradas y lee cada `id` mediante el tipo wire
  `Bc`;
- el handler nativo de retirada de doodad es `FUN_392fa800`, registrado en el
  opcode `0x031`;
- `FUN_399b2db0` consume exactamente `Bc id + bool e`, y el handler pasa ambos
  campos a `FUN_390f4f30`.

Por ello el runtime envía lotes de hasta 500 unidades mediante `0x230` y un
paquete singular `0x031` por doodad. El lote histórico `0x24F` fue eliminado
de las rutas de región y vivienda.

## Pruebas y despliegue

- suite completa Docker .NET Core 3.1: 227/227;
- build de `game`: correcto;
- imagen desplegada después de retirar los paquetes históricos de hora:
  `sha256:fa0fdb7a05f3df0260d18768d067f9deab4380606228de9ffdaaf92421a94555`;
- imagen de retirada de región conservada como
  `aaemu-game:pre-aa8-native-world-time-quarantine-20260726`
  (`sha256:d4c72af6d8d49f7f2c5677c097f755c1f56f53c97139ea2d00625afd833768e0`);
- imagen anterior conservada como
  `aaemu-game:pre-aa8-native-region-removal-20260726`
  (`sha256:6039f1f290af889a3b64c8283ec87cbe643f9a154ae79e5b666b16637c4d8ba4`);
- respaldo inmediatamente anterior a retirar los paquetes históricos de hora:
  `D:\Proyectos\AAemu\backups\aaemu-pre-aa8-native-world-time-quarantine-20260726-004500.sql`;
- SHA-256 de ese respaldo:
  `65A7E9FED65018100C1C732515B1A8B638ADC28DAE85A8F5B21DBD990D28A2E4`;
- respaldo inmediatamente anterior a corregir la retirada de región:
  `D:\Proyectos\AAemu\backups\aaemu-pre-aa8-native-region-removal-20260726-001308.sql`;
- SHA-256 de ese respaldo:
  `E484E8FC7333274F662C0E921EA2110149F6496219A0D74364C6AE1FC3ACDF28`;
- respaldo MySQL:
  `D:\Proyectos\AAemu\backups\aaemu-native-character-creation-v2-20260725-183410.sql`;
- SHA-256 del respaldo:
  `F61148A65DA5D321475245F43442BC0C365C22DD0FA096777A685B9446054AE2`;
- respaldo previo a normalizar de forma dirigida el mundo del personaje de
  aceptación:
  `D:\Proyectos\AAemu\backups\aaemu-pre-main-world-normalization-20260725-231141.sql`;
- SHA-256 de ese respaldo:
  `EF1BF11FDA4BC2EFAC1BE4F8A87B804CC6346C47720330F7C9C60FCA72386AB4`;
- solo se reinició `game`;
- compact montada:
  `A062929C8FEAE4B7796018083AD5B0FEC8FF5A5985032E62AEED3F57343AA973`;
- puertos 2239/2250 activos;
- catálogo: 12 plantillas cargadas;
- registro con login: correcto;
- reinicios del contenedor: 0.

## Cierre temporizado al entrar al mundo

Una segunda prueba visible del elfo descartó la retirada de región como
disparador: el cliente cerró primero Stream y Game y solo entonces el servidor
produjo `0x031`/`0x230` al limpiar la sesión. No hubo excepción, kick ni
reinicio del contenedor.

Las dos reproducciones cerraron a los 42--49 segundos. La correlación exacta
fue el quinto envío periódico, cada diez segundos, del paquete histórico
`SCTimeOfDay 0x070`.

La revisión nativa demostró que ninguno de los dos opcodes usados por el
servidor para hora del mundo conserva esa identidad en Kakao 8:

- el registro de `0x070` ocupa `param_1 + 0x390` y usa
  `PTR_FUN_39d028f8`;
- su objeto usa `PTR_FUN_39cfb178` y `FUN_3998c1e0`;
- el serializer consume exactamente `uint32 type + uint64 processingTime`;
- el servidor histórico emitía únicamente un `float`, dejando el paquete
  truncado;
- `0x1A1` ocupa `param_1 + 0xD18`, usa `PTR_FUN_39d05988` y el objeto
  `PTR_FUN_39cfb780`;
- `FUN_3998cfa0` consume `bool enter`, un enum nativo y `uint32`;
- su handler `FUN_392fb360` entrega los dos últimos valores a
  `FUN_395e3690`; por tanto tampoco es el paquete detallado de hora compuesto
  por cuatro `float`.

El ancho de los campos de `0x070` no se dedujo por nombres: el mismo contrato
de serializer aparece en `FUN_3998b100`, donde el método virtual `+0x80`
ocupa campos contiguos de cuatro bytes y `+0x78` ocupa los ocho bytes de
`freshnessTime`.

Se retiraron las emisiones históricas de `0x070` y `0x1A1` al aparecer,
reaparecer o cargar una instancia, junto con sus nombres y clases de paquete
incorrectos. No se sustituyeron por valores inventados. La sincronización
nativa de hora queda como dominio futuro y no forma parte de la aceptación de
creación de personajes.

En el mismo ingreso el cliente emite tres C2G todavía no registrados:

- `0x053`: `byte content + bool visible`;
- `0x206`: vacío;
- `0x164`: vacío.

Sus layouts de salida están confirmados, pero no existe todavía evidencia de
que requieran respuesta ni de que participen en el cierre. No se respondió a
ninguno por aproximación.

## Cierre de la primera etapa y matices pendientes

La primera etapa de creación nativa queda operativa y separada de los defectos
generales de protocolo encontrados durante la prueba visible. Está demostrado
en cliente que un personaje nuevo puede:

- crearse con la combinación raza/género/habilidad solicitada;
- entrar al mundo en el `main_world` funcional;
- recibir apariencia, equipo y suministros iniciales;
- recibir la habilidad inicial y el snapshot de barra;
- moverse, combatir, recolectar y guardar cambios de barra;
- abandonar el mundo mediante la secuencia normal de diez segundos.

Esto no cierra todavía la matriz exhaustiva de aceptación de 96 combinaciones
ni la prueba posterior a reiniciar `game`. Tampoco convierte los paquetes
históricos ajenos al bootstrap en autoridad AA8.

### Caída del elfo y opcode `0x30A`

En la sesión del elfo:

- `CSNotifyInGame` terminó a las `04:49:47`;
- a las `04:50:49` se enviaron 14 paquetes consecutivos que el servidor llama
  `SCConflictZoneStatePacket 0x30A`;
- a las `04:50:50` se envió el paquete histórico `0x2FE`;
- el cliente cerró Stream y Game a las `04:50:52`;
- no hubo excepción, kick ni reinicio del contenedor.

La revisión nativa de `x2game.dll` demuestra que la identidad/layout histórico
de `0x30A` no es válido para Kakao 8:

- su slot de registro es `param_1 + 0x1860`;
- `FUN_3936e130` registra el handler `FUN_393927a0`;
- el dispatcher usa `PTR_FUN_39d04ec0`;
- el objeto de paquete usa `PTR_FUN_39cfb008`;
- el serializer `FUN_3998bd20` consume tres campos ubicados en `+0x10`,
  `+0x14` y `+0x18`;
- el handler resuelve esos tres valores como identificadores antes de actualizar
  relaciones del cliente;
- el servidor, en cambio, escribe `ushort zoneId + byte state + dos DateTime`.

Por tanto, la emisión actual está demostrablemente mal identificada y tiene un
payload incompatible. La ráfaga `0x30A` es la hipótesis principal para la caída
del elfo porque fue específica de esa sesión/zona y precedió inmediatamente al
cierre. No se retiró ni reconstruyó todavía: debe retomarse como un dominio de
protocolo de zonas/facciones, confirmando primero la identidad semántica exacta
del paquete nativo y localizando el opcode AA8 real del estado de conflicto.

### Opcode `0x2FE`

`SCCharacterLaborPowerChangedPacket 0x2FE` también conserva una identidad
histórica incorrecta:

- su slot nativo es `param_1 + 0x1800`;
- el handler es `FUN_392fa4e0`;
- el objeto usa `PTR_FUN_39d0d0e0`;
- `FUN_3998aa40` consume un `type` seguido de una estructura compleja;
- esa estructura contiene, entre otros, `teamId` y `scorePoint`;
- esto no coincide con los cuatro campos pequeños de labor que escribe el
  servidor.

Sin embargo, no se considera el detonante inmediato de la caída observada. El
nuiano entró al mundo a las `04:55:05`, recibió `0x2FE` a las `04:55:50`,
`04:56:29` y `04:56:33`, continuó combatiendo y recolectando, y solicitó la
salida normal con `CSLeaveWorld` a las `04:59:34`. Durante esa sesión no recibió
la ráfaga `0x30A`.

`0x2FE` queda registrado como deuda de protocolo global: no debe reutilizarse
como paquete de labor en una reconstrucción AA8 futura, aunque esta prueba
indica que no explica por sí solo la caída del elfo.

No se hicieron cambios de runtime ni reinicios después de este diagnóstico.
El contenedor permaneció activo con cero reinicios.

## Corrección de contabilidad de habilidades iniciales

La validación visible posterior detectó que un nuiano Battlerage recién creado
mostraba `-1` punto de habilidad al nivel 5 y `0` después de reconectar. La
reproducción quedó cerrada con datos persistidos y catálogo AA8:

- `levels.skill_points` entrega 2 puntos al nivel 5;
- la habilidad inicial Battlerage `18132` tiene `need_learn=1` y costo 1;
- las habilidades predeterminadas nuianas `35418` y `35420` tienen
  `ability_id=0`, `need_learn=0` y costo nominal 1;
- la creación V2 había materializado las tres como filas aprendidas, por lo que
  cliente y servidor restaban 3 a los 2 puntos disponibles.

`character_default_skills → default_skills` no representa compras del árbol.
Esas relaciones declaran habilidades predeterminadas disponibles para la
plantilla y el cliente ya las conoce por su catálogo. El backend las admite
mediante `SkillManager.IsDefaultSkill`; no deben entrar en `character.Skills`,
en `SCUnitState.learnedSkills` ni en la tabla MySQL `skills`.

La creación persiste ahora exclusivamente `plan.LearnedSkills`. Como defensa
adicional, `CharacterSkills` rechaza habilidades con `need_learn=0`, no las
cuenta como puntos gastados, las omite al cargar datos inválidos heredados y
no vuelve a guardarlas. Las pasivas continúan consumiendo su
`passive_buffs.skill_points` nativo.

Para un personaje Battlerage válido, la contabilidad esperada queda:

- nivel 1: 1 total, `18132` consume 1, disponible 0;
- nivel 5: 2 totales, `18132` consume 1, disponible 1.

La ausencia posterior de `18132` en el personaje de prueba no fue producida
por el filtro de carga: la fila ya no existía en MySQL y los logs anteriores
se perdieron al recrear el contenedor. Se repara únicamente ese personaje de
prueba de forma dirigida; no se ejecuta un backfill general.

## Aceptación visible pendiente

La implementación y el despliegue están listos, pero el criterio no se declara
cerrado hasta realizar desde el cliente:

1. crear personajes desechables que cubran las seis razas, ambos géneros y las
   ocho habilidades;
2. comprobar posición, apariencia, equipo, suministros, habilidad y barra;
3. reconectar cada personaje;
4. mover una acción, reconectar y confirmar persistencia;
5. expandir mochila o banco si la cuenta dispone del costo;
6. reiniciar `game`, reconectar y volver a inspeccionar.

El operador autorizó eliminar de forma dirigida personajes actuales si
interfieren con cupos o con esta matriz de prueba. No se borrarán cuentas ni
datos ajenos al dominio.
