# Checkpoint — Stage 30 world actors v1

Cliente autoridad: Kakao `8.0.3.12 r558734`.

Clasificación: `client_forensics_only`; no es una compact ni un artefacto
desplegable.

## Resultado

Se creó `stage-30-world-actors.sqlite` y se integró como cuarta etapa de
`aa8-client-knowledge.sqlite`.

La etapa descifra y conserva:

- 1.598 `actor_models`.
- 2.907 `models`.
- 18.217 `npcs`.
- 12 plantillas nativas `characters`.
- 2.389 packs de ropa y 664 packs de armas.
- 114 filas de `system_factions` con 104 IDs distintos.
- 157 ocurrencias de spawner observadas en 13 capas de `game_pak`.
- 1.420 rutas únicas de modelos de actor.

El grafo Stage 30 contiene:

- 33.412 entidades.
- 2.135.515 propiedades tipadas.
- 170.232 relaciones.
- 26.058 filas nativas preservadas.
- 22.722 filas de cached results.
- 9 dimensiones de cobertura.
- 4 gaps y 3 regiones opacas.

## Clausura transversal

Se proyectaron relaciones desde NPCs hacia:

```text
model
faction
cloth/weapon pack
skill
quest
AI file/params
interaction/posture/strafe sets
grade/kind/template/nickname
items
sound
total character custom
```

También se proyectaron:

```text
model -> actor_model -> model asset
character_template -> model/face item/custom/faction/zone/equipment
system_faction -> mother faction
game_pak spawner evidence -> npc
```

Los destinos pertenecientes a etapas futuras se materializan como endpoints
`unknown`; no se inventan filas ni comportamiento.

## Evidencia bloqueada

- `models` conserva 357 referencias globales de strings sin resolver.
- `npcs` conserva 5.469 referencias globales de strings sin resolver.
- `total_character_customs` sigue opaco: los IDs están relacionados, pero falta
  descifrar el accessor/layout de los datos de apariencia.
- Los layouts de `npc_spawners` y `npc_spawner_npcs` están confirmados, pero una
  búsqueda exhaustiva en `game0`, `game2`, `game6`, `game7` y `game11` no
  encontró cadenas de resultados nativos.
- Las posiciones de capas de `game_pak` son corroboración; todavía falta cerrar
  mundo/zona, revisión activa y parámetros runtime del spawner.

## Determinismo e integridad

Dos construcciones consecutivas de Stage 30 produjeron:

```text
E4B340A91DBCBFADA29C8334837257D33D66EAB71D6734A0F5B9DCE7351B3C4F
```

La consolidada resultante:

```text
775D6D549F075D2F44BB296C054DB2AE773BD5517BA4B8ECD3D042DC7F277F27
```

Conteos consolidados principales:

- 191.991 entidades.
- 4.309.852 propiedades.
- 618.291 relaciones.
- 462.415 filas cacheadas.
- 132.424 filas nativas.
- 4 etapas registradas en `stage_lineage`.
- cero propiedades, relaciones o cached results huérfanos.

Todas las bases verificadas cumplen:

```text
PRAGMA quick_check=ok
PRAGMA integrity_check=ok
```

## Próxima frontera recomendada

Cerrar la apariencia antes de avanzar a Stage 40:

1. Descifrar el accessor fijo de `custom_face_presets.modifier` y
   `total_character_customs.modifier`.
2. Recuperar esas dos tablas en el gap acotado de `game11`.
3. Resolver las referencias globales de strings reproduciendo la caché en orden
   de ejecución.
4. Completar la cadena NPC/character → custom → face/hair/decal → assets.

Luego corresponde Stage 40 quests y relaciones NPC/doodad/skill asociadas.
