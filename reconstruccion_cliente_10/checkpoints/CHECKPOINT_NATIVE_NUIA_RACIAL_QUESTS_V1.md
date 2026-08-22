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

El defecto no estaba en la misión, los porcentajes de drop ni el estado reservado del personaje.
La reconstrucción de `x2game.dll` 10.0.2.13 probó que `SCQuestNotifierInit` (`0x287`) serializa un
booleano y su callback despacha el evento interno de UI `0x2A4`, que inicializa/recalcula el
notificador de objetivos. El paquete ya existía en el servidor, pero no tenía ningún productor.

`CharacterQuests.SendInitialState()` envía ahora `SCQuestNotifierInit(true)` una sola vez, después
de `SCQuests` y `SCCompletedQuests`. La solución es global y conserva la clasificación del cliente:
no contiene ramas por quest, item, loot pack o NPC, ni fuerza refrescos por cada muerte. Una
regresión de red fija el orden `0x132 -> 0x133 -> 0x287` y el booleano final `true`.

Build integral Release cerró con cero errores; pruebas focales **4/4**, suite completa
**1501/1501** y Stage 40 **8/8**, con 43.737 referencias habilitadas y cero hallazgos. Se desplegó
únicamente Game con imagen
`sha256:fe6bc46f715fa82cfe123ba2a10d1dca9955d1f418c61bba811df58aa5a61b5b`, DLL Game
`01aa807cc45a4253d870c44fec9be24db1e83062cc90930fb1edf1a70e22b437` y DLL World
`cdedc9577531e98fa7d0703b282d18e83680cc9b198981c8899d41afd9168003`. El rollback preservado es
`aaemu-world:10.0.2.13-r575-local-rollback-20260821-225455` ->
`sha256:69fcdba620e7cb6f168caf4021f3371f01d41add1511e957e62affdf7a4b7790`.
Game quedó healthy, sin reinicios, Strict 43.696/0, cargó 8.901 quests, abrió 1239/1240/1250 y se
registró en Login. No se inició, detuvo ni relanzó ninguna Zone y no se controló el cliente. La
aceptación dinámica requiere reconectar el personaje para recibir el paquete durante la selección
y verificar el marcador sobre cualquiera de los tres tipos de planta con 7131 activa.

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
