# Quest 10101: aparición de Anthalon en Delphinad

Target `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`; padre `upstream/client_version/zone-10.0.2_r575`. Se conservan reparaciones anteriores, incluido Return 1023 confirmado por el usuario. No commit/push.

## Diagnóstico nativo

El usuario cruzó el portal 1023 correctamente y quedó en la sala vacía con La guarida de Anthalon activa. Log `artifacts/quest10101/before.log` a las 22:19:05 UTC: TeleportEnded zone=384, X=1761.5, Y=2113.6, Z=273. A las 22:19:09 entra en sphere 3044, pero no se ejecuta skill ni spawner. Zone 384 está ZoneLoaded, instancia de Dannia 100.

Clausura r575 en `artifacts/quest10101/native.json`:

- sphere 3044, enter=true, SphereSkill detail 312, trigger 3, intervalo 3600000 ms. Geometría zone 384 local (745.588,1072.96,271.507), radio 16.5; origen world (1,1).
- UnitReq 69953 exige quest 10101 en Progress (kind32).
- sphere_skills 312: skill 44277, min/max_rate=100/100. Skill instantánea, objetivo propio, sin plot; skill_effect63370 -> effect83842 -> NpcSpawnerSpawnEffect6820.
- Efecto: spawner205923, lifetime0, activation=false, sin despawn por muerte del creador ni aggro del invocador.
- `zone_server/npc_spawners.g`: spawner205923 -> template22545, local (752.893,1063.05,272.997), rotación0.523599. Plantilla22545 (NPC20019) tiene activation_state=false, población máxima1, save_indun=true. Su comentario nativo indica expresamente que lo activa sphere3044.
- Objetivo quest10101: QuestActObjSphere868 / sphere3043, protegido por buff26463. La aparición no concede ese objetivo. La siguiente quest10102 usa sphere3045; tampoco se fuerza.

SphereGameData leía sphere_skills sin consumidor ni getter. CharacterQuests procesaba otras clases de área, pero ignoraba SphereSkill. Padre y AA8 no ofrecen un consumidor aplicable; no se copiaron contratos AA8. BugReports por 10101 y 10102 sin resultados.

## Corrección

Se expone GetSphereSkill y se conecta el evento de entrada a la habilidad original mediante Skill.Use y su flujo de efectos/Zone. Se activa únicamente la clausura verificada de esta sala (384/3044/312/44277, tasas100/100, entrada con trigger3). No se infiere el comportamiento de otras SphereSkills.

Se revalidan requisitos y ZoneLoaded. El intervalo se registra sólo cuando la habilidad acepta el uso, separado por personaje/instancia y conservado al salir/entrar de nuevo. No se ejecuta en cada tick mientras permanece dentro. El spawner nativo controla la población y el encuentro; no se conceden crédito, buffs ni quests artificialmente.

## Verificación y entrega

Restore/build Release correctos. 2831/2831 tests, cero fallos. Cuatro casos nuevos verifican la publicación del evento nativo SpawnAllOnceAndDeactivate para spawner205923/actor1046, intervalo de una hora, requisitos Progress frente a quest ausente/Ready, Zone no disponible/probe ausente, uso fallido reintentable, otras áreas y aislamiento entre jugadores/instancias. Suite reutiliza el efecto real para comprobar el evento de spawner; la ejecución completa de la habilidad en cliente queda pendiente.

Artefactos `E:/AAEmu/rama_10/artifacts/quest10101`. Respaldo `E:/AAEmu/rama_10/backups/quest10101-20260915`; rollback `aaemu-world:rollback-quest10101-20260915`. Se despliega sólo Game; no se opera lifecycle Zone ni se toca DB/compact/game_pak. Imagen, hashes DLL y startup en manifiesto asociado.

Aceptación: restaurar Zone 384 desde Control Center, entrar con Dannia con quest10101 en curso y acercarse al centro de la sala. Debe aparecer Anthalon. No abandonar ni completar la misión por GM; comprobar primero la aparición y después los eventos originales del encuentro.

## Aceptacion parcial del usuario: 2026-09-15 22:44 UTC

Spawn confirmado: sphere3044 -> spawner205923 -> NPC20019/bc1047. El NPC ejecuto skill43979 (invocacion de sacrificios). El usuario uso /die a las22:44:47; se registro muerte22:44:50, sin skill44012 ni buff26463. No se confirma fallo de la salida por umbral con esta muerte GM. La skill44012 exige UnitReq69579, kind26, valores1..50%HP; tiene casteo6000ms, aplica buff26463 de5000ms y cambia la salida/retira elementos del encuentro. La descripcion nativa explicita huida a <=50%HP, no objetivo de matar. Siguiente prueba: combate normal hasta el umbral, dejar terminar huida. No se modifica codigo ni se reinicia Game/Zone en este diagnostico. Evidencia escape-condition.json y encounter-user-after.log.
