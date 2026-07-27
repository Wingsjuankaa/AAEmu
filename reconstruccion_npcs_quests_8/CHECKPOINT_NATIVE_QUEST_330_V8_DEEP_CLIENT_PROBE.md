# Checkpoint AA8 nativo — quest 330 V8, corte cliente/servidor

Fecha: 2026-07-26
Autoridad de datos y protocolo: cliente Kakao 8.0.3.12 r558734
Referencia arquitectónica secundaria: rama `develop`

## Estado limpio confirmado

Antes de cerrar sesión, el jugador abandonó la quest 330. La base de datos
confirma que no está activa ni completada. La siguiente prueba debe comenzar
desde Lucius y no debe usar `/quest force 330`.

Esto elimina como causa inmediata un estado persistido de la prueba forzada
anterior.

## Hechos ya demostrados

La definición nativa reconstruida es:

```text
quest 330 — Exciting News
Start  1520 -> QuestActConAcceptNpc npc=3597  (Lucius)
Ready  1521 -> QuestActConReportNpc npc=11541 (Gossiper Parish)
Reward 1522 -> recompensas
```

- No tiene una quest previa obligatoria.
- El requisito de facción de Nuia pasa para el personaje probado.
- El spawn seleccionado de Gossiper Parish usa realmente `TemplateId=11541`.
- Lucius puede aparecer en varios lugares, pero la búsqueda nativa de quests
  utiliza el `TemplateId` del NPC seleccionado, no su `ObjId` ni su spawn.
  Por tanto, sus múltiples apariciones no mezclan la identidad de la quest.
- `SCQuests` inserta la quest en el mapa activo del cliente usando su
  `TemplateId` y copia el byte de estado sin transformarlo.
- La API nativa de entrega sólo publica una quest cuando su estado activo es
  exactamente `3` (`Ready`) y la relación de reporte coincide con el
  `TemplateId` del NPC seleccionado.

## Reconstrucción estática del cliente

Artefactos de decompilación:

```text
E:\AAEmu-Research\output\ghidra-static\dynamic-npc-record-manager-v14.c
E:\AAEmu-Research\output\ghidra-static\npc-manager-constructor-v16.c
E:\AAEmu-Research\output\ghidra-static\scquests-handler-v21.c
E:\AAEmu-Research\output\ghidra-static\scquests-apply-v22.c
E:\AAEmu-Research\output\ghidra-static\scquests-entry-apply-v23.c
E:\AAEmu-Research\output\ghidra-static\quest-state-record-apply-v24.c
```

Conclusión del corte estático:

```text
NPC visible -> ObjId dinámico -> registro NPC -> TemplateId real
SCQuests    -> quest TemplateId -> estado recibido sin conversión
TemplateId NPC + estado 3 -> colector de quests entregables
```

No hay evidencia de un identificador alternativo de Parish ni de una
interferencia entre los distintos spawns de Lucius.

## Instrumentación V8 del servidor

Al interactuar con un NPC, el servidor registra:

```text
[QuestNpcProbe] character=<nombre>
                npcObj=<objeto dinámico>
                npcTemplate=<TemplateId>
                readyReportQuests=<quests Ready que reportan a este NPC>
```

Para Parish después de aceptar la 330, el resultado correcto es:

```text
npcTemplate=11541 readyReportQuests=330
```

`/quest diagnose 330`, con un NPC seleccionado, ahora muestra separadamente:

```text
acceptNpc expected=3597 targetMatch=PASS|FAIL
reportNpc expected=11541 targetMatch=PASS|FAIL
```

## Sonda Lua del cliente: no disponible en esta sesión

El `game_pak` de esta misma versión contiene los dos artefactos:

```text
game/default_binding.g        -> CTRL-i toggle_gm_console
x2ui/hud/gm_console.lua       -> ventana y ejecución Lua
```

Sin embargo, la prueba real mostró que `Ctrl+I` no abre ninguna ventana. El
`ArcheAge.log` tampoco registra el evento `TOGGLE_GM_CONSOLE` ni un error al
crear la ventana. Por tanto, la acción queda filtrada antes de llegar al
manejador Lua en esta sesión del cliente comercial.

La presencia de la tecla y del script en el `game_pak` no demuestra que el
módulo GM esté habilitado durante una sesión normal. Los comandos `/quest` del
emulador se autorizan en el servidor y no activan por sí mismos la interfaz GM
interna del cliente.

La siguiente sonda queda conservada como evidencia y para una futura sesión
con interfaz GM habilitada, pero no forma parte de la prueba manual actual:

```lua
gmConsole:AddMessage("AA8 q330 status="..tostring(X2Quest:GetActiveQuestListStatusByType(330)).." completed="..tostring(X2Quest:IsCompleted(330)).." start="..tostring(X2Quest:GetNpcQuestContextCountStart()).." startType="..tostring(X2Quest:GetNpcQuestContextQuestTypeStart(1)).." complete="..tostring(X2Quest:GetNpcQuestContextCountComplete()).." completeType="..tostring(X2Quest:GetNpcQuestContextQuestTypeComplete()))
```

## Sonda sustituta mediante protocolo observado

No es necesario alterar el cliente. Después de
`SCNpcInteractionSkillListPacket`, la respuesta del cliente permite observar
si su colector local encontró una interacción de quest:

```text
SCStartInteraction
-> servidor responde SCNpcInteractionSkillList
-> cliente envía CSInteractNPC
   = encontró una interacción local para el NPC
-> cliente no envía CSInteractNPC
   = su colector local no publicó ninguna interacción
```

Prueba observada en Lucius:

```text
npcTemplate=3597
SCNpcInteractionSkillList enviado
CSInteractNPC ausente
```

Esto confirma por comportamiento que el cliente no publicó la oferta de la
quest 330, independientemente del símbolo visual.

También se observó:

```text
/quest try 330
-> requisitos PASS
-> SCQuestContextStarted
-> SCQuestContextUpdated
-> servidor: Step=Ready, Status=Ready
```

La quest fue abandonada seis segundos después, por lo que todavía falta
realizar la mitad Parish de esta sonda emparejada.

## Validación automática

- `git diff --check`: correcto.
- Pruebas C# en .NET Core 3.1: `234/234`.
- ScriptCompiler: `0 errors`.
- Se reconstruyó y recreó únicamente el servicio `game`.
- Imagen desplegada:
  `sha256:a88f2b434b990fca1de5a0771463c44d8274bbdfcb98cc090fde786b7b535c3f`.
- Game/Stream escuchando en `2239/2250`.
- Registro en LoginServer: correcto.
- Errores o excepciones de inicio: `0`.
- Compact esperado:
  `compact-8.0-runtime-native-quest330-v5.sqlite3`.
- SHA-256 esperado:
  `F9284947A6162004D6E8B62A8D8A33A05B2E47F25B5F7AF8B1827AF8399E714B`.

## Secuencia manual V8

1. Entrar con la quest 330 abandonada.
2. Seleccionar a Lucius.
3. Ejecutar `/quest try 330`; no usar `force`.
4. Confirmar que el tracker muestre `Exciting News`.
5. Seleccionar a Gossiper Parish y hacer clic derecho directamente sobre el
   NPC. No usar `F` para esta sonda.
6. No abandonar ni entregar todavía la quest.
7. Inspeccionar `[QuestNpcProbe]` y si el cliente envía `CSInteractNPC` o
   `CSCompleteQuestContext`.

Con esa secuencia se podrá separar la relación de entrega del marcador visual
sin depender de la consola GM deshabilitada.

### Corrección de la prueba con Parish

La primera prueba usó `F`. El cliente seleccionó correctamente a Parish:

```text
CSChangeTarget -> target ObjId 32959
```

pero no emitió `CSStartInteraction`. Esto no prueba todavía la respuesta al
paquete de interacción: `F` ejecuta la primera acción que el cliente ya haya
publicado localmente y, si la lista está vacía, no consulta al servidor.

El clic derecho sí fuerza:

```text
CSStartInteraction (mouseButton=2)
```

y es el estímulo correcto para esta sonda. La base persistida después de
cerrar la sesión conserva:

```text
quest=330 owner=5 status=3 (Ready)
```

## Resultado del clic derecho válido sobre Parish

Con la quest 330 persistida en estado `3` (`Ready`), el clic derecho produjo
la secuencia:

```text
CSChangeTarget                target ObjId=32959
CSStartInteraction            mouseButton=2
[QuestNpcProbe]               npcTemplate=11541 readyReportQuests=330
SCNpcInteractionSkillList     opcode=0x1BD
CSInteractNPC                 npc ObjId=32959
```

La secuencia se repitió tres veces, pero el cliente no envió
`CSCompleteQuestContext` y no abrió la ventana de recompensa. Esto demuestra:

- el spawn seleccionado es Parish;
- la relación de reporte del servidor es correcta;
- el cliente acepta el paquete de interacción y elige una acción;
- el corte restante está dentro del estado/contexto de quest que consume la
  UI local.

## Hallazgo transversal: contadores AA8 comprimidos

La investigación nativa encontró el desajuste que corrompía silenciosamente
el registro de quest después de `TemplateId` y `Status`.

El lector/escritor nativo `FUN_39920110` no serializa diez `int32` planos.
Serializa los diez contadores en grupos `4 + 4 + 2`. Cada grupo comienza con
un byte de control que dedica dos bits a cada valor:

```text
00 -> 1 byte
01 -> 2 bytes
10 -> 3 bytes, little-endian
11 -> 4 bytes
```

`FUN_3991dce0` confirma la lectura: cada código se convierte en un ancho entre
uno y cuatro bytes y se copia little-endian a un entero de 32 bits.

El servidor AA8 estaba enviando diez `int32` sin esa cabecera ni los anchos
variables. Para una quest con diez objetivos en cero, enviaba `40` bytes donde
AA8 espera `13`. El cliente podía leer el ID, el título y el estado antes del
corte, pero interpretaba desplazados los campos posteriores del registro.

También se confirmó:

```text
SCQuestContextStarted (0x35D)
  -> Quest nativa
  -> uint32 componentId

SCQuestContextUpdated (0x051)
  -> Quest nativa
  -> diez uint32 comprimidos con el mismo esquema 4 + 4 + 2
```

El servidor conservaba el formato histórico de cinco `int32` después de la
quest actualizada. Se reemplazó por los diez valores AA8 comprimidos.

La respuesta `SCNpcInteractionSkillList` no era la causa: su lector base
`FUN_3999db50` termina en `interactable`, y la envoltura nativa
`FUN_399a30a0` lee después `mkeys`. Por tanto, los cuatro bytes finales de
teclas modificadoras sí pertenecen al paquete AA8.

## Relación con `!` y `?`

Los consumidores nativos del tag de quest
`FUN_395f4b40`, `FUN_395f49a0` y `FUN_395f5dc0` comprueban:

```text
featureSet.questNpcTag = fset[8] & 0x40000000
```

La configuración enviada ya tiene ese bit activo. Esos consumidores
recalculan los tags a partir de los componentes y del estado local de quests;
`SCQuests` llama directamente a esa ruta al aplicar la instantánea.

La corrección de serialización es, por tanto, necesaria para:

- construir correctamente el contexto `complete` de Parish;
- mostrar `?` sobre Parish;
- abrir la ventana de entrega.

El `!` de Lucius debe probarse por separado con la quest abandonada, porque una
instantánea activa mal serializada no interviene cuando la lista de quests
activas está vacía. Si Parish queda corregido pero Lucius continúa sin `!`, el
siguiente corte es el filtro nativo de inicio/requisitos, no el protocolo de
interacción.

## Implementación y pruebas V9

Cambios:

- `Quest.Write` usa los diez contadores AA8 de ancho variable;
- `SCQuestContextUpdatedPacket` usa diez valores AA8 de ancho variable;
- pruebas de fronteras `255`, `256`, `65535`, `65536`, `0xFFFFFF`,
  `0x1000000`, negativos y `int.MinValue`;
- prueba exacta de una actualización con componente `1521`;
- scripts Ghidra reutilizables:
  `ghidra/DumpAa8NpcInteractionFlow.java` y
  `ghidra/DumpAa8Functions.java`.

Validación previa al despliegue:

```text
git diff --check: correcto
.NET Core 3.1 Docker SDK: 237/237
```

Aceptación manual obligatoria:

```text
quest 330 abandonada -> Lucius muestra ! y abre oferta
quest 330 aceptada   -> Parish muestra ? y abre recompensa
recompensa aceptada  -> cliente envía CSCompleteQuestContext
```

No se declarará completa la reconstrucción mientras falte cualquiera de los
dos símbolos o cualquiera de las dos ventanas.

## Resultado V9 y corte V10: orden de inicialización

La prueba manual posterior al despliegue V9 mantuvo:

```text
quest 330 = Ready
Parish npcTemplate = 11541
readyReportQuests = 330
CSInteractNPC = presente
marcador ? = ausente
```

Por tanto, corregir la serialización nativa era necesario, pero no suficiente.
La comparación entre el código de selección y el orden real de paquetes reveló
una contradicción transversal:

```text
orden anterior observado:
SCQuests
SCCompletedQuests
SCSystemFactionList
SCSystemFactionList
```

El filtro nativo de disponibilidad `FUN_39a62240` y los requisitos de unidad
de la quest 330 dependen de la raza y de la jerarquía de facciones. El servidor
pretendía enviar el catálogo nativo antes del cálculo de tags, pero lo enviaba
después de las instantáneas que disparan ese cálculo. El tracker podía aceptar
el estado `Ready`, mientras el pase `NPC -> !/?` se ejecutaba sin la jerarquía
de Nuia completa.

V10 mueve `FactionManager.SendFactions` antes de `SCQuests` y
`SCCompletedQuests`. El nuevo orden esperado al seleccionar personaje es:

```text
SCSystemFactionList (todos los lotes)
SCQuests
SCCompletedQuests
```

La aceptación manual continúa siendo la misma: primero `?` y ventana de Parish;
después, con la quest abandonada, `!` y oferta de Lucius.

Artefactos de investigación reutilizables añadidos:

```text
ghidra/DumpAa8CallGraph.java
E:\AAEmu-Research\output\ghidra-static\aa8-quest-record-full-v2.c
E:\AAEmu-Research\output\ghidra-static\aa8-quest-marker-callgraph-v3.c
E:\AAEmu-Research\output\ghidra-static\aa8-quest-state-transition-v4.c
```

Validación previa al despliegue V10:

```text
.NET Core 3.1 Docker SDK: 237/237
```

Despliegue V10:

```text
imagen game = sha256:b00ba47c9323f6a3717f0b8c301273debe89851b8e91cde44c5d27ced462834a
rollback     = aaemu-game:pre-aa8-quest-marker-init-order-20260726
ScriptCompiler = 0 errores, 8 advertencias
Game/Stream = 2239/2250
LoginServer = registrado
compact SHA-256 = F9284947A6162004D6E8B62A8D8A33A05B2E47F25B5F7AF8B1827AF8399E714B
```

Sólo se recreó `game`; Login y MySQL conservaron sus contenedores. La base
mantiene la quest 330 para el personaje de prueba en `status=3` (`Ready`).

## Resultado V10 y corrección V11: componente Ready real

La prueba manual de V10 confirmó que el nuevo orden de facciones se aplica,
pero Parish continuó sin mostrar `?`. El orden queda como corrección preventiva
transversal y se descarta como causa directa de este caso.

La revisión del consumidor nativo de `SCQuestContextUpdated` demostró que sus
diez valores son IDs de componentes que el cliente debe recalcular:

```text
valor != 0 -> refresca ese QuestComponent y su relación con NPC
valor == 0 -> slot vacío, se ignora
```

`NormalizeImmediateReadyStep()` estaba cambiando correctamente:

```text
Step: Progress -> Ready
```

pero borraba el vínculo que el cliente necesitaba:

```text
ComponentId: 1520 -> 0
```

Por eso la actualización incremental de la quest 330 contenía diez ceros. El
tracker podía mostrar `[Complete] Exciting News` a partir de `Status=Ready`,
pero el administrador local no recibía el componente `1521`, cuyo acto
`QuestActConReportNpc(329)` enlaza con Parish `npc_id=11541`.

V11 conserva el componente Ready real:

```text
quest 330
Start component = 1520 -> Lucius npc_id=3597
Ready component = 1521 -> Parish npc_id=11541
Reward component = 1522
SCQuestContextUpdated changed component = 1521
```

También se descartaron dos hipótesis:

- `quest_contexts.detail_id` de la 330 es `2`; no cae en el filtro nativo que
  excluye los valores `4` y `5`;
- `quest_components.next_component=3543` no identifica una fila faltante de
  `quest_components`: `3543` pertenece a otros catálogos, por lo que no se
  importó ni reinterpretó sin consumidor nativo confirmado.

Validación V11:

```text
git diff --check = correcto
.NET Core 3.1 Docker SDK = 237/237
ScriptCompiler = 0 errores, 8 advertencias
Game/Stream = 2239/2250
LoginServer = registrado
compact host/container =
  f9284947a6162004d6e8b62a8d8a33a05b2e47f25b5f7af8b1827af8399e714b
imagen game =
  sha256:262b72c2754c8a36ce894f14413236a669a39ec75349ff1302bbe09797afb040
rollback =
  aaemu-game:pre-aa8-quest-ready-component-20260726
```

Prueba manual V11 obligatoria:

```text
1. abandonar quest 330 si sigue activa;
2. ejecutar /quest force 330;
3. confirmar que Parish muestra ?;
4. clic derecho en Parish;
5. confirmar ventana de recompensa y CSCompleteQuestContext.
```

La quest y los marcadores no se consideran completos hasta observar ese flujo.

## Resultado V11: `?` todavía ausente

La prueba manual válida de V11 mantuvo el resultado negativo:

```text
quest 330 activa
tracker = [Complete] Exciting News
Parish = npcTemplate 11541
marcador ? = ausente
ventana de recompensa = ausente
```

Los logs prueban que el cliente recibió la transición reconstruida:

```text
SCQuestContextStarted
SCQuestContextUpdated
SCQuests
servidor: Step=Ready Status=Ready ComponentId=1521
```

Al hacer clic derecho en Parish, el servidor siguió observando:

```text
readyReportQuests=330
CSInteractNPC presente
CSCompleteQuestContext ausente
```

Por tanto, V11 conserva un dato nativo correcto, pero no resuelve el corte
`NPC seleccionado -> contexto complete de la UI`.

## Ruta nativa exacta del contexto `complete`

El Lua de `x2ui/interaction/npc_interaction.lua` consulta:

```text
X2Quest:GetNpcQuestContextCountComplete()
X2Quest:GetNpcQuestContextQuestTypeComplete()
X2Quest:CallQuestUi(2, questType, npcId)
```

Los exports nativos correspondientes llegan a:

```text
FUN_3977ac90 -> GetNpcQuestContextCountComplete
FUN_3977d9e0 -> GetNpcQuestContextQuestTypeComplete
FUN_397710f0 -> CallQuestUi
```

El contador resuelve el NPC seleccionado, toma su `TemplateId`, consulta el
índice nativo de quests por NPC y cruza sus resultados con el journal activo.
Para la ruta normal de la 330, el estado exigido por
`FUN_39a639f0` es exactamente `3`.

El constructor del índice es:

```text
FUN_395f8ae0
-> FUN_395f8650
-> recorre todos los QuestContext
-> componentes kind 2/3/4/6
-> actos AcceptNpc/ReportNpc
-> índices separados de inicio y entrega
```

La definición de la 330 satisface ese constructor:

```text
Start kind=2 -> AcceptNpc 3597
Ready kind=6 -> ReportNpc 11541
```

También se refinó el significado de los diez `uint32` comprimidos de
`SCQuestContextUpdated`: son filtros de `QuestComponent` usados al recalcular
objetivos/contextos afectados. `1521` es un componente válido. Sin embargo,
la ruta `FUN_395f1830` que consume esos filtros reúne principalmente objetivos
ligados a objetos del mundo; no reemplaza la consulta independiente del índice
`ReportNpc`. Esto explica por qué V11 era correcta pero insuficiente.

Artefactos estáticos nuevos:

```text
E:\AAEmu-Research\output\ghidra-static\aa8-npc-quest-index-reference-sites-v20.txt
E:\AAEmu-Research\output\ghidra-static\aa8-npc-quest-index-init-helper-v21.c
E:\AAEmu-Research\output\ghidra-static\aa8-npc-quest-index-owner-v22.c
E:\AAEmu-Research\output\ghidra-static\aa8-npc-quest-index-populators-v23.c
E:\AAEmu-Research\output\ghidra-static\aa8-npc-quest-index-init-callers-v24.c
```

## Sonda de memoria de sólo lectura

Queda preparada:

```text
reconstruccion_npcs_quests_8\probe_aa8_client_quest_state.ps1
```

La sonda no inyecta código ni escribe memoria. Lee del `x2game.dll` del cliente
en ejecución:

```text
índice Start:  npc 3597  contiene quest 330
índice Report: npc 11541 contiene quest 330
journal activo: quest 330 y status
journal completado: grupo 5, máscara y bit de quest 330
```

Este corte dinámico separará definitivamente:

```text
índice ausente       -> carga/construcción de datos del cliente
índice presente,
status distinto de 3 -> estado/protocolo
índice y status bien,
completed=true       -> snapshot de completadas
todo correcto        -> target/contexto Lua posterior al colector
```

La última sesión ya estaba cerrada al preparar la sonda, por lo que falta
ejecutarla con ArcheAge abierto, la quest 330 activa y Parish seleccionado.

## Resultado dinámico: los dos índices estaban completamente vacíos

La sonda elevada de sólo lectura se ejecutó contra el cliente AA8 vivo con:

```text
quest 330 activa mediante /quest force 330
tracker = [Complete] Exciting News
Parish seleccionado
```

Resultado exacto:

```text
active_entry_found = true
active_status = 3 (Ready)
completed = false

StartNpc index entry count = 0
ReportNpc index entry count = 0
quest 330 en StartNpc 3597 = false
quest 330 en ReportNpc 11541 = false
```

Esto descarta el estado de la quest 330, el bit de completada, la repetición de
Lucius y el modelo del NPC como causa del marcador ausente. El cliente había
recibido correctamente el journal, pero nunca había construido ninguno de sus
dos índices globales NPC -> quest.

Evidencia dinámica:

```text
E:\AAEmu-Research\output\aa8-live-quest330-parish-probe-v2.json
```

## Causa raíz: faltaba SCFilterPacket 0x138

La traza estática desde el constructor de los índices llegó hasta
`FUN_392f8140`. El registro nativo del paquete demuestra:

```text
opcode = 0x138
clase del port = SCFilterPacket
payload = uint32 filterBufferSize + filterBuffer[filterBufferSize]
```

Su manejador ejecuta, en este orden:

```text
WorldContent::Initialize(filterBuffer, filterBufferSize)
inicialización del administrador de quests
construcción de los índices StartNpc y ReportNpc
```

Con `filterBufferSize=0`, el propio cliente entra en su rama nativa
`WorldContent::Initialize: no filter config`, retorna éxito y continúa
construyendo ambos índices con todo el contenido local. No hace falta inventar
un filter pack.

El port contenía `SCOffsets.SCFilterPacket = 0x138`, introducido junto con el
port AA8 original, pero nunca tuvo una clase de paquete ni un envío. Se añadió:

```text
AAEmu.Game\Core\Packets\G2C\SCFilterPacket.cs
FinishStatePacket state 0 -> SCFilterPacket vacío
```

Artefactos estáticos:

```text
E:\AAEmu-Research\output\ghidra-static\aa8-npc-quest-index-trigger-callers-v25.c
E:\AAEmu-Research\output\ghidra-static\aa8-npc-quest-index-trigger-registration-v26.c
E:\AAEmu-Research\output\ghidra-static\aa8-npc-quest-index-trigger-packet-v27.c
E:\AAEmu-Research\output\ghidra-static\aa8-world-content-init-packet-vtable-v28.c
E:\AAEmu-Research\output\ghidra-static\aa8-scfilter-packet-vtable-v29.c
```

Validación automática previa al despliegue:

```text
git diff --check = correcto
.NET Core 3.1 Docker SDK = 239/239
ScriptCompiler = 0 errores, 8 advertencias históricas
Game/Stream = 2239/2250
LoginServer = registrado
compact host/container =
  f9284947a6162004d6e8b62a8d8a33a05b2e47f25b5f7af8b1827af8399e714b
imagen game =
  sha256:c9cc92de2cb43d0b8f2ba8566d5ef4f0454f1b10d43e7f685d0453fde3816cf7
rollback =
  aaemu-game:pre-aa8-world-content-filter-20260726
```

La aceptación final requiere una nueva sesión, porque `SCFilterPacket` pertenece
al handshake inicial anterior a la selección de personaje:

```text
1. reconectar el cliente;
2. comprobar ! sobre Lucius sin /quest force;
3. aceptar quest 330;
4. comprobar ? sobre Parish;
5. completar mediante clic derecho en Parish;
6. repetir la sonda y confirmar ambos índices con entradas.
```

## Aceptación visual de SCFilterPacket y marcador ReportNpc

El usuario cerró y abrió el cliente para repetir el handshake completo. El log
del servidor confirmó el envío real:

```text
2026-07-26 22:08:59
FinishStatePacket : BEGIN
GamePacket: S->C type 138 .G2C.SCFilterPacket
FinishStatePacket : END
```

Después del ingreso, la quest 330 estaba en:

```text
ComponentId = 1521
Step = Ready
Status = Ready
act.DetailType = QuestActConReportNpc
```

Resultado visible confirmado por el usuario:

```text
Gossiper Parish muestra el marcador ? de entrega
tracker muestra [Complete] Exciting News
distancia al ReportNpc = 3 m
```

Evidencia visual recibida:

```text
archivo original =
  C:\Users\juank\AppData\Local\Temp\
  codex-clipboard-3008fdb8-9035-4057-885d-019766312b9c.png
SHA-256 =
  50DE3C3A59F8F4F5696688C126DED675F1B957FB52A449DD773F8166C45BDE90
```

Esto acepta la causa raíz y la reparación de la capa global de marcadores. La
captura no se usa por sí sola para afirmar que la recompensa y la persistencia
posterior a la entrega fueron probadas; esas etapas mantienen su propio criterio
de aceptación.

El procedimiento reusable queda en:

```text
reconstruccion_npcs_quests_8\QUEST_RECONSTRUCTION_PLAYBOOK_V1.md
```

## Aceptación natural completa de la quest 330

Los eventos inmediatamente posteriores completaron las etapas que la captura
por sí sola no demostraba:

```text
2026-07-26 22:12:03
CSStartQuestContext
quest 330, Start 1520
QuestActConAcceptNpc = true
SCQuestContextStarted
SCQuestContextUpdated

2026-07-26 22:12:42
CSCompleteQuestContext
quest 330, Ready 1521
QuestActConReportNpc = true
Status = Completed
QuestActSupplyExp = true
QuestActSupplyItem = true
QuestActSupplySelectiveItem = true
SCItemTaskSuccess, action QuestSupplyItems
SCItemTaskSuccess, action QuestComplete
SCQuestContextCompleted
quest 330 retirada del journal activo
```

Por tanto, quedan aceptados dentro de la misma sesión:

```text
[x] oferta natural sin /quest force
[x] marcador ! y aceptación mediante AcceptNpc
[x] estado Ready
[x] marcador ? sobre ReportNpc
[x] entrega natural
[x] experiencia
[x] recompensas fijas y selectivas
[x] notificación de completada
[x] retiro del journal activo
```

Queda como comprobación separada la persistencia tras un relog posterior.

La misma sesión demostró cobertura transversal adicional:

```text
quest 2531
  AcceptNpc -> ReportNpc -> SupplyItem -> QuestComplete
  completada naturalmente

quest 2532
  iniciada naturalmente

quest 251
  iniciada naturalmente
  Progress = QuestActObjItemGather
  item_id = 4058
  count = 3
```
