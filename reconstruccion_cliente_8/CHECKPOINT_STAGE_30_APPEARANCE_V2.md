# Checkpoint — Stage 30 appearance native v2

Cliente autoridad: Kakao `8.0.3.12 r558734`.

Clasificación: `client_forensics_only`. No modifica AAEmu, compacts runtime,
MySQL, Docker ni mecánicas.

## Catálogos descifrados

La frontera de apariencia agrega resultados nativos con límites exactos:

- 1.797 `face_decal_assets`.
- 449 `custom_face_presets`.
- 1.546 `total_character_customs`.
- 2 `body_diffuse_maps`.
- 27 `body_normal_maps`.
- 0 `face_diffuse_maps` (vacío nativo confirmado).
- 138 `face_normal_maps`.
- 0 `face_eyelash_maps` (vacío nativo confirmado).
- 436 `customizing_item_assets`.
- 5 `custom_hair_textures`.

Los payloads `modifier` de presets y total customs se preservan como
`uint32_le length + 128 bytes`; las 1.995 filas tienen longitud 128 y terminan
exactamente en sus límites `SQLITE_DONE`. La semántica interna permanece
opaca.

## Clausura del grafo

Se añadieron relaciones:

```text
total_character_custom
  -> body/face normal map
  -> body/face/hair/horn item
  -> hair/horn customizing item asset
  -> skin/hair/horn color
  -> fixed/movable face decal
  -> icon/model

item_body_part item -> custom_hair_texture -> texture asset
customizing_item_asset -> item/category/model
body/face map -> icon/model/texture asset
face_decal_asset -> item/category/icon/model/texture asset
```

Todas las referencias positivas de `body_normal_map_id`,
`face_normal_map_id` y `custom_texture*_id` cierran contra filas nativas.

## Evidencia negativa y anomalías preservadas

- `customizing_item_asset_colors` y `skin_colors` tienen SQL, loaders y layouts
  exactos, pero ninguna coincidencia de resultado no vacío en `game0…game11`.
- En `game11` no existe resultado entre el final de
  `character_equip_packs` y el siguiente header; los calls 273 y 274 no
  emitieron cached result.
- Seis items de cabello referenciados no tienen fila en
  `customizing_item_assets`: `24036, 24078, 24145, 32000, 34013, 46266`.
- `total_character_customs:548` referencia el decal ausente `118`.
- Una ruta nativa no existe literalmente en el índice congelado de
  `game_pak`:
  `objects/characters/nuian/male/nude/custom/nu_m_underpants01_df.dds`.
- Los catálogos ausentes, el decal y la ruta no se reconstruyen por similitud.

## Resultado Stage 30

- 42.375 entidades.
- 2.238.802 propiedades tipadas.
- 197.385 relaciones.
- 30.458 filas nativas.
- 27.122 filas de cached results.
- 18 catálogos nativos.
- 17 dimensiones de cobertura.
- 8 gaps y 5 regiones opacas.

Dos construcciones consecutivas produjeron:

```text
stage-30-world-actors.sqlite
9A7045014A9673CD168DD233F8FE0C51B9824F978DFBB6EB5159B492C1222543
```

## Consolidada

Dos consolidaciones consecutivas produjeron:

```text
aa8-client-knowledge.sqlite
576100F03793E1DFAB1303F6285F596314F15F845487594E1AF0FAA5C06701D2
```

Conteos principales:

- 200.248 entidades.
- 4.413.139 propiedades.
- 645.444 relaciones.
- 466.815 filas cacheadas.
- 136.824 filas nativas.
- 147 query specs y 147 cached results.
- 74 artefactos con hash.
- cero propiedades, relaciones o cached results huérfanos.

Todas las bases verificadas cumplen:

```text
PRAGMA quick_check=ok
PRAGMA integrity_check=ok
```

## Próxima frontera recomendada

Cerrar los dos blockers todavía descifrables desde binario/ejecución:

1. mapear los campos internos del payload `modifier[128]`;
2. reproducir la caché global de strings para los resultados de
   modelos/NPC/facciones que aún conservan `<ref:N>`.

Después corresponde Stage 40: quests y clausura
`NPC/doodad/sphere/item/skill -> quest`.
