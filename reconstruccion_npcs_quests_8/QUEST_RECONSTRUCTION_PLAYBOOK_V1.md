# Hilo conductor para reconstruir quests AA8

## Objetivo

Este procedimiento evita volver a investigar desde cero cuando una quest no
aparece, no progresa o no puede entregarse. Separa dos capas:

```text
capa global del cliente
  inicializa WorldContent y construye los índices NPC -> quest

capa individual de la quest
  datos, NPC, spawns, requisitos, actos, progreso, recompensa y persistencia
```

La quest 330, `Exciting News`, es el caso de referencia probado.

## 1. Base global obligatoria

Antes de depurar una quest individual deben cumplirse estas condiciones.

### 1.1 SCFilterPacket 0x138

El cliente AA8 registra el paquete:

```text
opcode  = 0x138
level   = 5
payload = uint32 filterBufferSize
          byte filterBuffer[filterBufferSize]
```

El manejador nativo ejecuta:

```text
WorldContent::Initialize
-> inicialización del administrador local de quests
-> construcción del índice StartNpc
-> construcción del índice ReportNpc
```

`filterBufferSize=0` es una modalidad nativa válida. El cliente registra
`WorldContent::Initialize: no filter config`, retorna éxito y usa todo el
contenido local. No se debe inventar un filter pack.

Implementación AAEmu:

```text
AAEmu.Game\Core\Packets\G2C\SCFilterPacket.cs
AAEmu.Game\Core\Packets\Proxy\FinishStatePacket.cs
```

Debe enviarse durante `FinishStatePacket state 0`, antes de seleccionar el
personaje. Por eso cualquier cambio en esta capa requiere cerrar y abrir el
cliente; un relog parcial puede no repetir el handshake completo.

### 1.2 Qué construye el cliente

El índice StartNpc relaciona NPC con quests ofrecidas a partir de componentes
de inicio y sus actos nativos, incluido `QuestActConAcceptNpc`.

El índice ReportNpc relaciona NPC con quests listas para entregar a partir del
componente Ready y `QuestActConReportNpc`.

Estos índices son globales y se construyen desde los datos de quests que posee
el cliente. El servidor no envía una lista individual de signos `!` y `?`.
El servidor sí entrega los estados que permiten al cliente decidir cuál signo
mostrar:

```text
journal activo
quests completadas
facción y jerarquía
nivel, raza, género y demás requisitos
estado y componente actual de cada quest
```

### 1.3 Síntoma exacto cuando falta la base global

```text
/quest force ID agrega la quest al tracker
el journal contiene la quest
el estado puede ser Ready
ningún NPC muestra ! o ?
clic derecho no abre oferta ni recompensa
```

No seguir corrigiendo componentes individuales bajo este síntoma. Primero
verificar `SCFilterPacket` y los índices.

### 1.4 Prueba dinámica de los índices

Usar:

```text
reconstruccion_npcs_quests_8\probe_aa8_client_quest_state.ps1
```

La sonda es de sólo lectura. No inyecta ni modifica memoria. Como ArcheAge se
ejecuta elevado, PowerShell también debe elevarse.

Para la quest 330 comprueba:

```text
StartNpc  = Lucius, npc template 3597
ReportNpc = Gossiper Parish, npc template 11541
status    = 3, Ready
completed = false antes de entregarla
```

Interpretación:

```text
ambos índices tienen 0 entradas
  -> falta la inicialización global 0x138

índices poblados, pero no contienen la quest
  -> faltan componentes/actos nativos en el contenido local o están filtrados

índices correctos, status incorrecto
  -> problema de transición, serialización o snapshot del journal

índices y status correctos, completed=true
  -> la quest está excluida legítimamente por completada/no repetible

todo correcto, pero no hay UI
  -> revisar target, interacción, requisitos Lua y contexto posterior
```

## 2. Cierre mínimo de una quest individual

No declarar una quest reconstruida sólo porque `/quest force` funciona. Para
cada ID se debe cerrar esta cadena completa:

```text
identidad
-> grafo de componentes
-> actos y condiciones
-> NPC de inicio y entrega
-> spawns/ubicaciones
-> requisitos
-> objetivos y transiciones
-> recompensas
-> protocolo
-> persistencia
-> presentación del NPC
```

### 2.1 Identidad

Registrar desde fuentes AA8:

```text
quest ID
nombre localizado
categoría/detail type
nivel
repetible o no repetible
cadena anterior y siguiente, si existen relaciones nativas
```

Una wiki sólo corrobora nombre, texto, NPC y recorrido visible. No sustituye
filas, relaciones, layouts o condiciones nativas.

### 2.2 Grafo de componentes

Extraer todos los componentes y clasificarlos por función:

```text
Start
Progress
Ready
Reward
Failure u otras ramas, cuando existan
```

Para cada componente registrar:

```text
component_id
kind_id
next_component
actos asociados en orden
condiciones
objetivos
```

No asumir que `next_component` apunta necesariamente a otra fila de
`quest_components`. Confirmar siempre su consumidor en AA8.

### 2.3 NPC de inicio y entrega

Resolver mediante los actos nativos, no por coincidencia de nombres:

```text
QuestActConAcceptNpc -> npc template que ofrece
QuestActConReportNpc -> npc template que recibe
```

Formato de registro recomendado:

```text
quest 330
  Start component 1520
    QuestActConAcceptNpc -> Lucius, npc 3597

  Ready component 1521
    QuestActConReportNpc -> Gossiper Parish, npc 11541

  Reward component 1522
```

Un mismo template de NPC puede tener múltiples instancias o aparecer en varias
zonas. Eso no rompe por sí mismo la quest: el índice usa el template y los
requisitos/contexto deciden disponibilidad. No deduplicar spawns sin evidencia.

### 2.4 Spawns y ubicación

Separar siempre:

```text
npc template = identidad y comportamiento
spawner       = instancia, mundo, zona, posición y rotación
```

Autoridad de ubicación:

```text
game_pak
  -> capas de spawner del mundo
  -> spawnerId
  -> npc template
  -> world/zone
  -> XYZ/rotación
```

Reusar:

```text
extract_gamepak_npc_spawner_layers.py
generated\gamepak-native-npc-spawner-layers-v1-manifest.json
```

No tomar coordenadas de una wiki como autoridad de runtime; sirven para
corroborar que la zona visible coincide.

### 2.5 Requisitos de visibilidad

Auditar antes de concluir que el marcador está roto:

```text
quest previa requerida
quest ya completada
nivel mínimo/máximo
raza y género
facción y mother faction
zona o esfera
periodicidad
repeatable
items, buffs o estados requeridos
detail/category excluidos por el consumidor
```

La jerarquía de facciones enviada al cliente debe estar completa; un ID de
facción correcto sin su `mother_id` puede volver falsa una condición.

### 2.6 Objetivos y progreso

Por cada acto de progreso:

```text
identificar la clase concreta
confirmar layout y campos
confirmar evento del servidor que lo incrementa
confirmar contador objetivo
confirmar transición a Ready
confirmar SCQuestContextUpdated o snapshot equivalente
```

Casos frecuentes:

```text
matar NPC
interactuar con NPC/doodad
obtener o entregar item
entrar en zona
usar skill
hablar/reportar
temporizador o evento
```

Si falta el manejador genérico de un tipo de acto, implementarlo como primitiva
reutilizable; no insertar excepciones específicas para un quest ID.

### 2.7 Recompensa y cierre

Registrar y probar:

```text
componente Reward
oro/XP/honor/labor
items fijos
items opcionales
capacidad de inventario
skills/buffs/títulos
quest siguiente
bit de completada
persistencia y repeatability
```

La entrega debe ser atómica: si falla un requisito o no hay espacio, no debe
quedar una recompensa parcial ni marcarse la quest como completada.

### 2.8 Modelo y presentación del NPC

Un NPC funcional con cuerpo blanco o sin rostro es un problema distinto del
flujo de quest. Seguir:

```text
NPC_MODEL_RECONSTRUCTION_PATTERN_V1.md
```

Mantener separados los diagnósticos:

```text
marcador/interacción -> índices, estado, requisitos y protocolo
modelo/ropa/rostro   -> template, total_character_custom y assets
spawn/posición       -> capas de mundo y spawner
```

## 3. Árbol rápido según el síntoma

### No aparece `!` en ninguna quest/NPC

```text
1. buscar en logs el envío S->C 0x138;
2. confirmar que se envía en FinishState state 0;
3. reiniciar completamente el cliente;
4. ejecutar la sonda;
5. si los dos índices están vacíos, no tocar quests individuales.
```

### No aparece `!` sólo para una quest

```text
1. verificar componente Start;
2. verificar QuestActConAcceptNpc;
3. verificar npc template y spawn;
4. verificar prerequisitos/completada/repetible;
5. comprobar que la quest está presente en el índice StartNpc.
```

### Aparece `!`, pero clic derecho no ofrece la quest

```text
1. confirmar target ObjId y npc template;
2. revisar CSStartInteraction/CSInteractNPC;
3. revisar evaluación de requisitos del servidor;
4. revisar paquete/contexto de oferta;
5. confirmar que no se está usando una instancia equivocada.
```

### `/quest force` funciona, pero la quest normal no

```text
el journal/protocolo básico existe;
el fallo está antes de la aceptación:
  índice StartNpc, actos de inicio, requisitos o interacción.
```

### La quest se acepta, pero no progresa

```text
1. identificar el acto concreto de Progress;
2. confirmar su evento disparador;
3. revisar contador y target IDs;
4. revisar transición de componente;
5. revisar actualización enviada al cliente.
```

### Aceptar la quest desconecta al jugador

```text
1. buscar el último QuestAct ejecutado antes de la excepción;
2. si fue QuestActSupplyItem, cerrar item -> tipo concreto -> cobertura;
3. si el objeto se usa, cerrar también item.use_skill_id -> skill_effect
   -> effect -> detalle concreto;
4. comprobar que aaemu_item_definition_coverage permite crear el objeto;
5. un rechazo de cobertura debe devolver false y cancelar la aceptación,
   nunca producir NullReferenceException ni desconectar la sesión;
6. si la caída ocurrió después de agregar el journal, abandonar y volver a
   aceptar tras la reparación para recibir naturalmente el SupplyItem.
```

Importar una fila a `items` no basta. La cobertura de creación es una
dependencia obligatoria de cada `QuestActSupplyItem` y recompensa de objeto:

```text
quest act
  -> items
  -> impl_id o descriptor concreto
  -> aaemu_item_definition_coverage = complete
  -> use_skill_id y cierre de skill, cuando corresponda
```

### La quest aparece, se acepta y se abandona inmediatamente

```text
1. buscar Start res=True seguido de Supply res=False;
2. identificar el item del QuestActSupplyItem;
3. comprobar si falta la fila items o si su cobertura no es Complete;
4. no confundir una lista "suppressed_adjacent_quest_ids" del manifiesto con
   una compuerta ejecutable: SCFilter en modo sin filtro puede seguir
   publicando la oferta desde el catálogo del cliente;
5. QuestStartDependencyGuard debe rechazar la aceptación antes de insertar el
   journal mientras la dependencia siga incompleta;
6. para habilitarla, cerrar el item y toda su use_skill antes de promover su
   cobertura y retirar la supresión documental.
```

Caso patrón: quest `2258`, cuya oferta desde Malphus seguía visible en V4
aunque el item inicial `16288` no estaba importado.

### El tracker dice Complete, pero no aparece `?`

```text
1. status debe ser Ready;
2. component_id debe ser el componente Ready real;
3. verificar QuestActConReportNpc;
4. verificar índice ReportNpc;
5. verificar completed=false y requisitos vigentes.
```

### Aparece `?`, pero no abre o no entrega recompensa

```text
1. revisar interacción con ReportNpc;
2. revisar CSCompleteQuestContext;
3. revisar componente Reward;
4. revisar selección de recompensa;
5. revisar espacio y mutación atómica;
6. revisar bit/persistencia de completada.
```

### Se entrega, pero reaparece tras relog

```text
1. revisar completed_quests y máscara;
2. revisar persistencia MySQL;
3. revisar snapshot SCCompletedQuests;
4. revisar repeatable/periodicidad;
5. probar segundo relog.
```

## 4. Orden de trabajo recomendado

Para cada lote:

1. Elegir una quest representativa y obtener su cierre completo.
2. Identificar primitivas genéricas faltantes.
3. Implementar esas primitivas una sola vez.
4. Generar un runtime versionado desde el último runtime estable.
5. Construirlo dos veces y comparar SHA-256.
6. Ejecutar `quick_check`, `integrity_check` y auditoría de huérfanos.
7. Ejecutar pruebas dirigidas y toda `AAEmu.Tests` en .NET Core 3.1.
8. Actualizar manifest y checkpoint antes de desplegar.
9. Recrear sólo `game`.
10. Verificar scripts, puertos, LoginServer y hash montado.
11. Probar dentro del juego sin `/quest force`.
12. Probar abandono, repetición cuando corresponda y relog.

Agrupar quests por la primitiva que necesitan suele ser más eficiente que
trabajar solamente por zona:

```text
hablar/reportar
matar
recolectar/entregar items
interactuar con doodads
entrar en zona
usar skill
temporizadas
cinemáticas y scripts
```

## 5. Aceptación obligatoria por quest

Una quest sólo está cerrada cuando se observa:

```text
[ ] NPC inicial aparece con modelo aceptable
[ ] NPC está en ubicación nativa
[ ] ! aparece sin comando GM
[ ] clic derecho abre oferta y texto
[ ] aceptar crea el journal correcto
[ ] cada objetivo progresa por su evento real
[ ] tracker cambia a Complete
[ ] ? aparece sobre el ReportNpc correcto
[ ] clic derecho abre recompensa
[ ] recompensa se aplica una sola vez
[ ] quest queda completada/persistida correctamente
[ ] relog conserva el estado
[ ] abandono y repetición respetan reglas nativas
```

`/quest force` es una sonda diagnóstica, no un criterio de aceptación.

## 6. Plantilla para cada nueva quest

Copiar este bloque al checkpoint del lote:

```text
Quest:
  id:
  nombre:
  fuente AA8:
  categoría/detail:
  repeatable:
  prerequisitos:

Componentes:
  Start:
    component_id:
    actos:
  Progress:
    component_id:
    actos:
  Ready:
    component_id:
    actos:
  Reward:
    component_id:
    recompensas:

NPC inicial:
  template_id:
  nombre:
  spawner_id:
  world/zone:
  xyz/rotación:
  modelo:

NPC entrega:
  template_id:
  nombre:
  spawner_id:
  world/zone:
  xyz/rotación:
  modelo:

Protocolo:
  snapshot:
  update:
  interacción:
  completion:

Implementación genérica requerida:

Pruebas automáticas:

Prueba manual sin force:

Resultado tras relog:

Evidencia y hashes:
```

## 7. Caso patrón: quest 330

```text
quest 330 = Exciting News

Start 1520
  AcceptNpc -> Lucius 3597

Ready 1521
  ReportNpc -> Gossiper Parish 11541

Reward 1522

estado antes de entregar = Ready/status 3
completed antes de entregar = false
```

Fallo global descubierto:

```text
SCFilterPacket 0x138 nunca se enviaba
-> StartNpc index vacío
-> ReportNpc index vacío
-> sin ! ni ?
```

Corrección:

```text
enviar 0x138 con uint32 size=0 durante FinishState state 0
-> WorldContent inicializado
-> índices construidos
-> marcador ? observado sobre Gossiper Parish
```

Esta corrección pertenece a la base global y no debe reimplementarse por quest.

## 8. Patrón AA8: un NPC puede ser un client_doodad lógico

La quest `2532` demostró que `ReportNpc` y `ReportDoodad` no son
intercambiables aunque visualmente el jugador esté frente a un NPC.

```text
QuestActConReportDoodad -> doodad 14074
doodad 14074           -> client_doodad=1
func group             -> model=npctype://10581
func quest             -> report quest 2532
NPC 10581              -> Marian
```

Diagnóstico obligatorio para `AcceptDoodad` y `ReportDoodad`:

```text
1. extraer el detalle concreto del act;
2. extraer doodad_almighties;
3. revisar client_doodad;
4. cerrar doodad_func_groups y su model;
5. cerrar doodad_funcs y doodad_func_quests;
6. si model=npctype://X, tratarlo como proxy lógico del NPC X;
7. localizar el spawn histórico de NPC X y sustituir esa instancia por el
   client_doodad, conservando posición y rotación;
8. iniciar el client_doodad en el grupo Normal que contiene npctype://X, no
   en un grupo Start vacío;
9. no convertir el act a ReportNpc;
10. seleccionar la función de quest por quest_kind: 1=aceptar, 2=entregar.
```

El consumidor transversal quedó implementado en:

```text
DoodadManager
  -> indexa client_doodad + model npctype://X

SpawnManager
  -> reemplaza la instancia histórica NPC X por el doodad nativo

Doodad.GetFuncGroupId
  -> usa el grupo Normal npctype://X para client_doodad

GiveQuest / CompleteQuest
  -> seleccionan DoodadFuncQuest por quest_kind y estado del personaje
```

No se debe ejecutar siempre el primer `DoodadFuncQuest` del grupo. Marian
`14074` contiene, en orden, las funciones de entregar `2532`, aceptar/entregar
`2255` y aceptar `2256`. Elegir siempre la primera reinicia o bloquea la cadena.

### Marian y el monolito cercano

La escena contiene entidades distintas:

```text
Marian visible
  -> apariencia NPC 10581
  -> entidad lógica client_doodad 14074
  -> acepta/entrega 2532, 2255 y 2256

monolito cercano
  -> doodad 4500
  -> modelo stone_solzreed_a_fl.cgf
  -> DoodadFuncFakeUse
  -> no es el target de ReportDoodad de quest 2532

quest 2255
  -> entrega Engraved Lodestone 16280
  -> el progreso usa el objeto cerca de Marian/monolito
  -> vuelve a entregar en el doodad lógico Marian 14074
```

El primer inicio natural de `2255` confirmó además una regla de catálogo:

```text
items 16280 presente + cobertura Unknown
  -> ItemManager rechaza correctamente la creación
  -> QuestActSupplyItem recibe null
  -> el consumidor antiguo desreferenciaba null y desconectaba al jugador
```

La reparación reproducible está en:

```text
build_native_nuian_green_arc_v2_runtime.py
test_native_nuian_green_arc_v2.py
CHECKPOINT_NATIVE_QUEST_2255_ITEM_CLOSURE_V1.md
```

La proximidad visual puede hacer parecer que toda la secuencia pertenece al
monolito. La autoridad se decide por el act concreto y la función del doodad.

La reparación transversal de quests debe operar sobre grafos completos,
no sobre filas aisladas:

```text
context -> components -> acts -> concrete details
        -> NPC/doodad/item/skill -> función -> protocolo
```

## 9. Frontera obligatoria entre Progress, Ready y Reward

Completar el último objetivo no autoriza al servidor a recorrer
automáticamente los componentes de entrega y recompensa:

```text
evento de objetivo
-> completa Progress
-> selecciona el componente Ready real
-> envía SCQuestContextUpdated
-> se detiene

interacción explícita con NPC/doodad de entrega
-> valida CanReport
-> ejecuta Complete
-> aplica Reward una sola vez
```

Un `QuestActConReportNpc` o `QuestActConReportDoodad` no debe ejecutarse como
continuación del mismo `Update` que completó el objetivo. Su existencia
describe el destino de entrega; la autorización real nace de la interacción
del jugador.

Durante `Update` y `Complete`, los eventos secundarios producidos por la propia
transición tampoco pueden reentrar en esa quest:

```text
SupplyExp  -> OnLevelUp
SupplyItem -> OnItemGather
use item   -> OnItemUse
```

Sin esa protección, una recompensa puede restablecer `Step=Progress` mientras
la transición sigue activa y crear un ciclo de recompensas. La quest `2255`
es el caso patrón que descubrió esta clase de error.

Pruebas mínimas obligatorias para esta frontera:

```text
[ ] completar objetivo termina en Step/Status Ready
[ ] ComponentId corresponde al componente Ready real
[ ] Reward todavía no se ejecutó
[ ] eventos de recompensa no reentran durante Update/Complete
[ ] sólo la interacción con el destino correcto ejecuta Complete
[ ] recompensa y persistencia ocurren una sola vez
```

## 10. Actores con apariencia NPC respaldados por `client_doodad`

Que una entidad se vea como un NPC no demuestra que el grafo nativo use un
act NPC. Antes de implementar un puente `Npc -> Doodad`, comprobar siempre las
filas AA8 de `quest_acts` y del detalle concreto.

El patrón nativo confirmado es:

```text
QuestActConAcceptDoodad o QuestActConReportDoodad
-> doodad_almighty D
-> client_doodad=1
-> grupo Start o Normal model=npctype://X
-> reemplaza visualmente el spawn del NPC X
```

Casos confirmados:

```text
Marian
  doodad 14074 -> npctype://10581
  quest 2256 Start -> AcceptDoodad 14074

Bloodhand Corpse
  doodad 14073 -> Start group npctype://10646
  quest 2256 Ready -> ReportDoodad 14073
```

El runtime histórico puede contener `AcceptNpc X` o `ReportNpc X` para esas
mismas escenas. Esa coincidencia de modelo no convierte las filas históricas
en autoridad AA8. Deben reemplazarse por el grafo Doodad exacto.

Sólo conservar un puente para acts NPC cuando el propio `game11` demuestre que
el act nativo sigue siendo NPC y exista evidencia independiente de que el
actor lógico es un client-doodad. Nunca usar el puente para ocultar una
divergencia conocida entre `AcceptNpc/ReportNpc` históricos y
`AcceptDoodad/ReportDoodad` nativos.

## 11. Un mismo doodad puede cerrar una quest e iniciar la siguiente

Extraer todas las funciones y fases del doodad antes de desplegarlo. El grupo
Normal puede contener simultáneamente:

```text
DoodadFuncQuest kind=2 -> completar quest A
DoodadFuncQuest kind=1 -> aceptar quest B
```

No basta con reconstruir `A`: aceptar `B` puede cambiar de fase y alcanzar una
skill, efecto, ítem o recompensa todavía ausente. Si la clausura de `B` no
está completa:

1. registrar el grafo y las dependencias nativas de `B`;
2. excluir explícitamente del runtime sus funciones de oferta/uso;
3. documentar esa exclusión como compuerta temporal, no como contenido nativo;
4. validar que `A` sigue mostrando su marcador y cerrando correctamente;
5. restaurar las funciones exactas sólo cuando `B` tenga cierre completo.

Caso patrón:

```text
doodad 14073
  func 1512 kind=2 -> completa 2256
  func 1507 kind=1 -> inicia 2257
  phase 41493/use skill 41925 -> progreso de 2257
```

## 12. Fases personales de doodad (`once_one_man`)

Un `highlight_doodad_phase` dentro de `QuestActObjInteraction` no autoriza a
cambiar globalmente `Doodad.FuncGroupId`. Si el doodad tiene
`once_one_man=1`, esa fase pertenece al estado de quest del personaje.

Ruta de reconstrucción:

```text
quest activa / Progress
  -> QuestActObjInteraction
  -> doodad_id o highlight_doodad_id
  -> highlight_doodad_phase
  -> doodad_func en esa fase y skill recibida
```

La ejecución debe conservar la fase mundial. Si la fase personal contiene
`doodad_phase_funcs`, mantener la compuerta cerrada hasta reconstruir un
evaluador local de esas funciones.

## 13. Loot packs disparados por interacción con doodad

No asumir que `GainLootPackItemEffect` siempre recibe `SkillCasterItem`.
Interacciones nativas pueden usar `SkillCasterUnit`.

Sólo exigir item fuente si `consume_source_item` o `inherit_grade` lo
requieren. Para quest items:

```text
skill
  -> skill_effects
  -> GainLootPackItemEffect
  -> loot_pack_id
  -> loots
  -> items.loot_quest_id
  -> QuestActObjItemGather
```

Si la tabla autoritativa `loots` no existe en el cliente, cualquier fila
reconstruida debe marcarse `server_derived`, apoyarse en una relación única y
quedar diferenciada de evidencia nativa.
