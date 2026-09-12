# Garden: buff de rango intermitente — 2026-09-11

## Estado
Corrección server-required del evaluador de BuffTickEffect. 2737 pruebas pasan, incluida repetición de 120 ciclos. Aceptación retail pendiente: el usuario informa que el despliegue anterior NO resolvió el combate ni el parpadeo. No declarar Garden completo.

## Causa verificada
- Imagen anterior efectiva: 1195e8471e1e5e61ffbb466eeb53459afb2a8af193aaec29f544350e015f5c00.
- Buff ambiental 26390: permanente, tick 1000 ms. TickEffect 4486 / effect 83663 / DispelEffect 4774 retira tag 4497 solamente cuando unit_req 69741 (ExceptProgressQuestContext 72, quest 10056) pasa. TickEffect 4489 / effect 83680 / BuffEffect 33106 añade buff 25655 solamente cuando unit_req 69796 (ProgressQuestContext 32, quest 10056) pasa.
- El loader descartaba id y or_unit_reqs de buff_tick_effects; TimeToTimeApply y DoAreaTick sólo filtraban tags. Por tanto quitaban 25655 y lo reponían en el mismo tick. Dispel de 25655 también retiraba 26196 porque require_buff_id=25655.
- La recreación dispara trigger 13605 / SpecialEffect 50589 / SkillUse 44268 / plot4848. IMPORTANTE: event_id 12 es Started, NO OnTick. La interpretación del checkpoint anterior era incorrecta: la repetición proviene de recrear el buff, no de un trigger periódico de ese buff.
- Log previo: 02:39:30 crea 26196 para Dannia (1762), seguida de DispelEffect4774 y BuffEffect33106 en múltiples unidades; NPCs 19594,19943,19596, etc. ejecutan 44268. El log Server.log contenía 685174 líneas que coincidían con 26196/44268/Garden score (incluye coincidencias no relacionadas de doodads); no usar ese total como conteo exacto de casts.
- Full y compact runtime coinciden exactamente en la clausura consultada. tick-contract.json SHA256 619b8387aa0ae11b0a069455af7d5bd1aed92e32e5d18174da41683f7028f66c.

## Cambio
- TickEffect conserva su Id y OrUnitReqs; SkillManager carga ambos.
- UnitRequirementsGameData.CanApplyBuffTickEffect evalúa las filas habilitadas del owner BuffTickEffect con AND/OR y el receptor del efecto; no usa el CurrentTarget de combate. Sin requisitos conserva la ejecución.
- BuffTemplate aplica la puerta antes de efectos periódicos individuales y a cada receptor de ticks de área.
- Se conservan datos nativos, tiempos, paquetes y políticas existentes. No se modifica game_pak, SQLite, puntuación acumulada ni se opera lifecycle de Zones.
- Padre exacto upstream/client_version/zone-10.0.2_r575 y comparador AA8 presentan la misma carencia de Id/requisitos. No son autoridad para omitirlos.

## Verificación y límites
- Release build sin errores; suite 2737/2737. BuffTickRequirementsTests ejercita el pipeline TimeToTimeApply con BuffEffect/DispelEffect reales: una instancia de patrulla/rango tras 120 ticks, retirada de ambos al dejar Progress, rechazo de NPC/sin misión, AND/OR, filas deshabilitadas y efectos sin requisitos.
- Las pruebas existentes de Hiram, buffs, plots y Garden siguen pasando.
- No se reconstruyen en este cambio los comparadores de ZoneScoreLevel distintos de igualdad, requisitos todavía no soportados o KillAny. No se afirma resuelto todo el contador/premios de Garden. El evaluador conserva el rechazo de requisitos desconocidos.
- Prueba retail: arrancar el perfil Garden del personaje desde Control Center, entrar con quest10056 en Progress, observar el rango al menos 15 s y probar un casteo estando quieto. Verificar ausencia de retiro/recreación 25655/26196 y de spam 44268 en NPCs antes de aceptar el combate.

## Despliegue / recuperación
Respaldo E:/AAEmu/rama_10/backups/garden-buff-20260911/aaemu_game.before.sql. Imagen anterior conservada como aaemu-world:rollback-garden-buff-20260911. Rollback de código: etiquetar esa imagen como aaemu-world:10.0.2.13-r575-local y recrear solamente Game con los mismos compose. No restaurar la DB sobre progreso posterior; no hubo migración en esta entrega.

Imagen desplegada: `8ca2a526c276bd5f418fa1740da3fc3096bcb69f35696704f7278857d677f225`. DLL Game efectiva: `e12a81f13005b8a791bcb20ab7e3f5659dbb91fd0355043f85ca8f10db44afc1`. Game recreado 12:24:45 UTC.
