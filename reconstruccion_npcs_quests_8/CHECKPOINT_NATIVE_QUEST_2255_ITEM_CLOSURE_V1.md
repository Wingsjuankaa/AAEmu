# Checkpoint AA8 nativo — objeto de inicio de quest 2255

Fecha: 2026-07-26
Cliente: ArcheAge Kakao 8.0.3.12 r558734

## Resultado observado

La entrega natural de `2532` funcionó una sola vez y abrió correctamente la
siguiente quest:

```text
2532 completada
-> DoodadFuncQuest 1509
-> aceptar 2255
```

La desconexión ocurrió después de aceptar `2255`, no durante la recompensa de
`2532`. El log cerró la causa exacta:

```text
QuestActConAcceptDoodad 14074
-> Quest 2255 Start
-> QuestActSupplyItem 1337
-> item 16280
-> ItemManager: coverage=Unknown
-> Create devuelve null
-> ItemContainer desreferencia newItem.Template
-> NullReferenceException y desconexión
```

El personaje quedó con `2255` en el journal, pero sin el objeto suministrado,
porque la excepción ocurrió después de agregar la quest y antes de completar
su inicio.

## Cierre nativo

La fila de `16280` del runtime V1 coincide columna por columna con el compact
del cliente AA8:

```text
item_id:        16280
impl_id:        0
loot_quest_id:  2255
max_stack_size: 1
use_skill_id:   17326
```

En AA8, `impl_id=0` es la implementación concreta genérica; no representa un
tipo desconocido. La cadena alcanzable quedó validada:

```text
quest 2255
  Start 9941 -> AcceptDoodad 14074
  Progress supply 9942 -> QuestActSupplyItem 1337 -> item 16280 x1
  Progress use 9943 -> QuestActObjItemUse 588 -> item 16280 x1

item 16280
  -> skill 17326
  -> skill_effect 14619
  -> effect 18267
  -> DispelEffect 385
```

No se importó gameplay histórico 3.0 ni se sustituyó el objeto por uno
parecido.

## Reparación

El constructor:

```text
build_native_nuian_green_arc_v2_runtime.py
```

parte del runtime V1 validado, comprueba la igualdad del objeto con el compact
AA8 y sólo entonces registra:

```text
item_id:              16280
concrete_type:        generic
coverage:             complete
missing_dependencies: vacío
provenance:
  client_compact_8
  + game11_native_skill_closure
  + AA8_native_quest_2255_graph
```

Además, `ItemContainer.AcquireDefaultItemEx` ahora trata un `Create=null` como
una adquisición fallida. Así, cualquier `SupplyItem` futuro con cobertura
incompleta puede hacer fallar y retirar limpiamente la quest, pero no tumbar la
conexión del jugador.

## Artefactos y validación

```text
Runtime:
  D:\Proyectos\AAemu\client_kakao\
  compact-8.0-runtime-native-nuian-green-arc-v2.sqlite3

SHA-256:
  98E0AB85FABDBD38CFD46B0DED19447E8DCC3D2EE384A6C2DE967628A67CA69C

Manifiesto:
  generated/native-nuian-green-arc-v2-runtime-manifest.json
```

Gates offline:

```text
dos construcciones consecutivas: SHA-256 idéntico
PRAGMA quick_check:              ok
PRAGMA integrity_check:          ok
tests Python NPC/quests:         30/30
tests .NET Core 3.1:             245/245
git diff --check:                sin errores
```

## Regla transversal para quests

Cada objeto alcanzable desde una quest debe auditarse como cierre, no como una
fila aislada:

```text
SupplyItem / SupplySelectiveItem / recompensa
-> items
-> tipo concreto o generic impl_id=0 confirmado
-> cobertura complete
-> skill/effect/loot closure si el objeto los referencia
-> creación y notificación ItemTask
-> consumo/progreso
-> limpieza al abandonar o completar
```

Una prueba que sólo confirme `SELECT id FROM items` es insuficiente: V1 tenía
la fila correcta de 16280 y aun así el objeto no podía crearse.

## Prueba manual posterior al despliegue

Como la caída dejó `2255` activa sin el SupplyItem:

1. reconectar con `Wingsjuanka`;
2. abandonar `2255` desde el journal;
3. confirmar que reaparece `!` sobre Marian;
4. aceptar nuevamente sin comando GM;
5. comprobar que recibe exactamente un `16280` y no se desconecta;
6. usarlo frente a Marian/monolito;
7. comprobar transición a Ready y `?` sobre Marian;
8. entregar una vez, reloguear y revisar persistencia.

No se debe intentar continuar la instancia incompleta de `2255` sin
abandonarla y volver a aceptarla.

## Despliegue controlado

Desplegado el 2026-07-26 recreando únicamente `game`:

```text
imagen activa:
  sha256:30ab858d1cf487b18a3c31e1ad43de0bcddbf1c108b32b5fdd962fb0d6327cd0

rollback:
  aaemu-game:pre-aa8-quest2255-item-closure-20260726
  sha256:e2a9c47af12371fe4d17a63a67ec716207b1d2e117b89821e51aa6150128c2e0

compact host/container:
  98e0ab85fabdbd38cfd46b0ded19447e8dcc3d2ee384a6c2de967628a67ca69c

backup MySQL previo:
  backups/aaemu_game-before-quest2255-item-closure-20260726.sql
  sha256:
  DE7322076360CC4F233497A1980754E3C89954E744FAC777954606151FB7892D
```

Arranque aceptado:

```text
QuestManager:       6628 quests
ItemManager:        22624 item templates
ScriptCompiler:     0 errors
Game/Stream:        2239/2250 escuchando
LoginServer:        registrado
errores fatales:    0
```

La aceptación dentro del cliente y la persistencia posterior al relog siguen
siendo la puerta manual pendiente.

## Segunda falla descubierta al usar el objeto

La aceptación natural de `2255` ya reparada entregó exactamente un `16280`.
Al usarlo una vez, el log de `2026-07-26 02:02:44` mostró otra falla
independiente:

```text
skill 17326
-> Quest.OnItemUse(2255)
-> Progress 9943 completado
-> Update continuó evaluando Ready 9944
-> QuestActConReportDoodad devolvió true sin interacción
-> Reward 9946 se ejecutó dentro del mismo Update
-> EXP e items de recompensa volvieron a disparar eventos de la quest
-> Step regresó a Progress durante la transición
-> ciclo de recompensas, subida de nivel y desconexión
```

El personaje de prueba quedó en nivel 34 y con múltiples recompensas. Se
conservó como evidencia mediante borrado lógico:

```text
character id: 6
nombre:       !deleted-6-Wingsjuanka-20260726
deleted:      1
nombre Wingsjuanka libre: sí
```

Backups:

```text
estado limpio previo:
  backups/aaemu_game-before-quest2255-item-closure-20260726.sql
  SHA-256:
  DE7322076360CC4F233497A1980754E3C89954E744FAC777954606151FB7892D

estado posterior a la cascada:
  backups/aaemu_game-after-quest2255-item-use-cascade-20260726.sql
  SHA-256:
  31833E2613FF6919690F5CD3805096EB842986456C22C3FD8732AF66001BFC7A
```

## Protección transversal Progress -> Ready

`Quest.Update` ahora tiene dos invariantes:

```text
1. una actualización de objetivo no puede reentrar mientras ya está activa;
2. al completar Progress, la quest cambia al componente Ready real, envía
   exactamente una actualización y se detiene.
```

Los eventos de obtener items, usar items y subir de nivel también se ignoran
para esa misma quest mientras su `Update` o `Complete` está activo. Por tanto:

```text
usar 16280
-> completa Progress 9943
-> Step=Ready, Status=Ready, ComponentId=9944
-> aparece ? sobre Marian
-> NO ejecuta ReportDoodad ni Reward

clic derecho explícito sobre Marian
-> CharacterQuests.OnReportToDoodad
-> valida doodad 14074
-> Complete ejecuta Reward una sola vez
```

Pruebas de regresión añadidas:

```text
RewardEventsAreIgnoredWhileQuestUpdateIsRunning
CompletedProgressStopsAtRealReadyComponent
```

Esta protección es genérica y no contiene excepciones para quest `2255`.

## Protocolo manual seguro posterior

La próxima prueba debe hacerse con un personaje nuevo llamado `Wingsjuanka`:

1. recorrer la cadena natural hasta aceptar `2255`;
2. confirmar que recibe un solo `16280`;
3. usar el objeto una sola vez;
4. detenerse sin hacer clic sobre Marian;
5. confirmar tracker `Complete` y marcador `?`;
6. revisar logs y persistencia antes de autorizar la entrega;
7. sólo entonces hacer clic derecho una vez para completar.

## Despliegue de la protección Progress -> Ready

Desplegado el `2026-07-26` recreando únicamente `game`:

```text
imagen activa:
  sha256:84eb3516748e0e47d0ea4ec144263de5516fd2b906141e3e433b9a16ac635a3f

rollback inmediato:
  aaemu-game:pre-aa8-quest-progress-ready-guard-20260726
  sha256:30ab858d1cf487b18a3c31e1ad43de0bcddbf1c108b32b5fdd962fb0d6327cd0

compact host/container:
  98e0ab85fabdbd38cfd46b0ded19447e8dcc3d2ee384a6c2de967628a67ca69c
```

Validación final:

```text
tests Python NPC/quests: 30/30
tests .NET Core 3.1:     245/245
ScriptCompiler:          0 errores, 8 warnings conocidos
Game/Stream:             2239/2250 escuchando
LoginServer:             registrado
errores fatales:         0
db y login recreados:    no
nombre Wingsjuanka:      libre
```

## Validación manual positiva

La prueba con el personaje nuevo `Wingsjuanka` confirmó el flujo natural el
`2026-07-26`:

```text
02:20:57 aceptar 2255 en Marian
         -> SupplyItem entrega un único 16280

02:20:59 usar 16280 una vez
         -> Progress 9943 completo
         -> Status Ready
         -> Update se detiene sin recompensa

02:21:03 clic explícito sobre Marian
         -> valida ReportDoodad 14074
         -> entra por Ready 9944
         -> SupplyExp una vez
         -> SupplyItem 18792 una vez
         -> QuestComplete una vez
         -> retira 16280 una vez
         -> elimina 2255 del journal
```

No hubo cascada de recompensas, subida masiva de nivel, excepción ni
desconexión.

La desconexión limpia de `02:24:02` y el guardado de `02:24:12` confirmaron:

```text
personaje id 7:             nivel 4, activo
quest 2255 en journal:      ausente
completed_quests block 35:  0080000000000000
bit de quest 2255:          activo
item temporal 16280:        ausente
```

Por tanto, `2255` queda cerrada también a nivel de persistencia.
