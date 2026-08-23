# Checkpoint nativo — cadena racial Nuia AA10 r575 v1

Fecha del corte: 2026-08-21. Rama objetivo: `Wingsjuankaa/AAEmu:rama_10`.

## Alcance y autoridad

Este corte audita la historia racial Nuia definida por `quest_contexts.category_id=3`,
`race=1`, capítulos 0–6: **55 quests, 344 actos habilitados y 18 tipos de acto**.
AA8 se usó sólo como índice comparativo de incidentes. Todas las decisiones se volvieron a
probar contra AA10 Returns 10.0.2.13 r575:

- `game_decrypted.sqlite3`: `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`.
- compact retail: `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849`.
- `x2game.dll`: `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.
- `game_pak`: `AB3B86E694CFC0141453AD9B734BABEE67019C58D8E0B52498036ABC0DCBCBF0`.

El Stage 40 estricto generado en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\quest-stage40\nuia-racial-audit-20260821`
cerró con `status=pass`: 43.737/43.737 referencias habilitadas implementadas,
43.696 referencias cargables en runtime, 55/55 quests Nuia, 344/344 actos Nuia y cero actos
Nuia no soportados. Esto prueba cobertura de datos/runtime; la prueba jugable sigue siendo la
autoridad final para materialización, diálogo y secuencia visual.

## Hallazgo que reproduce el incidente AA8

`Divine Intervention` (quest 2256) no espera cualquiera de los cadáveres decorativos NPC
`11544`. Su Ready usa `QuestActConReportDoodad` sobre el `client_doodad 14073`, modelo
`npctype://10646`. Ese actor no existía en el catálogo de spawns AA10, por lo que el cliente
marcaba la posición pero no había objeto servidor con el cual completar la interacción.

El mismo doodad encadena dos estados personales:

- grupo `41492`: reporta 2256 y ofrece 2257;
- grupo `41493`: `DoodadFuncUse` con skill `41925` para el objetivo de interacción de 2257;
- `once_one_man=true`: la fase de 2257 debe resolverse por personaje, sin mover el cadáver para
  todos los jugadores.

## Catálogo nativo reconstruido desde el game_pak AA10

La herramienta read-only `reconstruccion_cliente_10/tools/PakDoodadScan` abre el paquete una vez,
analiza los `main_world/level_design/cells/*/doodad.g` y convierte coordenadas de celda y cuaternión
a posición mundial/yaw. No escribe el cliente ni las bases fuente.

| doodad | actor | X | Y | Z | yaw | fase inicial |
|---:|---|---:|---:|---:|---:|---:|
| 14073 | Bloodhand Corpse | 14918.901 | 14715.250 | 145.790 | -71 | 41492 |
| 14074 | Marian | 15036.458 | 14739.861 | 150.425 | 179 | 41496 |
| 14109 | Marian | 12322.548 | 13975.236 | 131.104 | 111 | 41537 |
| 14114 | Departing Marian | 11760.374 | 12959.033 | 140.023 | -43 | 41557 |
| 14118 | Guard Captain Dalia | 11760.203 | 12961.994 | 140.103 | -115 | 41555 |
| 14120 | Ghost Scott | 10695.821 | 11898.747 | 126.692 | -91 | 41562 |
| 14121 | Fallen Marian | 12381.982 | 12166.577 | 122.691 | -65 | 41567 |
| 14122 | Malcolm | 12384.027 | 12166.247 | 122.691 | 84 | 41568 |
| 14124 | Lucius Quinto | 12272.270 | 12123.518 | 140.817 | -174 | 41574 |
| 14125 | Standing Marian | 12271.310 | 12121.333 | 140.818 | -45 | 41603 |
| 14134 | Deceased Scott | 14282.768 | 14921.494 | 122.227 | -63 | 41592 |

Las fases se fijan explícitamente y se validan contra los grupos del template antes de iniciar el
doodad. Esto evita dos selecciones incorrectas del heurístico anterior: 14073 debía arrancar en
`41492`, no en el primer Normal `41493`, y 14125 debe arrancar en la fase interactiva `41603`, no
en el primer modelo NPC `41577`.

## Crosswalk de reparaciones AA8 → AA10

| familia observada en AA8 | decisión AA10 r575 |
|---|---|
| Índice global/SCFilter de quests | No portado: el contrato AA10 ya estaba resuelto y el opcode/layout AA8 no es compatible. |
| Proxy `client_doodad` con modelo `npctype://` | Extendido al catálogo completo de 11 actores Nuia con coordenadas y fase r575. |
| Quest 2256, cadáver lógico ausente | Cerrado con doodad 14073/fase 41492; NPC 11544 permanece sólo decorativo. |
| Quest 2257, fase `once_one_man` global | Añadida resolución local desde el objetivo activo; sólo ejecuta fases sin phase-functions y no muta la fase compartida. |
| Quest 2257, `GainLootPackItemEffect` sin item caster | AA10 ya permite caster no-item cuando `consume_source_item=false` y `consume_count=0`; la fila r575 4165 cumple ese contrato. |
| Skills de interacción que se relanzan a sí mismas | `DoodadFuncUse` ya no agenda la misma skill que lo activó; cubre 41925 y la interacción 41999 de 14125. |
| Skill-object de interacción desconocido | Captura AA10 viva: `CSStartSkill` recibió flag 28 y dejó exactamente 8 bytes sin consumir. Se implementó type 28 como dos `u32` opacos antes de `inputDirection`; Started/Fired ahora reenvían también ese cuerpo completo. |
| Supply items de 2255/2258/2259/2260 | No se copió el parche AA8: Stage 40 AA10 reporta cero productores faltantes y la ruta AA10 existente conserva suministro/reintento idempotente. |
| Selección de report doodad/reward y diálogo de 2532 | Ya cerrada en AA10 y confirmada durante la prueba anterior; no se duplicó lógica AA8. |
| Talk objective (por ejemplo 2486) | El paquete AA10 conserva npcObjId, quest, component y act y publica el evento explícito; no depende de `CurrentTarget`. |
| Quest 3993 con varios Progress | El motor AA10 nuevo evalúa todas las components activas y los objetivos se serializan hasta 10; no se portó el reconciliador del motor legado AA8. |
| Quest 4411 / doodad 14125 | Fase inicial explícita 41603 más guardia anti-recursión de skill 41999. |

## Cambios y garantías

- `DoodadSpawner` acepta el `FuncGroupId` del placement, valida pertenencia al template y lo fija
  antes de `InitDoodad`.
- El catálogo `doodad_spawns_aa10_client_quest_proxies.json` contiene los actores
  lógicos usados por la cadena Nuia auditada.
- La fase personal sólo se habilita para templates `once_one_man`, quests activas en Progress y
  fases sin funciones de fase. Cualquier caso más complejo falla cerrado.
- Type 28 consume y reenvía el cuerpo completo en CS/SC sin inventar semántica para sus dos valores.
- No se aceptan cuerpos NPC decorativos como reemplazo genérico de un doodad objetivo.

## Validación automática y aceptación manual

- Build Game: correcto, 0 errores.
- Unitarias: **1477/1477**, 0 errores.
- Stage 40 strict: pass, 55/55 quests Nuia, 344/344 actos, 0 no soportados.
- Tests nuevos: catálogo/fases, validación de fase inicial, fase `once_one_man`, anti-recursión y
  wire type 28 de 10 bytes incluyendo `inputDirection`.

El 2026-08-21 el usuario completó de punta a punta los **Capítulos 1–6 Nuia** con un personaje de
prueba. El capítulo 1 se recorrió después de validar las correcciones dinámicas de los actores
lógicos, las interacciones personales y el traslado a Lacton; el capítulo 2 se completó a
continuación y el recorrido prosiguió hasta cerrar el capítulo 6. Esto cierra la aceptación
jugable de la cadena auditada 0–6, salvo las regresiones transversales documentadas por separado
y su repetición específica después de cada despliegue. Zone y cliente permanecieron bajo control
del usuario.

## Despliegue Game

El 2026-08-21 se reconstruyó y desplegó únicamente el servicio `game`; no se operaron Zone ni el
cliente. La imagen activa `aaemu-world:10.0.2.13-r575-local` quedó en
`sha256:5504b067a5a79fa5f31f5ddf976f53691ac8a75a2c911d3b23aa6611519b51b4`, con DLL desplegada
`84de6062a11c8c0f684b8c0a33cfd8eed67146e94c722ff0d3c0f1687c35e92c`.

El catálogo fuente y su bind mount de runtime se sincronizaron con las mismas 11 filas antes del
reinicio final. Game cargó 8901 quests, pasó el coverage gate estricto con 43.696 actos y cero
hallazgos, abrió 1239/1250 y se registró correctamente en Login. La imagen previa permanece como
rollback recuperable en `aaemu-world:10.0.2.13-r575-local-rollback-20260821-103339`; el rollback
anterior `aaemu-world:10.0.2.13-r575-local-rollback-20260821-091038` también se conserva.

## Extensión: quest 3503 y Lacton Memory Tome

La aceptación manual alcanzó `Ahead of the Hunter` (3503). El item `Lacton Memory Tome` 47877
ejecutó la skill 42067 y Game confirmó tanto el consumo como `QuestActObjItemUse` 983, pero el
personaje no se movió. La traza viva de las 14:22:15–14:22:16 cerró la causa:

- skill 42067 disparó `SpecialEffect Return`, type 25, con `value1=18`;
- `Return` buscó 18 sólo en `worldgates.json` y registró `Need to add information`;
- el destino r575 ya estaba presente en `recalls.json`: return point 18, Lacton, Zone 142,
  SubZone 338, `(13594, 14536, 109)`, yaw 75;
- la Zone de Lacton estaba activa, pero Game nunca emitió el teleport porque el resolvedor devolvió
  `null` antes de producir los paquetes de movimiento.

Se añadió `PortalManager.GetReturnDestinationById`: conserva prioridad de worldgate para los tres
IDs que se solapan entre catálogos y, si no existe worldgate, cae al return point normal. El mismo
resolvedor se usa en la validación previa de `Skill` y en la ejecución de `Return`; no hay branches
por quest, item o skill. El comparador AA8 retenía la misma suposición incompleta y se clasificó
como `structural_candidate`, no como autoridad.

La cadena racial Nuia 0–6 contiene un único item suministrado cuyo use-skill ejecuta Return:
3503 → 47877 → 42067 → return point 18. Por tanto, esta corrección cierra todos los teleports por
item de esa cadena. La aceptación dinámica se completó el 2026-08-21: el usuario reobtuvo y usó el
tomo con la Zone 142 activa, confirmó la llegada a Lacton y posteriormente terminó el Capítulo 1
Nuia.

La extensión cerró con build Release sin errores y **1479/1479** pruebas unitarias en Debug y
Release. Game cargó 111 recalls y 24 worldgates, volvió a pasar el coverage gate estricto con
43.696 actos y cero hallazgos, abrió 1239/1250 y se registró en Login.

## Extensión: casteo visual de interacciones type 28

Después de completar el Capítulo 2, el usuario reportó que las interacciones con objetos de quest
respetaban la espera y completaban el objetivo, pero no mostraban barra ni animación de casteo.
Los logs vivos del 2026-08-21 confirmaron varias solicitudes `CSStartSkill` con flag 28; la skill
11629 observada a las 15:48:35 tiene `casting_time=3000`, `start_anim_id=59` y `fire_anim_id=48` en
la SQLite AA10. Por tanto, el tiempo y las animaciones sí estaban authored.

La causa era una asimetría del wire: `CSStartSkill` ya consumía los dos `u32` de type 28, pero
`WriteSkillCastExtra` anunciaba el mismo tipo en `SCSkillStarted`/`SCSkillFired` sin escribir sus
ocho bytes. El cliente consumía `inputDirection` y los tiempos como parte del objeto opaco y
descartaba el timeline visual, mientras Game continuaba su `CastTask` y aplicaba el efecto al
final. El helper común ahora reenvía ambos valores antes de `inputDirection`; no se añadió ningún
casteo sintético ni un tiempo especial por quest.

La regresión serializa la interacción real de 3000 ms y demuestra type 28 + dos `u32` +
`inputDirection` + tiempos `300/300` alineados. Build Release cerró con 0 errores, la prueba focal
con 2/2 y la suite completa con **1480/1480**. La aceptación dinámica pendiente es repetir una
interacción type 28 con tiempo de casteo y confirmar barra/animación antes de continuar el
Capítulo 3.

Se reconstruyó y desplegó únicamente `game`. La imagen activa quedó en
`sha256:714696e249a1cbf674fe4308c9606b9be2905b90b5f21e61b8e77b114bdfa692`, con DLL Game
`23527f505feee0c335419b96f18ff8f0f9b7c2f90d0bdd35ca73b1e2ea6e53c7`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260821-115418` ->
`sha256:5504b067a5a79fa5f31f5ddf976f53691ac8a75a2c911d3b23aa6611519b51b4`. Game quedó healthy,
pasó Strict con 43.696 actos y cero hallazgos, cargó 8.901 quests, abrió 1239/1240/1250 y se
registró en Login. No se inició, detuvo ni relanzó ninguna Zone y no se controló el cliente.

## Extensión: cierre de Zone al materializar a Lucius en quest 4409

El 2026-08-21 la quest 4409 reprodujo dos veces un cierre aislado de la Zone 149. La skill 17844
publicó `SpawnAllOnceAndDeactivate` para el spawner 68410, Zone encontró el placement y emitió
`ZWSpawnNpc` para Lucius, template 10564/spawner type 11727. En la segunda captura el diálogo y el
objetivo `ObjTalk` llegaron a completarse antes de que la conexión de esa Zone desapareciera entre
ocho y nueve segundos después. Por tanto, ni las coordenadas, ni `npc_spawners.g`, ni la máquina de
estados de la quest explicaban el cierre.

La prueba nativa se cerró en el proyecto Ghidra AA10 Zone, programa
`x2game-dev_dedicate.dll` SHA-256
`8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A`:

- `FUN_3938e0e0` serializa `ZWSpawnNpc`: cabecera/placement, unión `BaseUnit` del creador, dos
  strings, faction, `NpcSpawnReason`, flags, `lifeTime` e `isFactionPermission`;
- `FUN_393700b0` deserializa `WZNpcState` con otro orden: cabecera, unión del creador, flags,
  `lifeTime`, reason, UnitState y group;
- ambos usan `FUN_39387ca0` para la misma unión de identidad;
- el cuerpo observado de 78 bytes ya contenía los 17 bytes de identidad Character, reason
  default, `despawnOnCreatorDeath=true`, `useSummonerAggroTarget=true` y `lifeTime=60`.

`ZwSpawnNpcParser` sólo consumía la cabecera y posición y trataba la cola como padding. Luego
`NpcSpawnRelay` reconstruía el ack con creador cero, ambos flags falsos y vida cero. La reparación
es transversal: el parser preserva por separado las uniones nativas de creador/reason y los tres
campos de lifecycle, y `WorldIntegration` los reordena al formar `WZNpcState`. No existe branch por
quest, NPC o spawner; creators no probados fallan cerrados y conservan el fallback anterior.

La regresión cubre exactamente 68410/11727/10564, identidad Character no cero, 60 segundos, ambos
flags, reason variable después de nombres y rechazo cerrado de una unión no demostrada. Restore y
build Release cerraron sin errores; focal 4/4 y suite completa **1484/1484**. La aceptación dinámica
pendiente es repetir 4409 desde el doodad 14121 y comprobar que Lucius aparece, permite completar
el diálogo y la Zone 149 continúa conectada después de al menos 60 segundos.

Se reconstruyó y desplegó únicamente `game`. La imagen activa quedó en
`sha256:630c67920acd03f96271999decdf15781a924b3fc9e9ade1dea65c4b548731c6`, con DLL World
`ca9813a42b97beec2977cb354a951334517b95d7588eebe315c41fa0950d2d91` y DLL Game
`f64734f823a78d4dda6dfffb2d03eed1e26c6e7307f9f4e3b01ffbb5f99e85ce`. El rollback es
`aaemu-world:10.0.2.13-r575-local-rollback-20260821-142053` ->
`sha256:714696e249a1cbf674fe4308c9606b9be2905b90b5f21e61b8e77b114bdfa692`.
Game quedó healthy sin reinicios, Strict 43.696/0, 8.901 quests, puertos 1239/1240/1250 y registro
correcto en Login. No se inició, detuvo ni relanzó ninguna Zone y no se controló el cliente.

## Extensión: marcador de mapa tras teletransporte `Return`

Al completar el capítulo 6, el usuario confirmó un defecto repetido en los dos traslados por item
de quest: el personaje llegaba y persistía en el destino correcto, pero su marcador desaparecía
del mapa hasta reloguear. La traza viva de quest 4410 cerró la divergencia a las 18:32:22:

- skill 17848 ejecutó `Return value1=406` hacia worldgate 406, Zone 149, `(12279.8,12112.6,140.2)`;
- Game emitió `SCLoadInstance(instanceId=1, zoneId=149, ...)`, pero construyó el nuevo
  `Transform` con `InstanceId=0`;
- el `main_world` AA10 está creado explícitamente con `WorldManager.DefaultInstanceId=0`;
- AA10 respondió primero `CSTeleportEnded (0,0,0)`, rechazado, y luego confirmó la coordenada
  correcta; el relog reconstruía el contexto con instancia 0 y devolvía el marcador.

El literal heredado `1` fue reemplazado por una única variable
`WorldManager.DefaultInstanceId`, usada tanto en `SCLoadInstance` como en el `Transform` de
destino. Es una corrección general de `SpecialEffect Return`: no contiene ramas por quest, skill,
item o portal y cubre tanto el Lacton Memory Tome como worldgates posteriores. AA8 sólo aportó la
pista estructural de una desincronización de teleport; la causa y el valor se probaron con runtime
y modelo de instancias AA10.

Las regresiones fijan el orden wire `instanceId=0 -> zoneId=149 -> posición` y prohíben que
`Return` vuelva a declarar el literal de instancia 1. Restore y build Release cerraron sin errores;
pruebas focales **2/2** y suite completa **1486/1486**. La aceptación dinámica pendiente es
repetir un `Return` por item y verificar que el marcador continúa visible sin relog.

Se reconstruyó y desplegó únicamente `game`. La imagen activa quedó en
`sha256:e51f027b29d9ae0396c1bf32ac609e61ec272ad9aa5f9dd2b49edcab7fc18971`, con DLL Game
`22f74cdc7ea6ec9620bf4fe911850937430bc3888d4277995b9ba4a157d43aa5` y DLL World
`ca9813a42b97beec2977cb354a951334517b95d7588eebe315c41fa0950d2d91`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260821-144650` ->
`sha256:630c67920acd03f96271999decdf15781a924b3fc9e9ade1dea65c4b548731c6`.
Game quedó healthy sin reinicios, Strict 43.696/0, 8.901 quests, puertos 1239/1240/1250 y registro
correcto en Login. No se inició, detuvo ni relanzó ninguna Zone y no se controló el cliente.

## Extensión: Cinderstone Teleport Scroll de quest 7115

Al comenzar el capítulo 7, el usuario recibió el `Cinderstone Teleport Scroll` 47879 en
`Your Legend Continues` (7115). El item casteó la skill 42069 y completó
`QuestActObjItemUse` 985, pero no trasladó al personaje. La traza viva de las 19:02:37–19:02:38
cerró la causa: `SpecialEffect Return` pidió `value1=999` y el resolvedor no encontró ese ID en
`worldgates.json` ni en `recalls.json`.

La clausura se reconstruyó sólo con AA10 r575:

- `return_points[999]` identifica `quest7115` y el campamento Burnt Castle Watch Camp;
- quest 7115 suministra 47879, cuyo use-skill 42069 ejecuta Return 999, y luego pide hablar con
  NPC 15558;
- la Zone r575 emitió el spawner 144295/type 17455/NPC 15558 en partition 148, posición local
  `(1047,1040,175.667)` y `zRot=2.79253`;
- el archivo nativo `zone/148/zone_server/npc_spawners.g`, SHA-256
  `0859D697423A61565650B6FF5E98BCF3456927FFEC29401789B40C92CC29B0C8`, conserva esos valores
  exactos; con el offset de celda resultan `(14359,11280,175.667)`, yaw 160 grados.

Se añadió el worldgate 999 con `ZoneId=148` y esa posición. No existe branch por quest o item:
continúa usándose el resolvedor genérico de Return. La auditoría inicial de
`QuestActObjItemUse` limitada a quests `race=1` encontró las rutas 3503/47877/42067/18 y
7115/47879/42069/999. Esa consulta sólo es válida para los capítulos cubiertos hasta ese punto;
las continuaciones compartidas de la historia pasan a `race=255` y requieren seguimiento por
categoría/cadena, como quedó demostrado posteriormente por quest 7148.

El catálogo fuente y su bind mount runtime quedaron idénticos, SHA-256
`52376471D2C43E1D4731E5772C3469FBFCC372E8E78FF85E5DF2862EAA4681E4`. Restore y build Release
cerraron con cero errores; pruebas focales 4/4 y suite completa **1487/1487**. La aceptación
manual pendiente es reobtener el item de 7115, usarlo y verificar simultáneamente llegada al
campamento y marcador de jugador visible sin relog, cerrando también la regresión anterior de
instancia de mapa.

Se desplegó únicamente `game` con ambos compose AA10. La imagen activa quedó en
`sha256:9ea6a9975b5a70a95f1cda9fb59e32563eb0dc8d85a6133887394d8badb2b64f`, DLL Game
`22f74cdc7ea6ec9620bf4fe911850937430bc3888d4277995b9ba4a157d43aa5` y DLL World
`ca9813a42b97beec2977cb354a951334517b95d7588eebe315c41fa0950d2d91`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260821-151507` ->
`sha256:e51f027b29d9ae0396c1bf32ac609e61ec272ad9aa5f9dd2b49edcab7fc18971`. Game quedó healthy,
sin reinicios, cargó 25 worldgates/111 recalls, Strict 43.696/0, 8.901 quests, abrió
1239/1240/1250 y se registró en Login. El lifecycle de Zones y el cliente permanecieron bajo
control del usuario.

## Extensión: continuidad Nuia desde capítulo 8

El 2026-08-21 el usuario llegó a `The Traitor in the Tower` y activó la esfera 2871 en la torre
al norte de Howling Abyss. La cinemática se reprodujo y la misión desapareció, pero no apareció
un actor que ofreciera el siguiente paso. La SQLite AA10 prueba que este primer efecto es
correcto: quest 7129 ejecuta `QuestActConAutoComplete` 3392 después de la esfera, mientras la
siguiente quest 7130 sólo se acepta mediante `QuestActConAcceptDoodad` 846 sobre el actor lógico
14237. No corresponde reinyectar 7129 ni convertir el final en una entrega NPC.

AA8 ya clasificaba 14237–14246 y 14309 como el bloque de `client_doodad` que sostiene la cadena
7130–7148. Esa clasificación se usó solamente como pista de alcance. Identidad, modelos, enlaces
de quest, fases y ubicaciones fueron revalidados contra `game_decrypted.sqlite3` y los
`main_world/level_design/cells/*/doodad.g` del `game_pak` AA10 r575:

| doodad | actor | X | Y | Z | yaw | fase inicial | enlace inicial |
|---:|---|---:|---:|---:|---:|---:|---|
| 14237 | Eldris | 7804.000 | 10336.000 | 262.000 | 180 | 41846 | accept 7130 |
| 14239 | Eldris | 7984.048 | 9041.542 | 193.584 | -110 | 41856 | report 7132 / accept 7133 |
| 14240 | Kona's Corpse | 8916.000 | 8171.000 | 154.000 | 140 | 41859 | accept 7134 |
| 14241 | Eldris | 8905.840 | 8289.174 | 154.502 | -80 | 41861 | report 7134 / accept 7135 |
| 14242 | Eldris | 10999.000 | 9500.000 | 166.000 | 0 | 41863 | report 7137 / accept 7138 |
| 14243 | Eldris | 26858.542 | 9038.822 | 773.438 | 20 | 41865 | report 7138 / accept 7139 |
| 14244 | Eldris | 23865.000 | 7174.000 | 373.997 | 0 | 41867 | report 7139 / accept 7140 |
| 14245 | Eldris | 9724.452 | 17200.412 | 128.562 | 20 | 41869 | report 7146 / accept/report 7147 / accept 7148 |
| 14246 | Aril | 9694.577 | 17362.141 | 137.889 | 5 | 41871 | use skill 29817 |
| 14309 | Kidnapped Child | 29944.830 | 8734.583 | 522.027 | -50 | 41989 | use skill 29806 -> phase 41990 |

Los diez placements se añadieron al catálogo genérico ya existente con `FuncGroupId` explícito.
No se agregó lógica por quest ni se alteró la base retail. La regresión del catálogo exige ahora
los 21 actores Nuia, sus fases exactas y las posiciones r575 del bloque posterior al capítulo 7.
La aceptación dinámica pendiente comienza en 14237: después de cargar el despliegue debe aparecer
Eldris en `(7804,10336,262)` y ofrecer 7130 sin repetir 7129.

Build integral Release cerró con 0 errores; prueba focal 1/1 y suite completa **1500/1500**.
Catálogo fuente y bind mount quedaron idénticos, SHA-256
`61377160202549C4D7B37CC27F88ACBE68560A1392BC5BE6F7693EEA0EB4AEF5`. Se desplegó únicamente
Game con imagen `sha256:69fcdba620e7cb6f168caf4021f3371f01d41add1511e957e62affdf7a4b7790`,
DLL Game `b3503e484671edcf08fd1b9812632c432ec57cacc381e274abe12acf7d034325` y DLL World
`cdedc9577531e98fa7d0703b282d18e83680cc9b198981c8899d41afd9168003`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260821-215807` ->
`sha256:7bfb97b28053b6d99d76af9fe1e22a3bd27ce9a8959d8b5ba4144d5224650fef`.
Game quedó healthy, sin reinicios, Strict 43.696/0, cargó 8.901 quests, abrió
1239/1240/1250 y se registró en Login. No se inició, detuvo ni relanzó ninguna Zone y no se
controló el cliente.

## Extensión: marcadores sobre mobs objetivo de quest

Durante `A Dangerous Antidote` (7131) el progreso y el loot funcionaban, pero los mobs válidos no
mostraban el marcador de objetivo sobre el nameplate. La relación retail AA10 quedó cerrada sin
inferencias ni listas manuales: el item `Blackroot Fragment` 37887 declara `loot_quest_id=7131`, y
los loot packs asociados apuntan a los NPC 9216, 9217 y 9218 (Rafflesia, Saracenia y Spotted
Flytrap). El cliente r575 carga esa relación con su consulta nativa
`items.loot_quest_id -> loots.loot_pack_id -> loot_pack_dropping_npcs.npc_id`.

La primera reconstrucción probó que `SCQuestNotifierInit` (`0x287`) serializa un booleano y que su
callback despacha el evento interno de UI `0x2A4`. Se añadió el productor después de `SCQuests` y
`SCCompletedQuests` durante la selección de personaje. Build integral Release cerró con cero
errores; pruebas focales **4/4**, suite completa **1501/1501** y Stage 40 **8/8**. Se desplegó
únicamente Game con imagen
`sha256:fe6bc46f715fa82cfe123ba2a10d1dca9955d1f418c61bba811df58aa5a61b5b`, pero la prueba dinámica
posterior demostró que el icono sobre el nameplate seguía ausente: la estructura del paquete era
correcta y el punto del ciclo de vida no.

La reproducción posterior en `Missing Information` (8548) aportó un segundo caso independiente. El
item `Anthalon's Orders` 42893 declara `loot_quest_id=8548`, `notify_ui=true`, y sus loot packs
12080, 12081 y 12082 enlazan respectivamente a los NPC 17861, 17862 y 17863. El NPC 17762 visible
en la captura no pertenece al conjunto de drop, lo que confirma la necesidad funcional del
notificador y descarta que falten relaciones de contenido.

La segunda pasada nativa cerró el detalle que faltaba: el serializer `FUN_39a94460` lee el booleano,
pero el handler `FUN_393404e0` lo ignora y siempre despacha el evento `0x2A4`. Durante
`CSSelectCharacter` todavía no existen el jugador local, la UI in-world ni los subscribers de los
nameplates, por lo que ese evento se perdía. `SCQuestNotifierInit(true)` se mueve ahora a
`CSNotifyInGameCompleted`, después de `WorldManager.OnPlayerJoin` y antes de armar el streaming de
NPC espejo. `CharacterQuests.SendInitialState()` vuelve a limitarse a las listas `0x132` y `0x133`;
la nueva regresión separa y fija el envío `0x287` en el borde de carga completa. La solución sigue
siendo global: no contiene ramas por quest, item, loot pack ni NPC, y conserva la clasificación
nativa del cliente.

Build integral Release cerró con cero errores, y la suite completa pasó **1522/1522**. Se desplegó
únicamente Game con imagen
`sha256:28b9652e330728b564a53b7bf98d6f49df12c3d0253a395c13868b2b83fd1036`, DLL Game
`7eab956101cab3974467554b625cf895b088857cfb63adb7dd761f38e1523ef1` y DLL World
`5b3d86f9a93c3e3629ba74d76ba86d354fc55332057bbb6b84394ec7f55a9957`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-quest-notifier-timing` ->
`sha256:68f40e3b58ac2b0abb26539c6474c847ca2d2945ba8fe417fb71267422f824b5`. Game quedó healthy,
sin reinicios, abrió 1239/1240/1250, cargó 8.901 quests con Strict 43.696/0 y se registró en Login.
La aceptación dinámica requiere volver a seleccionar el personaje y verificar el marcador sobre
NPC 17861, 17862 o 17863 con 8548 activa. No se inició, detuvo ni relanzó ninguna Zone.

La prueba dinámica posterior volvió a fallar: `Aust Mage` 17861 y `Aust Fighter` 17863 estaban
presentes, pero ninguno mostraba la marca. El análisis completo corrigió la interpretación del
evento `0x2A4`: `SCQuestNotifierInit` sólo refresca la UI lateral y no construye las marcas sobre
unidades. El constructor real está en el handler de `SCQuests`: `FUN_396b2560` carga cada quest,
`FUN_39b6a100` invoca el callback virtual y `FUN_396b2ce0` extrae los NPC relacionados mediante
`FUN_396af630`, inserta la relación NPC-template/quest y activa el flag visual de las unidades ya
existentes. Esa ruta está protegida por el bit in-world `0x40000000` del jugador local.

El `SCQuests` inicial se enviaba durante `CSSelectCharacter`, antes de que el cliente activara ese
bit. El cliente conservaba la quest, pero omitía silenciosamente todas sus relaciones de targets;
el notifier posterior no podía recuperarlas. `CharacterQuests.ResyncClientQuestTargetMappings()`
ahora reenvía las quests activas en `CSNotifyInGameCompleted`, después de
`WorldManager.OnPlayerJoin`, y sólo después emite `SCQuestNotifierInit(true)`. La corrección es
transversal y no contiene IDs de quest, item ni NPC. La regresión fija el orden wire `0x132` antes
de `0x287`; pruebas focales de `CharacterQuestsTests` cerraron **6/6**.

## Extensión: Diamond Shores Teleport Scroll de quest 7148

El 2026-08-22 el usuario usó el `Diamond Shores Teleport Scroll` 49628 suministrado por
`The Souleye's Location` (7148). El item respetó los 5 segundos de casteo, se consumió y completó
`QuestActObjItemUse` 977, pero el personaje no se movió. La traza viva cerró la ruta exacta:
skill 38883 ejecutó effect 70355 (`SpecialEffect` 35110), `Return value1=927`, y el resolvedor
registró que 927 faltaba en `worldgates.json`.

No es una tercera primitiva de teleport: es el tercer destino de quest ausente observado durante
la prueba Nuia. La auditoría anterior había seguido `quest_contexts.race=1`; quest 7148 pertenece
a la categoría racial compartida 131 y usa `race=255`, por lo que el criterio de cobertura quedó
corregido a categoría/cadena. `Return 750`, observado durante quest 7147, fue clasificado aparte:
lo ejecuta la skill directa 42112 de traslado hacia Elpis y no un item suministrado.

La posición de 927 se reconstruyó con autoridad AA10 r575. `return_points[927]` identifica
`quest_shining_shore`; quest 7148 reporta después al NPC 15623, enlazado al spawner type 17544;
el archivo Zone `zone/282/zone_server/npc_spawners.g` contiene el placement 144757 en local
`(1351.19,1670.61,199.864)`, `zRot=0.261793`. Con el offset nativo de celda resulta
`(18759.19,27270.61,199.864)`, yaw 15 grados, en partition 282. AA8 coincidió en las coordenadas
globales y se usó sólo como comparador estructural.

Se añadió worldgate 927 al resolvedor genérico y una regresión fija partition, coordenadas y yaw.
La aceptación dinámica pendiente es reusar el scroll recién reobtenido con la Zone 282 activa y
confirmar llegada a Scout Karlsburg conservando el marcador de jugador sin relog.

El JSON fuente y el bind mount runtime quedaron idénticos, SHA-256
`296C7806D81FE33F604C7CE3A1ECB0EE6A1676F8A3FD0D8D7F6708A6AF1D0118`. Build Release cerró con
0 errores, regresión focal 5/5, suite completa **1502/1502** y Stage 40 **8/8**; el gate offline
conservó 43.737 referencias y cero hallazgos. Se desplegó únicamente Game con imagen
`sha256:6fce5d7c6ef8943024dc82f893c358fe54173ccb118997141c4011cbd6cfa058`, DLL Game
`01aa807cc45a4253d870c44fec9be24db1e83062cc90930fb1edf1a70e22b437` y DLL World
`cdedc9577531e98fa7d0703b282d18e83680cc9b198981c8899d41afd9168003`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260821-235855` ->
`sha256:fe6bc46f715fa82cfe123ba2a10d1dca9955d1f418c61bba811df58aa5a61b5b`. Game quedó healthy,
sin reinicios, cargó 111 recalls/26 worldgates, Strict 43.696/0 y 8.901 quests; abrió
1239/1240/1250 y se registró en Login. No se inició, detuvo ni relanzó ninguna Zone y no se
controló el cliente.

## Cierre de jornada 2026-08-22: capítulos Nuia 1–10 aceptados

El usuario completó manualmente y de extremo a extremo la historia racial Nuia desde el
capítulo 1 hasta el capítulo 10 inclusive. Esta aceptación dinámica comprende la continuidad
entre capítulos después de las reparaciones de NPC y doodads condicionales, autocompletado,
entrega y aceptación de quests, items suministrados, casteos, teletransportes de quest y
sincronización del mapa encontradas durante el recorrido. Los capítulos 1–10 quedan por tanto
clasificados como **jugables y completables en el runtime AA10 desplegado** con la evidencia de
esta sesión; no se extiende esa aceptación a quests opcionales ni a rutas raciales distintas.

El capítulo 11 no forma parte de este cierre. `The Souleye's Location` (7148) y su
`Diamond Shores Teleport Scroll` ya permitieron identificar y reparar el destino genérico
`Return 927`, y la versión que contiene esa reparación está desplegada, pero falta repetir el
uso del scroll y confirmar en cliente tanto la llegada a Diamond Shores como la conservación del
marcador del jugador sin relog. Ese es el punto exacto para reanudar la prueba Nuia.

Pendientes conocidos que no invalidan la aceptación de los capítulos 1–10:

- el marcador de área de los mobs objetivo funciona en el mapa, pero el icono sobre el
  nameplate del NPC todavía no quedó confirmado; el usuario decidió diferirlo;
- los destinos `Return` 708, 997, 998 y 863 aparecen más adelante en la categoría/cadena 131
  como candidatos de auditoría; no se consideran defectuosos sin una falla dinámica o sin cerrar
  primero su evidencia nativa exacta;
- los problemas restantes del flujo de instancias y del botón de salida de dungeon se conservan
  en `CHECKPOINT_NATIVE_INDUN_EXIT_BUTTON_V1.md` y quedan fuera del cierre de quests Nuia.

Al cierre, Game continúa healthy, sin reinicios, con la imagen
`sha256:6fce5d7c6ef8943024dc82f893c358fe54173ccb118997141c4011cbd6cfa058`, 111 recalls,
26 worldgates, Strict 43.696/0, 8.901 quests y listeners 1239/1240/1250 registrados en Login.
La última validación permanece en build Release sin errores, pruebas focales 5/5, suite
completa 1502/1502, Stage 40 8/8 y gate offline con 43.737 referencias y cero hallazgos. No se
controló el cliente ni el lifecycle de Zones durante este cierre. El worktree pendiente se
preservó y no se ejecutaron commit ni push.

## Extensión: Lagor no finaliza su muerte en `The Riven Gates` (7149)

La primera prueba del capítulo 11 alcanzó `The Riven Gates` (7149), pero el NPC
`Necromancer Lagor` 19497 quedó activo con la barra agotada y no entregó el `Souleye` 37890. La
captura tiene SHA-256
`3F035FBEABD92B37ECD84AE408E76814480D84D13A835327AAE18F98C14A8BF8` y fija el mirror
`ObjId=1151`, template 19497, en la Zone 282.

La traza viva del 2026-08-22 cerró la causa sin inferir buffs ni flags del NPC. A las 15:04:54
World llevó 1151 a HP cero y emitió `SCUnitDeath`, pero `LootPack.GeneratePackNewV2` lanzó
`KeyNotFoundException` en `selectedItemsByGroup[1]`. La excepción salió desde
`LootingContainer.GenerateLoot` a través de `Unit.DoDie` y evitó que `Npc.DoDie` alcanzara el
handoff `WZUnitDeath`. Zone conservó el actor y continuó casteando 14506, 16667 y 23925; a las
15:06:47 World registró explícitamente `already dead hp=0` mientras la AI seguía activa.

La SQLite full AA10 prueba la clausura: NPC 19497 referencia el loot pack 12359; su grupo 1
contiene únicamente loot 92713/item 37890, `loot_quest_id=7149`, cantidad 1. El código separaba
correctamente ese item como loot de quest, pero sólo creaba el bucket de selección para loot
ordinario; al fusionar un grupo compuesto exclusivamente por quest loot indexaba una clave
inexistente. La auditoría completa detectó nueve grupos AA10 con la misma forma. Full y compact
retail conservaron `PRAGMA quick_check=ok`; la proyección compact deja esos campos de loot en cero
y no se usó como reemplazo de la autoridad full.

`MergeQuestItemsForGroup` crea ahora el bucket sólo cuando el grupo actual contiene quest loot y
fusiona sin duplicar un item que el roll ordinario ya hubiera elegido. La reparación es genérica:
no contiene branches por quest, NPC, item o loot pack. El padre upstream conserva el defecto;
AA8 no posee `GeneratePackNewV2` y quedó clasificado como comparador no aplicable.

Restore correcto, build integral Release con cero errores, regresión focal **1/1**, suite completa
**1503/1503**, Stage 40 **8/8** y gate offline con 43.737 referencias y cero hallazgos. Se
desplegó únicamente `game` con imagen
`sha256:5e16f4595d01ab33083a0261e63ef9829567da58320233f3797f1a7538253ee0`, DLL Game
`74c7e9b6aa9ed9bea62f02821d61f166072381d252a91e93262982fe0ee9480f` y DLL World
`a9334834e4b2d0f4c6df3fe85fdc145b5b4f6465bd21b912fe4bc328bb586d38`. El símbolo
`MergeQuestItemsForGroup` quedó presente en el ensamblado runtime. El rollback conservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-112247` ->
`sha256:6fce5d7c6ef8943024dc82f893c358fe54173ccb118997141c4011cbd6cfa058`.

Game quedó healthy, sin reinicios, con Strict 43.696/0, 8.901 quests, 111 recalls, 26 worldgates,
listeners 1239/1240/1250 y registro exitoso en Login. DB y Login conservaron sus contenedores y
estado healthy. La compact retail del bind mount coincide host/runtime en SHA-256
`8b1619b11702892aee02008deccd70d6a2a206e2dea57482bf52201c19ce9849`. No se operaron Zones ni
se controló el cliente desde Codex.

La aceptación dinámica cerró el gap el 2026-08-22 después de que el usuario relanzara Zone 282.
El Lagor nuevo `bc=476` llegó a muerte completa a las 15:29:45: cliente recibió `SCUnitDeath` y
`SCLootableState`, World emitió `WZUnitDeath` y el cadáver expiró normalmente mediante
`WZUnitRemoved`. A las 15:29:48 `LootAll` produjo `SCItemTaskSuccess`/`SCLootItemTook` y el acto
`QuestActObjItemGather(3296)` pasó el Souleye 37890 de 0/1 a **1/1**, sin
`KeyNotFoundException`. La quest 7149 quedó lista para reportar al NPC 15623 y fue entregada a
las 15:30:49; el servidor suministró los items de continuación 38183 y 47952. El defecto queda
clasificado como **corregido, desplegado y aceptado dinámicamente**.

## Extensión: vela ritual ausente en `A Mysterious Ally` (6700)

La captura del 2026-08-22 mostró el marcador de `A Mysterious Ally` a cinco metros dentro de la
casa abandonada, pero sin objeto interactuable. Su SHA-256 es
`202B79A8B97339C92162D31752664F32452EEC4FD451780F59078CD1C5840667`. El dossier suministrado
`aa10-quest-6700.json`, tratado sólo como evidencia, tiene SHA-256
`8D6830E810C1D3D80ADCFE4317B1B336075C4B88A770A2CF70FFB784F02775A9`.

La clausura AA10 r575 fija quest 6700, componente 41374, act 64605/detail 1125
`QuestActObjInteraction`: interacción `use`, doodad 8440, alias 6659 y count 1. La plantilla 8440
es server-owned (`client_doodad=false`) y posee Start 23787 con el modelo apagado y
`DoodadFuncFakeUse` 2893/skill 27882 hacia Normal 23788; esa fase muestra el modelo encendido y un
timer de 10 segundos vuelve a 23787. Full y compact contienen la misma clausura funcional y
conservan `PRAGMA quick_check=ok`.

`game_pak` contiene una única colocación retail en
`main_world/level_design/cells/009_010/doodad.g`: `(9242.4814,10452.202,198.292)`, yaw
`139.00001`, scale 1. La inspección viva ubicó a Dannia en `(9238.82,10448.172)` dentro de Zone
206, pero `findobject doodad 8440` no encontró ninguna instancia. La causa fue una divergencia de
catálogos: `AAEmu.Game/Data` ya incluía la vela, mientras el `GameContentRoot=/app/game` efectivo
de Docker monta `.server_files/AAEmu.Game/Data`; su catálogo reducido no contenía 8440.

Se añadió 8440 al overlay versionado de placements Nuia con su posición retail exacta, fase inicial
23787 y escala 1, y se proyectó la misma copia al bind mount operacional. La entrada existente del
catálogo genérico se normalizó a la misma posición, de modo que el cargador inverso la deduplica en
entornos que usan ambos archivos. La regresión valida inventario completo, deserialización de fase,
escala y equivalencia exacta de coordenadas entre catálogo genérico y overlay.

Build integral Release cerró con cero errores, regresión focal **1/1**, suite completa
**1503/1503**, Stage 40 **8/8**, full-authority Strict 43.737/43.737 y gate offline 43.737/0. La
aceptación dinámica pendiente consiste en relanzar Zone 206 después del recreate de Game, volver a
entrar y usar la vela: debe pasar 6700 de 0/1 a 1/1, mostrar la fase encendida durante diez segundos
y luego restaurar la fase apagada.

Se desplegó únicamente `game` con imagen
`sha256:d936aef06abbe70843e280768a66c9924998ab878875d18d60abccbecaf6e4bf`. La fuente y el bind
mount del overlay coinciden en SHA-256
`7D1150D3D0EE2312CB89AA3574F29C0CEC86E113B192610C3891C7EFB2B5AC4C`; el runtime cargó 42.632
doodads frente a los 42.631 anteriores, cerrando exactamente la colocación añadida. La compact
operacional `DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD` conserva template
8440, grupos 23787/23788 y `quick_check=ok`.

Game quedó healthy, sin reinicios, con Strict 43.696/0, 8.901 quests, listeners 1239/1240/1250 y
registro exitoso en Login. DB y Login conservaron sus IDs de contenedor. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-120425` ->
`sha256:5e16f4595d01ab33083a0261e63ef9829567da58320233f3797f1a7538253ee0`. No se operó ninguna
Zone ni se controló el cliente.

La aceptación dinámica quedó cerrada el 2026-08-22. Después del relanzamiento de Zone 206 por el
usuario, la vela se materializó como `obj=101022`; a las 16:22:07 inició skill 27882 y a las
16:22:09 ejecutó `DoodadFuncFakeUse` desde 23787 hacia 23788. El acto
`QuestActObjInteraction(1125)` pasó de 0/1 a **1/1**, quest 6700 quedó lista para reportar y fue
entregada a NPC 15136 a las 16:22:13. A las 16:22:19 el timer nativo devolvió el doodad a 23787.
La vela queda clasificada como **corregida, desplegada y aceptada dinámicamente**, incluidos
aparición, interacción, progreso, entrega y ciclo visual de diez segundos.

## Extensión: transición 6701 → 6702 cerrada por `QuestActConAcceptComponent`

Los dossiers adjuntos `aa10-quest-6701.json` y `aa10-quest-6702.json`, usados únicamente como
evidencia, tienen SHA-256
`BAB18E4D3FBE408193CE1CBB78B8E6C94B7FB391C6F83BB074DF67E0EE87B806` y
`8985C43EB1A730BA441DB09DA3891E62C9193E91CB7308DC4CB8AD65D488FDE2`. La captura del punto de
llegada tiene SHA-256 `1D2E35B6F7C96097107AD21CFE35D819BE6B26953E740C86EB96FC098B8AFB21`.

La clausura AA10 r575 no define un cadáver como *starter* de la continuación: 6702 se inicia por
el componente cruzado de 6701 y el cadáver es su primer actor de progreso. `A Shocking Truth` 6701
parte del NPC 15136, progresa al entrar en la esfera 2435 y su componente Reward 28590 combina
`QuestActConAutoComplete(1930)`, `QuestActConAcceptComponent(595 → 6702)` y la Gilda Star 23633.
`Rescue Mission` 6702 también parte de NPC 15136/`Chamberlain Bertos`, y luego pide interactuar
con doodad 8439 y reunir item 35386 antes de reportar a NPC 15135. El spawner nativo 140793/type
16929 coloca a Bertos sólo en Zone 206, local `(2075.2,1235.01,198.292)` y yaw `1.48353`; el
`npc_spawners.g` que lo prueba tiene SHA-256
`545AFDD849AF95649E44CD0CA0AC027A672FFEC6FE75D1C4F4C1582CBD8F8BCA`. No existe esa colocación
en la Zone 138 del punto fotografiado.

La traza viva fijó el defecto. Bertos apareció tras usar la vela a las 16:22:10 y entregó 6701 a
las 16:22:13. Dannia entró en Zone 138 a las 16:24:23 y en la esfera 2435 a las 16:24:51. El
runtime consideró satisfecho el cross-reference 6702 sólo porque su template estaba cargado,
ejecutó AutoComplete y SupplyItem, eliminó 6701 y nunca inicializó 6702.

La primera interpretación de la auditoría clasificó erróneamente el cross-reference como compuerta
de recompensa y se desplegó en la imagen `3a8de659...`. La aceptación del usuario rechazó esa
semántica: al restaurar 6701 y entrar en la esfera a las 17:00:39, 6701 quedó activa en
`Reward/Completed`; sólo al añadir 6702 manualmente a las 17:01:11 se liberó la recompensa. Ese
resultado no corresponde al cliente retail y no se promovió como cierre.

La reevaluación full resolvió la forma completa: las 475 filas `QuestActConAcceptComponent` se
separan en **299 self-references exclusivamente en Start**, **175 cross-references exclusivamente
en Reward** y una arista cross en Ready/Test. En la cadena exacta, 6701 Reward referencia 6702 y
6702 Start se referencia a sí misma; además, los acts de Start se evalúan como OR, por lo que el
self-reference acepta el autoencadenamiento y `QuestActConAcceptNpc(15136)` queda como ruta
alternativa desde Bertos. La distribución exhaustiva demuestra que el cross-reference materializa
la quest sucesora, no que espere a que el jugador ya la haya aceptado.

`QuestActConAcceptComponent` conserva ahora las self-references como starters por componente y,
para una referencia cruzada, inicia exactamente una vez la quest sucesora con tipo wire `Unknown`
y su identidad de contexto en `AcceptorId`. Si la sucesora ya está activa o completada, la
operación es idempotente. El preflight de Reward valida template, requisitos de contexto y unit
requirements antes de cualquier XP/item; si la sucesora no puede materializarse, la recompensa
fuente no muta parcialmente. La reparación es global y no contiene IDs 6701/6702. El padre
comunitario conserva el TODO permisivo; la inferencia AA8 por template materializado quedó
rechazada como comparador no autoritativo.

Validación: focales **6/6**, build Release con cero errores, suite completa **1503/1503**, Stage 40
Strict **43.737/43.737**, pruebas Stage 40 **8/8** y gate offline con 43.737 referencias y cero
hallazgos. Se desplegó únicamente `game` con imagen
`sha256:f8e538b78d8a1d10ca183a66b3f091134208c3a0d3970f991741b37f8ede35cd`, DLL Game
`3f847d0a285db8fc3830b542e584e889e3b26ddca66f93f8e26458ff51c609c9` y DLL World
`50ee7532a1974e2bae1afab74d31904a84b7a908a0a6044d191ac6a0255def18`. Runtime quedó healthy,
sin reinicios, Strict 43.696/0, 8.901 quests, listeners 1239/1240/1250 y registro exitoso en Login.
DB y Login conservaron sus IDs de contenedor. El rollback es
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-130842` →
`sha256:3a8de6599749a0f5d65a4b20bf6a46bc8c3356c973b0047d53125dbec40d3b17`. No se operó ninguna
Zone. La aceptación de esa imagen volvió a rechazar el cierre: tras limpiar 6701/6702, restaurar
sólo 6701 y reloguear, la entrada nativa en la esfera 2435 a las 17:33:59 dejó 6701 en
`Reward/Completed` y no inició 6702. La esfera y el objetivo funcionaron; faltaba ejecutar en el
mismo ciclo el Reward que contiene `QuestActConAutoComplete`.

La auditoría completa cuenta **3.177** `QuestActConAutoComplete`, todos en componentes Reward. El
runtime ahora detecta ese act al transicionar a Reward y ejecuta el step inmediatamente, sin
esperar otro evento de cliente o World. Así 6701 debe aplicar su Reward, materializar 6702 y
retirarse en el mismo ciclo de la esfera.

El `game_pak` sí contiene el actor físico siguiente. En
`game/worlds/main_world/level_design/cells/026_008/doodad.g` aparece doodad **8439**, modelo
`nu_m_corpse1.cgf`, local `(205.810,809.776,783.089)`, quaternion equivalente a
`Roll=15°, Pitch=0°, Yaw=10°`. La conversión nativa de celda lo fija en World
`(26829.810,9001.776,783.089)`, a 3,34 m de la última posición persistida de Dannia
`(26826.5,9001.3,783.68)`. El catálogo de spawns efectivo no contenía 8439. Se añadió al overlay
versionado y al bind mount operacional con `FuncGroupId=42008`, la fase visible/interactuable que
contiene el modelo y `DoodadFuncUse`/skill 27921. La regresión exige template, fase, escala y
coordenadas exactas.

Validación previa al despliegue: suite completa **1504/1504**, Stage 40 Strict
**43.737/43.737**, pruebas Stage 40 **8/8** y gate offline **43.737/0**. Se desplegó únicamente
`game` con imagen `sha256:6a5f40615ee4e331f8a9a81adf030bb4c268da84c4fbb245b6d885fca6a397f8`,
DLL Game `d3fc4955e391163f0ca7d029fe283c7f3ee87384d409247345328566d85e90cc` y DLL World
`d5e74c152c4237685c040f6e6d1e382339a67d12714837ec159436363e411ea3`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-134500` ->
`sha256:f8e538b78d8a1d10ca183a66b3f091134208c3a0d3970f991741b37f8ede35cd`. El catálogo fuente,
bind mount y contenedor coinciden en SHA-256
`e0fd48791714ae56e83c235d827817704e9db64269ea2032076dc8c958937ae6`. El runtime quedó healthy,
RestartCount 0, Strict 43.696/0, 8.901 quests, listeners 1239/1240/1250 y registro exitoso en Login;
DB y Login conservaron sus contenedores. El mundo cargó **42.633 doodads**, uno más que la imagen
rechazada, confirmando que el cadáver entró al catálogo efectivo. No se operó ninguna Zone.

Queda pendiente la nueva aceptación dinámica: 6701 debe autoentregarse, 6702 debe aparecer en
Progress y el cadáver 8439 debe verse e interactuar para progresar y obtener la carta 35386, sin
comandos intermedios.

La aceptación de la imagen `6a5f4061...` a las 18:04:24 confirmó que el overlay sí corrigió el
actor físico: el cadáver 8439 apareció en la posición retail, con marcador e interacción. También
rechazó la transición: 6701 volvió a quedar `Reward/Completed`, 6702 permaneció ausente y el cadáver
respondió `Rescue Mission must be in-progress`. La captura de evidencia tiene SHA-256
`07796EE78859CFE3D4629993F7C2B6AE555E94162112642E970BB07CDC09820A`.

La causa exacta quedó en la fila autoritativa `unit_reqs.id=47448`: el Start 28591 de 6702 exige
`complete_quest_context(6701)`. El preflight de Reward intentaba validar y crear 6702 antes de que
el cierre posterior de 6701 persistiera su completed bit, formando una dependencia circular. La
auditoría completa encontró 98 emparejamientos Reward-cross/Start-complete, 92 aristas distintas y
84 filas donde el requisito es precisamente la quest fuente, por lo que no es una excepción local.

El motor mantiene ahora un scope transaccional de *completion in flight* durante cada evaluación
Reward. `CompleteQuestContext` lo considera satisfecho y `ExceptCompleteQuestContext` lo considera
no satisfecho sólo dentro de ese scope; el bit durable continúa en falso hasta que todos los acts y
la distribución de recompensas concluyen correctamente. El scope cubre preflight y el `AddQuest`
anidado, admite anidación y siempre se libera mediante `IDisposable`. No contiene IDs de quest.
Validación previa al nuevo despliegue: suite completa **1505/1505**, Stage 40 Strict
**43.737/43.737**, Stage 40 **8/8** y gate offline **43.737/0**.

Se desplegó únicamente `game` con imagen
`sha256:ac2f366bac2a5102d2b3110b57723e27bed832395857f1f32c6d0bce7f789af7`, DLL Game
`00c8b7d9b6bba4750d726ad1235068b937c027a4175a38a369d41a0a045d4ac4` y DLL World
`3fe274a03190ca559e6fffeedb48ff5128361d7b5d89e8924237a5cdec4a9b70`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-141257` ->
`sha256:6a5f40615ee4e331f8a9a81adf030bb4c268da84c4fbb245b6d885fca6a397f8`. Game quedó healthy,
RestartCount 0, Strict 43.696/0, 8.901 quests, 42.633 doodads, listeners 1239/1240/1250 y registro
exitoso en Login. DB y Login conservaron IDs; no se operó ninguna Zone.

La aceptación dinámica final se cerró el 2026-08-22 sin comandos intermedios después de la
restauración limpia. A las 18:20:42 Dannia entró en la esfera 2435 de Zone 138;
`QuestActObjSphere(707)` ejecutó el objetivo, el runtime inició naturalmente quest 6702,
`QuestActConAutoComplete(1930)` aplicó el Reward y 6701 emitió
`SCQuestContextCompletedPacket`. La 6701 desapareció de la lista activa y la 6702 quedó creada por
la arista de Reward, sin alta manual.

A las 18:20:45 comenzó la interacción retail de tres segundos con doodad 8439 mediante skill
27921 y fase 42008. A las 18:20:48 `QuestActObjInteraction(1121)` registró la interacción,
`GainItem` entregó la carta 35386 y ambos objetivos de 6702 alcanzaron **1/1**. El estado final
observado fue 6701 ausente y 6702 en `Ready/Ready` con objetivos `(1,1,0...)`. Quedan aceptados de
extremo a extremo la autoentrega por esfera, el inicio de la sucesora, la presencia e interacción
del cadáver y la adquisición del item; esta cadena se clasifica como **corregida, desplegada y
aceptada dinámicamente**. El usuario operó el relanzamiento de Zone; Codex no operó ninguna Zone.

## Cierre regional AA10 r575 — placements de doodads de Halcyona

La ausencia de la roca sólida 8441 de quest 6703 expuso un defecto regional, no una coordenada
local de la misión. La fila de quest usa alias 5788 y `highlight_doodad_id=8441`; el
`game_pak` r575 coloca una única roca en World `(11017.739,10279.9595,243.677)`, identidad de
rotación y scale 1. El catálogo server base contiene la misma posición, por lo que se rechazó la
hipótesis estricta de que esa roca conservara coordenadas de otra versión.

La hipótesis sí quedó confirmada para el catálogo de Halcyona como conjunto. Dentro de los bounds
autoritativos de `w_golden_plains` —`[7368.648649,12288) × [9216,12168.648649)`— el base generado
contiene 8.092 placements contra 6.600 placements retail r575. Sólo 5.172 emparejan por template y
posición a menos de un metro: faltan 1.428 retail y sobran 2.920 server. Además, el base perdió
todas las rotaciones y grabó scale 0, mientras retail tiene 812 escalas no unitarias. Esto explica
en una sola causa las camas y mesas en caminos, sillas flotantes y actores de quest ausentes o
desplazados. La regresión entró con `a98e96a2b` (`regenerate main_world doodad spawns`) y también
está presente en el padre comunitario actual.

Se implementó una sustitución regional declarativa: el manifest
`doodad_spawn_replacements.json` suprime sólo las filas de Halcyona procedentes de
`doodad_spawns.json`; el catálogo `doodad_spawns_aa10_halcyona_r575.json` repone posiciones,
quaternions convertidos a Euler y escalas retail. Los overlays nombrados se cargan primero en
orden ordinal descendente, por lo que las fases explícitas de la vela 8440 y los proxies Nuia
siguen ganando sobre un duplicado retail. El loader valida bounds y archivos y falla cerrado ante
un manifest incompleto.

El generador reproducible `build_halcyona_doodad_overlay.py` extrae las 15 celdas retail
007_009…011_011, valida sus SHA-256 y exige exactamente 6.600 placements, una roca 8441 exacta y
escalas positivas. Una regeneración directa desde `game_pak` produjo el mismo SHA-256 que el
catálogo versionado: `871635fa0011912d89376f487aa387d1f7e2469bf761a77c59f3a5fcb1c94df7`.
Validación previa al despliegue: focales del dominio doodad **21/21**, build Release con cero
errores y suite completa **1508/1508**.

El bind mount operacional contenía sólo 4.418 de las 8.092 filas legacy regionales del catálogo
versionado; todas fueron suprimidas y sustituidas por retail. Se desplegó únicamente `game` con
imagen World `sha256:ee57f29762fafbd452ceea2d291fbba80b5849ff932ab641bbca49b05e670c95`,
DLL Game `63922f25ff5e451e94d3d844279ec370484ee71c08ad81f99c2d2611365c236c` y DLL World
`44101587d0ad060c8bd4e2d1b4ab7560ba6f5d4e8525bcde4bb17e3fc6a101d8`. El catálogo y manifest
efectivos conservan respectivamente SHA-256 `871635fa...` y
`e9a2c3b277cb2e082997142acd1f87b1b4e9c699e51ead5711f861bcf5154ba7`. El mundo cargó 44.796
doodads, frente a 42.633 antes del reemplazo; Strict quedó 43.696/0, se cargaron 8.901 quests y
Game registró correctamente en Login. DB y Login conservaron contenedor e identidad; Game quedó
healthy y RestartCount 0. Rollback:
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-145814` → `sha256:ac2f366b...`.
No se operó ninguna Zone. El usuario cerró la aceptación dinámica: quest 6703 funcionó y una
inspección visual confirmó que el mobiliario y numerosos doodads de Halcyona recuperaron su
disposición retail después del relanzamiento de Zone operado por el usuario.

### Corrección de llegada — retorno 176 de Sunset

La aceptación visual del catálogo retail hizo visible un segundo defecto independiente: el portal
`Halcyona Community Center` llevaba al return point 176 en World
`(9317.3,10317.1,187.7)`, dentro del mobiliario. Los logs cerraron el flujo completo
`UsePortal -> TeleportEnded` sobre esas coordenadas, por lo que el transporte no fallaba; la fila
de `recalls.json` era la autoridad equivocada. La misma fila histórica está en AA8, rama moderna y
el padre comunitario AA10, pero no procede de la SQLite r575: `return_points.id=176` sólo aporta
identidad `sunset_town`, district 127 y binding 79, sin coordenadas.

El cruce con las celdas retail r575 identifica el tomo 3591 en
`(9319.904,10332.5339,187.332)` y la mesa de procesamiento 12151 en
`(9318.205,10316.7358,187.332)`. La llegada heredada queda a sólo **0,98 m** del centro de la
mesa. Los otros tres retornos de Halcyona no presentan un solapamiento equivalente, por lo que se
descartó trasladarlos en bloque. El retorno 176 se reconstruyó de forma puntual a
`(9319.747,10329.538,187.332)`: tres metros delante del tomo, sobre su mismo plano y a más de
10 m de la mesa. Una regresión de datos fija identidad, zona/subzona, coordenadas, anclaje al tomo
y separación del mobiliario. La validación cerró con focales Portal **6/6**, build Release con
cero errores y suite completa **1509/1509**. Se desplegó únicamente Game con imagen
`sha256:012a11bd76e603153810e9400e93ef3b977dc6c30137d2f321f2e900f5303dda`; el catálogo efectivo
de recalls tiene SHA-256 `91d588d90e0e832282fe00223b528776746394fe1e9896c8e4a3c382cdb08126`.
Game quedó healthy/RestartCount 0, Strict 43.696/0, 8.901 quests, 111 recalls, 44.796 doodads y
registrado en Login. DB y Login conservaron sus contenedores. Rollback:
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-portal176` → `sha256:ee57f297...`.
La aceptación dinámica quedó cerrada a las 19:36:49 después del relanzamiento de Zone 206 por el
usuario: `UsePortal` resolvió `Halcyona Community Center` y `TeleportEnded` dejó a Dannia en Zone
206, `(9319.7,10329.5,187.3)`, fuera del mobiliario. Codex no operó ninguna Zone.

### Cierre transversal de Return para la historia Nuia/compartida

La prueba siguiente expuso una distinción importante. El resolver de `SpecialEffectType.Return`
ya era transversal —busca primero worldgate y luego recall—, pero el catálogo server-owned de
destinos seguía incompleto. A las 19:37:08 quest 6705 ejecutó `QuestActObjItemUse(1142)`, consumió
el item 49633 y completó el objetivo 1/1; no siguió ningún `TeleportEnded`. La cadena completa en
la full SQLite AA10 r575 es item 49633 → skill 38890 → effect 70362 → special effect 35116,
tipo 25 `Return`, `value1=708`. `return_points.id=708` aporta identidad pero no coordenadas, y 708
no existía en worldgates ni recalls.

Se auditó el universo completo `QuestActObjItemUse → item.use_skill_id → skill_effects → effects →
special_effects(Return)` y se cerró como conjunto la categoría 131 compartida por Nuia (`race=1`)
o todas las razas (`race=255`). Sus destinos exhaustivos son 999, 927, 708, 998 y 863; 999 y 927
ya estaban cubiertos. Se añadieron los tres faltantes con autoridad nativa AA10:

- 708, Golden Ruins: quest 6705/8539/8545, spawner 140881/type 16894/NPC 15144 en Zone 281;
  `(17233.918,27511.28,141)`, yaw -134°.
- 998, Whalesong: quest 8550, spawner 166550/type 20048/NPC 17823 en Zone 310;
  `(16482.9,28100.27,105.262)`, yaw -57°.
- 863, Aegis Island: quest 8556, spawner 166545/type 20053/NPC 17828 en Zone 344;
  `(14434.69,26684.73,134.25)`, yaw -20°.

Las coordenadas globales se resolvieron desde los `npc_spawners.g` y offsets de partición r575.
AA8 sólo corroboró las coordenadas; sus ZoneId y yaw fueron rechazados y sustituidos por los de
AA10. El destino 997 se excluye explícitamente porque sólo pertenece a quests 7117/7118 de la ruta
Harani/Warborn (`race=16/32`) y su posición Ynystere AA10 aún no está demostrada.

`PortalManagerTests` incluye ahora una compuerta exhaustiva para que todos los Return de historia
Nuia/compartida sigan presentes y anclados a su Zone/posición AA10. Los focales Portal cerraron
**7/7**, build Release terminó con cero errores y la suite completa cerró **1510/1510**.

Se desplegó únicamente Game con imagen
`sha256:4a31c70834c9c3dade98163315e0e58d9ba7d203ceb0b25ef2079e7e9fd3902a`. Fuente, bind mount y
contenedor comparten el SHA-256 de worldgates
`0d6446fc826a818c8d548d17b9ea615439bff86ca500b1b7fd84e44419554559`. Runtime quedó healthy,
RestartCount 0, Strict 43.696/0, 8.901 quests, 111 recalls, **29 worldgates**, 44.796 doodads,
listeners 1239/1240/1250 y registro exitoso en Login. DB y Login conservaron sus contenedores. El
rollback es `aaemu-world:10.0.2.13-r575-local-rollback-20260822-return-category131` →
`sha256:012a11bd76e603153810e9400e93ef3b977dc6c30137d2f321f2e900f5303dda`.

La aceptación dinámica de Return 708 quedó cerrada el 2026-08-22. A las 19:56:29 Dannia inició
skill 38890 desde scroll 49633; a las 19:56:34 `QuestActObjItemUse(1142)` alcanzó 1/1 y a las
19:56:37 `TeleportEnded` confirmó Zone 281 en `(17233.9,27511.3,141.0)`. Quest 6705 se entregó
naturalmente a NPC 15144 a las 19:56:47 y la progresión continuó hasta 6708. No se forzó el
teletransporte y Codex no operó ninguna Zone.

### Capítulo 14 — actores cliente de Golden Ruins

Quest 6708 no reporta a un NPC convencional: `QuestActConReportDoodad(216)` exige doodad 14250,
localizado como **Scout Alcanto**. La misión entró correctamente en Ready y el marcador señaló el
lugar, pero el catálogo efectivo no contenía el actor. `doodad_almighties.id=14250` lo clasifica
como `client_doodad=t`, modelo `npctype://15139`; su fase inicial 41880 aplica el model change y
las reacciones de quest que sostienen 6708–6710.

La auditoría de todos los acts doodad de categoría 131, `race in (1,255)`, capítulo 14 en adelante
encontró otros dos actores cliente ausentes dentro del mismo capítulo: Volio 14253 para 6711/6712
y Jettin 14313 para 6714/6715. Se cerraron los tres juntos desde `game_pak` r575:

| doodad | actor | celda | X | Y | Z | yaw | fase inicial |
|---:|---|---|---:|---:|---:|---:|---:|
| 14250 | Scout Alcanto | 017_026 | 17683.549 | 27036.408 | 139.537 | 45 | 41880 |
| 14253 | Volio | 017_026 | 18202.637 | 27538.898 | 151.853 | 0 | 41888 |
| 14313 | Jettin | 017_027 | 17941.245 | 27988.464 | 259.163 | -135 | 42011 |

`PakDoodadScan` abrió el paquete read-only y resolvió posición global, quaternion/yaw y escala 1.
La full SQLite aportó identidad, modelos, fases, `DoodadFuncQuest`, `DoodadFuncQuestReact` y
`DoodadFuncModelChange`. Upstream padre y el catálogo base no contienen ninguno de los tres.
No se añadió lógica por quest: sólo placements r575 al overlay declarativo existente. La
regresión `NuiaRacialQuestProxyCatalogTests` fija fases y coordenadas de los tres; focal **1/1**,
build Release cero errores y suite completa **1510/1510**.

Se desplegó únicamente Game con imagen
`sha256:53eaf1347eac96eb0553dc77f2a5bfed92fd6c5163605a850436f49678caa1a0`. Fuente, bind mount y
contenedor comparten SHA-256 del overlay
`3df20f95fa4c873962d1216020d97d7973678cee79f4dadabca2123dfe97cd10`. Runtime quedó healthy,
RestartCount 0, Strict 43.696/0, 8.901 quests, 111 recalls, 29 worldgates y **44.799 doodads**,
exactamente tres más que la imagen anterior; listeners 1239/1240/1250 y registro Login correctos.
DB y Login conservaron contenedor. Rollback:
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-golden-ruins-actors` →
`sha256:4a31c70834c9c3dade98163315e0e58d9ba7d203ceb0b25ef2079e7e9fd3902a`. Queda pendiente la
aceptación visual/interactiva de Alcanto después del relanzamiento de Zone 281 operado por el
usuario; Codex no operó ninguna Zone.

### Capítulo 14 — fases QuestReact por personaje en doodads compartidos

La prueba de Alcanto confirmó que el placement 14250 era correcto y que quest 6709 alcanzaba
naturalmente `Ready`, pero el servidor seguía buscando funciones en la fase compartida 41880.
El cliente había aplicado sus callbacks `DoodadFuncQuestReact` y mostraba el cadáver curado con
marcador de entrega; el servidor, que no cargaba la tabla `doodad_func_quest_reacts`, volvía a
ejecutar skill 27750 y respondía que **The Poisoned Scout must be in-progress**.

La full/compact r575 define el flujo sin ambigüedad: 41880 + 6709/Progress → 41881, 41880 +
6709/Ready → 41973 y 41880 + 6709/Completed → 41973. La fase 41881 contiene el uso curativo;
41973 contiene report 6709 y offer 6710. Se incorporó el template nativo completo —incluidos
`quest_component_id`, bubble y orden de las aristas— y un resolver acotado/cycle-safe que calcula
la fase efectiva por personaje. `Use` y `UseQuest` consumen esa fase sin escribir la fase global
del doodad `once_one_man`; no hay branches por 14250, 6709 ni 6710.

Las regresiones cubren Progress/Ready/Completed de 6709, precedencia de la sucesora 6710 y aristas
específicas por componente. Build Release terminó con cero errores y la suite completa cerró
**1515/1515**. Queda pendiente la aceptación dinámica del report de 6709 y oferta natural de 6710
después del despliegue; Codex no opera ninguna Zone.

Se desplegó únicamente Game con imagen
`sha256:fa30da82c3e393425f100d05d9a0ecaa5744002efa28ff4713cff9ab1880df43`, DLL Game
`619db6e36c1744143cca41f8f876b962221fea2aa1f0c170cde02956a44352a2` y DLL World
`6027d939733b8306b7d5380b75664a6d7b28c0d1df28333dbc9a0e66756d0a73`. Runtime quedó healthy,
RestartCount 0, Strict 43.696/0, 8.901 quests, 111 recalls, 29 worldgates, 44.799 doodads,
listeners 1239/1240/1250 y registro exitoso en Login. DB y Login conservaron sus contenedores.
Rollback: `aaemu-world:10.0.2.13-r575-local-rollback-20260822-questreact6709` →
`sha256:53eaf1347eac96eb0553dc77f2a5bfed92fd6c5163605a850436f49678caa1a0`. La aceptación debe
continuar con 6709 en su estado Ready persistido: entregar al cuerpo y comprobar que ofrece 6710,
sin restaurar ni forzar la quest. El usuario debe relanzar Zone 281; Codex no opera ninguna Zone.

### Catálogo nativo del libro de teletransportes y portal de `A Prophetic Warning` (8547)

La auditoría transversal del libro partió de las relaciones AA10 r575, no del JSON histórico. Los
`DoodadFuncBinding` de Memory Tome enlazan **187 distritos** con **192 return points**. El catálogo
manual sólo cubría 120 ids/111 subzonas físicas. `PortalManager` reconstruye ahora en el arranque
las coordenadas desde los `return_point.g` de `game_pak` y registra el desbloqueo usando la
relación autoritativa `binding.district_id -> district_return_points.return_point_id`; esto evita
inferir distritos por proximidad y también cubre tomos cuyo doodad se genera dinámicamente.

La carga de polígonos tenía además dos defectos previos: iteraba instancias World todavía no
creadas y almacenaba por `zones.id` en vez de `zones.zone_key`. Se expuso el catálogo de templates
y se corrigió la clave. Runtime carga ahora **1.428 subzonas** y **785 áreas de housing** desde 70
world templates. Al recibir `CSNotifySubZone`, `CharacterPortals` persiste una sola visita en
`portal_visited_district`, resuelve el return point de la facción o de su facción madre y vuelve a
emitir el libro sin duplicados.

Cobertura efectiva: **190/192** destinos, con 185 coincidencias nativas en `return_point.g`, 215
aliases por destino y 190 aliases directos por binding. Los únicos ids excluidos son 858 y 1076:
r575 los declara como destinos dinámicos, pero no contiene ni placement `return_point.g` ni
coordenadas manuales demostrables. Se mantienen como evidencia negativa y no se fabricaron
teleports rotos.

Para quest 8547, r575 define los doodads 12216/12217, skills 36724/36725 y
`SpecialEffect Return` 868/869. Faltaban esos destinos en el servidor. Se añadieron worldgates
868, interior del Abandoned Warehouse en Zone 310 `(16491.2,28105.46,105.597)`, y 869, exterior
`(16499.04,28109.83,105.538)`, ambos desde evidencia AA10 r575. La entrada puede así llevar a
Jakar y la salida devolver al porche sin lógica específica de quest.

La primera aceptación visual demostró que eso sólo cerraba la mitad del contrato: el catálogo
fuente/upstream contenía ambos placements, pero el bind operativo reducido de Docker no. Además,
esas filas legacy habían perdido fase, rotación y escala. `game_pak` r575 fija entrada 12216 en
`(16496.795,28108.146,105.358)`, yaw -60°, fase Start 35813 y escala 1; salida 12217 en
`(16478.0376,28096.633,105.262)`, yaw -59°, fase Start 35814 y escala 1. SQLite confirma sus
`DoodadFuncFakeUse` 3466/3467, skills 36724/36725 y el timer de entrada 36039 → 35813. AA8
conserva orientaciones -63°/-62° y se rechazó como autoridad. Los dos actores se añadieron al
overlay versionado y a su bind efectivo.

Validación: build integral con cero errores y suite completa **1520/1520**. Se desplegó únicamente
Game con imagen `sha256:cef18d0d3fd94e29c6583ae249366559b3cd46d4e4beb98faa338c921adcaf8e`,
DLL Game `fb504365c4b49d58ff63a83f8685070e329e47e6e9963a1c1db30ad4f42d962c` y DLL World
`e5a37a01bb35ca88aa60cbf7c041ac3aada6dc3ba359c13556906505d9ac1bc9`. Fuente, bind y
contenedor comparten worldgates SHA-256
`3a24e83162e4d2f6154ad43b6d0684c22e9065855f115bf9ea4b08560428bc13`. Runtime quedó healthy,
RestartCount 0, Strict 43.696/0, 8.901 quests, 111 recalls, 31 worldgates, 44.804 doodads,
listeners 1239/1240/1250 y registro exitoso en Login. DB y Login conservaron contenedores; no se
operó ninguna Zone. Rollback preservado:
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-teleport-book-warehouse` ->
`sha256:fca7131ba811bd55d1b66ee4b604330a3d1bedfd21604303e5e52a48281cfc4c`.

Pendiente de aceptación cliente: reloguear, atravesar el portal 12216 de la bodega y confirmar la
llegada al interior/Jakar; además entrar a un distrito con Memory Tome aún no registrado y
comprobar que aparece automáticamente en el libro y permanece después de otro relog.

Segundo despliegue correctivo: sólo Game, imagen
`sha256:94781de1f6fb1c51d621382ca011a4f402befdd09ee577cea5cf5ee78083d8d8`. El overlay coincide
entre fuente, bind y contenedor con SHA-256
`f9ea493f6c7ede845ea274abe47bcdb7f41e052fbf356074697b0935913a0d5a`; runtime cargó exactamente
**44.806 doodads**, dos más que el intento anterior, quedó healthy/RestartCount 0 y se registró
en Login. DB/Login conservaron contenedores y no se operó ninguna Zone. Rollback inmediato:
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-warehouse-destinations` →
`sha256:cef18d0d3fd94e29c6583ae249366559b3cd46d4e4beb98faa338c921adcaf8e`.

La segunda aceptación alcanzó por fin la entrada 12216, pero expuso una regresión transversal de
`Return` dentro de `main_world`. La traza de las 01:21:33–01:21:38 cerró el orden exacto: skill
36724 terminó, `Return(868)` resolvió el destino, Game envió `SCLoadInstance` seguido de
`SCTeleportUnit`, el cliente contestó `CSTeleportEnded` en `(0,0,0)`, Game lo rechazó como Zone 0
y el cliente se desconectó tres segundos después. No fallaron el placement, la skill ni la Zone
310; ésta mantuvo heartbeat estable.

El contrato quedó separado por instancia. Un `Return` cuya fuente ya está en
`WorldManager.DefaultInstanceId` mueve primero el estado autoritativo y emite sólo
`SCTeleportUnit`; `SCLoadInstance` permanece reservado para volver desde una instancia distinta.
Es una corrección general por transporte, no por quest, skill o return point. Coincide con el
flujo same-instance de `PortalManager.UsePortal` y con la primitiva x64 de AA8, usada sólo como
comparador estructural. Las regresiones fijan ambos planes (`TeleportOnly` y `LoadInstance`), el
build Release cerró con cero errores y la suite completa con **1521/1521**.

Se desplegó únicamente Game con imagen
`sha256:68f40e3b58ac2b0abb26539c6474c847ca2d2945ba8fe417fb71267422f824b5`, DLL Game
`30fcd719fecec08af6a5f12a2d04233e2d65b2d29923b509e3e5dabf1eed7d38` y DLL World
`237ea5a05dd577db7d0977fcfff8dcb8f2f483b60338d348a1f2ca80ce5cba83`. Runtime quedó
healthy/RestartCount 0, Strict 43.696/0, 8.901 quests, 111 recalls, 31 worldgates y 44.806
doodads; abrió 1239/1240/1250 y se registró en Login. DB y Login conservaron contenedores. El
rollback es `aaemu-world:10.0.2.13-r575-local-rollback-20260822-warehouse-return-same-instance` →
`sha256:94781de1f6fb1c51d621382ca011a4f402befdd09ee577cea5cf5ee78083d8d8`. Pendiente de
aceptación: el usuario debe relanzar Zone 310, reloguear e interactuar una vez con 12216; se exige
un `TeleportEnded` no-cero en el interior sin caída del cliente. Codex no operó ninguna Zone.

### Marcas nativas de objetivos de quest sobre NPCs

La misión 8548 (`Missing Information`) permitió aislar el fallo transversal: el cliente r575
deriva las marcas sobre NPCs a partir de `SCQuests` (`0x132`) y de sus relaciones retail de
quest/item/loot. Para esta misión, las relaciones válidas apuntan a Aust Mage 17861, Aust
Assassin 17862 y Aust Fighter 17863; Aust Soldier no es objetivo. `SCQuestNotifierInitPacket`
(`0x287`) sólo refresca el notifier lateral y no construye estas asociaciones.

El primer `SCQuests` se enviaba durante `CSSelectCharacter`, antes de que el jugador local tuviera
activo el bit nativo in-world `0x40000000`. El handler del cliente cargaba las quests, pero omitía
silenciosamente la construcción del mapa quest-target y no existía una segunda pasada. Se añadió
una resincronización general al completar `CSNotifyInGameCompleted`: primero se repite la lista de
quests activas con `SCQuests` y después se emite `SCQuestNotifierInit`. No se fabricaron marcas ni
se codificaron NPCs por misión; el cliente vuelve a resolverlas desde sus propios datos AA10.

Validación: prueba focal **6/6**, build Release integral con cero errores y suite completa
**1522/1522**. Se desplegó únicamente Game/World con imagen
`sha256:c6584328900f9101d95b69128f0e4947f11c3ec2e84d2c72222bfb8d834f3b7e`, DLL Game
`c3126b274cf787cc91da089fb852de366b08f90e06c07b8e4afdd56bb18816e7` y DLL World
`1320a270b940e2615ee18d85455dbbf9a510fe9a1975b6063e5efdaec280e238`. Runtime quedó healthy,
abrió 1239/1240/1250, cargó 8.901 quests con Strict 43.696/0 y se registró en Login. Rollback:
`aaemu-world:10.0.2.13-r575-local-rollback-20260822-quest-target-map-order` →
`sha256:28b9652e330728b564a53b7bf98d6f49df12c3d0253a395c13868b2b83fd1036`.

El Zone nativo se desconectó al recrearse World y no se operó su ciclo de vida. Pendiente de
aceptación cliente: relanzar/conectar Zone, volver a selección de personaje y entrar de nuevo;
Aust Mage y Aust Fighter deben exhibir marca mientras 8548 esté activa, y Aust Soldier debe
permanecer sin ella.

#### Corrección forense del intento de resincronización (2026-08-23)

La aceptación cliente demostró que el reenvío anterior no reconstruía las marcas. La ampliación
de la frontera nativa cerró la razón: `FUN_39b6a4d0` sólo llama a la inserción
`FUN_39b6a100` —y por tanto al callback virtual `+0x28`/`FUN_396b2ce0` que deriva los NPC
objetivo— cuando el contexto todavía no existe. Para una quest ya cargada, copia sus campos en
sitio y retorna sin ese callback. `SCQuestContextUpdated` termina en el mismo tipo de actualización
sin reinserción. Por ello, repetir `SCQuests` tras `CSNotifyInGameCompleted` nunca podía reparar el
mapa omitido durante selección de personaje.

También quedó localizado el UI real. `game/prefabs/quest_mark.xml` define
`marker.huntsign` con `ncom_huntsign.cdf`; `FUN_396ba5b0` lo asocia al enum `0x10`,
`FUN_396723c0` selecciona el tipo y `FUN_396721c0` instancia el prefab. Es independiente de
`SET_OVERHEAD_MARK`, del decal de target y del notifier Lua. El `compact.sqlite3` cargado por el
cliente contiene completa la cadena 8548 → item 42893 → loot packs 12080/12081/12082 → NPC
17861/17862/17863, de modo que no corresponde sintetizar marcas ni hardcodear objetivos.

La reconstrucción corregida difiere por primera vez la lista activa: durante
`CSSelectCharacter` sólo se envían los bloques de quests completadas (`0x133`), y
`CSNotifyInGameCompleted` realiza la primera inserción de las activas (`0x132`) ya con el jugador
in-world, seguida por el notifier (`0x287`). La regresión comprueba que una quest activa no aparece
en el burst temprano y que el orden tardío es `0x132` con un contexto real antes de `0x287`.
Validación local: build Release integral con cero errores y suite completa **1522/1522**. No se ha
desplegado esta cuarta corrección ni se ha operado Zone; la prueba viva exige despliegue, relog
completo y verificar marcas sólo en Mage/Assassin/Fighter.

#### Rechazo en cliente de la inserción tardía y restauración del diario (2026-08-23)

La prueba viva rechazó también la cuarta estrategia. Dannia conservó en el servidor la quest
8548 activa y el log la evaluó con item 42893 en `0/1`. Tras `CSNotifyInGameCompleted`, el
servidor emitió efectivamente `SCQuests` (`0x132`) seguido de `SCQuestNotifierInit` (`0x287`),
pero el cliente r575 no construyó el diario: mostró el tracker vacío y volvió a ofrecer
`Missing Information`. El intento de aceptarla falló porque no había pérdida persistente; el
servidor ya contenía la quest. Esto prueba que `SCQuests` tardío no es un bootstrap válido aunque
la entrada sea nueva en el journal del cliente.

Se restauró el contrato estable de selección
`SCQuests -> SCCompletedQuests -> SCQuestNotifierInit` y se eliminó por completo el envío tardío
desde `CSNotifyInGameCompleted`. Suite completa **1521/1521**, build Release con cero errores.
Se desplegó sólo Game/World con imagen
`sha256:f5067f7c626133556bbd1fc3b459b1f7ab742577b71267f8e074049043bb8cf5`; el runtime quedó
healthy, sin reinicios, abrió 1239/1240/1250 y se registró en Login. La imagen rechazada quedó
preservada como `aaemu-world:rejected-late-scquests-20260823` y no se operó Zone.

La frontera pendiente queda restringida al consumidor de alta/spawn de NPC o a la invalidación
nativa in-world que recalcula el flag de objetivo en `+0x712e`. No se volverá a mover, omitir,
resetear ni reinyectar el diario para resolver las marcas, y no se hardcodearán NPCs ni prefabs.

#### Raíz nativa definitiva: `questNpcTag` (2026-08-23)

- A fresh in-world acceptance of quest 8548 proved that replay/order was not the marker blocker:
  the quest entered the journal correctly while eligible NPCs remained unmarked.
- Retail `x2game.dll` function `FUN_396b2ce0` expands the quest act through
  `FUN_396af630`, maps item 42893 through loot packs 12080/12081/12082 to NPC templates
  17861/17862/17863, and attaches `marker.huntsign` through `FUN_39661a80`.
- That entire target-map build is gated by
  `(ClientPlayer+0x30 & 0x40000000) != 0`. `SCInitialConfig` copies the 31-byte fset at
  `ClientPlayer+0x28`, so this is fset byte 11 bit 6, absolute bit 94: `questNpcTag`.
- The enum and 31-byte serializer were already correct, but the shipped feature baseline left
  `questNpcTag` disabled. Enabling it is the transversal client-native repair; no quest-specific
  packet replay or synthetic marker packet is required.
- Validación: suite completa **1523/1523** y build Release integral con cero errores. Se desplegó
  sólo Game/World con imagen
  `sha256:ead6131af1213c50f5d0dbdf9a280bb2434985c59bdd91ecda0ecdb0100fa9a3`; el runtime confirmó
  `questNpcTag` dentro de `Enabled Features`, abrió 1239/1250, se registró en Login y quedó
  healthy con RestartCount 0. Rollback:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260823-quest-npc-tag` →
  `sha256:f5067f7c626133556bbd1fc3b459b1f7ab742577b71267f8e074049043bb8cf5`.
  Como el fset se recibe en `SCInitialConfig`, la aceptación requiere relog completo; Codex no
  inició, detuvo ni relanzó Zone.
- **Aceptación dinámica cerrada.** Después del relog, quest 8548 permaneció activa en `0/1` y el
  cliente mostró `marker.huntsign` sobre Aust Raider, Aust Mage y Aust Fighter. Los Wereshark y
  Starfish visibles permanecieron sin marca, confirmando tanto el caso positivo como la exclusión
  de NPCs ajenos. Queda probado extremo a extremo que el cliente clasifica los objetivos desde
  sus relaciones retail al recibir `questNpcTag`; no se necesitan paquetes sintéticos ni ramas por
  quest/NPC.
