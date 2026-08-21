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
| Skill-object de interacción desconocido | Captura AA10 viva: `CSStartSkill` recibió flag 28 y dejó exactamente 8 bytes sin consumir. Se implementó type 28 como dos `u32` opacos antes de `inputDirection`. |
| Supply items de 2255/2258/2259/2260 | No se copió el parche AA8: Stage 40 AA10 reporta cero productores faltantes y la ruta AA10 existente conserva suministro/reintento idempotente. |
| Selección de report doodad/reward y diálogo de 2532 | Ya cerrada en AA10 y confirmada durante la prueba anterior; no se duplicó lógica AA8. |
| Talk objective (por ejemplo 2486) | El paquete AA10 conserva npcObjId, quest, component y act y publica el evento explícito; no depende de `CurrentTarget`. |
| Quest 3993 con varios Progress | El motor AA10 nuevo evalúa todas las components activas y los objetivos se serializan hasta 10; no se portó el reconciliador del motor legado AA8. |
| Quest 4411 / doodad 14125 | Fase inicial explícita 41603 más guardia anti-recursión de skill 41999. |

## Cambios y garantías

- `DoodadSpawner` acepta el `FuncGroupId` del placement, valida pertenencia al template y lo fija
  antes de `InitDoodad`.
- El catálogo `doodad_spawns_aa10_client_quest_proxies.json` contiene exactamente los 11 actores
  lógicos usados por la cadena Nuia auditada.
- La fase personal sólo se habilita para templates `once_one_man`, quests activas en Progress y
  fases sin funciones de fase. Cualquier caso más complejo falla cerrado.
- Type 28 consume y reenvía el cuerpo completo sin inventar semántica para sus dos valores.
- No se aceptan cuerpos NPC decorativos como reemplazo genérico de un doodad objetivo.

## Validación automática y aceptación pendiente

- Build Game: correcto, 0 errores.
- Unitarias: **1477/1477**, 0 errores.
- Stage 40 strict: pass, 55/55 quests Nuia, 344/344 actos, 0 no soportados.
- Tests nuevos: catálogo/fases, validación de fase inicial, fase `once_one_man`, anti-recursión y
  wire type 28 de 10 bytes incluyendo `inputDirection`.

La aceptación manual debe recorrer, en orden, 2256 (aparece/entrega en 14073), 2257 (interacción
41925 y obtención de item 16287), un actor representativo de cada bloque 14109–14124, 3993 y 4411.
Abandonar/reaceptar sigue siendo una prueba útil, pero ya no es un requisito de despliegue. Zone y
cliente permanecen bajo control del usuario.

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
item de esa cadena. La aceptación dinámica pendiente consiste en reobtener el tomo y verificar la
llegada a Lacton con la Zone 142 ya levantada por el usuario.

La extensión cerró con build Release sin errores y **1479/1479** pruebas unitarias en Debug y
Release. Game cargó 111 recalls y 24 worldgates, volvió a pasar el coverage gate estricto con
43.696 actos y cero hallazgos, abrió 1239/1250 y se registró en Login.
