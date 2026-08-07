# Checkpoint — loot de quest tombstone 2263/24126

Fecha: `2026-07-31`  
Cliente: ArcheAge Kakao `8.0.3.12 r558734`

## Fallo observado

Dannia aceptó `2263 A Deadly Plot`, mató un Bloodhand Duelist y vio
`24126 Bloodhands' Instructions` en la ventana de loot. Al recogerlo, el
cliente mostró `Your bag is full`, aunque MySQL confirmó sólo `12/50` objetos
en el bolso.

La traza exacta fue:

```text
23:49:01 quest 2263 -> Progress / QuestActObjItemGather
23:49:28 CSLootItemPacket iid=203276507217921 count=1
23:49:28 SCLootItemFailedPacket
```

El loot podía existir como entrada temporal porque `CreateLootDropItems` sólo
necesita el `template_id`. La transferencia al bolso llamaba
`AcquireDefaultItem`, que no podía construir el template y devolvía `false`;
la ruta histórica convertía cualquier `false` en `BagFull`.

## Clausura AA8

```text
quest 2263
  Progress component 9978
  QuestActObjItemGather act 24956 / detail 2046
  item 24126 x1
  cleanup=1

loots
  item 24126
  8 loot packs
  drop_rate=10000000 en los 8
  min=max=1
```

El dossier forense clasifica `item:24126` como `tombstone`: existe una
referencia tipada nativa, pero el ID está ausente del catálogo positivo
completo de `items` de AA8. No se copió una fila 3.0 ni se afirmó haber
recuperado una fila nativa inexistente.

La wiki compatible corroboró la secuencia visible:

```text
quest 2263 -> collect 1 item 24126 -> report to Chloe
item 24126 -> Book, Basic, level 1, cannot sell
```

Corroboración solamente:

- https://wiki.archerage.to/na-en/db/quests/2263
- https://wiki.archerage.to/na-en/db/items/24126

## Decisión de reconstrucción

Se creó un proxy mínimo `server_derived_accepted`, limitado a la función que
la propia quest todavía exige:

```text
permitido:
  loot -> inventario -> ItemGather -> persistencia -> cleanup

deshabilitado:
  use, open paper, skill, buff, craft, trade, auction

seguridad:
  generic impl_id=0
  max_stack_size=1
  bind on pickup
  sellable=false
  loot_quest_id=2263
```

La cobertura declara explícitamente:

```text
server_derived_accepted:quest2263_native_tombstone_proxy:v1
```

No se presenta como `client_compact_8` ni `game11_native`.

## Alcance transversal medido

Antes del proxy, el runtime contenía esta familia de huecos:

```text
743 relaciones QuestActObjItemGather + loots sin definición completa
590 quests
532 item IDs
```

Después de reparar únicamente `2263/24126`:

```text
742 relaciones
589 quests
531 item IDs
```

El resto permanece fail-closed. Este censo demuestra el patrón, pero no
autoriza una importación global sin dossiers y evidencia por objeto.

## Artefactos

```text
builder:
  build_point0_quest_loot_proxy_v5_runtime.py

runtime:
  D:\Proyectos\AAemu\client_kakao\
  compact-8.0-runtime-point0-quest-loot-proxy-v5.sqlite3

sha256:
  76F1D8A82B1ECEA85FEECAA3A8A114F1BEA9001C6CB8F34D160CE3284FD8EE77

manifest:
  generated/point0-quest-loot-proxy-v5-runtime-manifest.json
```

Dossiers:

```text
quest-2263.json
sha256=9D918B408DDDCE7A427E5E64301EC6B39562A88D1328621B0865889CEC0BA519

item-24126.json
sha256=EAA6EEAE0A6B4583E8C66D764F96CA9680DCF1403ACE98110C8F99FC3DBAF9C2
```

## Validación previa al despliegue

```text
dos builds SQLite:        SHA-256 idéntico
PRAGMA quick_check:       ok
PRAGMA integrity_check:   ok
pruebas dirigidas:        5/5
suite Python quests:      90/90
suite AAEmu.Tests:        314/314
ScriptCompiler en tests:  0 errores, 8 warnings conocidos
```

## Retest manual controlado

Después del despliegue:

1. matar exactamente un Bloodhand Duelist;
2. recoger `Bloodhands' Instructions` una sola vez;
3. confirmar que desaparece el mensaje falso de bolso lleno;
4. confirmar exactamente un `24126` y tracker `1/1`/Ready;
5. detenerse antes de reportar a Chloe;
6. auditar logs y MySQL;
7. sólo entonces reportar, verificar cleanup y reloguear.

## Despliegue y disponibilidad

Desplegado el 2026-07-31 recreando exclusivamente el servicio `game`.
Los servicios `db` y `login` conservaron sus contenedores.

```text
backup MySQL:
  D:\Proyectos\AAemu\backups\pre-point0-quest-loot-proxy-v5-20260731\mysql-all.sql
  sha256=9C6571B147F8D78F1B2BE0489A3AAC532BDF03E53092B080D5B449661ACB326E

rollback image:
  aaemu-game:pre-point0-quest-loot-proxy-v5-20260731

runtime montado:
  D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-point0-quest-loot-proxy-v5.sqlite3
  sha256=76F1D8A82B1ECEA85FEECAA3A8A114F1BEA9001C6CB8F34D160CE3284FD8EE77

ItemManager:       24217 templates cargados
ScriptCompiler:    0 errores, 8 warnings conocidos
Game 2239:         escuchando
Stream 2250:       escuchando
registro en Login: correcto
RestartCount:      0
errores fatales:   ninguno
```

Estado: listo para el retest manual controlado de los pasos anteriores.
