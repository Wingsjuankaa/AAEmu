# Checkpoint Point 0 — quest initial SupplyItem crosswalk V8

Fecha: `2026-07-31`

## Incidente

`2265 A Dead Man's Wish` quedó esperando al aceptar desde Fisherman Tugger.
La traza demostró el rechazo antes de insertar journal o inventario:

```text
03:24:14 CSStartQuestContextPacket
[AA8QuestStartGuard] Rejected quest 2265 for Dannia:
unavailable initial supply item 21604
reason=item_coverage_Unknown
```

MySQL confirmó antes del despliegue:

```text
quest 2265 activa: 0 filas
item 21604:        0 filas
```

La misión anterior sí había entregado y persistido `34004 x5`.

## Contrato AA8

```text
quest 2265, A Dead Man's Wish
Start 9987
  AcceptNpc 1862 -> Fisherman Tugger 10585
Initial Supply 9988
  SupplyItem 1336 -> item 21604 x1
  cleanup=1, destroy_when_drop=1, drop_when_destroy=1
  show_action_bar=1, try_equip=0
Ready 9989
  ReportNpc 4868 -> Flora 12022, alias 3190
Reward 9991
  6700 EXP
  item 23633 x1
  item 34000 x5
```

Dossiers:

```text
quest-2265.json
sha256=A9EAEB052DDB873177E4A92FA42CB5D78B5C8105360AF54013C9FAB8844327E5
forensic=profile_complete

item-21604.json
sha256=D36B4E5E61B810DC658CB0C619BC911A303A2A9B134E2F3B3697ED0C08ECB8DA
lifecycle=tombstone

item-34000.json
sha256=FDAE093E16A217794C83A195F5B2DF44BF554DD2035717726948403A94784D76
lifecycle=present

skill-35238.json
sha256=F22E688FAFD28818BBAFEA8321C406B97162B0BE3CF10C98BD854E117583F217
forensic=profile_complete
```

## Uso transversal del crosswalk

Fuente:

```text
quest-item-crosswalk-v1.sqlite3
sha256=38E5CE75C90B0E64367A69E182E301B844E0904628CA726442F2D08A8DD34709
```

La política selecciona solamente filas que cumplan simultáneamente:

```text
grant AA8 confirmado
grant_phase=initial_supply
selection_mode=fixed
QuestActSupplyItem
comparación crosswalk: overall=match, role=match, count=match
item lifecycle=tombstone
fila runtime existente category_id=64, impl_id=0
use_skill_id=0, buff_id=0, craft_id=0
sellable=0
cobertura runtime distinta de complete
```

Aplicada al runtime activo, esta política transversal encontró exactamente un
candidato seguro:

```text
quest 2265 -> item 21604 x1
```

Los otros huecos permanecen fail-closed:

```text
before: relations=1174 quests=1083 items=1111
after:  relations=1173 quests=1082 items=1110
```

El crosswalk no habilita contenido automáticamente; reduce y prueba el
conjunto que el builder puede auditar.

## Materialización corroborada de 21604

AA8 demuestra el ID y la relación exacta con quest 2265. La wiki compatible
corrobora `Sloane's Will`, Quest Item, Basic, nivel 1, no vendible y su vínculo
con `A Dead Man's Wish`:

- https://wiki.archerage.to/na-en/db/quests/2265
- https://wiki.archerage.to/na-en/db/items/21604

La fila ya heredada del compact 3.0 se comparó con la fuente:

```text
legacy compact sha256:
9FB1838113820D4F5BAC93BB7E79A3E51613CF7B2828B28545B59F506B4F4397

55 campos compartidos: exactos
field overrides:        0
filas nuevas importadas:0
9 columnas sólo-AA8:    padding 0 validado
```

La cobertura queda explícita:

```text
legacy_3_0_corroborated:AA8_quest2265_crosswalk_match:v1
```

No se presenta como fila nativa. Se habilitan únicamente initial supply,
inventario, transición Ready, persistencia y cleanup. Uso, skill, buff, craft,
equipo, venta, comercio y subasta permanecen deshabilitados.

## Cierre preventivo de recompensa

`23633 Gilda Star` ya tenía cobertura completa. `34000 Adventurer's Hardtack`
era una fila positiva AA8, pero seguía `phase_a_candidate`. Se promovió a
`complete` después de comprobar:

```text
item 34000 -> use skill 35238
skill 35238: cast 3000 ms, cooldown 10000 ms
10 skill_effects -> BuffEffect
10 buff_effects, chance=100, stack=1
10 buffs, duration=5000 ms
```

El uso de Hardtack no forma parte del primer retest; se probará por separado.

## Runtime y pruebas

```text
compact-8.0-runtime-point0-quest-initial-supply-crosswalk-v8.sqlite3
bytes=140087296
sha256=DA7F6026EDE6F9AE2E7B684BDF6BB199078ABF001C50CBD921F8DE50AADA295C

manifest sha256:
455FCE0DBF127AEFA61E09D699BD4CDEDF992A40A773B495E47BD5FC9FF8648C

dos builds deterministas: idénticos
quick_check=ok
integrity_check=ok
pruebas dirigidas V8: 7/7
suite Python quests:   113/113
AAEmu.Tests .NET 3.1:  321/321
ScriptCompiler tests:  0 errores, 8 warnings conocidas
```

El runtime parte del cierre de mercader Deven V1 y conserva sus 37 goods.

## Respaldo y despliegue

Se recreó exclusivamente `game`; `db` y `login` conservaron sus IDs.

```text
backup:
D:\Proyectos\AAemu\backups\pre-point0-quest-initial-supply-crosswalk-v8-20260731-234035

mysql-all.sql sha256:
01C68989AC414D0C66026AD1029052CFF3934882816191C4AAD87ED7C7A04B16

runtime anterior sha256:
1625ABD2DA6E6350A0F64B6ADAA90FF61CCD93FE32F480DB3DB282640B998E66

rollback image:
aaemu-game:pre-point0-quest-initial-supply-crosswalk-v8-20260731-234035

runtime montado sha256:
DA7F6026EDE6F9AE2E7B684BDF6BB199078ABF001C50CBD921F8DE50AADA295C

ItemManager:     24242 templates
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
1. entrar con Dannia;
2. aceptar A Dead Man's Wish exactamente una vez;
3. confirmar que el diálogo cierra;
4. confirmar exactamente un Sloane's Will, item 21604;
5. confirmar que la quest queda Ready y apunta a Flora;
6. no intentar usar el objeto;
7. detenerse antes de reportar a Flora.
```

Después de auditar logs y MySQL se habilitará el reporte. La segunda etapa
validará `6700 EXP`, `23633 x1`, `34000 x5`, cleanup de `21604` y persistencia.
