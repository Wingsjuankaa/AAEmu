# Checkpoint AA8 nativo — cadena verde Nuian V1

## Motivo

Después de completar naturalmente la quest `330` y avanzar la cadena verde,
la quest `2532` (`A Mysterious Visitor`) quedó en estado Ready frente a Marian,
pero Marian no mostró `?`.

Este síntoma no era una repetición del fallo global de `SCFilterPacket`.
El cliente ya tenía sus índices globales de quests construidos.

## Causa raíz comprobada

El runtime histórico y AA8 describen la misma misión de forma distinta:

```text
runtime histórico
  component 10966
  QuestActConReportNpc 2301
  NPC 10581 = Marian

AA8 game11
  component 10966
  QuestActConReportDoodad 163
  doodad 14074
```

El doodad `14074` tampoco es un objeto físico ordinario. Su cierre nativo es:

```text
doodad_almighties 14074
  client_doodad = 1

doodad_func_groups 41496
  model = npctype://10581

doodad_funcs 38378
  DoodadFuncQuest 1508

doodad_func_quests 1508
  quest_kind_id = 2
  quest_id = 2532
```

AA8 representa esta entrega como un doodad lógico del cliente respaldado por
el modelo de Marian. Convertirlo manualmente a `ReportNpc` borra la relación
nativa que el cliente utiliza para calcular el marcador y la interacción.

## Alcance transversal recuperado

Se seleccionó la primera cadena verde Nuian mediante:

```text
category_id = 3
race = 1
zone_id = 9
```

Resultado nativo:

```text
quests:     7  (2255, 2262, 2264, 2265, 2266, 2531, 2532)
components: 25
acts:       40
```

Tipos concretos cerrados:

```text
AcceptNpc
ReportNpc
AcceptDoodad
ReportDoodad
SupplyItem
SupplyExp
SupplySelectiveItem
ObjItemGather
ObjItemUse
```

También se recuperaron:

- `doodad_almighties`;
- `doodad_func_groups`;
- `doodad_funcs`;
- `doodad_func_quests`;
- los ítems de quest ausentes del runtime (`16280`, `21604`, `24967`) desde
  el compact del cliente AA8.

## Migraciones de consumidor

El esquema histórico de `quest_act_obj_item_gathers` descartaba campos de AA8:

```text
item_grade_id
use_grade
```

El servidor ahora los carga y aplica la restricción de grado cuando
`use_grade=true`.

`DoodadTemplate` ahora conserva también:

```text
client_doodad
```

No se añadió todavía un atajo que convierta un `ReportDoodad` en
`ReportNpc`. Primero debe observarse qué paquete emite el cliente con el
grafo nativo cargado.

## Herramientas durables

Auditor y extractor de evidencia:

```text
extract_native_nuian_green_arc.py
```

Constructor no destructivo del runtime:

```text
build_native_nuian_green_arc_runtime.py
```

Pruebas:

```text
test_native_nuian_green_arc.py
```

Artefactos:

```text
generated/native-nuian-green-arc-v1-manifest.json
generated/native-nuian-green-arc-v1-runtime-manifest.json
D:\Proyectos\AAemu\client_kakao\
  compact-8.0-runtime-native-nuian-green-arc-v1.sqlite3
```

Hash del runtime offline validado:

```text
F15F3A2AA00DDF2DD0AE31EDA9B7C4CBE00172D342BBE4E713E5FF945A478BC7
```

## Validación automática

```text
Python: 7/7
.NET Core 3.1 Docker SDK: 239/239
SQLite integrity_check: ok
quest 2532 Ready:
  63971, QuestActConReportDoodad, detail 163
doodad 14074:
  client_doodad=1
  proxy npctype://10581
  DoodadFuncQuest 1508 -> report quest 2532
```

## Regla para futuras reconstrucciones

Nunca decidir el destino de una quest solamente por el texto visible o por
la fila histórica del servidor.

Para cada Start/Progress/Ready/Reward hay que cerrar:

```text
quest_context
  -> component
  -> quest_act
  -> concrete act detail
  -> NPC/doodad/item/skill
  -> función del objeto
  -> ubicación o clasificación client_doodad
  -> protocolo observado
```

Si el act es `AcceptDoodad` o `ReportDoodad`, comprobar siempre
`client_doodad` y los modelos `npctype://...` antes de buscar un spawn físico.

## Prueba manual siguiente

1. desplegar de forma controlada el runtime generado;
2. reconectar para que `SCFilterPacket` vuelva a inicializar los índices;
3. conservar la quest `2532` en Ready;
4. comprobar si aparece `?` sobre Marian;
5. interactuar y capturar el paquete exacto;
6. sólo si el servidor no reconoce ese paquete, implementar el consumidor
   genérico de `client_doodad`, sin hardcodear quest `2532`.

## Despliegue controlado

Desplegado el `2026-07-26`:

```text
imagen:
  sha256:c9dde48c83f06df88e7450404f583626fc9210a4956101711ba8b678e1bface7

compact host/container:
  f15f3a2aa00ddf2dd0ae31eda9b7c4cbe00172d342bbe4e713e5ff945a478bc7

rollback:
  aaemu-game:pre-aa8-native-nuian-green-arc-20260726
  sha256:c9cc92de2cb43d0b8f2ba8566d5ef4f0454f1b10d43e7f685d0453fde3816cf7
```

El primer arranque de validación detectó que las columnas nuevas agregadas a
filas históricas quedaban `NULL`. La migración se corrigió para inicializar
campos numéricos/bool a `0` y texto a cadena vacía; los consumidores también
usan lectores tolerantes a columnas ausentes o nulas.

Arranque aceptado:

```text
QuestManager: 6628 quests
ItemManager: 22624 item templates
ScriptCompiler: 0 errors, 8 warnings históricas
Game/Stream: 2239/2250
LoginServer: registrado
```

Estado persistido antes de la prueba:

```text
Wingsjuanka
quest 2532
status 3 = Ready
component 10966
```

No se forzó, abandonó ni completó la quest durante el despliegue.
