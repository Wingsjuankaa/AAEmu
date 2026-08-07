# Checkpoint — Truth Extraction 2261 / Hypnotic Staff 16293

Fecha: `2026-07-31`  
Cliente: ArcheAge Kakao `8.0.3.12 r558734`

## Fallo observado y causa

Dannia abrió la oferta `2261 Truth Extraction`, pero el diálogo quedó
esperando porque el servidor rechazó el inicio sin poder crear el objeto
inicial:

```text
[AA8QuestStartGuard] Rejected quest 2261 for Dannia:
unavailable initial supply item 16293, reason=missing_item_template
```

El personaje salió limpiamente del mundo y MySQL confirmó que no quedó una
quest 2261 parcial ni un item 16293 persistido.

## Autoridad y cierre AA8

Los dossiers del cliente prueban:

```text
quest 2261
  Supply component 9965
    QuestActSupplyItem 2273 -> item 16293 x1
    show_action_bar=1, cleanup=1
  Progress component 9967
    QuestActObjItemUse 598 -> item 16293 x1
    quest_act_obj_alias_id=6578, use_alias=1
  Reward component 9970
    QuestActSupplyExp 3933 -> 4500 EXP
    QuestActSupplyItem 8881 -> item 18791 x5

skill 13886
  plot 383
  target hostile, selection target, target_unit_param=119
  range 0-20 m, cooldown 10000 ms
  8 plot events, 7 next events, 14 effects
```

Los efectos requeridos están presentes: ocho SpecialEffects, BuffEffects
6728/6731, buffs 1648/3862 y BubbleEffects 1845/1846/1847/1875.

La fila positiva de `item 16293` no existe en el catálogo completo de items
AA8. El dossier lo clasifica como `tombstone`; por eso no se declara una falsa
recuperación nativa ni se copia una fila histórica 3.0.

La wiki compatible sólo corroboró nombre y flujo visibles:

- https://wiki.archerage.to/na-en/db/quests/2261
- https://wiki.archerage.to/na-en/db/items/16293
- https://wiki.archerage.to/na-en/db/skills/13886

## Reparación

Se restauraron seis filas/cambios que sí son nativos de `game11`:

```text
quest_act_obj_aliases[6578]
quest_act_obj_item_uses[598] alias/use_alias exactos
quest_act_supply_exps[3933]
quest_act_supply_items[8881]
quest_acts[64103]
quest_acts[65631]
```

Se añadió una sola fila derivada y auditada:

```text
item 16293
classification=server_derived_accepted
provenance=server_derived_accepted:quest2261_native_tombstone_use_proxy:v1

habilitado:
  quest supply, inventario, barra temporal, skill 13886,
  QuestActObjItemUse, persistencia, cleanup

deshabilitado:
  trade, venta, subasta, craft, buff, equipo
```

El censo de SupplyItem incompleto cambia exclusivamente así:

```text
antes: 999 acts / 960 item IDs incompletos
después: 998 acts / 959 item IDs incompletos
```

## Artefactos y validación

```text
builder:
  build_point0_quest_use_proxy_v6_runtime.py

runtime:
  D:\Proyectos\AAemu\client_kakao\
  compact-8.0-runtime-point0-quest-use-proxy-v6.sqlite3

sha256:
  6C8797A8F133DEDC4E1247B737160E5EB4818BF19A841A351238EAEAC0091C15

manifest:
  generated/point0-quest-use-proxy-v6-runtime-manifest.json

dos builds SQLite:       SHA-256 idéntico
PRAGMA quick_check:      ok
PRAGMA integrity_check:  ok
pruebas dirigidas:       8/8
suite Python quests:     98/98
suite AAEmu.Tests:       314/314
ScriptCompiler tests:    0 errores, 8 warnings conocidas
```

## Retest manual por etapas

Primera interacción:

```text
1. entrar con Dannia;
2. aceptar Truth Extraction una sola vez;
3. confirmar cierre del diálogo y aparición de la quest;
4. confirmar exactamente un Hypnotic Staff y su acción temporal;
5. detenerse antes de usarlo.
```

Después de auditar logs/MySQL se probará una sola vez la vara sobre el objetivo
Bloodhand indicado. Luego se verificará reporte, `4500 EXP`, `18791 x5`,
cleanup y persistencia tras relog.

## Despliegue

Desplegado el `2026-07-31` recreando exclusivamente el servicio `game`.
Los contenedores `db` y `login` conservaron sus IDs.

```text
backup:
  D:\Proyectos\AAemu\backups\
  pre-point0-quest-use-proxy-v6-20260731-205351\

mysql-all.sql sha256:
  4ED06B345966BCADA5E9CF16E42089D15417140FCC671E499FE38E54CD04CF52

runtime anterior respaldado sha256:
  76F1D8A82B1ECEA85FEECAA3A8A114F1BEA9001C6CB8F34D160CE3284FD8EE77

rollback image:
  aaemu-game:pre-point0-quest-use-proxy-v6-20260731

runtime montado read-only sha256:
  6C8797A8F133DEDC4E1247B737160E5EB4818BF19A841A351238EAEAC0091C15

ItemManager:       24218 templates
ScriptCompiler:    0 errores, 8 warnings conocidas
Game 2239:         escuchando
Stream 2250:       escuchando
LoginServer:       registrado correctamente
RestartCount:      0
errores fatales:   0
```

Estado: listo para la primera interacción del retest manual.
