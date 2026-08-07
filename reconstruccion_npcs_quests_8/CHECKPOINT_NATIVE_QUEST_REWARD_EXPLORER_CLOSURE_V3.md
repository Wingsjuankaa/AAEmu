# Checkpoint — cierre nativo de recompensa y cajas Explorer V3

Fecha local: 2026-07-31  
Autoridad: ArcheAge Kakao 8.0.3.12 r558734  
Quest: 2260, `Battle by the Bay`  
Componente Reward: 9962

## Fallo demostrado

El cliente enviaba `CSCompleteQuestContext quest=2260 selected=2`, pero el
servidor rechazaba la entrega con `reason=invalid_selective_reward`. El compact
V2 sólo contenía las recompensas fijas del componente 9962; faltaban las tres
alternativas selectivas, la experiencia y el cobre. El intento no produjo una
mutación parcial: Dannia conservó la quest activa y no recibió la caja.

Las cajas Explorer 47985, 47986 y 47987 tampoco tenían cerrado su grafo de uso:
faltaban `skill_effects`, los efectos `GainLootPackItemEffect`, sus detalles y
los loot packs del servidor.

## Cierre AA8 reconstruido

```text
Reward 9962
  act 64100 QuestActSupplyExp detail 3930 -> 2800 EXP
  act 65260 QuestActSupplySelectiveItem detail 3655 -> 47985 x1
  act 65261 QuestActSupplySelectiveItem detail 3656 -> 47986 x1
  act 65262 QuestActSupplySelectiveItem detail 3657 -> 47987 x1
  act 65675 QuestActSupplyCopper detail 3823 -> 2500 copper

47985 Moonrise Cloth Component Crate
  skill 42226 -> effect 78590 -> loot pack 12951
  48018, 48020, 48021 x1

47986 Moonrise Leather Component Crate
  skill 42228 -> effect 78592 -> loot pack 12953
  48025, 48027, 48028 x1

47987 Moonrise Plate Component Crate
  skill 42230 -> effect 78594 -> loot pack 12955
  48032, 48034, 48035 x1
```

Los nueve renglones `loots` son la única derivación del servidor: la tabla no
existe en el cliente y cada descripción AA8 enumera de forma exhaustiva sus
tres resultados. No se incorporaron filas históricas 3.0.

## Evidencia de autoridad

```text
client compact
sha256=4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57

game11
sha256=E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031

quest-2260.json
sha256=574CA90A7E98B863C491610D00D965F3D3C0512C1AE38C9AAC086286679B8549

item-47985.json
sha256=ACE0CA3AE511D4E6CC3F9997DE9411DCA4BF91F937DAEBC3BFC452AAF889E6DB

item-47986.json
sha256=80F334C41446DB05AD937429A07F543BC3BBA268F7A2DC05EAEAD9178D1EC594

item-47987.json
sha256=C8D2B58C938266ABA6FF00C5EFAC9A339C3CFF9FE18C1649A8B385147A28C565
```

La URL compatible de wiki quedó registrada sólo como corroboración potencial;
no aportó filas al runtime porque no devolvió contenido durante esta ejecución.

## Artefactos y validación

```text
compact-8.0-runtime-point0-quest-reward-explorer-stack-v3.sqlite3
sha256=171AABCAC72D1333439433396B70728F9786BB73E0A3054FA2A56E467EC53203
bytes=140025856

dos builds deterministas: hash idéntico
quick_check=ok
integrity_check=ok
orphan_loot_items=0
regresiones Python del stack quest=26/26
suite AAEmu.Tests .NET Core 3.1=311/311
ScriptCompiler=0 errores, 8 advertencias históricas
```

Builder:
`build_native_quest_reward_explorer_closure_v3_runtime.py`

Regresión:
`test_native_quest_reward_explorer_closure_v3.py`

Manifiesto:
`generated/native-quest-reward-explorer-closure-v3-runtime-manifest.json`

Backup MySQL previo al despliegue:

```text
D:\Proyectos\AAemu\backups\quest-reward-explorer-v3-20260731-2130\mysql-all.sql
sha256=D01F88C663657928DFDA4A9A11B26866F7B3D90C4274E5805E143EF7A3AAE54F
```

Despliegue:

```text
servicio recreado: game solamente
compact montado sha256=171AABCAC72D1333439433396B70728F9786BB73E0A3054FA2A56E467EC53203
restart_count=0
ScriptCompiler=0 errores, 8 advertencias históricas
Game 2239 y Stream 2250 escuchando
registro en LoginServer exitoso
tiempo de arranque=00:01:46.0589636
```

## Estado persistido de Dannia antes del despliegue

```text
character id=1, level=6, experience=10348, money=2751
quest 2260 status=3, activa
item 16260 x1
item 23633 x5 preexistente
sin 48507, 47985, 47986, 47987 ni resultados Explorer entregados
```

El mismo estado se comprobó nuevamente en MySQL después de recrear `game`.

## Aceptación manual por etapas

Primero, con al menos seis espacios libres, elegir una sola vez la alternativa
2 (Leather). Verificar cierre del diálogo, finalización de quest, consumo de
16260, `+2800 EXP`, `+2500 copper`, `+1` de 23633, `+2` de 48507 y exactamente
una caja 47986. Detenerse antes de abrirla para inspeccionar logs y MySQL.

Después, con al menos tres espacios libres y sólo tras confirmar el primer
estado, abrir 47986. Debe consumirse la caja y entregar exactamente 48025,
48027 y 48028 x1. Finalmente verificar persistencia tras relog.

## Aceptación manual — entrega confirmada

Fecha local: 2026-07-31 22:13.

```text
CSCompleteQuestContext quest=2260 selected=2
ReportNpc 10583 validado
todos los acts Reward retornaron res=True
quest activa 2260 eliminada
bit de completed_quests 2260=1
EXP 10348 -> 13148 (+2800 exactos)
23633 5 -> 6 (+1 exacto)
47986 0 -> 1 (+1 exacto)
48507 0 -> 2 (+2 exactos)
16260 1 -> 0 (limpieza exacta)
sin rechazo AA8QuestRewardGuard ni mutación duplicada
```

El saldo cambió `2751 -> 5328`; el act nativo de 2500 copper retornó éxito,
pero el delta agregado contiene 77 copper adicionales obtenidos entre las dos
muestras, por lo que esa porción no se atribuye a la quest sin evidencia.

Corroboración visible por ítem:

```text
https://wiki.archerage.to/na-en/db/items/47983
https://wiki.archerage.to/na-en/db/items/47986
https://wiki.archerage.to/na-en/db/items/48507
```

La wiki confirma que 47986 enumera 48025, 48027 y 48028 x1. El dossier y el
compact AA8 siguen siendo la autoridad de las relaciones habilitadas.

Estado: entrega de quest `aceptada`; apertura 47986 `pendiente_controlada`.

## Aceptación manual — caja de componentes confirmada

Después de abrir `47986` una sola vez y realizar un relog limpio:

```text
47986 1 -> 0
48025 Moonrise Fists 0 -> 1
48027 Moonrise Guards 0 -> 1
48028 Moonrise Belt 0 -> 1
las tres piezas son visibles y equipables
las tres filas persisten en MySQL después del relog
completed_quests 2260 continúa en 1
sin duplicación ni resultado adicional
```

Estado: entrega y caja de componentes `aceptadas_con_persistencia`.

Pendientes separados:

```text
47983 Moonrise Leather Armor Crate -> requiere cierre runtime nuevo
48507 Unidentified Story Quest Infusion: Rank 1 -> cierre B14 presente;
                                               intercambio visible confirmado;
                                               persistencia directa continúa en V4
```
