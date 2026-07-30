# Checkpoint — Stage 30 appearance and model closure v3

Cliente autoridad: Kakao `8.0.3.12 r558734`.

Clasificación: `client_forensics_only`. No modifica AAEmu, compacts runtime,
MySQL, Docker ni mecánicas.

## Payload nativo de CustomModel

La evidencia cruzada de `x2game.dll` de 64 y 32 bits confirma que el campo
`modifier` de `CustomModel`:

- comienza en `CustomModel + 0xA8` en x64;
- copia y serializa exactamente `0x80` bytes;
- se representa como `signed int8[128]`;
- conserva el contenedor cacheado `uint32_le length + 128 bytes`;
- tiene el slot reservado `0` siempre en cero.

Se proyectaron 1.995 payloads:

- 449 `custom_face_presets`;
- 1.546 `total_character_customs`;
- 255.360 propiedades `modifier_int8`, una por slot.

## Targets faciales

Se importaron los 12 perfiles XML nativos de raza y género, con 966 targets
nombrados. El grafo materializa:

```text
CustomModel
  -> face_target_profile
  -> face_target
  -> modifier_int8[index]
```

Se crearon 2.201 relaciones `uses_face_target_profile`, 966 relaciones
`defines_face_target`, 7.899 propiedades de target y 72 propiedades de perfil.

Sólo permanecen opacos 11 pares perfil/slot que tienen valores no cero pero no
poseen un `Target` XML:

```text
dwarf/female[80]
dwarf/female[81]
dwarf/male[75]
elf/female[26]
elf/female[87]
elf/male[86]
hariharan/female[84]
hariharan/male[84]
nuian/female[83]
nuian/male[83]
warborn/female[26]
```

No se les asignó un nombre por semejanza ni desde datos históricos.

## Clausura de modelos

La caché local exacta de `attach_anims` demuestra las referencias globales:

```text
150126 -> VehicleModel
150127 -> ShipModel
```

Con esa evidencia quedan clasificados todos los subtipos de `models`:

- 1.598 `ActorModel`;
- 975 `PrefabModel`;
- 246 `VehicleModel`;
- 88 `ShipModel`.

Las relaciones del grafo son `uses_actor_model`, `uses_prefab_model`,
`uses_vehicle_model` y `uses_ship_model`. Aún quedan 23 referencias crudas en
el campo textual `models.name`; ya no bloquean identidad ni subtipo.

## Localización de actores

El compact cliente descifrado aporta `localized_texts` como autoridad nativa:

- 18.217 nombres `en_us` de NPC importados;
- 228 campos localizados de facciones;
- 18.445 localizaciones totales.

Los 18.217 NPCs tienen nombre de presentación cerrado. En la caché original
permanecen 5.461 referencias crudas en `npcs.name` y 8 en `npcs.so_state`;
se preservan como evidencia del stream y no sustituyen la localización
confirmada. Las 114 facciones tienen nombre localizado; quedan 2
`owner_name` crudos.

## Resultado Stage 30

`stage-30-world-actors.sqlite`:

- 44.661 entidades;
- 2.520.578 propiedades tipadas;
- 201.861 relaciones;
- 30.470 filas nativas;
- 27.122 filas de cached results;
- 18 catálogos nativos;
- 18.445 localizaciones;
- 20 dimensiones de cobertura;
- 8 gaps y 5 regiones opacas.

Dos construcciones aisladas produjeron exactamente:

```text
DEC51A1ECD71CDA96D3007671FF46AAAF105278DCD2722A1772C428B872C5F8D
```

Tamaño: `1.176.510.464` bytes.

## Consolidada transversal

`aa8-client-knowledge.sqlite` contiene:

- 202.534 entidades;
- 4.694.915 propiedades;
- 649.920 relaciones;
- 466.815 filas cacheadas;
- 136.836 filas nativas;
- 148 query specs y 148 cached results;
- 91 artefactos;
- 172.190 registros de cobertura;
- 98.014 gaps;
- 11 regiones opacas;
- 4 etapas de linaje.

Se eliminó una fuente de no determinismo: los cuatro artefactos derivados de
etapa ya no almacenan el directorio absoluto de salida, sino su nombre
canónico. Dos consolidaciones completas en directorios distintos produjeron
el mismo archivo:

```text
BF5AF751F7C6A87DBA8926AF68F2D3B827883B7774620142F17F7EAD270A0572
```

Tamaño: `2.808.909.824` bytes.

Todas las bases verificadas cumplen:

```text
PRAGMA quick_check=ok
PRAGMA integrity_check=ok
```

La consolidada tiene cero propiedades, relaciones, cached results u orígenes
y destinos de relación huérfanos. Los 21.419 IDs positivos de items continúan
clasificados.

## Bloqueos que permanecen explícitos

Esta frontera no equivale al 100% del cliente. Permanecen, entre otros:

- los 11 slots de modifier sin descriptor XML;
- referencias textuales crudas de la caché global indicadas arriba;
- resultados nativamente ausentes para `customizing_item_asset_colors`,
  `skin_colors`, `npc_spawners` y `npc_spawner_npcs`;
- anomalías y dependencias de items heredadas de Stage 20;
- superficies DLL/Lua/XML/assets todavía corroborativas hasta vincularlas con
  un loader o consumidor nativo.

## Próxima frontera recomendada

Construir Stage 40 para quests y su clausura transversal:

```text
quest
  -> acts/components
  -> NPC/doodad/sphere/item/skill
  -> rewards/requirements
  -> localización/assets
```

Debe comenzar por inventariar loaders, SQL, cached results y tablas del compact
cliente, registrar resultados ausentes y sólo después proyectar entidades y
relaciones. La wiki compatible se usará como corroboración y enriquecimiento,
nunca para reemplazar una fila o relación nativa opaca.
