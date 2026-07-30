# Checkpoint AA8 nativo: quest 2532, diálogo y recompensas

Fecha: 2026-07-27
Branch: `client_version/8.0.3.12-kakao-r558734-port`
Cliente: Kakao `8.0.3.12-r558734`

## Resultado

La quest `2532`, **A Mysterious Visitor**, ya tenía importado su grafo nativo,
pero el backend completaba la entrega al primer `F` sobre Marian. Eso evitaba
que el cliente abriera el diálogo/reward frame y llamaba `Complete` con
`selected=0`. Como la quest tiene tres recompensas selectivas 1-based, ninguna
de ellas podía entregarse.

La reparación es transversal:

1. la interacción inicial con un `ReportDoodad` envía el paquete AA8 que abre
   el diálogo nativo;
2. el cliente devuelve la confirmación y el índice elegido;
3. el servidor distingue correctamente el ObjId NPC del ObjId doodad;
4. una quest con recompensas selectivas rechaza `selected=0`;
5. todas las recompensas de ítem se validan antes de mutar al personaje;
6. un fallo devuelve `0`, conserva la quest activa y no se interpreta como
   finalización exitosa.

No se agregó ninguna excepción por ID de quest.

## Verdad visible corroborada

Página usada:

```text
https://wiki.archerage.to/na-en/db/quests/2532
```

Secuencia visible:

```text
prerequisito: The Prophet Terrien
inicio: Pan, NPC 11542
reporte: Marian, objeto 14074
siguiente: The Golden Mark
```

Recompensas visibles:

```text
fija:       23633 Gilda Star x1
EXP:        1800
selectiva:  47982 Moonrise Cloth Armor Crate x1
             o 47983 Moonrise Leather Armor Crate x1
             o 47984 Moonrise Plate Armor Crate x1
fija:       18791 Heart's Beat x5
```

La wiki es contexto de comportamiento. Los IDs y relaciones habilitados
siguen estando respaldados por el cliente AA8 y el manifiesto nativo.

## Grafo AA8 presente en V5

Fuente durable:

```text
generated/native-nuian-green-arc-v1-manifest.json
```

```text
quest_context 2532
  Start  10965 -> QuestActConAcceptNpc 2098 -> Pan 11542
  Ready  10966 -> QuestActConReportDoodad 163 -> Marian 14074
  Reward 10967
    -> QuestActSupplyItem          4812 -> 23633 x1
    -> QuestActSupplyExp           3924 -> 1800
    -> QuestActSupplySelectiveItem 3651 -> 47982 x1
    -> QuestActSupplySelectiveItem 3652 -> 47983 x1
    -> QuestActSupplySelectiveItem 3653 -> 47984 x1
    -> QuestActSupplyItem          8872 -> 18791 x5
```

Runtime montado y conservado:

```text
client_kakao/compact-8.0-runtime-native-nuian-green-arc-v5.sqlite3
SHA-256:
11E4D8FD9D28DBA23E25934A5A27CCAD7E4CE4C7B15DF3EEE09C0797622D953B
```

No fue necesario generar V6: las filas de quest y recompensa ya eran
correctas. El defecto estaba en el protocolo y la aplicación del reward.

## Prueba nativa del paquete de diálogo

En `x2game.dll`:

```text
SCOffsets.SCDoodadCompleteQuestPacket = 0x0AD
slot descriptor = 8 * (0x0AD + 1) = 0x570
FUN_3936fc30 -> *(param_1 + 0x570) = &DAT_3a5f62a0
constructor nativo = FUN_39341180
packet vtable = PTR_FUN_39cfb7e0
serializer = FUN_3998c8f0
handler = FUN_392fb290
```

El serializador escribe:

```text
+0x10: campo "bc"   -> ObjId del doodad en codificación BC
+0x14: campo "type" -> quest context id UInt32
```

El handler llama:

```text
FUN_395f4340(packet.questId, packet.doodadObjId)
```

`FUN_395f4340` publica el evento que consume
`COMPLETE_QUEST_CONTEXT_DOODAD(qtype, useDirectingMode, doodadId)`.

Artefactos de trabajo:

```text
E:\AAEmu-Research\output\ghidra-static\
  aa8-scalar-0570-quest-dialog-v1.c
  aa8-sc-doodad-complete-quest-vtable-v1.c
  aa8-sc-doodad-complete-quest-packet-v2.c
  aa8-sc-doodad-complete-registration-caller-v4.c
  aa8-sc-doodad-complete-handler-v5.c
  aa8-sc-doodad-complete-event-v6.c
  aa8-sc-doodad-complete-fields-v8.txt
  aa8-directing-quest-bindings-v9.c
  aa8-directing-quest-completion-v10.c
```

Scripts Ghidra reutilizables agregados:

```text
ghidra/FindAa8ScalarFunctions.java
ghidra/DumpAa8Data.java
```

## Flujo Lua confirmado

Fuente:

```text
x2ui/questcontext/quest_context_directing.lua
```

```text
SCDoodadCompleteQuestPacket
-> COMPLETE_QUEST_CONTEXT_DOODAD
-> CompleteQuest
-> StartDirectingMode
-> FillRewards + chats
-> jugador elige recompensa
-> CompleteDirectingQuest(selected)
-> CSCompleteQuestContext
```

La UI exige índice `1..N` cuando existen recompensas selectivas. `0` es el
sentinela sin selección, no la primera recompensa.

## Defectos corregidos

### Finalización prematura

Antes:

```text
DoodadFuncQuest quest_kind=2
-> OnReportToDoodad(..., selected=0)
-> Complete
```

Ahora:

```text
DoodadFuncQuest quest_kind=2
-> SCDoodadCompleteQuestPacket(doodadObjId, questId)
-> cliente muestra diálogo
-> CSCompleteQuestContext
-> OnReportToDoodad(doodadObjId, questId, selected)
```

### Orden de ObjIds C2G

`CSCompleteQuestContext` contiene:

```text
questId UInt32
npcObjId BC
doodadObjId BC
selected Int32
```

El código anterior trataba el primer BC como target universal e ignoraba el
segundo. Para un reporte doodad, el ObjId real está en el segundo BC.

### Selección inválida aceptada

Antes, saltar las tres `QuestActSupplySelectiveItem` con `selected=0` dejaba
`res=true` por un act anterior y la quest se marcaba completa.

Ahora:

```text
sin selectivas -> selected debe ser 0
con N selectivas -> selected debe estar entre 1 y N
```

### Fallo confundido con éxito

Antes:

```csharp
if (!res)
    return ComponentId;
```

Como `ComponentId` no era cero, `CharacterQuests.Complete` lo interpretaba
como éxito, borraba la quest y persistía el bit aun cuando un reward fallaba.

Ahora un fallo devuelve `0` y restaura `Status`, `Step` y `ComponentId`.

### Reward parcial

`QuestRewardDependencyGuard` valida antes de ejecutar:

```text
selección
template de cada ítem fijo y elegido
cobertura AA8 permitida
espacio agregado de stacks/slots
```

Los cofres `47982-47984` siguen clasificados como
`phase_a_candidate`; el entorno controlado AA8 tiene
`AAEMU_ITEM8_STAGING_ALLOW_CANDIDATES=1`, por lo que pueden recibirse para la
prueba. Abrir esos cofres es una validación de ítems separada y no forma parte
del cierre de entrega de la quest.

## Código

```text
AAEmu.Game/Core/Packets/G2C/SCDoodadCompleteQuestPacket.cs
AAEmu.Game/Core/Packets/C2G/CSCompleteQuestContextPacket.cs
AAEmu.Game/Models/Game/DoodadObj/Funcs/DoodadFuncQuest.cs
AAEmu.Game/Models/Game/Quests/QuestRewardDependencyGuard.cs
AAEmu.Game/Models/Game/Quests/Quest.cs
AAEmu.Tests/NativeQuestProtocolTests.cs
AAEmu.Tests/QuestCompletionGuardTests.cs
```

## Validación automatizada y despliegue

```text
build Docker game: OK
pruebas dirigidas: 39/39
suite completa: 272/272
imagen: sha256:bdb15f3210a59a5389d1f0a100510214e493f1e06f6eaf0d41cca37933a6a2af
puerto Game: 2239
puerto Stream: 2250
startup: Server started
```

## Resguardo y personaje de prueba

Antes de liberar el nombre:

```text
backups/aaemu_game-before-archive-wingsjuanka-id7-20260727-1128.sql
```

Se archivó recuperablemente:

```text
id 7
Wingsjuanka -> !deleted-7-Wingsjuanka-20260727
deleted = 1
```

No se eliminaron sus tablas relacionadas.

## Prueba manual pendiente

Crear un Nuian nuevo llamado `Wingsjuanka` y seguir la cadena naturalmente.
En la quest `2532`:

1. llegar a Marian/objeto `14074` con el marcador `?`;
2. presionar `F` una sola vez;
3. confirmar que aparece el diálogo nativo y el panel de recompensas;
4. verificar que obliga a elegir exactamente uno de los tres cofres;
5. elegir un cofre y confirmar una sola vez;
6. detenerse sin abrir el cofre.

Resultado esperado:

```text
23633 Gilda Star: +1
EXP: +1800
uno y sólo uno de 47982/47983/47984: +1
18791 Heart's Beat: +5
quest 2532 completada una sola vez
quest siguiente ofrecida
```

Después de la prueba hay que revisar logs, inventario, EXP,
`completed_quests` y persistencia tras relog.
