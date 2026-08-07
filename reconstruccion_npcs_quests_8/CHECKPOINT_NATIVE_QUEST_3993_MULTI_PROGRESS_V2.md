# Checkpoint AA8: quest 3993, refresco multi-Progress V2

## Alcance

Corrige el segundo corte observado en `3993 Runebearer`: el servidor ya
conservaba el siguiente componente nativo `19840`, pero el cliente seguía
mostrando objetivos ajenos y no emitía `CSQuestTalkMade` al interactuar con
Marian.

Cliente autoritativo: ArcheAge Kakao `8.0.3.12 r558734`.

## Evidencia del retest V1

La sesión controlada demostró:

```text
06:06:00 QuestActObjItemUse 17209 -> complete=true
06:06:00 QuestActObjTalk 19840 -> objective=0
06:06:00 reconciliación -> Step=Progress, Status=Progress, ComponentId=19840
06:06:00 SCQuestContextUpdated enviado
06:06:09 interacción con Marian npcTemplate=10849
06:06:09 CSInteractNPC recibido
06:06:12 CSInteractNPCEnd recibido
CSQuestTalkMade ausente
```

MySQL confirmó que la V1 reparó la identidad persistida:

```text
owner=1
template_id=3993
status=1 (Progress)
objective[0]=1
objective[1]=0
step=4 (Progress)
component_id=19840
```

Captura preservada:

```text
D:\Proyectos\AAemu\backups\quest-failures\QF-0013\capture-2.png
sha256=06F472FC7962D318216BE2B334A8FDE455A2810E71C04F0733327F5F42FD3D3D
```

## Causa V2

La V1 usó `ComponentId=19840` tanto para el estado persistido como para la
lista final de `SCQuestContextUpdated`. Son conceptos distintos:

```text
Quest.ComponentId
  -> siguiente componente pendiente del journal
  -> 19840, hablar con Marian

SCQuestContextUpdated.componentIds[10]
  -> filtros de componentes que el cliente debe recalcular
  -> deben incluir 17209 y 19840 en este grafo multi-Progress
```

El consumidor AA8 ya documentado para `0x051` recorre hasta diez IDs
comprimidos; cada valor no cero refresca ese `QuestComponent`. La V1 enviaba
sólo `19840`, por lo que el cliente nunca recalculó el componente `17209` que
acababa de cambiar. El journal del servidor era correcto, pero el contexto
local que habilita `QuestActObjTalk` quedó obsoleto.

## Reparación transversal

`SCQuestContextUpdatedPacket` acepta ahora una secuencia acotada de hasta diez
componentes, elimina ceros y duplicados, conserva el orden y usa el layout
nativo `4 + 4 + 2` de anchos variables.

Para una quest no selectiva soportada con múltiples componentes `Progress`:

```text
progreso parcial
  -> persiste el primer componente incompleto
  -> refresca todos los componentes Progress

transición completa a Ready
  -> refresca todos los Progress y el Ready real

relogin con estado persistido
  -> SCQuests
  -> SCQuestContextUpdated con todos los Progress
```

Para Runebearer, el refresco parcial exacto es:

```text
[17209, 19840]
bytes posteriores al registro Quest:
05 39 43 80 4D 00 00 00 00 00 00 00 00 00 00
```

No se añadió una excepción por quest, NPC o item.

Archivos:

```text
AAEmu.Game/Core/Packets/G2C/SCQuestContextUpdatedPacket.cs
AAEmu.Game/Models/Game/Quests/Quest.cs
AAEmu.Game/Models/Game/Char/CharacterQuests.cs
AAEmu.Tests/NativeQuestProtocolTests.cs
```

## Autoridad y runtime

El grafo nativo permanece sin cambios:

```text
Progress 17209 -> QuestActObjItemUse 686 -> item 26023 x1
Progress 19840 -> QuestActObjTalk 974 -> Marian npc 10849
Ready 19841    -> QuestActConReportDoodad 175 -> Lucius doodad 14124
```

Runtime activo, sin filas modificadas por esta reparación:

```text
compact-8.0-runtime-shadowplay-v2.sqlite3
sha256=AD62A01CF762317CFF49624AB2191B2289B096004C48735B95A2A9156587E5F7
quick_check=ok
integrity_check=ok
```

## Validación previa al despliegue

```text
NativeQuestProtocolTests + QuestCompletionGuardTests: 56/56
suite completa AAEmu.Tests: 338/338
ScriptCompiler: 0 errores, 8 warnings conocidas
git diff --check: correcto
```

Respaldo:

```text
D:\Proyectos\AAemu\backups\quest-3993-multi-progress-v2-20260802-021549\mysql-all.sql
sha256=BC6A6FEE9D4506A813440E7346D9DCBEC032444D091F77192CCB37D4C3BF6261
rollback=aaemu-game:pre-quest-3993-multi-progress-v2-20260802-021549
```

## Despliegue

Se recreó exclusivamente `game`; Login y MySQL conservaron sus contenedores.

```text
docker image=sha256:3f9a9c4724daeab4357566e5e405c76c9591ee7eebe49dc7826398111d446fcc
AAEmu.Game.dll=65A52427A65FB49B797E5E6EA976DDE82768BC8C0282B0BD2AF7C9DD7228C087
game restart_count=0
ScriptCompiler=0 errores, 8 warnings conocidas
Game/Stream=2239/2250 escuchando
LoginServer=GameServer 1 registrado
mounted compact=AD62A01CF762317CFF49624AB2191B2289B096004C48735B95A2A9156587E5F7
```

## Parada manual

Tras el despliegue:

```text
1. abrir el cliente y entrar con Dannia;
2. no abandonar ni volver a aceptar Runebearer;
3. confirmar que el tracker muestra hablar con Marian;
4. hablar una sola vez con Marian;
5. detenerse antes de interactuar con Lucius Quinto.
```

Se revisarán `CSQuestTalkMade`, la transición a `Ready 19841`, MySQL y el
marcador de Lucius antes de autorizar la entrega.
