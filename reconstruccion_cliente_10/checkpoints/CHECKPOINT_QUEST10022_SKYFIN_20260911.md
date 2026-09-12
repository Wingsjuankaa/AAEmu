# Quest10022: detección del Skyfin

Target rama_10, repositorio E:/AAEmu/rama_10/server/AAEmu. HEAD fd53b458573572cc354c8564293f274801d9aa3e; padre upstream/client_version/zone-10.0.2_r575 (7babcb3a706c64295b5aaaeec8abe57e4d09b4da). Reparación server-required, sin cambios de cliente ni datos. Conserva cambios ajenos, daño/proyectiles y puntuación Garden.

## Evidencia

Usuario confirma recompensa Garden recibida y pasa a misión de historia «Los sentidos de un Skyfin». NPC19990, mascota de Dannia, habilidad43798. Log artifacts/skyfin-live.log a14:57:56 registra CSStartSkill caster1763, SkillTl810, Started/Fired/Ended sin reacción de objetos. No es una petición ausente ni cooldown rechazado.

SQLite r575: habilidad43798 Source/Self, radio20, TargetAreaCount1, sin plot ni skill_effects. La reacción está en DoodadFuncSkillHit5555 (skill43798), doodad14916 grupo44090 (modelo oculto a://invalid), función40048 ->44101 (modelo garden_close_stone_04.cgf visible). El mundo ya cargó esos spawns; el log registra Obj101439..101442 entre otros. No se necesitan spawns inventados ni IA que camine hacia una posición artificial.

La fase44101 ofrece skill43856 ->44106. Su efecto83050/GainLootPackItemEffect4358 entrega pack13110: item48953 entre18 y32 unidades. Quest10022, objetivo4471, pide100 y resalta doodad14916/fase44101. La descripción nativa de43798 indica detectar energía en20m; no describe navegación automática de la mascota.

Clausura autoritativa/runtime idéntica en artifacts/skyfin-contract.json, SHA256 fd801c5c98c4b97db66528280e9e4512a55c00985f5fdf4c9417f159a07f525f. Incluye skill, efectos, función de detección, fases, loot y objetivo. TargetUnitParam119 se carga pero no se utiliza actualmente; no se adivina su semántica ni se modifica por este arreglo.

## Causa y reparación

ApplyEffects encontraba los objetos del radio y añadía al propio caster. Después ordenaba por distancia y truncaba a TargetAreaCount1, seleccionando al Skyfin a distancia0. OnSkillHit sólo recorría esa lista truncada; ningún objeto oculto podía reaccionar.

Ahora las notificaciones OnSkillHit recorren una sola vez los candidatos distintos ya filtrados por radio y relación, antes del límite de targets de efectos. Los efectos y dados de combate conservan su selección y límite. No se envían paquetes sintéticos ni se recastea. Doodad.OnSkillHit conserva matching de habilidad, ownership y fases.

AA8 conserva OnSkillHit para todos los candidatos del radio; aporta contraste de primitiva compartida, no autoridad para copiar radios ni protocolo. El padre AA10 local contiene el truncado anterior. No se realizó decompilación de la primitiva; el contrato observable de esta skill y su objeto está cerrado por datos AA10 y la reproducción.

## Pruebas y despliegue

DoodadAreaSkillTargetTests reproduce el cast Self/Source radio20 count1 con objetos a5,19 y21 metros. Antes del cambio, falla near.Data esperado1/real0; después, reaccionan los dos cercanos una vez, el lejano no y el efecto de prueba conserva un solo target (caster). Las pruebas existentes cubren Workbench40467, selección de centro, target único y SourceOnce. No se automatizó la recolección retail.

Suite Release2759/2759, cero fallos. Logs skyfin-red.log, skyfin-tests.log, skyfin-build.log. Respaldo E:/AAEmu/rama_10/backups/skyfin-20260911-150946 (DB/log/World); rollback aaemu-world:rollback-skyfin-20260911-150946. Manifest adjunto contiene imagen y DLLs desplegadas. No se operan Zones ni game_pak.

Aceptación pendiente: usuario inicia perfil Garden, vuelve a entrar, invoca Skyfin, usa detección dentro de20m de una energía oculta. Debe aparecer el objeto recolectable. Recogerlo mediante interacción normal debe aumentar el objetivo entre18 y32; repetir hasta100. El marcador de misión puede indicar un área más lejana que el radio de la habilidad. No anunciar navegación automática ni dar la misión por completada mediante comando.
