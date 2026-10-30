# Estado forense AA10 actual

## Sandbox y fronteras recientes — 2026-10-29

El consumidor tiene un sandbox privado aceptado en E, Zone411 custom con
terreno/modelos retail406 y cliente español. No es una Zone retail descubierta
ni una nueva fuente autoritativa. Ver [sandbox-evidence.md](sandbox-evidence.md)
y los checkpoints del repositorio. Incluye entrada automática, dummies,
servicios y Hot Reload C# real con sesión conservada. Las fronteras de escena
y geometría de23592 son auditorías acotadas; no equivalen a completar la
consolidada pendiente descrita en el baseline histórico inferior.

## Exclusión vigente del proyecto — 2026-09-03

Item Smelting queda DEPRECADO / FUERA DE ALCANCE por decisión explícita del usuario.
Su frontera y bloqueos inferiores se conservan como historia, no como trabajo pendiente.
No reabrir auditoría, reconstrucción ni activación sin petición explícita; feature178 OFF.
La cola del consumidor continúa en Housing H2/H5-B, sin excluir Lunagem ni crafting.

## Baseline 2026-08-15

- Cliente Returns `10.0.2.13` r575 localizado y legible.
- SQLite completa: 552,178,688 bytes, SHA-256
  `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`,
  1,374 tablas, `quick_check=ok`.
- Compact retail: 440,823,808 bytes, SHA-256
  `68919695CDD12C7B9CB4AC9BEA3828132B83C95D7DCCF46AA3E113CEA756507F`,
  1,003 tablas, `quick_check=ok`.
- Las 1,003 tablas compact están presentes en full; 371 existen sólo en full.
- x2game release Bin64: SHA-256
  `2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76`.
- game_pak localizado con 68,963,162,112 bytes; hash global aún no congelado.
- Existen proyectos Ghidra para cliente release, cliente dev y Zone, más un
  análisis dedicate de daño. No existe todavía corpus Stage 15 consolidado.
- No existe todavía `reconstruccion_cliente_10` ni
  `aa10-client-knowledge.sqlite`.

## Último cambio

2026-09-03: auditoría acotada `housing-interactable-state-frontier` para casa437,
puerta4566 y ventanas4568. Relog aceptado por el usuario: permanecen abiertas.
Full/retail/runtime coinciden en siete consultas; checks de integridad OK y dos
outputs idénticos. Loader Zone RVA0xBEAA50 y asociación housing RVA0xBEB780 con
hash8936ce89 confirmado: `force_db_save` es bit0 del descriptor+0x10. No se cerró
el consumer de guardado World/DB ni una referencia web de persistencia tras
mantenimiento: reinicio nativo `unknown`, sin parche ni despliegue. Ver
`server/AAEmu/reconstruccion_cliente_10/checkpoints/CHECKPOINT_HOUSING_INTERACTABLE_STATE_20260903.md`.

2026-09-03: frontera Item Smelting auditada en cuatro fuentes congeladas, dos
builds idénticos con integridad OK; outputs43482/43489 ausentes incluso full y
target40000 ausente en compact retail. Corrección de evidencia anterior:
35525 sí usa SpecialEffect151. Selector/iterador/caller reanclados byte a byte
entre baseline Ghidra2735819 y PE actual405242e. Ver item-smelting-frontier.md
y checkpoint del repo CHECKPOINT_ITEM_SMELTING_AVAILABILITY_20260903.md.
Estado bloqueado por contenido; no desplegado ni aceptación jugable.

El 2026-08-19 se cerró además la frontera `migration-scaling-frontier` para
Bless Uthstin. SQLite, Lua retail, guía visual y Zone r575 confirman 45 filas,
funciones normal/especial, páginas de 0x1c, los opcodes C2G 0x1BD..0x1C2 y G2C
0x2EA..0x2F1, y el flujo Consume/Preview/Confirm. La evidencia negativa muestra
que General Merchant no vende 42822/42325 en esta build. El consumidor implementó
el reemplazo principal; reset, extensión y administración de páginas siguen
clasificados como semántica de mutación no promovida. Ver
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\migration-scaling-frontier\CHECKPOINT.md`.

El 2026-08-19 se incorporó `tools\lua-types.rc` como índice estructural de la
API Lua/X2, con manifest, inspector reproducible y límites de autoridad. El
primer uso cubrió 28/28 símbolos únicos del flujo Item Evolving ReRoll en el
catálogo y en las cadenas del `x2game.dll` operacional. Esto prueba presencia
de vocabulario, no ABI ni semántica. Ver
`Docs\AA10LuaTypesForensics_es.md` en el repositorio consumidor.

Ese mismo día se cerró la frontera Item Smelting en
`forensics\output\aa10-client-forensics\item-smelting-frontier`: 13/13 APIs Lua
resueltas, skill-object tipo 20 (`bool + u32 recipe`), resultado 0xCF sin byte
heredado y códigos 0/1/2 confirmados por el Lua retail. La SQLite contiene 32
recetas, pero 29–32 referencian los templates ausentes 43482/43489; conservar
esta evidencia negativa y no completar esos items por inferencia.

El baseline anterior se conserva para reproducibilidad. La copia retail
operacional observada el 2026-08-19 difiere de aquel snapshot:

- Compact retail actual: SHA-256
  `0ADAA070936F8AFBE0A60307C391CF1C08ECCB98DD48A32024D4F295C140FC86`.
- x2game release actual: SHA-256
  `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.

No reutilizar RVA ni conclusiones binarias entre ambos hashes sin reanclaje.

## Siguiente entregable

Crear Stage 00 determinista: manifest de artefactos, SHA-256 del game_pak,
inventario completo de binarios y superficies, y diff full/compact sin
descartes. Después crear Stage 10 con schema/column/row coverage.

## Bloqueos explícitos

- Identidad exacta de binarios dev/dedicate frente al release no consolidada.
- game_pak sin hash global en el baseline.
- Sin pipeline, manifests ni visor AA10 propios todavía.

## Frontera Garden combate/puntuación — 2026-09-09

Auditoría acotada: `garden-combat-20260909/score-contract.json` bajo el output AA10. Buff25655/trigger13605 produce Skill44268 cada segundo; flags nativos skip_validate_source+ignore_global_cooldown y tiempos cero. Consumer Zone SHA8936CE89, RVA0x4E4230 resuelve umbrales acumulados; RVA0x4E4490 suma delta y RVA0x4E45A0 resetea. Kind3/content2/quest10056 persistente y reset al retirar misión. Igualdad value2=2 cerrada por las trece ramas mutuamente excluyentes0..12; operadores0/1 de UnitReq130, UnitReq131 y variantes no aditivas181 continúan opacos. No se interpreta enum_comparison_operators como el enum de UnitReq. Consumidor servidor y pruebas en CHECKPOINT_GARDEN_COMBAT_SCORE_20260909.md; aceptación retail pendiente. Esta auditoría no equivale a completar una etapa consolidada.
