# Checkpoint transversal de especializaciones AA8 v1

## Autoridad y alcance

- Cliente: Kakao 8.0.3.12 r558734.
- Contrato runtime: compact descifrada AA8, `game11`, grafo consolidado y Stage 15.
- Wiki: sólo corroboración congelada; no establece filas, fórmulas ni comportamiento.
- Compact histórica 3.0: no usada por el pipeline ni por los runtimes de este checkpoint.
- Battlerage y Shadowplay permanecen como regresiones congeladas.

## Pipeline implementado

- Suite forense de 14 especializaciones e índice global.
- Constructor runtime parametrizado por `ability_id`, nombre o slug.
- `COMPACT_DB` se lee desde `.env`; ningún nombre de fase está hardcodeado.
- Seis pasivas por spec con `skill_points=0` y `req_points` AA8.
- Cuarentena por raíz con poda de relaciones ejecutables, sin fallback silencioso.
- Dos builds deterministas, checks SQLite y manifiesto por runtime.

Índice final:

- `E:/AAEmu-Research/output/aa8-client-forensics/specialization-suite-v1.json`
- SHA-256: `E7B4BB7D62C49B84CB3794DA2F5D3A6BB4764D0378829ECE0F4BB23BCFF233FD`
- Manifiesto SHA-256: `419A23722F667C3C4597B450CD6C31E6F8E2A2049DED5369669007B269AC3E09`
- 14 specs, 462 raíces, 84 pasivas y 4.158 `reconstruction_test_cases`.
- Validación: 14/14 `confirmed`, `quick_check=ok`, `integrity_check=ok`, cero cierres sin clasificar.
- Determinismo contractual: 14/14 SQLite idénticos en dos construcciones completas.

## Primitivas compartidas

`RestoreManaEffect` quedó reconstruido desde la fórmula AA8:

- escalado por nivel del caster, `ability_level` y `level_step`;
- tramo fijo y tramo por nivel;
- variación `level_va_start/end`;
- porcentaje per-mille sobre `MaxMp`;
- reparto por tick, valores negativos y clamp `0..MaxMp`;
- paquete visible compatible con `CompressedGamePackets`.

El recálculo sólo habilitó la raíz Auramancy `11989`. Las otras dos raíces que
alcanzan la primitiva siguen aisladas por `BubbleEffect`, `HealEffect` y
`ExtendChargeEffect`; ninguna raíz ajena cambió de estado.

Bloqueos forenses explícitos:

- `ResetAoeDiminishingEffect`: el cliente prueba descriptor y multiplicador,
  pero no expone el estado backend que debe resetear.
- `KillNpcWithoutCorpseEffect.give_exp`: Stage 15 confirma el layout, pero el
  despacho efectivo permanece tras una región opaca.

## Gates automáticos

- Pruebas grafo: 9/9.
- Pruebas constructor runtime: 4/4.
- Pruebas dossier compartido: 4/4.
- Pruebas artefactos combate nativo: 12/12.
- `AAEmu.Tests`: 349/349 con SDK .NET 3.1.

Runtime Auramancy no desplegado:

- `D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-transversal-auramancy-restoremana-v1.sqlite3`
- SHA-256 de ambos builds: `374FDE44749E0A155B8A1BD08CF663E065278E882FDF679993965F6E982190F8`
- 20 raíces habilitadas, cuatro aisladas, seis pasivas, checks SQLite `ok`.

## Wave 0: Swiftblade

Runtime de aceptación:

- `D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-transversal-swiftblade-audit-v2.sqlite3`
- SHA-256 de ambos builds: `B8113A5BFC32279D98D5B0A8A7DE3CE686C2145F6A0FDF08A2B8D9345A5FA0C1`
- 46/46 raíces habilitadas, 12 visibles, seis pasivas, cero cuarentena.

## Rollback del despliegue Wave 0

Estado anterior:

- `COMPACT_DB=D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-native-quest4411-v2.sqlite3`
- SHA-256 compact: `B3514EB99127BEACBC469A52789D7C99C3347CE43B2F2AB661984E644EE178C8`
- imagen: `aaemu-game:0.0.2.0-alpha`
- image ID corto: `68f81d1c0fef`
- Login y MySQL no se recrean.

Rollback:

1. Restaurar la línea `COMPACT_DB` anterior en `.env`.
2. Ejecutar `docker compose up -d --no-deps --force-recreate game`.
3. Verificar el SHA montado en `/app/Data/compact.sqlite3`, puertos 2239/2250
   y registro del servidor en Login.

## Punto de parada manual

No declarar Swiftblade aceptada hasta completar, una transición por vez:

1. aprender/resetear/cambiar a Swiftblade y reloguear;
2. comprobar las 12 activas con objetivo válido e inválido;
3. probar las seis pasivas en sus umbrales;
4. repetir movilidad, AoE, proyectiles y combos rápidamente;
5. observar desde un segundo cliente;
6. revisar logs y persistencia antes de iniciar la siguiente spec.

## Incidente Wave 0: aprendizaje de pasiva Swiftblade

Durante la primera aceptación, el personaje `Dannia` aprendió las 12 activas y
la pasiva `360` (`buff_id=24895`). El trigger AA8 `12071` consulta el tag
`3379`; la compact autoritativa contiene cero miembros para ese tag. El backend
devolvía `null` para el conjunto ausente y `Buffs.CheckBuffTag` ejecutaba
`Contains` sin guard, provocando `NullReferenceException` y desconectando la
sesión desde `CSLearnBuffPacket`.

Corrección genérica:

- un tag sin filas devuelve un conjunto vacío;
- el lookup ignora efectos nulos o sin plantilla;
- no se introdujo ningún ID de skill/buff/tag en la implementación;
- regresión específica `BuffTagLookupTests`: 2/2;
- suite completa posterior: 352/352.

Despliegue reparado:

- imagen anterior recuperable:
  `sha256:6cc2f781b0df0e26c0eea5650323f619e3c81da7629840ea7dba895727d35cf8`;
- imagen nueva:
  `sha256:bfda13328bed1f15f5fa8352bb6cea641d1402a0dbc30356e0f69225913430c5`;
- compact y SHA no cambiaron;
- Login y MySQL no se recrearon.

La fila `skills(owner=1,id=360,type=Buff)` quedó persistida. El siguiente gate
manual es sólo reconectar; no volver a aprender ni resetear hasta revisar los
logs del load y confirmar que la pasiva reaplicada no expulsa la sesión.

### Reconexión y aprendizaje acelerado de las seis pasivas

La reconexión de `Dannia` terminó correctamente a las 19:07. Sin esperar el
gate individual, el cliente solicitó las cinco pasivas restantes entre
19:07:28 y 19:07:34. Cada `CSLearnBuffPacket` obtuvo su correspondiente
`SCBuffLearnedPacket` (cinco aceptaciones, contadores 107..111), sin excepción,
desconexión ni caída de `game`.

Esto confirma en la sesión viva:

- seis pasivas Swiftblade aceptadas en memoria;
- el lookup de un tag vacío ya no interrumpe la aplicación;
- `game`, Login y MySQL permanecen sanos;
- falta forzar un guardado controlado mediante salida a selección de personaje
  y validar que las seis filas se recargan y reaplican al reloguear.

Antes de esa salida, MySQL conserva sólo la fila `360`; es el estado persistido
de la sesión anterior, no evidencia de rechazo de las otras cinco.

## Incidentes Wave 0: Blink, Dusk Shroud y Bladeblast

La aceptación manual identificó tres cierres incompletos. Se reconstruyeron
desde SQLite AA8, Stage 15 y el comportamiento observado; la wiki no aportó
ninguna decisión runtime.

### Blink

- La primera acción `40333` aplica el buff `24610`, cuyo contrato nativo tiene
  `save_pos=1`, y habilita durante 5000 ms la segunda acción `41487`.
- La segunda acción ejecuta el special effect tipo `172` con `value1=24610` y
  después disipa ese buff.
- Se implementó genéricamente el guardado de posición en buffs que declaran
  `save_pos` y el retorno tipo `172`, validando mundo e instancia antes del
  movimiento y emitiendo el paquete visible de blink.

### Dusk Shroud

- El cierre de sus `InteractionEffect` alcanza los doodads `13939`, `14104`,
  `14130` y `14131`.
- `game11` prueba sus cuatro raíces y grupos de fase; no tienen `DoodadFunc`,
  por lo que son un cierre puro de presentación y se materializaron completos.
- El constructor permanece genérico: un doodad funcional sin descriptor
  completo se aísla y se declara en el manifiesto, sin fallback silencioso.

### Bladeblast

- El plot abortaba porque `AreaShape.kind=3` no existía en el backend.
- El corpus AA8 demuestra una forma prismática orientada hacia delante:
  semiancho `Value1`, longitud frontal `Value2` y semialtura `Value3`.
- Se implementó esa forma de manera genérica. Esto permite que continúe el
  plot nativo con detección en trayectoria, daño y su controlador de dash.

No se introdujeron IDs de skills en el backend.

## Runtime Swiftblade audit v3

- compact desplegada:
  `D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-transversal-swiftblade-audit-v3.sqlite3`;
- segundo build idéntico: SHA-256
  `012519970560E08D591692DBB3F49EF218E79F6F8B8A43D75242504AF5223D84`;
- `quick_check=ok`, `integrity_check=ok`;
- 46/46 raíces habilitadas, 12 visibles, seis pasivas y cero cuarentena;
- matriz Swiftblade: 414 casos ejecutados, 372 aprobados, 42 no aplicables y
  cero fallos;
- pruebas del constructor: 4/4;
- pruebas de movimiento/forma: 16/16;
- suite completa `AAEmu.Tests`: 355/355.

Artefactos:

- `specializations/generated/swiftblade-audit-v3.manifest.json`, SHA-256
  `D4EE0474E738E537E0EA366DCBC81F5AD319BB9AF2F6EC1B729CDCA6E307509F`;
- `specializations/generated/swiftblade-audit-v3-reconstruction-report.json`,
  SHA-256
  `A935DC38B9AD04E032AE100217B22745062DCBB4A67C86D922D109268A608794`.

Despliegue:

- sólo se reconstruyó y recreó `game`;
- imagen activa:
  `sha256:f9feec77ac3841afb24df663c80955ff4ed6d493d41cb884ea63a458f13fa2e5`;
- rollback de imagen:
  `aaemu-game:rollback-pre-swiftblade-native-fixes-v3-20260802-153845`;
- Login y MySQL conservaron sus contenedores;
- la compact montada en `/app/Data/compact.sqlite3` coincide con el SHA v3.

Swiftblade continúa pendiente de aceptación manual de estas tres transiciones;
no iniciar la siguiente especialización hasta cerrar ese gate.

## Swiftblade acceptance follow-up v4

La observación manual posterior a v3 corrigió dos conclusiones incompletas. El
efecto visual de Dusk Shroud no era el cierre funcional: `doodad_phase_funcs`
y `doodad_func_clouts` contienen su contrato runtime AA8. La captura de Blink
también demostró que el buff `save_pos` se crea después del movimiento, por lo
que guardar la posición corriente dentro del constructor del buff conserva el
destino en vez del origen del cast.

### Correcciones

- Blink conserva una instantánea inmutable de posición, world e instance antes
  de ejecutar el plot. El buff `save_pos` usa esa instantánea cuando caster y
  owner son la misma unidad; no hay ID de skill hardcodeada.
- Dusk Shroud materializa los cuatro `DoodadFuncClout` AA8 (`3805`, `3826`,
  `3828`, `3829`), sus shapes (`15500`, `15686`, `15707`, `15708`) y su cierre
  recursivo de buffs. El clout `3805` aplica el stealth nativo `24640` sólo al
  portador del marcador `24641`/tag `4176`. Los filtros de tag requerido y
  excluido se implementaron transversalmente en `AreaTrigger`.
- El botón Hereafter Threshold observado en cliente vivo envía C2G `0x1E5`,
  nivel 5, payload booleano. `CSResurrectCharacterPacket` queda registrado en
  ese opcode AA8, reemplazando el placeholder `0xFFF`.
- El extractor común ahora decodifica `doodad_phase_funcs` y
  `doodad_func_clouts`; el constructor por `ability_id` incluye su cierre en la
  compact y aísla tipos no soportados sin fallback silencioso.

### Runtime y pruebas

- compact desplegada:
  `D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-transversal-swiftblade-audit-v4.sqlite3`;
- dos builds idénticos, SHA-256
  `BE4CB8952E24731762301F79EF977993AE7058E02AA33929A519AFE7057A4E2F`;
- `quick_check=ok`, `integrity_check=ok`;
- 46/46 raíces habilitadas, 12 visibles, seis pasivas y cero cuarentena;
- 414 casos ejecutados: 372 aprobados, 42 no aplicables, cero fallos;
- pruebas focalizadas .NET: 20/20;
- pruebas Python de constructor/grafos: 20/20;
- suite completa `AAEmu.Tests`: 359/359.

Artefactos:

- `specializations/generated/swiftblade-audit-v4.manifest.json`, SHA-256
  `171A8187898ACB38EA2DD274990A97F498980899CE3F69DE63127AD322D5829A`;
- `specializations/generated/swiftblade-audit-v4-reconstruction-report.json`,
  SHA-256
  `6E9ABCE4E3A5183C98609A890DF728D10D4162A275A982E237FF86C13C4DF2F3`.

### Despliegue

- sólo se reconstruyó y recreó `game`;
- imagen activa:
  `sha256:52c7e2db75a4ca846fa92a3e803532f6017f5caa984468039ab4b47da4f8a7d5`;
- rollback:
  `aaemu-game:rollback-pre-swiftblade-native-fixes-v4-20260802-164557`;
- Login y MySQL conservaron sus contenedores;
- `/app/Data/compact.sqlite3` coincide byte por byte con el SHA v4;
- el servidor inició red y conexión a Login correctamente.

Swiftblade queda en gate de aceptación manual para respawn, retorno exacto de
Blink e invisibilidad/ruptura/reentrada de Dusk Shroud. No iniciar Wave 1 hasta
cerrar esas tres pruebas y revisar sus logs.

## Swiftblade acceptance follow-up v5: cierre visual de clouts

La aceptación manual cerró correctamente respawn, el retorno exacto de Blink y
las demás habilidades Swiftblade. Dusk Shroud aplicó su stealth y su zona de
juego durante los siete segundos nativos, pero el prefab continuo permanecía
visible y se acumulaba después del vencimiento.

### Evidencia y corrección

- Los cuatro `DoodadFuncClout` alcanzables desde `40334` tienen
  `duration=7000` y `next_phase=-1`. Los logs confirmaron creación y emisión de
  `SCDoodadRemoved` siete segundos después.
- El prefab AA8 `pc_skill.new_skill_smoke_launch` usa
  `NEW_skills_smokescreen_dot15s`, cuyos emisores hijos son continuos; depende
  de que el doodad abandone completamente el registro de mundo/región.
- El cierre de `DoodadFuncClout` ya no usa un `Task.Run` ajeno al scheduler del
  juego. `DoodadFuncCloutTask` retira primero el `AreaTrigger`, limpia la tarea
  propietaria y elimina el doodad cuando `next_phase=-1`; para otra fase ejecuta
  la transición nativa. Es una corrección transversal sin IDs de skills.
- El lote regional `SCDoodadsCreatedPacket` excluye doodads que ya están
  marcados invisibles. Esto cierra la carrera en que un cambio de región podía
  volver a materializar un prefab entre `Hide()` y la retirada del registro.
- `SCDoodadRemovedPacket.Verbose()` registra ahora el `objId` sin cambiar su
  payload, para correlacionar de forma exacta creación y retiro en cliente vivo.

### Validación y despliegue

- compact conservada: `compact-8.0-runtime-transversal-swiftblade-audit-v4.sqlite3`;
- SHA-256: `BE4CB8952E24731762301F79EF977993AE7058E02AA33929A519AFE7057A4E2F`;
- `quick_check=ok`, `integrity_check=ok`;
- 414 casos ejecutados: 372 aprobados, 42 no aplicables y cero fallos;
- pruebas Python del constructor: 4/4;
- suite completa `AAEmu.Tests`: 359/359;
- reporte reproducido byte por byte en
  `specializations/generated/swiftblade-audit-v5-clout-lifecycle-reconstruction-report.json`,
  SHA-256 `6E9ABCE4E3A5183C98609A890DF728D10D4162A275A982E237FF86C13C4DF2F3`;
- sólo se reconstruyó y recreó `game`, imagen
  `sha256:86e8810580b6952ec0a1a056db6e5e612452a69a5518263160cf28d7b77b89fb`;
- rollback: `aaemu-game:rollback-pre-dusk-clout-lifecycle-v5-20260802-174738`;
- Login y MySQL conservaron sus contenedores y la compact montada coincide con
  el SHA v4;
- el servidor inició las redes `2239`/`2250` y se registró correctamente en
  Login.

Queda un único gate manual: lanzar Dusk Shroud, permanecer junto a la zona por
más de diez segundos y repetir una segunda vez para verificar que cada prefab
desaparece sin acumulación. Revisar los `objId` de `SCDoodadRemoved` después de
esa prueba antes de iniciar Wave 1.

## Swiftblade acceptance follow-up v6: duración de fase en cliente

La prueba manual posterior a v5 falsó la hipótesis de una resurrección regional
del doodad. Para el cast vivo de `40334`, los cuatro objetos (`10108`, `10239`,
`10413`, `10665`) recibieron `SCDoodadRemoved` exactamente siete segundos
después de crearse y ninguno volvió a materializarse en el servidor. El estado
lógico terminaba correctamente, pero el cliente conservaba el emisor visual.

### Causa nativa y corrección

- `SCDoodadPhaseChangedPacket` enviaba `timeLeft=0`, aunque los cuatro clouts de
  Dusk Shroud tienen `duration=7000` en la SQLite contractual.
- El handler nativo Stage 15 `0x002fa860` entrega ese campo a `0x00630490`; esa
  función lo conserva en el doodad y `0x0062fc40` lo utiliza al cargar el modelo
  de fase. Un valor cero deja sin horizonte temporal el emisor continuo.
- Las fases ahora exponen transversalmente su duración contractual. Antes de
  emitir `SCDoodadPhaseChangedPacket`, `Doodad` fija `GrowthTime` con la mayor
  duración alcanzable de sus funciones de fase.
- `DoodadFuncClout` aporta su `Duration`; `DoodadFuncTimer` aporta `Delay + 1`,
  respetando la semántica temporal ya usada por el runtime. No hay IDs de
  habilidades ni excepciones específicas de Swiftblade.
- Se conserva `SCDoodadRemoved(..., false)`: el análisis del handler nativo
  demostró que `true` selecciona otra ruta de copia de objeto y no es la señal
  normal de retiro.

### Validación y despliegue

- compact conservada: `compact-8.0-runtime-transversal-swiftblade-audit-v4.sqlite3`;
- SHA-256: `BE4CB8952E24731762301F79EF977993AE7058E02AA33929A519AFE7057A4E2F`;
- `quick_check=ok`, `integrity_check=ok`;
- 414 casos ejecutados: 372 aprobados, 42 no aplicables y cero fallos;
- suite completa `AAEmu.Tests`: 361/361;
- `git diff --check` sin errores de whitespace;
- reporte `specializations/generated/swiftblade-audit-v6-phase-time-reconstruction-report.json`,
  SHA-256 `6E9ABCE4E3A5183C98609A890DF728D10D4162A275A982E237FF86C13C4DF2F3`;
- sólo se recreó `game`, imagen
  `sha256:d56959936652be60ccb27f04878397fc69e5d060f0fd679c1495bf959e203e5c`;
- rollback: `aaemu-game:rollback-pre-dusk-phase-time-v6-20260802-181331`;
- Login y MySQL conservaron sus contenedores; la compact montada conserva su
  SHA contractual.

Queda un único gate manual y no debe repetirse el cast antes de inspeccionar sus
logs: lanzar Dusk Shroud una vez, permanecer quieto y observar la zona durante
al menos diez segundos. El log esperado es `timeLeft` cercano a `7000` en el
cambio de fase y retiro de los mismos `objId` a los siete segundos.

## Swiftblade acceptance follow-up v7: retiro final y percepción de sigilo

La aceptación manual posterior a v6 volvió a conservar el prefab después de
los siete segundos. El cast vivo confirmó simultáneamente `timeLeft=6999` para
los cuatro doodads y `SCDoodadRemoved` para exactamente los mismos `objId`.
Por tanto, v6 corrigió el campo temporal pero demostró que éste no controla por
sí solo el retiro del emisor continuo.

### Retiro visual definitivo

- El handler AA8 `0x002fa800 -> 0x000f4f30 -> 0x000f3970` consume un booleano
  después del `objId`. Cuando es verdadero y el doodad efímero no conserva una
  representación asociada, ejecuta la ruta adicional `0x000f24b0` antes de
  destruir la entrada; el modo falso corresponde a una salida ordinaria de
  visibilidad/región.
- El runtime enviaba siempre `false`, incluso cuando `Doodad.Delete()` retiraba
  definitivamente un clout. Ahora `Hide()` y las transiciones regionales
  mantienen `false`, mientras que `Delete()` marca el doodad antes de retirar
  visibilidad y emite `finalRemoval=true`.
- La separación es transversal para doodads efímeros y no contiene IDs de
  skills, templates o buffs. El log de `SCDoodadRemovedPacket` expone el valor
  para validar el cliente vivo.

### Efecto hostil de Dusk Shroud

- La SQLite contractual define el clout `3826`, relación hostil `4`, radio `5`,
  buff `24906` y duración `7000`. El cast vivo creó `24906` sobre el NPC dentro
  de la zona.
- `24906` tiene `kind_id=3` (`Hidden`), por lo que no debe presentar un icono de
  debuff. Su comportamiento es el modificador nativo
  `DetectStealthRangeMul=-1000` (`unit_attribute_id=94`).
- La IA tenía dos TODO explícitos y adquiría objetivos sin consumir sigilo ni
  el atributo 94. `Unit` ahora calcula el multiplicador en la escala nativa de
  milésimas; `Npc.CanDetect` aplica los rangos frontal/trasero existentes y el
  multiplicador sólo cuando el objetivo está en stealth.
- Idle, roaming y la conservación del objetivo de combate usan la misma
  primitiva. Con `-1000`, el rango de detección de un objetivo invisible es
  cero y el NPC pierde/no adquiere al caster dentro de Dusk Shroud.
- Los buffs `24951` y `24952` permanecen condicionados a sus tags AA8 Shaken
  (`451`) y Fear (`12`); no se materializan sin esos estados.

### Validación y despliegue

- suite completa `AAEmu.Tests`: 365/365;
- pruebas focalizadas de protocolo y stealth: 7/7;
- matriz Swiftblade: 414 casos, 372 aprobados, 42 no aplicables, cero fallos;
- `quick_check=ok`, `integrity_check=ok`;
- reporte `specializations/generated/swiftblade-audit-v7-final-removal-stealth-reconstruction-report.json`,
  SHA-256 `6E9ABCE4E3A5183C98609A890DF728D10D4162A275A982E237FF86C13C4DF2F3`;
- imagen desplegada:
  `sha256:f5de7116958f360742bec49d2808c4496139c438f2fa177e8ea177189a2e1ac8`;
- rollback:
  `aaemu-game:rollback-pre-dusk-final-removal-v7-20260802-185836`;
- sólo se recreó `game`; Login, MySQL y la compact contractual se conservaron.

Gate manual v7: lanzar Dusk Shroud una sola vez sobre un NPC agresivo, entrar
en stealth dentro de la zona y esperar al menos diez segundos. Verificar que el
NPC pierde/no adquiere al caster y que el círculo desaparece. Antes de repetir,
correlacionar `buff=24906`, `timeLeft=6999` y `finalRemoval=True` en los mismos
objetos.

## Disposición Wave 0: Swiftblade con bloqueo visual aislado

La prueba manual final de v7 confirmó que el residuo de Dusk Shroud no depende
del ciclo de vida backend reconstruido:

- cast `40334` a las `23:10:35`;
- doodads `10718`, `10766`, `11860` y `12264` creados con `timeLeft=6999`;
- los cuatro retirados a las `23:10:42` con `finalRemoval=True`;
- el cliente conservó el círculo después del retiro definitivo.

Se clasifica como `presentation_blocker`: existe un controlador/emisor visual
cliente desacoplado de los cuatro doodads conocidos. El gameplay alcanzable y
el contrato de retiro permanecen activos; no se añade fallback, temporizador
inventado ni ID hardcodeada. El bloqueo queda aislado a la presentación de
Dusk Shroud y no detiene las especializaciones que no alcanzan esa ruta.

Por decisión de aceptación manual, Wave 0 avanza con este defecto conocido y
documentado. La siguiente especialización es Sorcery. Su primer gate será el
barrido de aprendizaje en cliente de las 12 activas y seis pasivas antes de
autorizar pruebas de casteo, para capturar raíces AA8 solicitadas por la UI que
puedan faltar en el cierre nativo.

## Incidente Wave 1: refresco incremental al cambiar especialización

El primer cambio vivo de Battlerage (`1`) a Sorcery (`7`) fue aceptado y dejó
el estado servidor `7/8/12`, pero la sesión mostró el primer slot como
`New Skillset`, no emitió el banner de clase y renderizó `86 ?? name_space4`.
El relog posterior cargó el personaje sin excepción, aislando el defecto al
paquete incremental y no a la persistencia.

Contrato nativo confirmado:

- cliente x64 `x2game.dll`, SHA-256
  `12229B1DC1EA8BE3453BC792586EC5A56E948CD8F6424132521F9AF7F9A53C4A`;
- handler `FUN_39310820` para el paquete `0x175`;
- serializer `FUN_399AB1C0`: `unitId` seguido de tres pares
  `old[i], new[i]`; los nombres `old` y `new` están en las cadenas nativas
  adyacentes `0x00E8ADC0` y `0x00E8ADBC`.

El backend repetía tres veces el par solicitado `1 -> 7`. Ahora captura las
instantáneas completas antes y después de cualquier cambio. Para el caso vivo
serializa `1 -> 7`, `8 -> 8`, `12 -> 12`. La implementación no contiene IDs de
skills ni excepciones de Sorcery.

Validación previa al despliegue:

- pruebas focalizadas de habilidad/protocolo: 7/7;
- suite completa `AAEmu.Tests`: 365/365;
- regresión byte a byte del payload BC y de los tres pares de slots.

Despliegue:

- imagen activa:
  `sha256:3690a81a948dcc23e0c3939ce092aff4865dd39010766846f9157362c41cef30`;
- rollback:
  `aaemu-game:rollback-pre-ability-slot-snapshot-v8-20260802-192956`;
- sólo se recreó `game`; Login y MySQL conservaron sus contenedores;
- compact montada y host:
  `BE4CB8952E24731762301F79EF977993AE7058E02AA33929A519AFE7057A4E2F`;
- `GameNetwork` 2239, `StreamNetwork` 2250 y registro en Login confirmados.

Gate manual: desde una sesión limpia, cambiar temporalmente Sorcery por otra
especialización y volver inmediatamente a Sorcery. En ambas transiciones deben
actualizarse los tres paneles, el nombre de clase y su banner sin relog. No
aprender ni lanzar skills hasta revisar ambos eventos en los logs.

## Incidente Wave 1 follow-up v9: activación inicial y reconstrucción visual

La prueba manual de Witchcraft (`2`) a Defense (`3`) demostró dos fallos
independientes. Inmediatamente después del cambio, Sorcery y Archery quedaron
visualmente en `0/12`, no apareció el banner y Defense figuró como nivel 15.
Después de volver a la selección de personaje, los skills sobrevivientes se
recuperaron, pero Defense cargó en nivel 1. El log vivo confirmó que el servidor
emitió `SCSkillsReset (0x1AB)`, `SCAbilitySwapped (0x175)` y sólo un
`SCSkillLearned (0x162)`; MySQL conservó `abilities(owner=1,id=3,exp=0)`.

### Contratos nativos recuperados

- `SCSpecialAbilityActived (0x1C2)` estaba declarado en offsets pero no tenía
  clase ni emisor en el servidor.
- Su constructor nativo está en `FUN_3933C3D0`; el serializer
  `FUN_3998AE20` escribe exactamente un byte llamado `activeAbility`.
- El handler `FUN_3935C480`, rotulado internamente
  `OnSpecialAbilityActived`, llama a `FUN_39A96040` para crear por primera vez
  la entrada de EXP como el mínimo entre la EXP del personaje y la EXP del
  nivel inicial configurado. También dispara el evento UI `0xBD`, que gobierna
  el banner observado como ausente.
- Para este cliente AA8 la UI y la tabla `levels` fijan el árbol inactivo en
  nivel 15: `total_exp=133000`. Un árbol con EXP positiva nunca se reinicializa.
- `SCAbilityExpChanged (0x211)` usa el serializer `FUN_399AAD30`: BC `unitId`,
  byte `ability`, int32 `exp` y bool `isApplyAll`. La clase existente omitía el
  booleano final aunque todavía no participaba en el swap.
- El handler de `SCAbilitySwapped` procesa los tres pares old/new. Los pares
  invariantes también limpian su lado old, por lo que el servidor debe reenviar
  los skills y pasivas sobrevivientes después de la instantánea.

### Corrección transversal

- Se implementó `SCSpecialAbilityActivedPacket` sin campos especulativos.
- Al activar un árbol cuya EXP es cero, el espejo servidor fija
  `min(characterExp, expNivel15)`; si ya tenía EXP, la conserva.
- El servidor publica primero la instantánea completa `0x175` y después envía
  `0x1C2` al propietario. El cliente sólo crea EXP cuando falta, pero siempre
  dispara `ABILITY_SET_CHANGED`, ya con los slots nuevos disponibles.
- Los árboles con EXP positiva conservan exactamente su progreso anterior.
- Después del swap se reemiten al propietario todos los `SCSkillLearned` y
  `SCBuffLearned` que sobrevivieron al reset; el skill automático del árbol
  nuevo se agrega a continuación.
- No se añadieron IDs específicos de Defense, Sorcery, Archery o Witchcraft.

### Evidencia, reparación y despliegue

- respaldo previo del personaje y sesión:
  `D:\Proyectos\AAemu\backups\ability-swap-failure-20260803-212521`;
- `dannia-abilities-skills.sql` SHA-256
  `1A6A803D623B4F6336892F0CD1B80FA97961E39BE49287414C4A4D0FA58D6CAB`;
- `dannia-character.sql` SHA-256
  `C815A57561F73B1768DFB51E62D3F72C9AFC0C89B4E02AAA0063DBC6D1893533`;
- `game-session.log` SHA-256
  `355C2F10E578C1B4E3808A27D8D0DD8D39A05CF46C6A397072B074C8D47C5277`;
- dossier serializer `0x0098AE20`:
  `x2game.dll-x64-0098ae20.json`, SHA-256
  `55CD326C10E03FBE31F379E9FFAFF0E20D7F95241935574BFB07A2295B923D23`;
- dossier handler `0x0035C480`:
  `x2game.dll-x64-0035c480.json`, SHA-256
  `698AD9DB5A82D013677BB24A4AFCE81D4903649639EC89CED3C86A6616B8808E`;
- dossier serializer `0x009AAD30`:
  `x2game.dll-x64-009aad30.json`, SHA-256
  `3F6A267B18B666E0E8C6B2B3651B1ECC09F26B5F71452CC59D8085BB65C5FE5B`;
- suite completa `AAEmu.Tests`: 368/368;
- imagen desplegada:
  `sha256:e683d6c55361c82964ed987b7b44cf185fed44245bd61a17939937b33deb3ce0`;
- rollback:
  `aaemu-game:rollback-pre-ability-swap-20260803`;
- con Game detenido, la única fila corrupta se reparó condicionalmente de
  `owner=1,id=3,exp=0` a `133000`; una fila afectada y verificación posterior
  exacta;
- sólo se recreó `game`; Login, MySQL y la compact contractual permanecieron
  intactos;
- compact host/montada SHA-256
  `BE4CB8952E24731762301F79EF977993AE7058E02AA33929A519AFE7057A4E2F`;
- `GameNetwork` 2239, `StreamNetwork` 2250 y registro en Login confirmados;
  cero reinicios y ninguna excepción fatal de arranque.

Gate manual v9: entrar con Dannia y comprobar primero, sin hacer otro cambio,
que Defense carga en nivel 15 y que Sorcery/Archery conservan sus skills. Luego
cambiar una sola vez Defense (`3`) a Witchcraft (`2`) y detenerse. Deben verse
los tres paneles completos, el banner y Witchcraft 55 sin relog. No efectuar la
transición inversa hasta correlacionar el orden de paquetes y el estado MySQL.

## Incidente Wave 1 follow-up v10: lista terminada de cambios `0x175`

La aceptación v9 confirmó que el estado y la EXP quedaron corregidos, pero
separó dos consumidores UI. Tras `Defense (3) -> Witchcraft (2)`, la ventana
Skills mostró inmediatamente `Sorcery 55 / Archery 55 / Witchcraft 55`, siete
puntos disponibles y clase `Stormcaster`; la ventana Change Skillset conservó
el tercer panel en Defense y no apareció el mensaje central. El log registró
`0x1AB -> 0x175 -> 0x1C2 -> 13 x 0x162`, y MySQL quedó exactamente en
`ability1/2/3 = 7/6/2`, Witchcraft `exp=7784000` y Defense `exp=133000`.

La causa era una interpretación incorrecta del arreglo fijo del serializer:

- `FUN_399AB1C0` siempre serializa tres pares `old/new`, pero el handler AA8
  `FUN_39392700` no los interpreta como una instantánea obligatoriamente llena.
- Para un cambio normal llama a `FUN_39600910`. Esa función recorre la lista
  mientras cada `new[i]` sea una habilidad válida y se detiene en el primer
  terminador.
- Con un solo par válido llama a `FUN_39A95D30` y, para el jugador local,
  publica el evento UI `0xBC` con `new` y `old`.
- Con dos o tres pares válidos toma la ruta masiva `FUN_39A95CA0` y no publica
  ese evento. La instantánea completa `7->7, 6->6, 3->2` actualizaba el estado,
  pero silenciaba exactamente los dos consumidores observados.
- El Lua AA8 confirma el contrato: `x2ui/abilitychange/ability_change.lua`
  ejecuta `abilityChangeFrame:Reset()` sólo con `ABILITY_CHANGED`; y
  `x2ui/centermessage/center_message_manager.lua` encola
  `ShowLearnAbilityEffect` para ese mismo evento. `ABILITY_SET_CHANGED`, emitido
  por `0x1C2`, sólo refresca la lista de combinaciones guardadas y explica por
  qué la ventana Skills sí cambió.

Corrección v10:

- `SCAbilitySwappedPacket` conserva el ancho nativo de tres pares, pero emite
  `old -> new` seguido de dos terminadores `None -> None` (`30 -> 30`).
- Se retiró `ResendLearnedToOwner`: era una compensación para la ruta masiva.
  La ruta simple sólo elimina el árbol saliente y conserva los dos árboles
  invariantes en el cliente.
- No se modificaron EXP, MySQL, opcodes, `SCSpecialAbilityActived` ni la compact.

Validación previa al despliegue:

- prueba byte a byte: `BC unitId, old, new, 30, 30, 30, 30`;
- pruebas focalizadas de habilidad/protocolo: 10/10;
- suite completa `AAEmu.Tests`: 368/368.

Gate manual v10: después del despliegue y desde una sesión limpia, cambiar una
sola vez Witchcraft (`2`) a Defense (`3`) y detenerse. La ventana Change
Skillset debe resetearse o cerrarse con Defense como tercer árbol, debe aparecer
el efecto central con la nueva combinación y Skills debe conservar Sorcery y
Archery sin reenvíos masivos ni relog.

Despliegue v10 confirmado el 2026-08-03 (America/Santiago):

- imagen activa `sha256:b9b57c48c2d5b49021ba8985d100eef2ff5dc7391f50e7687941b09222db3a40`;
- rollback previo etiquetado como
  `aaemu-game:rollback-pre-ability-swap-terminator-v10-20260803`, imagen
  `sha256:e683d6c55361c82964ed987b7b44cf185fed44245bd61a17939937b33deb3ce0`;
- sólo se recreó `aaemu8-game-1`; Login y MySQL conservaron sus contenedores y
  fechas de inicio;
- compact montada SHA-256
  `BE4CB8952E24731762301F79EF977993AE7058E02AA33929A519AFE7057A4E2F`;
- `GameNetwork` 2239, `StreamNetwork` 2250 y registro en Login confirmados;
  cero reinicios y ninguna excepción fatal de arranque.

## Wave 2 Sorcery audit v1: recuperación del catálogo pasivo

La evidencia visual y el estado vivo de Dannia separaron dos problemas. El
personaje conservaba diez skills activos de Sorcery, dos de Archery y uno de
Witchcraft, pero no tenía ninguna fila pasiva persistida. Tampoco aparecían
`CSLearnBuffPacket` ni `CSLearnSkillPacket` al intentar aprender las entradas
bloqueadas, por lo que la negativa ocurría antes de alcanzar el servidor.

La compact activa `compact-8.0-runtime-transversal-swiftblade-audit-v4` tenía
los diez roots visibles de Sorcery y cero filas `passive_buffs` para
`ability_id=7`. La causa era de composición: el constructor transversal
conserva las pasivas a nivel de habilidad sólo para habilidades totalmente
habilitadas, mientras que la capa específica reinsertaba únicamente las seis
pasivas de Swiftblade. Al reutilizar esa compact para auditar Sorcery, el
cliente recibía 0/6 plantillas pasivas aun cuando sus buffs de respaldo ya
existían.

Clausura nativa Sorcery AA8:

- ability `7`;
- 40 roots totales, 36 habilitados, 10 visibles y 6 pasivas nativas;
- plantillas pasivas `15, 38, 99, 257, 258, 301`;
- buffs de respaldo `536, 962, 963, 2910, 7566, 7567`;
- umbrales nativos de puntos `3, 5, 4, 6, 8, 7`;
- cuatro roots permanecen en cuarentena: `11939, 36477, 36478, 39674`;
- los cuatro dependen de `ResetAoeDiminishingEffect`. El cliente demuestra el
  descriptor y el multiplicador, pero no expone el estado backend que debe
  reiniciarse; no se inventó esa semántica ni se levantó la cuarentena.

Artefactos y validación:

- runtime:
  `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-audit-v1.sqlite3`;
- SHA-256 runtime:
  `780D08ECD6A3FB8294EC7B9305C6ADC9AFF558D951F83FF96FE928D48DD0195F`;
- manifest:
  `specializations/generated/sorcery-audit-v1.manifest.json`;
- SHA-256 manifest:
  `171D474255E14DB8D732D71D2AD8C74BEBA17EBA69C03A9C845ACB4FDDBBC60E`;
- dos builds deterministas byte a byte con el mismo SHA-256;
- `quick_check=ok`, `integrity_check=ok`;
- cero `skill_effects` de los roots en cuarentena en la salida;
- pruebas focalizadas Python/artefactos: 21/21;
- suite completa `AAEmu.Tests`: 368/368.

Despliegue Sorcery v1 confirmado el 2026-08-03 (America/Santiago):

- imagen activa conservada:
  `sha256:b9b57c48c2d5b49021ba8985d100eef2ff5dc7391f50e7687941b09222db3a40`;
- rollback etiquetado como
  `aaemu-game:rollback-pre-sorcery-audit-v1-20260803`, misma imagen;
- sólo se recreó `aaemu8-game-1`; Login y MySQL conservaron IDs y fechas de
  inicio;
- compact montada SHA-256
  `780D08ECD6A3FB8294EC7B9305C6ADC9AFF558D951F83FF96FE928D48DD0195F`;
- scripts compilados con 0 errores y 8 warnings históricos;
- `GameNetwork` 2239, `StreamNetwork` 2250 y registro en Login confirmados;
  cero reinicios y ninguna excepción fatal de arranque.

Esta Wave recupera el catálogo pasivo que faltaba y habilita una prueba
controlada. No declara todavía reparados todos los casts de Sorcery ni promueve
los cuatro roots bloqueados.

Gate manual Sorcery v1: iniciar una sesión limpia con Dannia, abrir Sorcery y
aprender solamente la primera pasiva de umbral 3 (plantilla `15`, buff `536`).
Detenerse inmediatamente: no aprender otra pasiva y no lanzar ningún skill.
El resultado esperado es `CSLearnBuff 0x016`, `SCBuffLearned 0x1F3`, una fila
MySQL `id=15,type=Buff` y actualización inmediata sin relog. Después se debe
correlacionar cliente, log y MySQL antes de continuar con las demás pasivas o
con los activos.

### Aceptación manual Sorcery v1 — pasiva de umbral 3

El gate se cerró completamente con Dannia:

- al aprender la plantilla pasiva `15`, el servidor recibió
  `CSLearnBuff 0x016` y respondió `SCBuffLearned 0x1F3` a las `02:54:08`;
- el cliente activó inmediatamente el efecto visible de mayor maná del buff
  de respaldo `536`;
- la salida limpia produjo `CSLeaveWorld 0x02C`,
  `SCPrepareLeaveWorld 0x0D1` y `SCLeaveWorldGranted 0x1FF`;
- MySQL persistió exactamente `id=15, level=1, type=Buff, owner=1`, con una
  sola pasiva y sin duplicados;
- en el relog se emitió el nuevo `SCUnitState 0x15C`, no hubo
  `Skipped invalid persisted passive` ni rechazo de plantilla;
- el cliente conservó la pasiva aprendida y reaplicó correctamente el aumento
  de maná después de volver al mundo.

Queda confirmado el ciclo `learn -> apply -> save -> load -> reapply` para la
primera pasiva Sorcery. Las cinco pasivas restantes y los activos continúan
bajo gates individuales; este resultado no levanta la cuarentena de los roots
`11939, 36477, 36478, 39674`.

### Aceptación manual Sorcery v1 — catálogo pasivo completo

Las cinco plantillas restantes se aprendieron en la misma sesión. La captura
viva registró exactamente cinco `CSLearnBuff 0x016` y cinco
`SCBuffLearned 0x1F3`, sin `Rejected unknown passive`, sin dependencia de buff
ausente y sin respuestas faltantes.

MySQL persistió las seis filas esperadas, todas con `level=1`, `type=Buff` y
`owner=1`, sin duplicados: `15, 38, 99, 257, 258, 301`. Una segunda salida
limpia produjo `CSLeaveWorld 0x02C` y `SCLeaveWorldGranted 0x1FF`; el relog
posterior emitió un nuevo `SCUnitState 0x15C` para Dannia y no registró
`Skipped invalid persisted passive` ni rechazo de plantilla. El usuario
confirmó que las seis continuaron aprendidas y que sus efectos se conservaron.

El catálogo pasivo de Sorcery queda aceptado como conjunto para
`learn -> apply -> save -> load -> reapply`. La siguiente frontera es el mapa
de activos; los roots `11939, 36477, 36478, 39674` continúan explícitamente en
cuarentena hasta reconstruir `ResetAoeDiminishingEffect` con evidencia backend.

### Baseline de activos Sorcery v1

El catálogo AA8 contiene diez roots base visibles. Nueve están habilitados:
`10664, 10667, 10752, 11314, 12796, 14774, 10670, 11967, 23593`. Fire Rain
`11939` permanece en cuarentena. Entre las variantes no visibles también están
en cuarentena `36477, 36478, 39674`; los cuatro casos alcanzan
`ResetAoeDiminishingEffect`, cuyo `Apply` backend sigue siendo no-op.

La captura viva previa a los gates individuales clasificó:

- `10667`: `SCSkillStarted result=Success`, `SCSkillFired` y buff objetivo
  `247`;
- `10752`: ejecutó su cadena `10752 -> 24894 -> 24895`, creó buffs `1403` y
  `2287`; los `result=CooldownTime` posteriores corresponden a repetición
  rápida y recibieron respuesta nativa para liberar el estado pendiente;
- `12796`: creó el buff propio `19037`, pero alcanzó
  `CombatResourceEffect 466` y registró que el recurso nativo `8` aún no está
  implementado; queda `partial`, no aceptado;
- `14774`: hay solicitud viva, pero todavía no evidencia suficiente de cierre
  de efecto;
- `11939`: tres intentos rechazados explícitamente por la cuarentena nativa,
  sin ejecutar un cierre incompleto.

Los roots restantes no se declaran funcionales por presencia de fila. Deben
probarse de uno en uno, correlacionando start/fire/end, efectos, daño/buffs,
presentación y cooldown. La investigación de `CombatResourceEffect` recurso
`8` y `ResetAoeDiminishingEffect` queda separada de los roots ya ejecutables.

## Wave 2 Sorcery native runtime v2: roots omitidos y escudo

La prueba viva de aprendizaje aportó evidencia que la extracción estática no
tenía: el cliente AA8 envió `CSLearnSkill` para `10153` y `10151`, y el servidor
rechazó ambos como desconocidos. Esto confirma identidad y alcanzabilidad de
los roots, pero no convierte propiedades 10.x en autoridad de balance AA8.

El crosswalk r575 clasifica ambos roots como `aa10_only`. Se usaron únicamente
como candidatos de fila raíz, mientras que todo el cierre ejecutable se repuso
desde la consolidada AA8: efectos `271,272,44888` para `10151`, efectos
`53089,65323` para `10153`, plot nativo `3096` y buff de absorción `95`. Los
cinco descriptores relacionados son `exact_id_exact_relation` en el crosswalk.
No se preservaron valores de gameplay de la compact histórica.

Se implementó y registró un backend candidato de `ExtendChargeEffect`,
incluyendo flags AA8 de carga fija, nivel, DPS, armas, porcentaje y salud.
Modern/10.x conservan `Apply` como TODO, de modo que su fórmula continúa en
estado semántico pendiente hasta el gate vivo. El recurso nativo Sorcery `8` y
su grupo `7` quedaron materializados, pero su paquete de sincronización
permanece bloqueado hasta recuperar opcode/layout AA8 exactos; no se portó
protocolo Modern. Fire Rain `11939` y variantes continúan en cuarentena por
`ResetAoeDiminishingEffect`.

Validación y despliegue:

- runtime `compact-8.0-runtime-transversal-sorcery-v2.sqlite3`, SHA-256
  `8D98CE42BC8A8835D012F1FE867D4B19CAF7795C6DB508B6EAF99AC421C173F5`;
- `quick_check=ok`, `integrity_check=ok`;
- pruebas C# 371/371, Sorcery 6/6, artefactos 12/12 y grafos 5/5;
- imagen activa
  `sha256:8bbaacec710c1c5faab2356936d9d4f953bd5dfd6050e418ec7d24284f96a72d`;
- rollback `aaemu-game:rollback-pre-sorcery-v2-20260804`;
- sólo se recreó Game; Login y MySQL se conservaron;
- puertos 2239/2250, registro en Login y cero reinicios confirmados.

Gate manual v2: aprender primero Freezing Earth `10151` e Insulating Lens
`10153`. Probarlas una por una, verificar AoE/daño/buffs/cooldown para la
primera y buff `95`/absorción/cooldown final para la segunda. Salir y volver a
entrar para confirmar persistencia. No probar Fire Rain todavía.
