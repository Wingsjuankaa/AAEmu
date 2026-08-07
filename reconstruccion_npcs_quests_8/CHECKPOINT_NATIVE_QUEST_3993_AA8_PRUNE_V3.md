# Checkpoint AA8: quest 3993, poda del componente heredado V3

## Resultado

`3993 Runebearer` ya no exige el paso espurio de hablar con Marian. En el
cliente Kakao `8.0.3.12 r558734`, el recorrido ejecutable es:

```text
Start 17208  -> aceptar en doodad 14124
Supply 21472 -> Engraved Lodestone 26023 x1
Progress 17209 -> usar 26023 x1
Ready 19841 -> reportar en doodad 14124 (proxy de Lucius Quinto)
Reward 17210
```

Después del uso del objeto, la quest debe cruzar directamente a `Ready` y
señalar a Lucius Quinto.

## Evidencia que invalida V1/V2

Las capturas V1, V2 y V3 demostraron que el cliente aceptaba el objetivo
nativo `17209` y mostraba el mensaje flotante correcto `1/1 (Complete)`, pero
el tracker lateral quedaba en `0/5` y `0/10`.

Captura V3 preservada:

```text
D:\Proyectos\AAemu\backups\quest-failures\QF-0013\capture-3.png
sha256=D3D1DFE0AF27651645F1E2B732B5CD43DF115DDA7F26DD1981BA8029BF73663A
```

La inspección tipada del grafo AA8 mostró cinco componentes, no seis. La fila
`quest_component=19840` no existe en Stage 40 para quest 3993. Ese número sólo
aparece allí como `quest_component_text.id=19840`, perteneciente al componente
de texto `39241`. El compacto heredado 3.0, en cambio, conservaba:

```text
quest_components.id=19840, quest_context_id=3993, kind=Progress
quest_acts.id=27031, QuestActObjTalk 974 -> Marian 10849
```

Por tanto, el dossier usado en V1 cerró una relación por colisión numérica
entre familias de entidad. V1 y V2 intentaron mantener y refrescar un paso que
el cliente AA8 ya no posee. Sus primitivas y pruebas específicas fueron
retiradas de la fuente.

Autoridad:

```text
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v2.sqlite3
sha256=39FD2589DC095E80722B94D3EB1D307E649C28AEAEB486AEF8725AD33DE82B5A

E:\AAEmu-Research\output\aa8-client-forensics\stage-40-quests.sqlite
sha256=0BB127E819232BFEE6D6559000E845B8C36E7F4C56A5ED64234DCD28B793D72C
```

## Materialización V3

El builder copia el runtime anterior y elimina exclusivamente las dos filas
heredadas que contradicen AA8:

```text
quest_acts.id=27031
quest_components.id=19840
```

No elimina los detalles globales `QuestActObjTalk 974` ni el alias 1893,
porque pueden pertenecer a otros cierres.

Archivos:

```text
reconstruccion_npcs_quests_8/build_native_quest_3993_v3_runtime.py
reconstruccion_npcs_quests_8/generated/native-quest-3993-aa8-prune-v3-manifest.json
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-quest3993-v3.sqlite3
sha256=E62DE56D6011CDF577ABDAA2F772338E80E971F82BFA13B1ED0AB9E88CAA0E94
```

Validación del runtime:

```text
PRAGMA quick_check=ok
PRAGMA integrity_check=ok
componentes AA8 exactos=5
acts AA8 exactos=8
legacy component 19840=0 filas
legacy act 27031=0 filas
Ready 19841 -> QuestActConReportDoodad 175 -> doodad 14124
```

## Estado persistido de Dannia

Antes del despliegue:

```text
owner=1, template=3993, status=Progress
objective[0]=1
step=Progress
component_id=19840
acceptor=doodad 14124
```

Con Game detenido, una actualización condicionada por el blob completo migró
exactamente una fila:

```text
status=Ready
objective[0]=1 (sin cambios)
step=Ready
component_id=19841
acceptor=doodad 14124 (sin cambios)
rows_affected=1
```

Respaldo:

```text
D:\Proyectos\AAemu\backups\quest-3993-aa8-prune-v3-20260802-025312\mysql-all.sql
sha256=E86BD6C62AC35555025FF86E856DC007131BEEA3AC0EB785E48B6F3C0C945A56

D:\Proyectos\AAemu\backups\quest-3993-aa8-prune-v3-20260802-025312\quest-3993-before.tsv
sha256=C0FF7D536D1DB107E3B6483A15468B1CB2EBE651CBDBD4CF1239987A89E4299A

rollback image=aaemu-game:pre-quest-3993-aa8-prune-v3-20260802-025312
```

## Validación y despliegue

```text
compilación AAEmu.Game=correcta
NativeQuestProtocolTests + QuestCompletionGuardTests=53/53
suite AAEmu.Tests=335/335
ScriptCompiler=0 errores, 8 warnings conocidas
Game restart_count=0
TCP 2239/2250 escuchando
LoginServer=GameServer 1 registrado
compact montado=E62DE56D6011CDF577ABDAA2F772338E80E971F82BFA13B1ED0AB9E88CAA0E94
```

Sólo se recreó `game`; Login y MySQL permanecieron activos.

## Parada manual

```text
1. entrar con Dannia sin abandonar la quest;
2. comprobar que Runebearer aparece Ready y Lucius tiene el marcador;
3. acercarse a Lucius sin confirmar todavía la entrega;
4. revisar logs y MySQL;
5. entregar una vez y verificar recompensa/cierre.
```
