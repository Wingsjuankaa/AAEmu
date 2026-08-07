# Checkpoint — cierre transversal de SupplyItem inicial V2

Fecha: 2026-07-31  
Autoridad: ArcheAge Kakao 8.0.3.12 r558734  
Estado: desplegado, listo para retest manual controlado

## Alcance

Este checkpoint cierra el segundo fallo observado de una quest cuyo diálogo de
aceptación queda abierto porque el servidor no puede crear su `SupplyItem`
inicial. El caso nuevo es `Battle by the Bay` (`quest 2260`) y el objeto nativo
es `Secret Crescent Throne Orders` (`item 16260`).

No se modificó la lógica del guard: `QuestStartDependencyGuard` continúa
rechazando antes de insertar el journal cuando una dependencia no está
demostrada. La reparación completa el dato AA8 que faltaba.

## Evidencia causal

```text
CSStartQuestContextPacket quest=2260
AA8QuestStartGuard:
  item=16260
  reason=missing_item_template
```

Antes del despliegue, MySQL confirmó para Dannia:

```text
quest 2260 activa: no
item 16260 en inventario: no
```

Por tanto, el intento fallido no dejó estado parcial que requiriera limpieza.

## Cierre nativo

```text
quest 2260
  Start 9959 -> AcceptNpc 1856 -> NPC 10582
  Supply 9960 -> SupplyItem 1334 -> item 16260 x1
  Progress 10002 -> ItemGather 938 -> item 16260 x1
  Ready 9961 -> ReportNpc 2092 -> NPC 10583
  Reward 9962

item 16260
  category_id=64
  impl_id=0
  auto_complete=1
  bind_id=2
  icon_id=1554
  loot_multi=1
  loot_quest_id=2260
  max_stack_size=1
  use_skill_id=0
  buff_id=0
  craft_id=0
```

Fuentes forenses:

```text
quest-2260.json
sha256=574CA90A7E98B863C491610D00D965F3D3C0512C1AE38C9AAC086286679B8549

item-16260.json
sha256=A248CB8CD805D0D16380A792FFA5EABD1A506BCD81B08438C699A37A16BD5468

game11
sha256=E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031
```

La página compatible de la quest fue corroboración visible únicamente; no fue
fuente de ninguna fila del runtime.

## Implementación transversal acotada

```text
build_native_quest_supply_closure_v2_runtime.py
test_native_quest_supply_closure_v2.py
generated/native-quest-supply-closure-v2-runtime-manifest.json
```

El builder mantiene un registro explícito de cierres observados y exige por
cada entrada:

```text
dossier quest + dossier item con hashes fijos
fila única extraída por el loader nativo de game11
impl_id/use_skill_id/buff_id/craft_id = 0
grafo exacto Accept -> SupplyItem -> ItemGather -> Report
cobertura generic/complete
```

El censo transversal del runtime mostró:

```text
SupplyItem iniciales: 1003 actos, 964 objetos distintos
antes: 1000 actos incompletos, 961 objetos distintos
después: 999 actos incompletos, 960 objetos distintos
```

Sólo `16260` cambia de incompleto a completo en V2. Las demás dependencias no
se promueven automáticamente, en particular las que poseen `impl_id`, skill,
buff o craft; siguen protegidas por el guard.

## Runtime

Base preservada:

```text
compact-8.0-runtime-point0-rifle-stack-v1.sqlite3
sha256=503BF9639F2005130C9E63A66A443AEA09577C082D7CE8EDC8AB11DA9118B77A
```

Salida:

```text
compact-8.0-runtime-point0-quest-supply-stack-v2.sqlite3
sha256=BD25C9EC6086E76A36C5E9DF7A41A1FCB7EA1D1599FB06A614235339B919604C
bytes=140570624
```

Dos construcciones independientes produjeron el mismo SHA-256. La capa
conserva el arreglo de barras de acción, el ataque de rifle y las reparaciones
de quests anteriores.

## Validación automática

```text
quick_check=ok
integrity_check=ok
quest 2259 y 2260 exactas
items 16259 y 16260 generic/complete
reward items 23633 y 48507 complete
regresión Python combinada: 24/24
items 16259 y 16260: una única fila por ID
suite completa AAEmu.Tests .NET Core 3.1: 311/311
ScriptCompiler: 0 errores, 8 warnings históricas
```

## Respaldo y despliegue

```text
D:\Proyectos\AAemu\backups\quest-supply-closure-v2-20260731-165916\
  mysql-all.sql
sha256=3048D8561ACED2FEDFC5E0755BDE244EFC230E28DBED9D49FA5D5E1DFB8B2E4B
```

Se actualizó `COMPACT_DB` y se recreó exclusivamente `game`. No se reiniciaron
`db` ni `login`, y no se reconstruyó la imagen porque el cambio es sólo de
datos montados read-only.

Verificación posterior:

```text
compact dentro del contenedor:
  BD25C9EC6086E76A36C5E9DF7A41A1FCB7EA1D1599FB06A614235339B919604C
imagen preservada:
  sha256:8c8aeb894caedc06b4c050dda9c6adb8f170c45f4f2479a0c0f7b53012a142d3
restart_count=0
Game 2239=escuchando
Stream 2250=escuchando
LoginServer=registrado
```

## Retest manual solicitado

Primera interacción únicamente:

1. Entrar con Dannia.
2. Hablar con Coast Guard Captain Baker.
3. Aceptar `Battle by the Bay` una sola vez.
4. Confirmar que el diálogo se cierra.
5. Confirmar la quest en el journal y exactamente un ítem 16260.
6. Detenerse antes de hablar con Officer Chloe y reportar el resultado.

Tras revisar logs y MySQL se probará por separado el reporte, la recompensa,
la limpieza del objeto y la persistencia después de relog.
