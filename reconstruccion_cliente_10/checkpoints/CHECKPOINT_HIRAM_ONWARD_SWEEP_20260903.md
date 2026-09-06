# Barrido de misiones Hiram y posteriores — r575

## Alcance y resultado

Petición: barrido completo tras tres bloqueos consecutivos por actores/objetos
ausentes. La nueva captura muestra Hiram Guardian Statue9212, activar estatua
para obtener Purifying Energy. El usuario ya avanzó tras Andega9174; se registra
esa aceptación retail en su manifest.

Target `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`, HEAD
`bdad11fec1493c43a854369e707de72a20f26f86`. Padre consultado mediante fetch:
`upstream/client_version/zone-10.0.2_r575`, SHA
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. El padre no aporta el catálogo
restaurado; se reutilizan las primitivas AA10 existentes y aceptadas, sin port AA8.

Se auditan **439 misiones**, capítulos18–34, categorías180/183/200/206/208/210/225
y las misiones de zonas266/270/294/295/297/298/299/301/302/304/305/311. El SQL
exacto está versionado en `audit_hiram_onward_quests.py`. Son423 templates doodad,
299 NPC y199 ítems referenciados. No faltan templates NPC/ítem ni detalles de actos
habilitados; full y compact coinciden en los detalles auditados.

El scanner encuentra978 placements main_world y201 placements en cuatro mundos
de instancia. **975 placements main_world faltaban tanto en fuente como en el
bind mount**, con dependencias hacia220 misiones. Se restauran todos en un único
overlay nuevo `doodad_spawns_aa10_hiram_onward_r575.json`, sin editar los catálogos
anteriores. Incluye679 ubicaciones client_doodad y296 no-client, siempre placements
explícitos del game_pak. No se infieren posiciones desde marcadores ni se agregan
NPC genéricos para reemplazar actores personales.

Cada registro conserva XYZ, escala, Euler derivados del quaternion original y
el único grupo Start de su template. Se comprueban full/compact para templates,
grupos, funciones y detalles de todas las entidades con placement. No se fuerza
una fase visible que omita QuestReact, ModelChange o requisitos individuales.

## Estatua de la incidencia

- Quest9212, objetivo ItemGather4244: item46452, highlight doodad13319.
- Doodad13319: client_doodad/once_one_man, prefab mother_startue_sw.
- **21 ubicaciones nativas** restauradas. Start39119, modelo encendido.
- Func35959/Use9995 usa skill39660 y pasa a43623; Timer18525 devuelve a39119
  después de10000ms. Fase38304 conserva QuestReact251/252/1610 para9176/9956/9212.
- Skill39660 incluye Effect72649 -> GainLootPackItemEffect3892 -> loot pack12628
  -> Loot94168: item46452, cantidad1, drop_rate10000000. El efecto existente admite
  esta interacción sin consumir item fuente. También están Interaction72105 y
  Buff73142. No se cambian probabilidades ni contadores de misión.

## Cobertura y límites de aceptación

Se extrajeron read-only180 archivos nativos `zone_server/npc_spawners.g`.
233 NPC referenciados tienen spawner nativo;49 tienen proxy o SpawnEffect;
17 no presentan una fuente estática en las búsquedas realizadas. Algunos son
alternativas de grupos de caza, por lo que ausencia de ese miembro no demuestra
bloqueo del objetivo. Los casos directos quedan identificados en el informe.

179 ítems tienen fuente en loot, suministro de misión, función doodad, efecto
especial27, producto de skill o crafting. Los5 restantes son46496/46497/46498
(aceptación de misiones),52589 (objetivo10779) y54453 (aceptación/ArchePass).
Se conserva evidencia de todas sus columnas item_id en
`remaining-item-references.json`; no se inventan recompensas ni drops.

La ausencia de main_world no se considera automáticamente un spawn faltante:
40 templates tienen placements de instancia y40 no tienen placement en los worlds
extraídos. Los201 placements de instancia corresponden a phantom_of_delphinad,
restraint_of_power, mount_ipnir_story y hanging_gardens_of_ipna; no tienen catálogo
de mundo en la fuente actual. No se habilitan instancias incompletas añadiendo sólo
sus objetos. Estos casos, invocaciones y recorridos completos requieren cierre
específico; el barrido estático no equivale a haber completado439 misiones retail.

## Evidencia reproducible

Raíz: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\hiram-onward-sweep`.

- `audit-before.json` / `audit.json`: cobertura antes/después y referencias por misión.
- `native-contracts.json`: full/compact para fases y funciones.
- `all-world-placements.csv`, `placements.csv`, `pak-index.tsv`: extracción r575.
- `supplier-coverage.json`, **`quest-coverage.csv`**: informe por cada misión.
- `npc-native` y `npc-extract.log`: placements de NPC administrados por Zone.
- `manifest.json`, logs restore/build/tests/image/shutdown/startup: entrega.

Scripts versionados: `audit_hiram_onward_quests.py`,
`audit_hiram_quest_suppliers.py`. El primero sólo genera el overlay con
`--write-overlay`, exige que no exista y rechaza divergencias fuente/runtime.
Sin flag es auditoría read-only, incluidas unicidad, orientación, escala y fase.
PakDoodadScan ahora admite `--all-worlds` y exporta W/roll/pitch además de las
columnas existentes, para no perder inclinaciones de los objetos.

## Gates y operación

Restore correcto; build Release0 errores/111 advertencias (incremental final); **1784/1784 pruebas**.
La nueva regresión compara975 placements contra fixture nativo y verifica las
21 estatuas y la deserialización de sus fases. No hay cambios de código de juego.

Despliegue autorizado por preferencia permanente del usuario. Game detuvo con
exit0 a02:25:45UTC (despliegue final); SaveManager terminó correctamente. Respaldo DB y catálogo
previo en `E:\AAEmu\rama_10\backups\hiram-onward-sweep-20260903`. DB SHA256
`19264b267fc8839bf5f377521cebe8082d39fb97ed262665c819d83a64efa75b`.
Rollback imagen `aaemu-world:rollback-pre-hiram-onward-sweep-20260903`:
`11d310722649a29ef7218bdc700f9f7724d7efdd501d59449aa63be8d6fcd203`.
Como el catálogo nuevo es un bind mount, un rollback requiere también retirar
únicamente ese nuevo archivo del mount (con Game detenido); retag de imagen solo
no revierte el cambio. SQLite/client/game_pak no modificados.

Imagen desplegada `1f1ed96af79261dc9e9595e6f75b5d990ca67ecbe8fec78bea2b098eac302aab`.
Overlay SHA256 `e0e510e2bca245368673d7493263cfbc8d444839f47bc96eddc9a378fecd3755`
idéntico en fuente, mount y contenedor. Game DLL actual
`9af07d423e9dcb747bb5a938462ce72e9b5fe6fbfd976f03e9f12ca0f08eb43b`.
Startup/health/cantidad final en manifest. DB/Login no se recrean. Codex no opera
Zones: el usuario relanza351 desde Control Center y activa la estatua con Dannia.

Verificacion final:45785 doodads main_world (44810+975), startup02:27:05UTC,
70.59s, Login registrado, healthy/0 reinicios. Auditoria postdespliegue:
978 ubicaciones nativas cubiertas,0 ausentes. Backup final:aaemu_game-final.sql.
Suite1784/1784 correcta; aceptacion retail de este barrido pendiente.
