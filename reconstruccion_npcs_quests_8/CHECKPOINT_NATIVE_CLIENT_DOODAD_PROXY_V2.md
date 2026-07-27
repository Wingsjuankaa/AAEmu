# Checkpoint AA8 native client_doodad proxy v2

Fecha: 2026-07-26

## Resultado

Se identificó y reparó la causa transversal por la que la quest `2532`
aparecía Ready en el tracker pero Marian no mostraba `?` ni permitía entregar.

El mundo histórico creaba un NPC normal:

```text
spawn 8182 -> NPC template 10581 -> Marian
```

AA8 define en cambio la entidad de quest como:

```text
doodad 14074
client_doodad = 1
grupo funcional 41496
model = npctype://10581
```

Por tanto, Marian debe verse como el NPC `10581`, pero existir en protocolo y
lógica de quest como doodad `14074`.

## Evidencia nativa

Quest `2532`, componente Ready `10966`:

```text
act 63971
QuestActConReportDoodad
detail 163
doodad_id 14074
cinema_id 80
```

Funciones de `14074`, grupo `41496`:

```text
actual 1508 -> quest_kind 2 -> quest 2532
actual 1509 -> quest_kind 1 -> quest 2255
actual 1510 -> quest_kind 2 -> quest 2255
actual 1511 -> quest_kind 1 -> quest 2256
```

La decompilación del consumidor de modelos de `x2game.dll` confirma una rama
especial para el prefijo `npctype://`:

```text
E:\AAEmu-Research\output\ghidra-static\aa8-npctype-consumer.c
FUN_3963f940 -> detecta npctype:// -> FUN_3963eec0
```

Esto prueba que el cliente puede renderizar un doodad usando la apariencia de
un NPC; no es una conversión inventada por el emulador.

## Separación Marian / monolito

El dato visual aportado durante la prueba permitió cerrar la topología:

```text
Marian 14074/10581:
  destino lógico de ReportDoodad 2532
  origen/destino de 2255

monolito 4500, a 3.85 m:
  model stone_solzreed_a_fl.cgf
  DoodadFuncFakeUse
  no es destino de ReportDoodad 2532

quest 2255:
  entrega item 16280, Engraved Lodestone
  pide usarlo cerca de Marian
  luego se entrega a Marian 14074
```

La escena hace que la interacción con el objeto y el regreso a Marian se
perciban como una sola mecánica, pero el grafo nativo mantiene las entidades
separadas.

## Reparación genérica

No hay hardcode de quest `2532`, Marian ni las coordenadas.

```text
DoodadManager:
  indexa todo client_doodad cuyo grupo Normal usa npctype://X

SpawnManager:
  cuando encuentra un spawn NPC X, lo sustituye por el client_doodad nativo
  y conserva transform/world/zone

Doodad.GetFuncGroupId:
  inicia esos proxies en el grupo Normal npctype://X

GiveQuest / CompleteQuest:
  seleccionan DoodadFuncQuest por quest_kind y estado

DoodadFuncQuest:
  quest_kind 1 solamente acepta
  quest_kind 2 solamente entrega
```

La misma regla detectó automáticamente:

```text
NPC 10581 -> doodad 14074 -> grupo 41496 (Marian)
NPC 10644 -> doodad 14134 -> grupo 41592 (Sloane)
```

## Trazas para las siguientes pruebas

```text
[AA8ClientDoodad]
  indexación y reemplazo de spawn

[AA8QuestDoodad]
  función elegida, quest_kind, quest y resultado de estado

[AA8QuestComplete]
  quest, objId, tipo/template del target y recompensa seleccionada
```

Estas trazas no alteran estado ni fuerzan misiones.

## Validación

```text
git diff --check: correcto
.NET Core 3.1 Docker SDK: 241/241
ScriptCompiler: 0 errores, 8 advertencias históricas
Game: 2239
Stream: 2250
LoginServer: registrado
```

Validación manual positiva del contexto explícito:

```text
02:45:33 Marian client_doodad 14074 selecciona quest 2256
02:45:33 QuestActConAcceptNpc 10581
02:45:33 Start res=True, component 10362
02:45:33 SCQuestContextStarted
02:45:33 SCQuestContextUpdated
Drop posterior: ninguno
```

La oferta `AcceptNpc` sobre un actor `client_doodad npctype://X` queda
confirmada dentro del cliente. La quest `2256` permanece activa; todavía debe
validarse su entrega natural a `QuestActConReportNpc 10646` y la persistencia
posterior.

Runtime nativo:

```text
compact:
  D:\Proyectos\AAemu\client_kakao\
  compact-8.0-runtime-native-nuian-green-arc-v1.sqlite3

SHA-256:
  F15F3A2AA00DDF2DD0AE31EDA9B7C4CBE00172D342BBE4E713E5FF945A478BC7
```

Despliegue:

```text
imagen:
  sha256:73a82fcb8fdc3919adafd9feef12fdd3ea431f5691ec5cf7bdd23e686319f886

rollback:
  aaemu-game:pre-aa8-client-doodad-proxy-20260726
  sha256:c9dde48c83f06df88e7450404f583626fc9210a4956101711ba8b678e1bface7
```

Persistencia preservada:

```text
Wingsjuanka
quest 2532
status 3 = Ready
component 10966
```

No se forzó, abandonó ni completó ninguna quest.

## Prueba manual

Se requiere una reconexión para recibir de nuevo el estado mundial:

1. entrar con Wingsjuanka;
2. acercarse a Marian;
3. comprobar que Marian mantiene su apariencia y muestra `?`;
4. hacer clic derecho y observar si se abre/completa la entrega de `2532`;
5. si aparece una selección de recompensa, escogerla normalmente;
6. comprobar que después aparece `!` para quest `2255`;
7. aceptar `2255`, usar Engraved Lodestone cerca de Marian/monolito y volver
   a Marian.

Si falla un punto, conservar el estado y revisar primero las tres trazas
anteriores. No usar `/quest force`.

## Incidente de reentrada al entregar quest 2532

La primera prueba de `F` sobre Marian confirmó que el proxy y la función
`CompleteQuest` funcionaban, pero descubrió un fallo severo del motor legado:

```text
01:10:21 CSStartSkill
InteractionEffect = CompleteQuest
doodad 14074 / group 41496
quest_kind 2 / quest 2532 / skill 11008
```

Una sola interacción ejecutó `OnReportToDoodad -> Quest.Update`. Ese método
alcanzó los actos Reward mientras la quest seguía en la colección activa.
Los objetos de recompensa generaron eventos de inventario, que volvieron a
entrar en la misma quest y concedieron recompensas repetidamente.

Consecuencias observadas:

```text
Wingsjuanka id 5
nivel final 29
items asociados 59
quests activas corruptas 2
```

El personaje fue archivado como eliminado y el nombre quedó libre:

```text
id 5
name !deleted-5-Wingsjuanka-20260726
deleted 1
active name Wingsjuanka count 0
```

Backup previo:

```text
backups\aaemu_game-before-delete-Wingsjuanka-20260726.sql
SHA-256 DC8699D5718979E0D902C27CC330497AA293B1A46E4ACB2413628ADDD3E7BFB9
```

Reparación transversal:

```text
CharacterQuests.Complete
  -> guard IsCompleting contra finalización reentrante

Quest.OnItemGather / Quest.OnItemUse
  -> ignoran eventos producidos por las propias recompensas mientras completa

CharacterQuests.OnReportToDoodad
  -> valida estado Ready y target ReportDoodad
  -> usa el único pipeline Complete que registra, retira y persiste la quest
```

Validación posterior:

```text
.NET Core 3.1 Docker SDK: 243/243
imagen:
  sha256:e2a9c47af12371fe4d17a63a67ec716207b1d2e117b89821e51aa6150128c2e0
rollback:
  aaemu-game:pre-aa8-quest-completion-guard-20260726
  sha256:73a82fcb8fdc3919adafd9feef12fdd3ea431f5691ec5cf7bdd23e686319f886
```

## Caso mixto descubierto en quest 2256

Después de completar correctamente `2255`, Marian seleccionó la función nativa
de inicio de `2256`, pero la quest se retiró inmediatamente:

```text
02:22:31 doodad 14074 / func 1511 / quest_kind 1 / quest 2256
02:22:31 QuestActConAcceptNpc
02:22:31 Start failed / res false
02:22:31 quest 2256 removed
```

El compact AA8 demuestra que ambas mitades son correctas:

```text
actor interactuado:
  doodad 14074
  client_doodad=1
  model=npctype://10581

quest 2256 Start 10362:
  QuestActConAcceptNpc 1954
  npc_id=10581 (Marian)

quest 2256 Ready 10364:
  QuestActConReportNpc 4005
  npc_id=10646
```

La falla estaba en el consumidor histórico: `QuestActConAcceptNpc` aceptaba
únicamente una instancia C# de `Npc`, aunque AA8 permite que el mismo actor sea
un `client_doodad` representado por `npctype://X`.

Reparación transversal:

```text
DoodadTemplate.IsNpcProxy(X)
  -> exige client_doodad
  -> exige grupo Normal
  -> compara exactamente model=npctype://X

Quest.MatchesNpcTarget
  -> acepta Npc template X
  -> o client_doodad que sea proxy exacto de X

QuestActConAcceptNpc / QuestActConReportNpc
  -> usan el mismo resolvedor

Quest.CanReportToDoodad
  -> permite ReportNpc únicamente cuando el doodad es proxy exacto
```

No se cambió `2256` a `AcceptDoodad`, no se duplicó el spawn de Marian y no se
usaron datos 3.0.

Pruebas:

```text
ClientDoodadNpcProxyMatchesNativeNpcTarget
AcceptNpcActAllowsMatchingClientDoodadProxy
ReportNpcActAllowsMatchingClientDoodadProxy

.NET Core 3.1: 249/249
Python NPC/quests: 30/30
```

Despliegue del puente:

```text
imagen activa:
  sha256:479d0107f26a6a5a8ed36fb07d19f2723bb27850bee4e91e47ff99f4ca219644

rollback:
  aaemu-game:pre-aa8-client-doodad-npc-act-bridge-20260726
  sha256:84eb3516748e0e47d0ea4ec144263de5516fd2b906141e3e433b9a16ac635a3f

compact host/container:
  98e0ab85fabdbd38cfd46b0ded19447e8dcc3d2ee384a6c2de967628a67ca69c

ScriptCompiler: 0 errores
Game/Stream:    2239/2250
LoginServer:    registrado
fatal:          0
```

Prueba manual pendiente:

1. reconectar con `Wingsjuanka`;
2. confirmar que `2255` no reaparece;
3. hacer clic derecho una sola vez sobre Marian;
4. aceptar `2256`;
5. confirmar que permanece en el journal;
6. no avanzar ni entregar hasta revisar el log de inicio.

## Segundo hallazgo: el target mutable no era el actor interactuado

La primera versión del puente seguía usando `character.CurrentTarget`. La
prueba de `02:37:57` confirmó que, aunque `GiveQuest` recibía correctamente el
doodad `14074`, ese campo no conservaba el actor al llegar a `Quest.Start`:

```text
DoodadFuncQuest owner = doodad 14074
-> CharacterQuests.Add(2256)
-> QuestActConAcceptNpc
-> CurrentTarget no representa al owner
-> Start false
```

La corrección definitiva transporta el contexto explícito:

```text
DoodadFuncQuest
-> CharacterQuests.Add(questId, ownerDoodad)
-> Quest.InteractionTarget
-> QuestActConAcceptNpc / QuestActConReportNpc
-> MatchesNpcTarget
```

`InteractionTarget` es transitorio y se limpia en `finally` tanto después de
`Start` como de `Complete`; nunca queda persistido ni contamina interacciones
posteriores. `CurrentTarget` sólo queda como fallback para los consumidores
históricos que aún no entregan un actor explícito.

Segundo despliegue:

```text
imagen activa:
  sha256:992cfaaa0bea913be52bcf252f46bd474381a6ab3b75b22813f2494cef5e93fb

rollback:
  aaemu-game:pre-aa8-explicit-quest-interaction-target-20260726
  sha256:479d0107f26a6a5a8ed36fb07d19f2723bb27850bee4e91e47ff99f4ca219644

.NET Core 3.1: 249/249
Python NPC/quests: 30/30
ScriptCompiler: 0 errores
Game/Stream: 2239/2250
LoginServer: registrado
```

## Corrección forense: quest 2256 usa el Object 14073

La interpretación anterior de esta sección, basada en las filas históricas
del runtime, quedó descartada. No era un `ReportNpc 10646`. La tabla nativa de
`game11` y la ficha de la wiki coinciden: el cadáver es el
`client_doodad 14073`, representado visualmente con el modelo del NPC `10646`.

La diferencia entre el runtime histórico y AA8 nativo es:

```text
runtime histórico
  Start 10362 -> AcceptNpc 10581
  Ready 10364 -> ReportNpc 10646
  Reward 10366 -> sin acts

AA8 game11
  Start 10362 -> AcceptDoodad 797 -> doodad 14074 (Marian)
  Ready 10364 -> ReportDoodad 165 -> doodad 14073, alias 6695
  Reward 10366
    -> SupplyExp 3926 -> 1800 EXP
    -> SupplyItem 8874 -> item 18791 x5
```

La definición nativa del cadáver es:

```text
doodad_almighties 14073
  client_doodad=1
  show_name=1
  use_target_highlight=1
  once_one_interaction=1
  once_one_man=1

Start group 41492
  model=npctype://10646

doodad_func 38382
  actual_func_type=DoodadFuncQuest
  actual_func_id=1512
  next_phase=-1

doodad_func_quest 1512
  quest_kind_id=2
  quest_id=2256
```

Esto explica simultáneamente:

1. por qué el actor parece un NPC;
2. por qué el objetivo se recuerda con marcador celeste;
3. por qué hacer clic en un NPC `11544` del mismo nombre no completa nada;
4. por qué un `ReportNpc` histórico nunca podía reproducir la escena nativa.

El spawner histórico contiene cinco cadáveres visuales:

```text
8191 -> NPC 10646, debe ser reemplazado por client_doodad 14073
8241 -> NPC 11544, decorativo
8242 -> NPC 11544, decorativo
8243 -> NPC 11544, decorativo
8244 -> NPC 11544, decorativo
```

La prueba negativa de las `03:04:13` fue válida pero se hizo sobre un
decorativo:

```text
CSStartInteraction npcObj=34471
npcTemplate=11544
readyReportQuests=<none>
CSInteractNPC objId=34471
```

No se debe ampliar la aceptación a todos los cadáveres con el mismo nombre.
La identidad exacta sigue siendo:

```text
spawn NPC 10646
-> reemplazo lógico client_doodad 14073
-> Start group npctype://10646
-> ReportDoodad de quest 2256
```

Corroboración visible:

```text
https://wiki.archerage.to/na-en/db/quests/2256
https://wiki.archerage.to/na-en/db/doodads/14073
```

## La misma entidad también inicia quest 2257

`14073` no termina en la entrega de `2256`. Su grupo Normal también contiene:

```text
doodad_func 38376
  DoodadFuncQuest 1507
  quest_kind=1
  quest=2257
  next_phase=41493

phase 41493
  DoodadFuncUse 10813
  skill=41925
  next_phase=41494
```

El grafo nativo de `2257` contiene:

```text
Start 9947       -> AcceptDoodad 14073
Progress 9998    -> ObjInteraction 1113
                     doodad=14073
                     highlight_doodad_phase=41493
                     wi_id=19 (Use)
Progress 17567   -> ObjItemGather 4330 -> item 16287 x1
Ready 9949       -> ReportNpc 3630
Reward 9950      -> item 23633 x1 + 1800 EXP + item 18792 x5
```

El runtime V2 todavía no contiene `item 16287`, `skill_effects 59150/59152`
ni `effects 77705/77710`. Por seguridad, el runtime V3 reconstruye `2256` y
publica sólo `DoodadFuncQuest 1512`; suprime temporalmente las funciones
`38376/38377` de `2257`. No se trata de una aproximación declarada nativa, sino
de una compuerta explícita para impedir aceptar una transición incompleta.

Artefactos reproducibles:

```text
extract_native_quest_2256.py
build_native_quest_2256_runtime.py
test_native_quest_2256.py
generated/native-quest-2256-client-doodad-v1-manifest.json
generated/native-quest-2256-client-doodad-v1-runtime-manifest.json
```

Validación manual completada para quest `2256`:

```text
[x] NPC 10646 aparece reemplazado por el client_doodad 14073
[x] se ve el marcador celeste de objetivo
[x] una interacción completa 2256
[x] recompensa 1800 EXP + item 18791 x5 ocurre una sola vez
[x] la quest 2257 no se ofrece mientras su cierre esté bloqueado
[x] estado persiste después de una desconexión limpia
```

Evidencia de la prueba en vivo del `2026-07-26`:

```text
03:49:38 CompleteQuest sobre doodad 14073 / grupo 41492
03:49:38 quest_kind=2 selecciona exclusivamente quest 2256
03:49:38 QuestActConReportDoodad res=True
03:49:38 Reward aplica SupplyExp y SupplyItem una vez
03:49:38 SCItemTaskSuccess QuestSupplyItems tasks=1
03:49:38 SCItemTaskSuccess QuestComplete tasks=1
03:49:38 quest 2256 removed
```

Tras la desconexión de `03:51:35`, MySQL confirma:

```text
quests activas del personaje: 0
completed_quests:
  bloque 35 = 0080010000000000
  quest 2256 = bloque 2256/64=35, bit 16 activo
item 18791: 13 -> 18
nivel/experiencia persistidos: 5 / 6143
```

Los clics posteriores (`03:49:47` a `03:51:20`) intentaron `GiveQuest`, pero
produjeron siempre:

```text
doodadTemplate=14073
funcGroup=41492
questKind=1
candidates=0
```

No hubo una segunda recompensa ni una excepción. Este resultado valida la
compuerta V3: la imposibilidad de aceptar `2257` es intencional mientras su
cierre nativo siga incompleto. El siguiente trabajo debe reconstruir primero
`item 16287`, `skill 41925`, `skill_effects 59150/59152`, los efectos
`77705/77710` y las fases `41493/41494`; sólo entonces se puede volver a
publicar `DoodadFuncQuest 1507`.

Validación automática y despliegue V3:

```text
Python NPC/quests: 34/34
.NET Core 3.1: 250/250
quick_check: ok
integrity_check: ok
dos builds: SHA-256 idéntico

runtime:
  compact-8.0-runtime-native-nuian-green-arc-v3.sqlite3
  SHA-256 E28B9282307185A026EE13CBB8CCABED8B2E049338A8E4733771F30A5DEEFE59

servicio recreado: game solamente
imagen: 779ea477406e33ca20e384d3d6b01db15d4060b542f2bb58561d850c6167b813
rollback: aaemu-game:pre-aa8-quest2256-start-group-20260726
ScriptCompiler: 0 errores
Game/Stream: 2239/2250
LoginServer: registrado
```

Durante el primer despliegue se descubrió una segunda suposición histórica:
el indexador y el mensaje de diagnóstico buscaban `npctype://X` únicamente en
un grupo `Normal`. `14073` lo guarda en el grupo `Start 41492`. El índice se
generalizó para preferir `Normal` cuando existe y aceptar el `Start` nativo
como fallback; el log reutiliza ahora el mismo grupo ya resuelto y no ejecuta
una segunda búsqueda incompatible.

Prueba de arranque definitiva:

```text
[AA8ClientDoodad] Indexed npcTemplate=10646
  -> doodadTemplate=14073, funcGroup=41492

[AA8ClientDoodad] Replaced NPC spawn 8191
  npcTemplate=10646
  doodadTemplate=14073
  funcGroup=41492
  world=0, zone=179
  x=14918.848, y=14716.1, z=145.648

restart_count=0
```
