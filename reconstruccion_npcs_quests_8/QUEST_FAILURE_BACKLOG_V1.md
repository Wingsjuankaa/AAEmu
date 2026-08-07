# Backlog de fallos de quests AA8

Fecha de inicio: `2026-07-30`

Runtime estable de prueba:

```text
compact-8.0-runtime-native-npc-visual-v1.sqlite3
sha256=A97D4162020F02AA579D2F95AA41B02F90302EC708E3ADD30A0156467281F5F7
```

## Propósito

Este archivo conserva los fallos observados durante pruebas manuales antes de
implementar nuevas correcciones. El objetivo es agruparlos posteriormente por
primitiva transversal y no generar parches específicos por quest.

Reglas:

- registrar el fallo cuando se informa, preservando el contexto disponible;
- detener la prueba ante bloqueo, desconexión, duplicación, pérdida de items o
  posible corrupción;
- distinguir hechos observados, evidencia técnica e inferencias;
- no cambiar el runtime mientras el usuario esté acumulando fallos;
- comenzar las reparaciones sólo cuando el usuario indique
  `aplica las correcciones`;
- implementar y validar primitivas reutilizables, no excepciones por quest ID.

Estados:

```text
capturado
evidenciado
agrupado
en_reparacion
listo_para_retest
cerrado
descartado
```

Severidades:

```text
critica  = corrupción, pérdida, duplicación, excepción o desconexión
alta     = cliente bloqueado o flujo imposible de continuar
media    = objetivo, reporte o recompensa incorrectos sin corrupción
baja     = presentación, texto, marcador o animación
```

## Resumen

| ID | Quest/transición | Síntoma | Familia preliminar | Severidad | Estado |
|---|---|---|---|---|---|
| QF-0001 | `330 -> quest siguiente no identificada` | El diálogo quedó bloqueado al intentar iniciar la segunda misión | convivencia de catálogo / respuesta de inicio | alta | evidenciado |
| QF-0002 | `330 -> abrir cofres de armas` | El arma se crea, pero la ventana y el inventario no reciben feedback inmediato | item selectivo / `ItemTask` / actualización de inventario | media | listo_para_retest |
| QF-0003 | `2257, Warning the Villagers` | No se ve el casteo al registrar el cadáver y una segunda interacción entrega otro guante | presentación de skill / loot de quest / idempotencia | critica | listo_para_retest |
| QF-0004 | `2258 -> 2259, The General's Orders` | Al aceptar la quest siguiente el diálogo permanece abierto | dependencia inicial ausente / inicio sin respuesta terminal | alta | listo_para_retest |
| QF-0007 | `2263, A Deadly Plot` | Loot visible responde “Your bag is full” con 38 espacios libres | item de objetivo tombstone / transferencia de loot | alta | listo_para_retest |
| QF-0008 | `2261, Truth Extraction` | La oferta queda esperando al aceptar | SupplyItem tombstone con skill de quest / cierre de recompensa | alta | listo_para_retest |
| QF-0011 | `2265, A Dead Man's Wish` | La oferta queda esperando al aceptar | SupplyItem tombstone / crosswalk corroborado | alta | listo_para_retest_controlado |

## QF-0001 — bloqueo al iniciar la misión siguiente a quest 330

### Reporte

```text
Fecha local: 2026-07-30
Hora aproximada: 17:05
Personaje: Wingsjuanka
Quest anterior: 330, Exciting News
Quest siguiente: no identificada en el paquete registrado
Etapa: inicio/oferta de la siguiente quest
NPC visible: Gossiper Parish
Diálogo visible: The Prophet Terrien
```

Resultado esperado:

```text
el diálogo avanza y la siguiente quest recibe una respuesta válida del servidor
```

Resultado observado:

```text
la pantalla de diálogo quedó bloqueada;
el cliente terminó mostrando el contador de salida;
la sesión se desconectó sin iniciar la siguiente quest
```

### Evidencia técnica observada

Runtime durante el fallo:

```text
compact-8.0-runtime-native-quest-catalog-v2.sqlite3
sha256=D8FBD65AC8906ACC876D31A10F31293CA4A8E1DD40BF3712FF2DFBEC696A2744
561 quests ejecutables
7265 quests en cuarentena
```

Secuencia confirmada en logs:

```text
17:05:30 CSCompleteQuestContext quest=330
17:05:30 se ejecutan recompensa EXP e items
17:05:30 quest 330 se elimina del journal activo
17:05:30 SCQuestContextCompletedPacket
17:05:31 CSStartQuestContextPacket para la siguiente interacción
17:05:58 desconexión del cliente
```

No se registró una respuesta de inicio después del segundo
`CSStartQuestContextPacket`.

Después del rollback, MySQL confirmó que `Wingsjuanka` no conservaba ninguna
quest activa parcialmente insertada.

Evidencia preservada fuera del repositorio:

```text
D:\Proyectos\AAemu\backups\quest-rollback-20260730-1705\
  game-before-rollback.log
  second-quest-client-stall.png
  aa8-runtime-observations.sqlite3
```

### Inferencia pendiente de confirmación

La explicación más consistente es que la siguiente quest estaba ausente o en
cuarentena en el catálogo V2 y el servidor terminó la ruta mediante un retorno
silencioso. Esto es una inferencia: falta identificar el quest ID concreto y
confirmar el consumidor y la respuesta esperada por el cliente AA8.

### Familia transversal preliminar

```text
catálogo runtime restrictivo
-> quest anunciada por el cliente pero no ejecutable en el servidor
-> CSStartQuestContext sin respuesta terminal válida
-> diálogo del cliente queda esperando
```

La futura corrección debe permitir la convivencia con el catálogo estable o
producir una respuesta AA8 confirmada. No se debe inventar un paquete de error
ni volver a excluir globalmente las quests no reconstruidas.

### Contención aplicada

Se revirtió el pipeline restrictivo mediante:

```text
c911b746 Revert "feat: add native AA8 quest observation pipeline"
```

El runtime volvió a `native-npc-visual-v1`, con `6628` quests cargadas. Esta
contención restaura el entorno de pruebas, pero no constituye la reparación
transversal definitiva de QF-0001.

## QF-0002 — falta feedback al confirmar un cofre de arma selectivo

### Reporte

```text
Fecha local: 2026-07-30
Hora observada en logs: 17:29-17:31
Personaje: Wingsjuanka
Quest relacionada: 330, Exciting News
Etapa: uso de recompensas después de completar la quest
```

Recompensas relacionadas confirmadas en el grafo runtime:

```text
QuestActSupplyItem
  -> item 51185
  -> Explorer's Ranged Weapon Crate

QuestActSupplySelectiveItem, selección 2
  -> item 47869
  -> Explorer's 2H Weapon Crate
```

Resultado esperado:

```text
seleccionar un arma y pulsar Confirm;
cerrar o resolver la ventana Uncloak;
consumir el cofre;
mostrar inmediatamente el arma nueva y la eliminación del cofre;
entregar feedback visible de éxito sin reabrir el inventario
```

Resultado observado:

```text
la ventana de selección se abre correctamente;
se puede elegir Explorer's Nodachi y pulsar Confirm;
no aparece feedback de éxito ni un delta visible confiable en el inventario;
al cerrar y volver a abrir el inventario aparece el arma entregada
```

No se observó desconexión, duplicación ni pérdida del arma.

### Evidencia visual

Las cinco capturas confirman:

```text
Explorer's Ranged Weapon Crate presente
Explorer's 2H Weapon Crate presente
ventana Uncloak con Explorer's Nodachi seleccionado
inventario antes de refrescar
Explorer's Nodachi visible después de reabrir el inventario
```

Evidencia preservada fuera del repositorio:

```text
D:\Proyectos\AAemu\backups\quest-failures\QF-0002\
  capture-1.png
  capture-2.png
  capture-3.png
  capture-4.png
  capture-5.png
  game-session.log
```

### Evidencia técnica observada

Selección del cofre 2H:

```text
17:29:14 C->S CSBagHandleSelectiveItemsPacket, opcode 0x1C4
skill selectiva 42209
source item 47869
option index 2
result item 47784, Explorer's Nodachi
ERROR: produced invalid ItemTask count 0; forcing resync
S->C cinco SCCharacterInvenContentsPacket
```

Selección del cofre ranged durante la misma prueba:

```text
17:30:58 C->S CSBagHandleSelectiveItemsPacket, opcode 0x1C4
skill selectiva 46956
source item 51185
ERROR: produced invalid ItemTask count 0; forcing resync
S->C cinco SCCharacterInvenContentsPacket
```

MySQL contiene el resultado 2H:

```text
item instance 16777219
template 47784
type Weapon
slot Inventory:7
count 1
created_at 2026-07-30 17:29:14
```

Esto confirma que la mutación autoritativa ocurrió y que el defecto principal
está en la notificación inmediata al cliente, no en la materialización final
del Nodachi.

### Familia transversal preliminar

```text
CSBagHandleSelectiveItemsPacket
-> consumir source item
-> crear result item
-> construir deltas ItemRemove/ItemAdd/ItemCountUpdate
-> tasks.Count queda en 0
-> no se envía SCItemTaskSuccessPacket SelectiveItem
-> se fuerza resync completo de inventario
-> UI no recibe la finalización/delta esperado en tiempo real
```

El log confirma `tasks.Count=0`; la razón por la que la comparación
before/after no detecta las mutaciones todavía debe demostrarse. No se debe
asumir aún si el origen es reutilización de instance ID, semántica de
`ItemTaskType.Invalid`, comparación de snapshots o layout del resultado.

### Alcance transversal preliminar

Todas las acciones registradas en:

```text
aaemu_selective_item_actions
aaemu_selective_item_options
```

pueden compartir el mismo defecto porque pasan por
`CSBagHandleSelectiveItemsPacket`. Deben enumerarse antes de reparar.

### Criterio futuro de retest

```text
[ ] Confirm cierra o resuelve correctamente la ventana
[ ] el cofre desaparece inmediatamente
[ ] el arma elegida aparece inmediatamente
[ ] se envía una tarea selectiva válida, no sólo un resync completo
[ ] no existe duplicación al pulsar Confirm repetidamente
[ ] estado persiste después de relog
[ ] repetir con cofre 2H y cofre ranged
```

No se aplicó ninguna corrección durante la captura de este incidente.

### Reparación aplicada en stack V1

La comparación `before/after` trataba como idéntico un instance ID que el
inventario había reutilizado inmediatamente para el item de resultado. Ahora,
si el mismo ID cambia de template, contenedor o slot, el delta nativo se
serializa como `ItemRemove + ItemAdd`; sólo una identidad realmente estable usa
`ItemCountUpdate`.

Alcance del catálogo activo:

```text
16 acciones selectivas
122 opciones selectivas
```

Estado: `listo_para_retest`.

## QF-0003 — casteo invisible y duplicación de Bloodhand Glove

### Reporte

```text
Fecha local: 2026-07-30
Hora visible en el cliente: 13:33:40-13:33:52
Personaje: Wingsjuanka
Quest: 2257, Warning the Villagers
Etapa: objetivo
Actor: Bloodhand Corpse
Doodad lógico AA8: 14073
```

Resultado esperado:

```text
al interactuar con el cadáver se muestra la animación o barra de casteo;
al terminar se entrega exactamente un Bloodhand Glove;
la quest pasa a Ready;
una interacción posterior no vuelve a mutar el objetivo ni el inventario
```

Resultado observado:

```text
el jugador no ve animación de casteo;
después de unos segundos aparece el guante en el inventario;
la quest queda Complete y pide reportar a Malphus;
una segunda interacción con el mismo cadáver entrega otro Bloodhand Glove;
el chat muestra dos líneas consecutivas "Acquired: [Bloodhand Glove]"
```

No se observó bloqueo ni desconexión. La duplicación confirmada hace que el
incidente sea crítico conforme a la escala de este backlog.

### Evidencia visual

La captura confirma simultáneamente:

```text
quest 2257 añadida a las 13:33:40
tracker en estado [Complete]
objetivo "Report to Malphus"
dos adquisiciones visibles de Bloodhand Glove
personaje sobre un Bloodhand Corpse todavía interactuable
```

Evidencia preservada fuera del repositorio:

```text
D:\Proyectos\AAemu\backups\quest-failures\QF-0003\
  capture-1.png
  game-session.log
```

### Autoridad AA8 confirmada en el compact activo

```text
quest 2257
  Start component 9947
    QuestActConAcceptDoodad
  Progress component 9998
    QuestActObjInteraction
  Progress component 17567
    QuestActObjItemGather, detail 4330
      item 16287, Bloodhand Glove
      count 1
      cleanup 1
      destroy_when_drop 1
  Ready component 9949
    QuestActConReportNpc

item 16287
  loot_quest_id 2257
  max_stack_size 10

client_doodad 14073
  personal phase 41493
  use skill 41925
```

El compact también contiene un item homónimo `16288`, pero pertenece a la
quest `2258`; no debe mezclarse con el guante `16287` de este incidente.

### Evidencia técnica observada

Primera interacción de recolección:

```text
17:33:42 C->S CSStartSkillPacket, skill 41925
17:33:42 S->C SCSkillStartedPacket
  realCast=2790
  baseCast=3000
  startAnim=56
17:33:45 S->C SCSkillFiredPacket
17:33:45 personal phase 41493 seleccionada
17:33:45 QuestActObjInteraction deja el componente 9998 Ready
17:33:45 QuestActObjItemGather alcanza 1 y deja el componente 17567 Ready
17:33:45 S->C SCItemTaskSuccessPacket, action=Loot, tasks=1
17:33:45 S->C SCSkillEndedPacket, completed=True
```

Segunda interacción:

```text
17:33:49 C->S CSStartSkillPacket, skill 41925
17:33:49 S->C SCSkillStartedPacket
  realCast=2790
  baseCast=3000
  startAnim=56
17:33:52 S->C SCSkillFiredPacket
17:33:52 la función GiveQuest rechaza reiniciar 2257:
  active=True, completed=False
17:33:52 OnItemGather continúa con objective=2
17:33:52 QuestActObjItemGather sigue Ready
17:33:52 S->C SCItemTaskSuccessPacket, action=Loot, tasks=1
17:33:52 S->C SCSkillEndedPacket, completed=True
```

Esto demuestra que el servidor sí envía la secuencia de casteo, aunque el
cliente no la representa como animación visible. También demuestra que el
rechazo de la función de quest no detiene los efectos posteriores de loot.

### Hechos confirmados

```text
la skill 41925 tiene un casteo servidor de aproximadamente 3 segundos
los paquetes Started, Fired y Ended se enviaron en ambas interacciones
el objetivo nativo exige un solo item 16287
el primer loot completa la quest
el segundo uso incrementa el objetivo observado a 2
el segundo uso envía otra tarea Loot y entrega un segundo guante
```

### Inferencias pendientes de confirmación

La ausencia visual puede depender de la combinación de `startAnim=56`,
`fireAnim=0`, el tipo de target doodad o datos de presentación de la skill.
Todavía no se ha demostrado cuál de ellos difiere de la semántica AA8
esperada.

La duplicación parece producirse porque el guard de quest y el efecto de loot
se ejecutan en rutas independientes: el primero rechaza el segundo
`GiveQuest`, pero no cancela el `OnItemGather` ni la creación del item. Falta
identificar el límite transaccional correcto antes de modificar el runtime.

### Familias transversales preliminares

```text
presentación de skills de interacción con doodad
-> Started/Fired/Ended presentes
-> el cliente no muestra casteo o animación

recolección de item de quest mediante skill/doodad
-> el objetivo ya está Ready o ya existe la cantidad requerida
-> una interacción repetida sigue creando loot
-> falta idempotencia antes de mutar inventario y progreso

función de doodad con varios efectos
-> un guard rechaza la operación de quest
-> los efectos hermanos continúan ejecutándose
-> el rechazo no es terminal para toda la interacción
```

Antes de reparar se deben enumerar todas las quests AA8 que combinen
`QuestActObjInteraction`, `QuestActObjItemGather` y loot originado por skill de
doodad. La solución debe validar la necesidad del objetivo antes de crear el
item y no codificar excepciones para quest `2257` ni item `16287`.

### Criterio futuro de retest

```text
[ ] la interacción muestra el casteo/animación AA8 esperada
[ ] cancelar o interrumpir el casteo no entrega el item
[ ] el primer casteo entrega exactamente un item 16287
[ ] el objetivo pasa a Ready y el tracker conserva el estado correcto
[ ] un segundo uso no modifica el objetivo ni el inventario
[ ] no se envía una segunda tarea Loot
[ ] completar la quest consume o limpia el item conforme al compact
[ ] abandonar y retomar la quest restaura un estado coherente
[ ] el resultado persiste correctamente después de relog
```

No se aplicó ninguna corrección durante la captura de este incidente.

### Reparación aplicada en stack V1

Se cerraron tres límites genéricos:

```text
SkillObject tipo 28:
  header + UInt32 + UInt32 + inputDirection

reentrada:
  una skill con casting_useable=0 no inicia otro CastTask superpuesto

loot:
  un item con loot_quest_id y relación exacta QuestActObjItemGather
  sólo se crea mientras exista un objetivo Progress incompleto
```

El guard exacto cubre `197` items del compact. Otros `641` items con
`loot_quest_id` pero sin una relación exacta `QuestActObjItemGather` conservan
el comportamiento anterior, evitando imponer semántica sobre objetivos de
grupo u otras primitivas todavía no reconstruidas.

Estado: `listo_para_retest`.

## QF-0004 — diálogo bloqueado al iniciar The General's Orders

### Reporte

```text
Fecha local: 2026-07-30
Hora observada en logs: 17:38:44-17:40:10
Personaje: Wingsjuanka
Quest anterior: 2258, An Urgent Message
Quest bloqueante: 2259, The General's Orders
Etapa: aceptar/iniciar la quest siguiente
NPC: General Govannon, template 3611
```

Resultado esperado:

```text
completar 2258;
iniciar 2259;
recibir General Govannon's Letter;
cerrar el diálogo y mostrar el nuevo objetivo hacia Captain Baker
```

Resultado observado:

```text
2258 se completa correctamente;
el cliente solicita iniciar 2259;
el servidor rechaza la dependencia inicial;
el diálogo queda abierto sin una respuesta terminal compatible;
el usuario no puede continuar el flujo
```

### Evidencia preservada

```text
D:\Proyectos\AAemu\backups\quest-failures\QF-0004\
  capture-1.png
  game-session.log
```

Secuencia exacta:

```text
17:38:44 CSCompleteQuestContext quest=2258
17:38:44 quest 2258 removida y SCQuestContextCompleted enviado
17:38:46 CSStartQuestContextPacket quest=2259
17:38:46 AA8QuestStartGuard rechaza item inicial 16259:
  reason=missing_item_template
17:40:10 desconexión
```

### Autoridad AA8 confirmada

El grafo nativo ya presente en el runtime declara:

```text
quest 2259, The General's Orders
  Start 9955
    QuestActConAcceptNpc -> General Govannon 3611
  Supply 9956
    QuestActSupplyItem -> item 16259 x1
  Progress 9958
    QuestActObjItemGather -> item 16259 x1
  Ready 9957
    QuestActConReportNpc -> Coast Guard Captain Baker 10582
  Reward 10001

item 16259, General Govannon's Letter
  fila exacta extraída de game11
  loot_quest_id 2259
  max_stack_size 1
  use_skill_id 0
```

Dossiers forenses:

```text
quest-2259.json
sha256=8F7F9578060849342CA19D30B179C829ED28D399D02E50C7F197E8FCCE824565

item-16259.json
sha256=D585FE288552A65A89050A1D6873301D0893A84B8F06A41EC8F26091690C7267
```

La wiki sólo corroboró visualmente el nombre, la carta entregada y el NPC de
reporte; no se usó como autoridad para generar ninguna fila.

### Causa demostrada

```text
el grafo de quest 2259 existe y es ejecutable
-> QuestActSupplyItem requiere 16259
-> el item 16259 no existe en el compact activo
-> QuestStartDependencyGuard rechaza antes de insertar el journal
-> no existe todavía layout AA8 demostrado para el paquete de fallo
-> el cliente conserva el diálogo pendiente
```

### Reparación del primer stack

Se reconstruyó un runtime incremental sobre el catálogo amplio y estable:

```text
compact-8.0-runtime-native-quest-repair-stack-v1.sqlite3
sha256=7C0100208A4846058F62377203DE48E237D332CFB77E926F90D96B5397C5DB25
```

La capa añade únicamente la fila nativa exacta de item `16259` y su cobertura
genérica completa. No reactiva el catálogo estricto V2, no elimina quests
históricas del runtime y no inventa un paquete de error.

Estado: `listo_para_retest`.

### Criterio de retest

```text
[ ] aceptar 2259 cierra el diálogo
[ ] se recibe exactamente una carta 16259
[ ] la quest aparece en el journal
[ ] el objetivo señala a Captain Baker
[ ] completar o abandonar limpia la carta según el grafo
[ ] el estado persiste después de relog
```

## QF-0005 — diálogo bloqueado al iniciar Battle by the Bay

### Reporte

```text
Fecha local: 2026-07-31
Personaje: Dannia, character id 1, nivel 6
Quest bloqueante: 2260, Battle by the Bay
Etapa: aceptar/iniciar
NPC: Coast Guard Captain Baker, template 10582
```

Resultado esperado:

```text
aceptar 2260;
recibir Secret Crescent Throne Orders 16260 x1;
cerrar el diálogo;
activar el objetivo de entrega a Coast Guard Officer Chloe 10583
```

Resultado observado:

```text
el diálogo no se cierra;
la quest no entra al journal;
el ítem inicial no se entrega;
el cliente queda esperando la terminación de la aceptación
```

### Evidencia de runtime y autoridad AA8

```text
20:47:47 CSStartQuestContextPacket quest=2260
20:47:47 AA8QuestStartGuard rejected quest 2260 for Dannia:
  unavailable initial supply item 16260
  reason=missing_item_template
```

El estado MySQL previo al despliegue confirmó que el intento fallido no dejó
quest 2260 ni ítem 16260 persistidos para Dannia.

El grafo nativo confirmado es:

```text
quest 2260, Battle by the Bay
  Start 9959
    QuestActConAcceptNpc 1856 -> Captain Baker 10582
  Supply 9960
    QuestActSupplyItem 1334 -> item 16260 x1
  Progress 10002
    QuestActObjItemGather 938 -> item 16260 x1
  Ready 9961
    QuestActConReportNpc 2092 -> Officer Chloe 10583
  Reward 9962

item 16260, Secret Crescent Throne Orders
  category_id 64
  impl_id 0
  use_skill_id 0
  buff_id 0
  craft_id 0
  loot_quest_id 2260
  max_stack_size 1
```

Dossiers:

```text
quest-2260.json
sha256=574CA90A7E98B863C491610D00D965F3D3C0512C1AE38C9AAC086286679B8549

item-16260.json
sha256=A248CB8CD805D0D16380A792FFA5EABD1A506BCD81B08438C699A37A16BD5468
```

La wiki compatible se usó sólo para corroborar nombre, NPCs y objeto visible;
las filas del runtime proceden exclusivamente del cliente Kakao AA8.

### Patrón transversal demostrado

QF-0004 y QF-0005 comparten exactamente esta cadena:

```text
SupplyItem inicial
-> fila items ausente
-> guard fail-closed antes de insertar el journal
-> cliente conserva el diálogo pendiente
```

La reparación V2 transforma el caso en una política reusable pero acotada:

```text
promover sólo entradas explícitamente documentadas
AND impl_id=0
AND use_skill_id=0
AND buff_id=0
AND craft_id=0
AND grafo SupplyItem/ItemGather exacto
```

El censo encontró 961 objetos iniciales sin cobertura completa antes de esta
reparación. Sólo 16260 fue promovido ahora; los otros 960 permanecen
fail-closed porque no tienen todavía dossier y cierre de dependencias. Esto
evita convertir una corrección transversal en una importación indiscriminada.

### Runtime y validación

```text
compact-8.0-runtime-point0-quest-supply-stack-v2.sqlite3
sha256=BD25C9EC6086E76A36C5E9DF7A41A1FCB7EA1D1599FB06A614235339B919604C

dos builds deterministas: hash idéntico
quick_check=ok
integrity_check=ok
regresión Python conjunta=24/24
suite completa AAEmu.Tests .NET Core 3.1=311/311
ScriptCompiler=0 errores, 8 warnings históricas
```

Despliegue:

```text
backup MySQL:
D:\Proyectos\AAemu\backups\quest-supply-closure-v2-20260731-165916\mysql-all.sql
sha256=3048D8561ACED2FEDFC5E0755BDE244EFC230E28DBED9D49FA5D5E1DFB8B2E4B

servicio recreado: game solamente
compact montado read-only con hash esperado
items 16259 y 16260: exactamente una fila por ID
restart_count=0
Game 2239 y Stream 2250 escuchando
LoginServer registrado
```

Estado: `listo_para_retest`.

### Criterio de retest controlado

```text
[ ] aceptar 2260 una sola vez
[ ] el diálogo se cierra
[ ] la quest aparece en el journal
[ ] se recibe exactamente un ítem 16260
[ ] detenerse antes de reportar a Officer Chloe
```

Después de verificar logs y MySQL se habilitará el segundo paso: reporte,
recompensa, limpieza del ítem y persistencia tras relog.

## QF-0006 — entrega bloqueada de Battle by the Bay y cajas Explorer inertes

### Reporte

```text
Fecha local: 2026-07-31
Personaje: Dannia, character id 1, nivel 6
Quest: 2260, Battle by the Bay
Etapa: recompensa
Resultado observado: Take Reward no completa la entrega
Incidencia asociada: las cajas de componentes Explorer no producen resultados
```

### Causa demostrada

```text
CSCompleteQuestContext quest=2260 selected=2
AA8QuestRewardGuard rejected selected=2 unavailableItem=0
reason=invalid_selective_reward
```

El componente Reward 9962 estaba incompleto en el runtime V2. Faltaban los
actos selectivos 65260/65261/65262, EXP 64100 y cobre 65675. Por separado, las
cajas 47985/47986/47987 no tenían completo el recorrido nativo
`use_skill -> skill_effect -> GainLootPackItemEffect -> loot pack`.

### Reparación V3

Se reconstruyó el componente 9962 completo desde el dossier AA8 y se cerraron
las tres cajas con datos del compact del cliente y game11. Los únicos renglones
derivados fueron los nueve `loots` server-only, enumerados exhaustivamente por
las descripciones AA8. No se importaron datos históricos 3.0.

```text
runtime sha256=171AABCAC72D1333439433396B70728F9786BB73E0A3054FA2A56E467EC53203
dos builds deterministas
quick_check=ok; integrity_check=ok; huérfanos=0
Python=26/26; AAEmu.Tests=311/311; ScriptCompiler=0 errores
```

Checkpoint completo:
`CHECKPOINT_NATIVE_QUEST_REWARD_EXPLORER_CLOSURE_V3.md`.

Estado: `listo_para_retest_controlado`.

### Criterio de retest

```text
[ ] disponer de al menos 6 espacios libres
[ ] elegir una vez la recompensa 2 (Leather, item 47986)
[ ] el diálogo cierra y quest 2260 queda completada
[ ] item 16260 se consume
[ ] se aplican 2800 EXP y 2500 copper
[ ] se entregan 23633 x1, 48507 x2 y 47986 x1
[ ] detenerse antes de abrir la caja y auditar estado
[ ] abrir 47986 con 3 espacios libres
[ ] la caja se consume y entrega 48025, 48027 y 48028 x1
[ ] el resultado persiste tras relog
```

## QF-0007 — Bloodhands' Instructions no entra al bolso

Dannia tenía 12 objetos en un bolso de 50. El Bloodhand Duelist produjo el
loot `24126`, pero `CSLootItemPacket` terminó en `SCLootItemFailedPacket`.

La misión y el loot convergen de forma exacta:

```text
quest 2263
-> QuestActObjItemGather 2046
-> item 24126 x1, cleanup=1
-> ocho loot packs con drop 100%
```

La causa es que `24126` está ausente de `items` y de la cobertura del runtime.
El dossier AA8 lo clasifica como tombstone: la relación sobrevivió, pero la
fila positiva del catálogo ya no existe. Se añadió un proxy genérico y
dependency-free, explícitamente `server_derived_accepted`, sólo para loot,
inventario, progreso, persistencia y cleanup. No se importaron filas 3.0.

Runtime preparado:

```text
compact-8.0-runtime-point0-quest-loot-proxy-v5.sqlite3
sha256=76F1D8A82B1ECEA85FEECAA3A8A114F1BEA9001C6CB8F34D160CE3284FD8EE77
```

El censo transversal registró `532` item IDs en `590` quests con el mismo
tipo estructural de hueco antes del proxy. Sólo `24126` fue habilitado; los
otros `531` continúan fail-closed hasta cerrar evidencia individual.

Estado: `listo_para_retest`.

Checkpoint: `CHECKPOINT_POINT0_QUEST_LOOT_PROXY_V5.md`.

## QF-0008 — Truth Extraction queda congelada al aceptar

Dannia intentó aceptar `2261 Truth Extraction` con Coast Guard Chugin. El
servidor recibió el paquete, pero el guard de dependencias rechazó la misión:

```text
CSStartQuestContextPacket quest=2261
[AA8QuestStartGuard] Rejected quest 2261 for Dannia:
unavailable initial supply item 16293, reason=missing_item_template
```

El grafo AA8 demuestra el contrato completo:

```text
SupplyItem 2273 -> item 16293 x1, show_action_bar=1, cleanup=1
ObjItemUse 598 -> item 16293 x1, alias 6578
skill 13886 -> plot 383, hostile, 0-20 m, cooldown 10 s
Reward -> 4500 EXP + item 18791 x5
```

`16293 Hypnotic Staff` es un tombstone nativo: conserva relaciones tipadas,
pero no una fila positiva en el catálogo completo AA8. Se creó un único proxy
`server_derived_accepted` limitado a suministro, inventario, barra temporal,
skill 13886, progreso, persistencia y cleanup. Comercio, venta, subasta,
craft, buff y equipo permanecen deshabilitados.

Durante el cierre también se detectaron y restauraron seis filas nativas de
quest omitidas por la composición anterior: alias 6578, campos nativos del
objetivo 598, EXP 3933, reward item 8881 y acts 64103/65631.

```text
runtime candidato:
compact-8.0-runtime-point0-quest-use-proxy-v6.sqlite3
sha256=6C8797A8F133DEDC4E1247B737160E5EB4818BF19A841A351238EAEAC0091C15

dos builds deterministas: idénticos
quick_check=ok; integrity_check=ok
Python quests=98/98
AAEmu.Tests=314/314
ScriptCompiler en tests=0 errores, 8 warnings conocidas
```

Estado: `listo_para_retest`.

Checkpoint: `CHECKPOINT_POINT0_QUEST_USE_PROXY_V6.md`.

## QF-0009 — compra en mercader no ejecutada

### Reporte

```text
Fecha local: 2026-07-31, 01:04
Personaje: Dannia, character id 1
NPC: Deven, Weapon Merchant, template 5342, ObjId 37049
Acción: comprar Explorer's 1H Weapon Crate, item 47868 x1
Precio mostrado: 250 copper
Resultado observado: el botón Purchase activa el envío, pero no entrega el
ítem ni descuenta dinero
```

### Evidencia cerrada

El cliente emitió dos veces el mismo paquete C2G nivel 5 y el servidor lo
rechazó antes de llegar a la lógica de comercio:

```text
01:04:24 Unknown packet 0xf0(5)
01:05:46 Unknown packet 0xf0(5)
payload:
b9 90 00 00 00 00 00 00 00 00 01 00 fc ba 00 00 00 01 00 00 00 00 00 00
```

Con la semántica `ReadBc` de tres bytes y el layout existente de compra, el
payload se descompone de forma coherente como:

```text
npcObjId=37049
doodadObjId=0
unkId=0
nBuy=1
nBuyBack=0
itemId=47868
grade=0
count=1
currency=0
useAAPoint=0
trailingByte=0
```

La auditoría inmediata confirmó `money=7097` sin cambios y ninguna instancia
de item 47868 para Dannia. No hubo mutación parcial.

El runtime AA8 relaciona el NPC 5342 con el pack proxy 914119 y contiene el
good `47868, grade 0, currency 0, price 250, sort 0`. La wiki de ArcheRage
corrobora únicamente que el NPC 5342 ofrece el item 47868; su precio publicado
es 0 y no se usa como autoridad económica.

### Causa y alcance

El cliente AA8 asigna `0x0F0` al constructor nativo x86
`x2game.dll RVA 0x00830970` (SHA-256
`078DB1B94236ECB8BBE21DC5C71CE90C178D51B6BF261C4767D32A44809BDDC3`).
El servidor todavía registra `CSBuyItemsPacket` en `0x188`, mientras `0x0F0`
permanece sin registrar como `off_3A0D7D80`.

La lógica autoritativa y atómica de compra ya existe en
`CSBuyItemsPacket`/`MerchantPurchaseService`; el bloqueo demostrado está en el
mapeo de protocolo AA8. El paquete observado coincide con el layout conocido,
salvo un byte final todavía no nombrado. Antes de reparar se debe cerrar ese
campo desde el corpus nativo y añadir fixtures de parseo para compra simple,
múltiple y buyback.

```text
severidad: alta; todos los comercios NPC quedaban sin compra
familia transversal: protocolo C2G de merchant purchase
estado: reparado y desplegado; listo_para_retest_controlado
retest: comprar exactamente un item 47868 y detenerse antes de abrirlo,
        repetir la compra o reloguear
```

Checkpoint de reparación:
`reconstruccion_items_8/phase_b_explorer_hiram/CHECKPOINT_B14A_NATIVE_MERCHANT_PURCHASE_PROTOCOL.md`.

## QF-0010 — Sloane's Secret no entrega el objeto del cofre

Dannia interactuó con `Empty Ring Box` durante `2264 Sloane's Secret`. La
skill `17310` completó la ruta del doodad, pero la creación de `24967 Sloane's
Will` fue rechazada por cobertura desconocida y el objetivo permaneció `0/1`.

El grafo AA8 conserva `QuestActObjItemGather 1800 -> item 24967 x1`, cleanup,
alias `1522` y doodad resaltado `14310`, pero `24967` es un tombstone sin fila
positiva en el catálogo completo. Se creó un proxy genérico mínimo,
`server_derived_accepted`, limitado a doodad-loot, inventario, progreso,
persistencia y cleanup. Se eliminó el `item_open_papers` heredado no probado.

La misma auditoría cerró la recompensa nativa `34004 x5`, que estaba marcada
como candidata a pesar de tener fila AA8 y cierre completo de `skill 35239`,
10 efectos y 10 buffs.

```text
runtime:
compact-8.0-runtime-point0-quest-doodad-loot-proxy-v7.sqlite3
sha256=6C58249234B000F41B10994703F09D1E9F909C05DBEBC5FE4E6F4B6DBECA1792

validación:
8/8 dirigida; 106/106 Python quests; 318/318 AAEmu.Tests

estado: listo_para_retest_controlado
```

Checkpoint:
`CHECKPOINT_POINT0_QUEST_DOODAD_LOOT_PROXY_V7.md`.

## QF-0011 — A Dead Man's Wish queda congelada al aceptar

La traza identificó el rechazo exacto:

```text
CSStartQuestContextPacket quest=2265
AA8QuestStartGuard rejected item 21604
reason=item_coverage_Unknown
```

El crosswalk terminado confirmó el grant inicial `21604 x1`, su rol y cantidad
con coincidencia estructural completa. La política transversal segura —grant
AA8 inicial fijo, match de rol/conteo, tombstone, fila genérica de quest sin
dependencias y no vendible— encontró sólo este candidato en todo el runtime.

La fila histórica ya existente conserva 55 campos compartidos exactos, cero
overrides y nueve columnas sólo-AA8 con padding cero. Se promovió como
`legacy_3_0_corroborated`, sin afirmar que sea una fila positiva nativa.

También se cerró la recompensa nativa `34000 x5` con `skill 35238`, 10 efectos
y 10 buffs.

```text
runtime:
compact-8.0-runtime-point0-quest-initial-supply-crosswalk-v8.sqlite3
sha256=DA7F6026EDE6F9AE2E7B684BDF6BB199078ABF001C50CBD921F8DE50AADA295C

validación:
7/7 dirigida; 113/113 Python quests; 321/321 AAEmu.Tests

estado: listo_para_retest_controlado
```

Checkpoint:
`CHECKPOINT_POINT0_QUEST_INITIAL_SUPPLY_CROSSWALK_V8.md`.

## QF-0012 — Frontera Nuia V2 capítulos 7–31

La reconstrucción V2 inventaría 294 quests y conserva V1 como prefijo
inmutable. El bloque A (capítulos 7–11) está listo para prueba controlada. La
frontera canónica se detiene en quest 6615 por seis NPC sin relación de spawn
en AA8 ni en el compact legacy compatible; no se inventaron coordenadas.

```text
runtime completo auditado:
compact-8.0-runtime-nuia-story-v2-chapter31.sqlite3
sha256=009D820472DD6F09E57511E6C1FEF663D336CC4AFE1073DDB5F4691B9E722F31

runtime desplegable bloque A:
compact-8.0-runtime-nuia-story-v2-chapter11.sqlite3
sha256=E7A889EEE77E643C8F4EB51BF066DC192551C2F904ACEB78C9A59C2FA1F0DDDB

validación:
28/28 Python V2; 328/328 AAEmu.Tests; Docker SDK 3.1 correcto

estado: bloque_A_listo_para_retest_controlado; capítulos_12_31_fail_closed
```

Checkpoint: `CHECKPOINT_NATIVE_NUIA_STORY_V2.md`.

## QF-0013 — Runebearer pierde el destino después de usar la piedra

Dannia completó `QuestActObjItemUse` de `3993 Runebearer` con el item `26023`,
pero el tracker mostró dos contadores ajenos al recorrido nativo, `0/5` y
`0/10`, y no indicó el siguiente actor.

La traza y MySQL demostraron `objective[0]=1`, `objective[1]=0`, `Step=Progress`
y `ComponentId=0`. La quest tiene dos componentes Progress no selectivos:

```text
17209 -> usar Engraved Lodestone 26023
19840 -> hablar con Marian 10849
19841 -> Ready, reportar a Lucius Quinto doodad 14124
```

Se añadió reconciliación genérica de componentes múltiples y reparación al
cargar persistencia. No se cambió el compact ni se editó el personaje.

```text
estado: V1 corrige persistencia pero no refresco cliente; V2 desplegada, pendiente retest manual
checkpoint: CHECKPOINT_NATIVE_QUEST_3993_MULTI_PROGRESS_V2.md
```

## Plantilla para el siguiente fallo

```text
ID:
Fecha/hora aproximada:
Personaje:
Quest ID y nombre:
NPC/doodad:
Etapa: oferta | aceptar | objetivo | reporte | recompensa | relog
Última acción:
Resultado esperado:
Resultado observado:
Items antes/después:
¿Cliente bloqueado o desconectado?:
Captura o video:
```

Campos que se completarán durante el análisis:

```text
severidad:
estado:
runtime y hash:
evidencia de logs:
estado MySQL:
familia transversal:
quests potencialmente afectadas:
hechos confirmados:
inferencias:
dependencias AA8:
criterio de retest:
```
