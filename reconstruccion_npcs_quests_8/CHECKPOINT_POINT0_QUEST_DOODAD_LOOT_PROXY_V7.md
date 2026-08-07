# Checkpoint Point 0 — quest doodad loot proxy V7

Fecha: `2026-07-31`

## Alcance

Reparación acotada de `2264 Sloane's Secret`. No modifica el protocolo ni la
lógica de compra de mercaderes.

El fallo se observó al interactuar con `Empty Ring Box`: la skill terminaba,
pero el servidor no podía crear el objeto de objetivo y la quest permanecía en
`0/1`.

## Evidencia AA8

El grafo nativo de `2264` conserva:

```text
Start 9981 -> AcceptDoodad 809 -> doodad 14134
Progress 9983 -> QuestActObjItemGather 1800
  item 24967 x1
  cleanup=1
  destroy_when_drop=1
  drop_when_destroy=1
  highlight_doodad=14310
  alias=1522
Ready 9985 -> ReportNpc 2096 -> NPC 10585
Reward 9986
  EXP 5400
  item 34004 x5
```

La interacción observada por el servidor usa `skill 17310` y alcanza la ruta
existente:

```text
doodad_func 9948
-> DoodadFuncLootItem 2482
-> item 24967 x1, 100%
```

La relación funcional se clasifica `server_observed_compatible`: el cliente
identifica el doodad nativo `14310`, mientras el runtime histórico conserva la
función compatible que la traza real demostró ejecutable.

Dossiers:

```text
quest-2264.json
sha256=B064F805C4E7219936CFBC83181CACBE564B7A8B7D175B40EF9B8DA27F64E876

item-24967.json
sha256=B7A3E66CB4C662920A53F1ED494FFBE6B55F8EC50B716F81B5C806C4FBD6B1F9
native_lifecycle=tombstone

item-34004.json
sha256=DB1CC839779E216B1F1C82E1A07116F9D523C869F0AFB74CA8949EA6773698AE
native_lifecycle=present

skill-35239.json
sha256=9B642F94C1CCFA7ED46DC52CC06FD2D021A62EC1F003D6725C948E6A7D997438
forensic_readiness=profile_complete
```

La wiki compatible sólo corroboró el nombre y la presentación de la misión y
del objeto; no fue autoridad para generar filas:

- https://wiki.archerage.to/na-en/db/quests/2264
- https://wiki.archerage.to/na-en/db/items/24967

Crosswalk:

```text
quest-item-crosswalk-v1.sqlite3
sha256=38E5CE75C90B0E64367A69E182E301B844E0904628CA726442F2D08A8DD34709
```

## Decisión de reconstrucción

`24967 Sloane's Will` es un tombstone: sobreviven referencias tipadas de
quest, pero no una fila positiva en el catálogo AA8 completo. Se sustituyó la
fila heredada por un proxy mínimo y explícito:

```text
authority=server_derived_accepted
category=Quest Item
impl=generic
bind=pickup
max_stack_size=1
pickup_limit=1
sellable=false
loot_quest_id=2264
```

Capacidades habilitadas:

```text
doodad_loot, inventory, quest_item_gather, persistence, cleanup
```

Capacidades deshabilitadas:

```text
item_use, open_paper, skill, buff, craft, trade, auction
```

Se eliminó la relación heredada `item_open_papers` de `24967`, ya que no está
respaldada por el cierre nativo. El proxy no se presenta como una fila nativa.

La auditoría detectó además que la recompensa nativa `34004 x5` seguía marcada
`phase_a_candidate`; el guard habría bloqueado la entrega de la misión. Se
promovió a `complete` sólo después de comprobar su fila AA8, `skill 35239`, sus
10 `skill_effects`, 10 `buff_effects` y 10 buffs de 5000 ms.

## Runtime

```text
compact-8.0-runtime-point0-quest-doodad-loot-proxy-v7.sqlite3
sha256=6C58249234B000F41B10994703F09D1E9F909C05DBEBC5FE4E6F4B6DBECA1792
bytes=140075008
quick_check=ok
integrity_check=ok
```

Dos construcciones consecutivas produjeron hashes idénticos para runtime y
manifiesto:

```text
runtime  =6C58249234B000F41B10994703F09D1E9F909C05DBEBC5FE4E6F4B6DBECA1792
manifest =7B61DBEAA9B1D9601BE67EDA2EC519C9788874DFA41445294664BDFCE078EA00
```

El censo directo de huecos doodad-loot cambió únicamente por `24967`:

```text
before: relations=746 quests=654 items=553
after:  relations=745 quests=653 items=552
```

## Validación

```text
prueba dirigida V7:       8/8
suite Python de quests:   106/106
AAEmu.Tests .NET 3.1:     318/318
ScriptCompiler tests:     0 errores, 8 warnings conocidas
git diff --check:         limpio para los artefactos V7
```

## Respaldo y despliegue

Se recreó exclusivamente `game`; `db` y `login` conservaron sus contenedores.

```text
backup:
  D:\Proyectos\AAemu\backups\pre-point0-quest-doodad-loot-proxy-v7-20260731-220359

mysql-all.sql:
  sha256=5DCE1061D5CFC48DA204C5401C383F5A60F09A9F8911E996E630C2EE091CF050

runtime V6 respaldado:
  sha256=6C8797A8F133DEDC4E1247B737160E5EB4818BF19A841A351238EAEAC0091C15

rollback image:
  aaemu-game:pre-point0-quest-doodad-loot-proxy-v7-20260731-220359

runtime montado read-only:
  sha256=6C58249234B000F41B10994703F09D1E9F909C05DBEBC5FE4E6F4B6DBECA1792

ItemManager:     24218 templates
ScriptCompiler:  0 errores, 8 warnings conocidas
Game 2239:       escuchando
Stream 2250:     escuchando
LoginServer:     registrado correctamente
RestartCount:    0
errores fatales: 0
```

## Retest manual controlado

Primera parada obligatoria:

```text
1. entrar con Dannia y confirmar que 2264 sigue activa en 0/1;
2. interactuar exactamente una vez con Empty Ring Box;
3. confirmar exactamente un Sloane's Will;
4. confirmar tracker 1/1 y estado Ready/Complete;
5. no usar el objeto y detenerse antes de reportar a Fisherman Tugger.
```

Después de auditar la traza y MySQL se habilitará la entrega. En esa segunda
etapa se comprobarán `5400 EXP`, `34004 x5`, cleanup de `24967` y persistencia
tras relog. El uso de `34004` será una prueba separada.
