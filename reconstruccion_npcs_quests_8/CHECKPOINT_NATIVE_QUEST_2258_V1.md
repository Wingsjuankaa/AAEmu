# Checkpoint AA8 nativo — quest 2258 / An Urgent Message

Fecha: 2026-07-27
Autoridad: ArcheAge Kakao 8.0.3.12 r558734

## Síntoma observado

Después de completar la quest 2257, Malphus ofrecía la quest 2258. Al
aceptarla, aparecía brevemente en el journal y se abandonaba de inmediato.
La prueba se repitió dos veces con el mismo resultado.

## Diagnóstico probado por logs

```text
04:53:45 QuestActConAcceptNpc
04:53:45 quest=2258 component=9951 step=Start res=True
04:53:45 QuestActSupplyItem
04:53:45 quest=2258 component=9951 step=Supply res=False
04:53:45 RemoveQuestItems item=16288
04:53:45 quest 2258 removed

04:53:50 misma secuencia y mismo resultado
```

La aceptación desde Malphus era correcta. Fallaba la entrega inicial del item
`16288`; `CharacterQuests.Add` recibía `false` de `Quest.Start` y ejecutaba el
rollback seguro.

V4 declaraba 2258 en `suppressed_adjacent_quest_ids`, pero esa entrada era
solamente documental. `SCFilterPacket` inicializaba el índice global
`StartNpc -> quests` con el catálogo completo del cliente, por lo que la
oferta de Malphus seguía visible.

## Cadena nativa cerrada

```text
quest 2258 — An Urgent Message

Start 9951
  QuestActConAcceptNpc 1854 -> Malphus 3630

Supply 9952
  QuestActSupplyItem 1339 -> Bloodhand Glove 16288 x1

Progress 9999
  QuestActObjItemGather 935 -> Bloodhand Glove 16288 x1

Ready 9953
  QuestActConReportNpc 2090 -> General Govannon 3611

Reward 9954
  QuestActSupplyItem 4814 -> Gilda Star 23633 x1
  recompensa genérica de nivel y Heart's Beat 18791 ya cubiertos en V4
```

La fila AA8 de item 16288 fue extraída del resultado `items` de `game11`:

```text
category_id=64
impl_id=0
auto_complete=1
bind_id=2
icon_id=6360
loot_multi=1
loot_quest_id=2258
max_stack_size=10
use_skill_id=0
```

Es un item genérico de transporte de quest. No tiene descriptor concreto ni
skill de uso pendiente.

La [wiki de ArcheRage para la quest 2258](https://wiki.archerage.to/na-en/db/quests/2258)
se usó como corroboración visible: Malphus entrega el guante y el jugador debe
llevarlo a General Govannon. La fila, los actos y los IDs habilitados provienen
de las fuentes Kakao AA8.

## Reparación transversal

Se añadió `QuestStartDependencyGuard`. Antes de insertar una quest en el
journal, revisa todos sus componentes `Supply`:

```text
QuestActSupplyItem
  -> ItemManager contiene la plantilla
  -> si existe catálogo AA8 de cobertura:
       coverage debe ser Complete
```

Si la dependencia no es creable, la quest se rechaza antes de crear el
journal. Esto evita la secuencia visible `Started -> Dropped` y deja una traza
`[AA8QuestStartGuard]` con el item y motivo exactos.

Esta compuerta no inventa datos ni habilita quests incompletas. El marcador
del cliente puede seguir siendo visible mientras `SCFilterPacket` opere en
modo nativo sin filtro, pero el servidor ya no corrompe o ensucia el estado
del journal.

## Runtime V5

```text
builder:
  reconstruccion_npcs_quests_8/build_native_quest_2258_runtime.py

tests:
  reconstruccion_npcs_quests_8/test_native_quest_2258.py

runtime:
  compact-8.0-runtime-native-nuian-green-arc-v5.sqlite3

SHA-256:
  11E4D8FD9D28DBA23E25934A5A27CCAD7E4CE4C7B15DF3EEE09C0797622D953B

base V4:
  3538C7120360ADA99BF6EC0E0CC051812E962576E0F0264DCE8676558E90AE95

dos builds:
  SHA-256 idéntico

SQLite:
  quick_check=ok
  integrity_check=ok

Python NPC/quests:
  47/47

.NET Core 3.1:
  257/257

despliegue:
  servicio recreado: game solamente
  imagen: 890bd4a33be17c7b728c5cb0fc2b954bf61385554e6ac28d3e86dd4de749a360
  rollback: aaemu-game:pre-aa8-quest2258-v5-20260727
  compact montado: 11E4D8FD9D28DBA23E25934A5A27CCAD7E4CE4C7B15DF3EEE09C0797622D953B
  restart_count: 0
  Game/Stream: 2239/2250
  LoginServer: registrado
  scripts: 0 errores
```

## Próxima prueba manual

Requiere al menos un espacio libre en la bolsa.

1. Interactuar una sola vez con Malphus.
2. Aceptar la quest 2258.
3. Confirmar que aparece y permanece en el journal.
4. Confirmar que se recibe exactamente un item 16288.
5. Confirmar que el objetivo queda completo y apunta a General Govannon.
6. Detenerse sin entregar la quest y solicitar revisión de logs.

No repetir la aceptación ni entregar a General Govannon hasta revisar el
primer resultado.
