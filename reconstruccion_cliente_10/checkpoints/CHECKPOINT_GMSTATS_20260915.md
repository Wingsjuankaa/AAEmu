# GM stats temporales — 2026-09-15

Target E:/AAEmu/rama_10/server/AAEmu, rama rama_10, padre exacto
upstream/client_version/zone-10.0.2_r575. Sin cambio de rama, commit ni push.

Petición: ajustar estadísticas para probar el encuentro de Anthalon sin matarlo
por GM. AA10 ya tiene GetAttribute (consulta), AddBuff, Damage y Speed; no un editor
de bonificaciones. Padre conserva GetAttribute. AA8 CombatStat es comparador
estructural de comandos temporales, limitado a porcentajes de combate y sin
refresco cliente; no se copian sus contratos.

Se añade /stats (alias gmstats), acceso100 explícito tanto en configuración
versionada como montada, con show/list/set/damage/reset. Sólo self. Modelo
GmStatBonuses en Character, separado de gear/buffs, sin serialización a DB.
Unit.GetBonuses agrega ese aporte al mismo cálculo de los atributos existentes.
Las potencias usan milésimas (DamageEffect consume DpsInc*0.001) y los modificadores
de daño (1000+bonus)/1000, según los getters AA10 existentes. Sin nuevos contratos
de red. Los cambios a máximos nunca curan; al reset sólo recortan los valores
actuales que exceden el máximo y usan el relay habitual de puntos. Relog reconstruye
Character; los HP guardados se recortan en Character.EnterWorld.

La ventana C no se promete sincronizada: conserva su cálculo desde datos cliente.
La ayuda y Docs/AA10GmStats_es.md lo explicitan. No se modifica game_pak, compact
ni NPC/AI/quest. No se opera lifecycle de Zones.

Build Release: cero errores; suite 2836/2836, cero fallos/omitidos. Cuatro tests
nuevos verifican getters reales de daño, reemplazo/reset, aislamiento, conservación
de aportes de equipo/buffs, escalas de potencia/per-mille y rechazo atómico de
valores inválidos. Artefactos en E:/AAEmu/rama_10/artifacts/gmstats.

Desplegado Game, imagen y hashes en GMSTATS_20260915.manifest.json. Rollback imagen
aaemu-world:rollback-gmstats-20260915 y configuración montada respaldada en
E:/AAEmu/rama_10/backups/gmstats-20260915. Aceptación con ataques de Dannia pendiente;
la suite valida cálculo servidor, no la fase de huida de Anthalon.
