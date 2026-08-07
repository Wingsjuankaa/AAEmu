# Checkpoint — Nuia Story Chapter 6 V1

Fecha: `2026-08-01`

Cliente: ArcheAge Kakao `8.0.3.12 r558734`

## Resultado

Se reconstruyó transversalmente la categoría racial nativa Nuia completa que
el cliente conserva hasta el capítulo 6:

```text
quests:       55
chapters:     0..6
components:   222
acts:         344
act types:    18
story items:  61
```

La selección no usa rangos de IDs ni nombres. Su raíz es exactamente:

```text
quest_contexts.category_id = 3
quest_contexts.race        = 1
```

No se incorporaron las 16 quests Nuia de otras categorías ni se inventaron
las seis fronteras narrativas entre capítulos que el cliente no demuestra.

## Autoridad

```text
nuia-story-quest-graph-v1.sqlite3
sha256=AF5D48C4AF1C9A266B058FF6D1D0A571C4A5E17C412320360C01F34FEA2056F9

aa8-client-knowledge.sqlite
sha256=63BBA93992D87B7BA9E2946CAC1C2077849CAC9BF4FA4C07D08424E91B8E568B

game11
sha256=E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031

base runtime Point 0 V8
sha256=DA7F6026EDE6F9AE2E7B684BDF6BB199078ABF001C50CBD921F8DE50AADA295C
```

## Grafo de quest

El generador reemplaza atómicamente los componentes, actos y detalles de las
55 quests por las filas AA8 del grafo congelado. Esto corrige:

- 4 componentes ausentes;
- 120 actos ausentes;
- cuatro divergencias de componentes;
- cantidades históricas incorrectas;
- aliases nativos ausentes;
- doodads, NPC, skills y cinemas divergentes.

Los 18 tipos concretos quedan materializados y verificados fila por fila.

## Primitivas compartidas

Se eliminaron cuatro comportamientos incompletos del backend:

```text
QuestActConAcceptSphere
  ahora acepta la quest y registra SphereId.

QuestActObjSphere
  ya no autocompleta mediante mensajes placeholder;
  progresa únicamente después del evento de entrada validado.

QuestActObjCinema
  progresa únicamente al recibir CSCompletedCinema.

QuestActObjTalk
  consume el contador validado por OnTalkMade y no vuelve a consultar
  Character.CurrentTarget, que es estado mutable.
```

`Quest.OnEnterSphere` conserva la frontera Progress -> Ready y deja que
`Update` seleccione el componente Ready real. `CSCompletedCinemaPacket` propaga
el evento a las quests activas sin identificar una quest por heurística.

## Items

Las 61 dependencias de items quedan presentes y con cobertura `complete`.

### Materialización heredada acotada

Se materializaron 23 tombstones como `legacy_3_0_corroborated`. Para cada uno
se exige simultáneamente:

1. relación tipada exacta desde una quest AA8;
2. identidad confirmada por la wiki compatible;
3. fila histórica schema-compatible;
4. item no vendible, sin buff ni craft heredados;
5. cierre AA8 presente para cualquier `use_skill_id` requerido.

La capa registra cada fila en:

```text
aaemu_nuia_story_chapter6_materializations
```

`24087 Noryette Ceremonial Cloak` importa además su descriptor mínimo
`item_armors`; los demás quedan como genéricos. No se importaron capacidades
históricas de lectura, crafting, comercio ni loot no demostradas.

### Promociones AA8

Once items AA8 que seguían en `phase_a_candidate` fueron promovidos tras
auditar su item row y skill existente:

```text
34001 34002 34003 34005 34006 34007
34008 34009 47861 47877 47955
```

## Client doodads

Se importó desde `game11` el cierre exacto de siete actores lógicos faltantes:

```text
14109 -> npctype://10550
14114 -> npctype://10555
14118 -> npctype://10554
14120 -> npctype://11277
14121 -> npctype://10563
14122 -> npctype://10560
14124 -> npctype://10798
```

Sus 19 `DoodadFuncQuest` sólo alcanzan quests dentro de las 55 seleccionadas.
El consumidor proxy y los spawns NPC existentes se reutilizan sin inventar
coordenadas.

## Límites que permanecen explícitos

No se inventaron dos relaciones de producción que el grafo aún clasifica como
no demostradas:

```text
quest 2492 -> doodad produce item 24160
quest 4404 -> doodad produce item 24575
```

Las definiciones de ambos items ya existen, por lo que una traza real puede
cerrar solamente el binding productor si falla. Este límite no impide probar
el recorrido desde el capítulo 2; obliga a detenerse en esas interacciones si
no producen el item.

## Runtime reproducible

```text
compact-8.0-runtime-nuia-story-chapter6-v1.sqlite3
bytes=140169216
sha256=2ABB3724CE94106E2DEE0FB5D638CCBC5572A43143FC3DCAFD430A99C059B6B6

manifest
sha256=9993BC2A816461BCC647AF61C71ACC580BDD57172EAF60AAEF5D8BC090189247
```

Dos ejecuciones consecutivas produjeron el mismo SHA-256 del runtime.

## Validación automática

```text
pruebas dirigidas del runtime:       9/9
regresión Python NPC/quests:       122/122
pruebas C# de primitivas:           36/36
AAEmu.Tests completa .NET 3.1:     324/324
ScriptCompiler:                    0 errores, 8 warnings conocidas
PRAGMA quick_check:                ok
PRAGMA integrity_check:            ok
```

## Respaldo y despliegue

Respaldo previo al despliegue:

```text
D:\Proyectos\AAemu\backups\pre-native-nuia-story-chapter6-v1-20260801-130021
mysql-all.sql
sha256=1CF9400A11BA17DDECCCD293D7FB384FDB5A1586E3E0C6A62B384E7A4A093B10

runtime anterior
sha256=DA7F6026EDE6F9AE2E7B684BDF6BB199078ABF001C50CBD921F8DE50AADA295C

imagen de rollback
aaemu-game:pre-native-nuia-story-chapter6-v1-20260801-130021
```

Se reconstruyó y recreó únicamente el servicio `game`; `db` y `login`
permanecieron activos. El runtime montado en `/app/Data/compact.sqlite3`
coincide con el artefacto reproducible:

```text
sha256=2abb3724ce94106e2dee0fb5d638ccbc5572a43143fc3dcafd430a99c059b6b6
game restart count=0
puerto 2239=abierto
puerto 2250=abierto
LoginServer registration=correcta
```

Durante la carga inicial ocurrió una sola carrera ya conocida entre
`TransferManager.GetTransfers()` y el poblado de transfers. No se repitió,
no produjo reinicio y no hay errores fatales; queda fuera del flujo de quests.

## Cierre transversal de QuestActObjTalk

La prueba real de Dannia avanzó hasta `2486 Tragedy in Riverspan`. El cliente
abrió correctamente la conversación con Malcolm y emitió:

```text
CSQuestTalkMadePacket 0x171
npcObjId=50554
questContextId=2486
questComponentId=10745
questActId=26178
```

El runtime AA8 y la wiki compatible corroboran el cierre exacto:

```text
quest 2486
  Progress component 10745
    quest_act 26178
      QuestActObjTalk detail 969
        npc 10586 Malcolm
```

La causa no era un dato ausente: `CSQuestTalkMadePacket` leía correctamente
los cuatro campos, pero el manejador histórico sólo los registraba y
descartaba el evento. Se conectó el paquete con `CharacterQuests.OnTalkMade`
y se añadió validación transversal de:

```text
personaje y quest activos
estado y step Progress
target NPC explícito y distancia <= 8 m
component exacto perteneciente a la quest
quest_act exacto perteneciente al component
tipo QuestActObjTalk
npc template exacto del act
```

El evento válido incrementa una sola vez el contador correspondiente; la
transición síncrona a Ready hace que una repetición posterior sea rechazada.

Evidencia visible compatible:

```text
https://wiki.archerage.to/na-en/db/quests/2486
```

### Respaldo y despliegue del cierre talk

```text
backup
D:\Proyectos\AAemu\backups\pre-native-quest-talk-v1-20260801-133936

mysql-all.sql
sha256=B9950997E4B82FB52E920A1AB2C9F75003A09C5DFA32FFFA2F1A40D38B6A231E

runtime preservado
sha256=2ABB3724CE94106E2DEE0FB5D638CCBC5572A43143FC3DCAFD430A99C059B6B6

imagen de rollback
aaemu-game:pre-native-quest-talk-v1-20260801-133936
```

Se recreó únicamente `game`. `db`, `login` y la SQLite no cambiaron. La
verificación posterior confirmó:

```text
ScriptCompiler=0 errores, 8 warnings conocidas
mounted compact sha256=2abb3724ce94106e2dee0fb5d638ccbc5572a43143fc3dcafd430a99c059b6b6
game restart count=0
puerto 2239=abierto
puerto 2250=abierto
LoginServer registration=correcta
fatal/unhandled=0
```

MySQL conserva a Dannia con `quest template_id=2486`, `status=1 Progress`.
La carrera conocida de `TransferManager` apareció una sola vez durante el
poblado inicial y no se repitió.

## Siguiente prueba manual

Punto de partida: `2486 Tragedy in Riverspan`, conversación con Malcolm.

```text
1. entrar con Dannia;
2. comprobar que 2486 continúa activa y en progreso;
3. hablar una sola vez con Malcolm;
4. pulsar Talk/F una sola vez;
5. confirmar que el diálogo cierra y el objetivo avanza a Ready/Complete;
6. no hablar todavía con el NPC de entrega y avisar para inspeccionar la traza.
```

Después de auditar ese inicio se continúa una interacción por vez hasta cerrar
el capítulo 2 y luego capítulos 3–6.
