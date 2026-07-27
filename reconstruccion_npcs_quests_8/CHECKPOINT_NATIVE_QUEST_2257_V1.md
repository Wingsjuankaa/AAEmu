# Checkpoint AA8 nativo — quest 2257 / Bloodhand Corpse

Fecha: 2026-07-27
Autoridad: ArcheAge Kakao 8.0.3.12 r558734

## Síntoma y diagnóstico

El cliente mostraba `!` sobre `Bloodhand Corpse`, pero el cuerpo no permitía
aceptar la misión. Los demás objetos cercanos sí podían seleccionarse.

La traza probó que el clic llegaba al objeto correcto:

```text
doodadTemplate=14073
objId=189982
funcGroup=41492
questKind=1
skill=11006
candidates=0
```

No faltaba hitbox ni selección. `14073` es un `client_doodad`, no un NPC
conversacional, por lo que no debe esperarse chat. V3 había suprimido
intencionalmente las funciones `38376/38377` hasta cerrar las dependencias de
la quest 2257.

## Cadena nativa reconstruida

```text
Bloodhand Corpse 14073
  Start 41492
    DoodadFuncQuest 1507 -> accept quest 2257 -> phase 41493

  character-local phase 41493
    DoodadFuncUse 10813
      outer skill=41925
      concrete skill=0
      next_phase=41494

skill 41925
  skill_effect 59150 -> effect 77705
    InteractionEffect 7864 -> WorldInteraction.Use (19)
  skill_effect 59152 -> effect 77710
    GainLootPackItemEffect 4165 -> loot pack 12908

loot pack 12908 -> item 16287 x1 (Bloodhand Glove)

quest 2257
  Start 9947 -> AcceptDoodad 795 -> doodad 14073
  Progress 9998 -> ObjInteraction 1113 -> doodad 14073 / phase 41493
  Progress 17567 -> ObjItemGather 4330 -> item 16287 x1
  Ready 9949 -> ReportNpc 2089 -> Malphus 3630
  Reward 9950 -> Gilda Star 23633 x1
                 EXP 1800
                 Mind's Edge 18792 x5
```

La [wiki de ArcheRage para la quest 2257](https://wiki.archerage.to/na-en/db/quests/2257)
se usó sólo como corroboración visible. IDs, fases, actos, skill effects,
efectos concretos e item provienen del cliente Kakao 8.0.

## Hallazgo transversal: fase personal

`once_one_man=1` significa que la fase de quest no puede escribirse en
`Doodad.FuncGroupId`: hacerlo cambiaría el cadáver compartido para todos.

La resolución genérica ahora busca, para cada personaje:

```text
quest activa / Progress
  -> QuestActObjInteraction
  -> doodad_id o highlight_doodad_id
  -> highlight_doodad_phase
  -> función que corresponde a la skill recibida
```

La función se ejecuta sin mutar la fase mundial. Por seguridad, una fase
personal con `doodad_phase_funcs` permanece cerrada hasta tener evaluador
local.

## Hallazgo transversal: GainLoot desde doodad

`GainLootPackItemEffect` asumía siempre `SkillCasterItem`. La skill 41925 usa
`SkillCasterUnit`; el cast directo producía `InvalidCastException`.

La corrección sólo exige item fuente cuando `consume_source_item=1` o
`inherit_grade=1`. Un loot pack de interacción con ambos flags en cero ya
puede entregar su resultado.

## Fila server-derived explícita

Kakao `game11` no contiene las tablas de loot autoritativas del servidor. Se
añadió:

```text
loot_pack_id=12908
item_id=16287
min=max=1
drop_rate=10000000
always_drop=1
```

Clasificación: `server_derived`, no nativa. La relación está cerrada por:

- `GainLootPackItemEffect 4165 -> loot_pack_id 12908`;
- `items.16287.loot_quest_id = 2257`;
- `QuestActObjItemGather 4330 -> item 16287 x1`.

## Artefactos, validación y despliegue

```text
builder:
  reconstruccion_npcs_quests_8/build_native_quest_2257_runtime.py

tests:
  reconstruccion_npcs_quests_8/test_native_quest_2257.py

runtime:
  compact-8.0-runtime-native-nuian-green-arc-v4.sqlite3

SHA-256:
  3538C7120360ADA99BF6EC0E0CC051812E962576E0F0264DCE8676558E90AE95

Python NPC/quests: 40/40
.NET Core 3.1: 250/250
SQLite: quick_check=ok, integrity_check=ok
reproducibilidad: dos builds con SHA-256 idéntico

servicio recreado: game solamente
imagen: 11a935cd4633720c40103c760d7539e151f420a71262fb24d723fa2fe246d16b
rollback: aaemu-game:pre-aa8-quest2257-v4-20260727
mount: compact-8.0-runtime-native-nuian-green-arc-v4.sqlite3
restart_count=0
Game/Stream=2239/2250
LoginServer=registrado
```

## Prueba manual escalonada

No encadenar acciones:

1. hacer **un solo clic** en el cadáver con `!`;
2. confirmar que 2257 queda aceptada;
3. detenerse y revisar logs;
4. sólo después usar `F` para examinar;
5. confirmar interacción, item 16287 x1 y transición a `Ready`;
6. detenerse antes de entregar a Malphus, porque 2258 queda fuera del alcance
   de V4.

## Prueba manual posterior: duplicacion del guante y casteo invisible

La prueba del 2026-07-27 avanzo correctamente la quest, pero tambien demostro
dos defectos transversales distintos.

### Evidencia de ejecuciones superpuestas

El cliente envio dos `CSStartSkillPacket` para la skill 41925 antes de que
terminara el primer casteo:

```text
04:49:47  SCSkillStarted tl=2285 realCast=3000 baseCast=3000 startAnim=56
04:49:48  SCSkillStarted tl=2288 realCast=3000 baseCast=3000 startAnim=56
04:49:50  SCSkillFired   tl=2285 -> interaction + item 16287 -> quest Ready
04:49:51  SCSkillFired   tl=2288 -> funcion de doodad rechazada, pero GainLoot
                                     igualmente entrega otro item 16287
04:49:57  nuevo inicio
04:50:00  nuevo disparo -> tercer item 16287
```

Persistencia confirmada:

```text
quest 2257: status=Ready
item 16287: count=3
```

La duplicacion no es solamente visual. Hay tres barreras genericas pendientes:

1. impedir un nuevo casteo mientras existe `caster.SkillTask`, salvo que la
   skill sea explicitamente `casting_useable`;
2. hacer que `OnItemGather` y `OnItemUse` solo progresen quests en estado
   `Progress`, nunca `Ready`;
3. antes de entregar un item con `loot_quest_id`, confirmar que esa quest sigue
   activa, en progreso y aun necesita ese item. Esta es la ultima barrera contra
   casteos que ya quedaron programados.

La fila nativa de skill 41925 confirma:

```text
casting_time=3000
casting_useable=0
casting_cancelable=0
casting_delayable=0
start_anim_id=56
fire_anim_id=0
cooldown_time=3000
```

### Evidencia nativa del SkillObject tipo 28

El servidor registraba:

```text
skillObject=28
inputDirection=21
warning: SkillObject doesn't inherit Read()
```

La decompilacion de `x2game.dll` AA8, funcion `FUN_399af960`, demostro que el
tipo `0x1c` (28) serializa:

```text
header
uint32 campo_1
uint32 campo_2
byte inputDirection
```

AAEmu solo conoce los tipos 0..11. Para el tipo 28 usa el objeto generico, no
lee los dos `uint32` y toma el primer byte de `campo_1` como si fuera
`inputDirection`. Luego devuelve al cliente un objeto truncado en
`SCSkillStartedPacket` y `SCSkillFiredPacket`.

Por tanto, el valor `inputDirection=21` de la traza no es fiable y la ausencia
visual del casteo tiene una causa protocolaria concreta pendiente de
implementar. El servidor si respeto los 3000 ms; no fue un casteo instantaneo.

Artefactos de evidencia:

```text
E:\AAEmu-Research\output\ghidra-static\aa8-skill-object-type28.c
E:\AAEmu-Research\output\ghidra-static\aa8-skill-started-41925-review.c
E:\AAEmu-Research\output\ghidra-static\aa8-skill-started-optional-callers.c
```
