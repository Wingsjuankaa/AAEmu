# Checkpoint AA8: quest 3993 y reconciliación multi-Progress V1

## Alcance

Repara el estado incoherente observado en `3993 Runebearer` después de usar
`26023 Engraved Lodestone`. La corrección es una primitiva compartida para
quests AA8 no selectivas con múltiples componentes `Progress`; no contiene
una excepción por quest o item.

Cliente autoritativo: ArcheAge Kakao `8.0.3.12 r558734`.

## Incidente reproducido

Personaje: `Dannia`, character id `1`.

Secuencia del servidor:

```text
03:11:33 quest 3993 aceptada desde doodad 14124
03:11:33 SupplyItem 3410 -> Engraved Lodestone 26023 x1
03:11:37 OnItemUse -> Progress 17209, objective[0]=1, complete=true
03:11:37 Update -> Status Ready por el componente 17209
03:11:37 Update -> Progress 19840, objective[1]=0, complete=false
03:11:37 snapshot final -> Step Progress, Status Progress, ComponentId=0
```

MySQL conservó la corrupción lógica sin pérdida de datos:

```text
quests.owner=1
template_id=3993
status=1 (Progress)
objective[0]=1
objective[1]=0
step=4 (Progress)
component_id=0
```

El tracker mostró dos contadores ajenos al recorrido nativo, `0/5` y `0/10`,
y dejó de señalar el siguiente actor. La captura no demuestra qué tablas usó
el cliente al resolver el componente vacío, por lo que no se asigna semántica
a esos dos iconos.

Evidencia preservada:

```text
D:\Proyectos\AAemu\backups\quest-failures\QF-0013\capture-1.png
sha256=E25CF3EEE5B19012DFAFCB4D4F2267B306CA866ACD442F588CA276BA4A284225

D:\Proyectos\AAemu\backups\quest-failures\QF-0013\game-session.log
sha256=C4E5DB96AA8CD2EEA27125512560757EC51335B808719A83ED29C8C7D3B3A943
```

Respaldo previo al despliegue:

```text
D:\Proyectos\AAemu\backups\quest-3993-multi-progress-v1-20260801-234719\mysql-all.sql
sha256=5E91333EA88D30584BF936B08445ED0C8F27E4A3E8E21DA56ADD6E5B2457D598

D:\Proyectos\AAemu\backups\quest-3993-multi-progress-v1-20260801-234719\dannia-quest-3993.tsv
sha256=2CB974E81EED1B489A3C151F003C313E5129CE5AE55746253B849760B03A1909
```

## Cierre nativo

El dossier AA8 `quest-3993.json` demuestra:

```text
Start 17208
  QuestActConAcceptDoodad 806 -> doodad 14124

Supply 21472
  QuestActSupplyItem 3410 -> item 26023 x1

Progress 17209
  QuestActObjItemUse 686 -> item 26023 x1

Progress 19840
  QuestActObjTalk 974 -> Marian npc 10849

Ready 19841
  QuestActConReportDoodad 175 -> doodad 14124 (Lucius Quinto)

Reward 17210
  item 23633 x1
  exp 43000
  item 47866 x2
  item 34002 x5
```

Dossier:

```text
E:\AAEmu-Research\output\aa8-client-forensics\dossiers\quest-3993.json
sha256=9D22B315A3A76200A30F2D18C5890355529F6952D476EC58A6C60FCE404021C8
```

La wiki compatible se usó solamente para corroborar el recorrido visible:
usar la piedra para revivir a Marian, hablar con Marian y reportar después a
Lucius Quinto. Las relaciones ejecutables proceden del cliente AA8.

## Causa

`Quest.Update` trataba el booleano del último act visitado como el estado de
toda la fase. En una quest no selectiva con dos componentes Progress:

```text
17209 completo -> Ready
19840 incompleto -> Progress + ComponentId 0
```

El segundo resultado sobrescribía al primero, pero eliminaba la identidad del
componente nativo todavía pendiente. El problema es transversal: el runtime
contiene 666 quests con más de un componente Progress; 566 también poseen una
frontera Ready.

## Reparación

`Quest.TryReconcileNonSelectiveMultiProgressState` se activa sólo cuando:

```text
quest.selective=false
dos o más componentes Progress
existe un componente Ready real
todos los actos objetivo pertenecen al conjunto de predicados ya implementado
```

La primitiva evalúa todos los componentes con contadores persistidos. Si falta
alguno, mantiene `Progress` y publica el primer componente nativo incompleto.
Sólo cuando todos están completos llama a la frontera Ready existente.
Grafos selectivos o con actos todavía no implementados conservan la ruta
anterior, sin inferir semántica.

`CharacterQuests.Load` ejecuta la misma reconciliación después de restaurar y
recalcular objetivos. Por ello el estado existente de Dannia se repara al
reloguear tras el despliegue, sin editar MySQL manualmente ni repetir el uso del
item consumido.

Archivos:

```text
AAEmu.Game/Models/Game/Quests/Quest.cs
AAEmu.Game/Models/Game/Char/CharacterQuests.cs
AAEmu.Tests/QuestCompletionGuardTests.cs
```

## Runtime

La reparación no cambia ninguna fila estática. Durante el despliegue otro
trabajo concurrente promovió el runtime de `shadowplay-v1` a `shadowplay-v2`;
se conservó esa promoción y se auditó el cierre completo de la quest 3993 en
ambos archivos. Contexto, seis componentes, nueve acts y nueve detalles son
idénticos:

```text
compact-8.0-runtime-shadowplay-v2.sqlite3
sha256=AD62A01CF762317CFF49624AB2191B2289B096004C48735B95A2A9156587E5F7
quick_check=ok
integrity_check=ok
quest_3993_closure_sha256=1D261E573D2945B4FC3D93ED440AD9B56A47339D29A292A5F4EA02F79136E18C
quest_3993_closure_identical_to_shadowplay_v1=true
```

Manifiesto:

```text
generated/native-quest-3993-multi-progress-v1-manifest.json
```

## Validación y parada manual

Automática:

```text
QuestCompletionGuardTests: 42/42
suite completa AAEmu.Tests: 337/337
ScriptCompiler: 0 errores, 8 warnings conocidas
Docker image: sha256:0dba9b75fb682ad64390f88439ceb410f118e1151ebf5140ebacecdd9b0c0d3c
AAEmu.Game.dll: sha256:840B5CE42F98656EE4D0B3F11E48262658F573887AE8BA7C15A0ACCDCD8E7E3E
game service: desplegado, restart_count=0
puertos: 2239 y 2250 escuchando
LoginServer: GameServer 1 registrado
```

Prueba manual controlada:

```text
1. cerrar completamente el cliente antes del despliegue;
2. volver a entrar con Dannia;
3. confirmar que Runebearer ya no muestra los premios como objetivos;
4. hablar una sola vez con Marian;
5. detenerse antes de entregar a Lucius Quinto.
```

Después de ese único diálogo se deben revisar logs y MySQL antes de autorizar
la entrega y la recompensa.

## Resultado del retest

La V1 reparó correctamente el estado persistido a `ComponentId=19840`, pero
el cliente no recalculó el componente `17209` ya completado y no emitió
`CSQuestTalkMade` frente a Marian. La continuación está documentada en:

```text
CHECKPOINT_NATIVE_QUEST_3993_MULTI_PROGRESS_V2.md
```
