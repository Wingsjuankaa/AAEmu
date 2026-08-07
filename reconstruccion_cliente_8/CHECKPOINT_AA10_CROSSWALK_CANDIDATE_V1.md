# Checkpoint AA10 crosswalk candidate V1

## Estado

Este checkpoint registra una fuente comparativa nueva. No cierra una etapa
forense, no modifica Stage 20/30/50/90, no cambia la consolidada AA8 y no
autoriza importar filas al runtime.

La SQLite descifrada 10.x se evalúa `9/10` como candidata de crosswalk:
cobertura de esquema 2/2, continuidad de IDs 2/2, estabilidad relacional 2/2,
capacidad de cerrar catálogos 2/2 y coincidencia de versión/procedencia 1/2.
La puntuación no representa autoridad AA8.

## Artefactos congelados

| Rol | Bytes | SHA-256 |
|---|---:|---|
| `game.sqlite3` 10.x principal | 552.178.688 | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` |
| compacto multilenguaje | 440.823.808 | `68919695CDD12C7B9CB4AC9BEA3828132B83C95D7DCCF46AA3E113CEA756507F` |
| compact cliente AA8 mínimo | 80.474.112 | `4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57` |

Ruta principal:

```text
E:\AAEmu-Research\test\ArcheAge Returns 10.0.2.13 - 8yx - r575 - 2026-06-18\game\db\game.sqlite3
```

`PRAGMA quick_check=ok`. Contiene 1.373 tablas. `bundle_versions` declara
`10.0.1.6`, SVN `622045`; conservar esa diferencia respecto del paquete r575.
Las copias del retail zone server llamadas `game.sqlite3` y `compact.sqlite3`
son byte a byte idénticas al artefacto principal y no agregan procedencia.

El compacto multilenguaje contiene 1.002 tablas y ninguna exclusiva. Omite
371 tablas presentes en `game.sqlite3`, incluidos `loot_packs`,
`npc_spawners`, `npc_spawner_npcs`, varios contratos de combate y los
catálogos enum/const. Su rol principal es localización.

## Cobertura comparativa inicial

- 67 superficies opacas activas AA8 tienen tabla homónima en 10.x.
- 179 tablas con query AA8 y cero filas recuperadas aparecen en 10.x.
- 177 conservan todas las columnas esperadas por los loaders AA8.
- 162 son compatibles y no vacías.
- Existen 285 tablas `enum_*` con 5.295 filas.
- Existen 28 tablas `const_*` con 653 filas.

| Superficie | AA8 | 10.x | Continuidad |
|---|---:|---:|---:|
| item IDs observados | 21.419 | 51.010 | 100 % |
| skill IDs observados | 33.466 | 38.043 | 100 % |
| craft IDs habilitados | 9.369 | 12.402 | 100 % |
| appellation IDs | 265 | 1.098 | 100 % |
| `skill_products` | 1.097 | 1.127 | 100 % relacional |
| `skill_reagents` | 2.712 | 2.804 | 99,45 % relacional |
| `tagged_buffs` | 49.526 | 52.542 | 99,93 % relacional |
| `tagged_skills` | 28.910 | 30.852 | 99,98 % relacional |

La mayoría de claves relacionales de items coinciden entre 99,68 % y 100 %;
`max_enchant_scale_id` coincide 85,05 %. En skills, casi todas las claves
coinciden por encima de 99,95 %; `active_weapon_id` coincide 99,49 %.

## Fronteras prioritarias

### Loot

AA8 conoce 4.195 `loot_pack_id` por referencias. La 10.x materializa 4.191
(99,90 %) y 4.181 tienen entradas en `loots` (99,67 %). Faltan `12556`,
`13079`, `13757` y `13758`.

No promover probabilidades ni cantidades. `loots` 10.x carece de
`loot_quest_id`, columna exigida por el loader AA8, por lo que esa relación
permanece bloqueada.

### Tagged items

El query legacy AA8 de `tagged_items` apunta a `game11` offset `21952540`,
exactamente el rango usado por `tagged_skills`, y produce los mismos valores
renombrados. La 10.x contiene 33.226 relaciones `tagged_items` distintas. Esto
es evidencia de una posible frontera de caché AA8 mal asignada; exige volver al
consumer y al resultado AA8, no sustituirlo por filas 10.x.

### Mundo y apariencia

- `skin_color`: 113/114 IDs AA8 aparecen en 10.x; falta `98`.
- `customizing_item_asset_color`: 880/881; falta `14917`.
- `sphere`: 997/999; faltan `132` y `743`.
- `npc_spawner`: 160/189; continuidad 84,66 %.
- `npc_group`: 316/616; continuidad 51,30 %.

Los primeros tres catálogos son candidatos fuertes. Spawners y grupos no
admiten importación masiva.

## Próxima etapa

Construir `aa8-aa10-crosswalk-v1.sqlite3` fuera de Git y clasificar cada fila:

```text
exact_id_exact_relation
stable_id_changed_properties
renumbered_row_stable_relation
aa8_only
aa10_only
structural_candidate
conflict
```

Separar identidad/relación de balance, conservar procedencia por campo, crear
manifest sin timestamps, construir dos veces con SHA idéntico, ejecutar
`quick_check` e `integrity_check`, exigir cero descartes y actualizar las
etapas sólo después de revisar cada frontera por dominio.

## Cierre verificable de la V1 — 2026-08-03

La etapa propuesta arriba quedó construida como capa comparativa independiente.
No se modificaron Stage 20/30/50/90, la consolidada AA8, `rama_8_modern`, el
servidor ni el runtime.

### Fuentes congeladas

| Fuente | Bytes | SHA-256 | quick_check | integrity_check |
|---|---:|---|---|---|
| AA8 consolidada | 8.906.633.216 | `92CDF5D1EB16DAF0C4D5ABFCB80B510DFDF827708D4F8087235CCFACE3CE3C4F` | `ok` | `ok` |
| 10.x `game.sqlite3` | 552.178.688 | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` | `ok` | `ok` |

La fuente 10.x contiene 1.373 tablas de usuario (1.374 contando
`sqlite_sequence`). El nombre externo del paquete es r575/10.0.2.13, pero su
fila principal `bundle_versions` declara `10.0.1.6`, SVN `622045`; ambos datos
de procedencia se preservan sin intentar reconciliarlos. Las copias idénticas
de esta SQLite no cuentan como evidencia independiente.

El inventario actual de la consolidada arroja 545 tablas consultadas, 541 con
homónimo 10.x, 181 sin cache recuperado, 180 con homónimo, 178 compatibles y
163 compatibles no vacías. La diferencia de +1 frente al triage histórico
179/177/162 se registra como evolución del inventario AA8, no se reescribe.
Las 67 superficies opacas homónimas históricas también se conservan; la foto
actual contiene 110 superficies opacas distintas, 67 con homónimo.

### Artefactos y reproducibilidad

```text
principal: E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3
bytes: 6.043.475.968
SHA-256: 44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71
manifest SHA-256: F8873B6C89856D3269192EBC5874D7166BF3F06D766DA0B74EE0F808F76279D9
repetición: E:\AAEmu-Research\output\aa8-client-forensics\aa10-crosswalk-v1-repeat
resultado: 16/16 artefactos byte a byte idénticos
informe de determinismo SHA-256: 5E94C1876F4EDAE243C3452AC3A372EFE98E9F39873E4333D4A7409BEBF6A8D5
```

Las dos bases obtuvieron `quick_check=ok`, `integrity_check=ok`, cero FKs
huérfanas internas, cero clasificaciones fuera del vocabulario, cero eventos
fallidos y cero descartes silenciosos. El informe completo es
`aa8-aa10-crosswalk-v1-determinism.json`. El validador oficial de la skill
confirmó además 13 tablas físicas de salida, 11 métricas de cobertura y 9
eventos de validación.

### Volumen clasificado

| Superficie | Total |
|---|---:|
| tablas físicas inventariadas | 1.410 |
| columnas | 8.086 |
| índices | 108 |
| FKs declaradas | 14 |
| tablas lógicas clasificadas | 1.444 |
| comparaciones de fila | 1.553.515 |
| comparaciones relacionales | 9.690.387 |
| evidencias negativas | 188 |
| conflictos registrados | 53 |

Las 1.312.038 filas de evidencia AA8 quedaron contabilizadas: 1.283.128 se
compararon y las 28.910 de `tagged_items` quedaron en cuarentena explícita.

Clasificación de filas:

| Clase | Filas |
|---|---:|
| `exact_id_exact_relation` | 835.279 |
| `stable_id_changed_properties` | 443.160 |
| `renumbered_row_stable_relation` | 17.311 |
| `aa8_only` | 11.890 |
| `aa10_only` | 241.477 |
| `conflict` | 4.398 |

Clasificación de relaciones:

| Clase | Relaciones |
|---|---:|
| `exact_id_exact_relation` | 7.810.667 |
| `renumbered_row_stable_relation` | 51.214 |
| `structural_candidate` | 214.266 |
| `aa8_only` | 60.691 |
| `aa10_only` | 1.548.827 |
| `conflict` | 4.722 |

`structural_candidate` se materializa donde corresponde a nivel tabla o
relación; no se fuerza como etiqueta de fila cuando no existe identidad
natural suficiente.

### Relaciones confirmadas y cobertura parcial

- Items: 21.419/21.419 IDs AA8 presentes en 51.010 IDs 10.x.
- Skills: 33.466/33.466 presentes en 38.043.
- Crafts habilitados: 9.369/9.369 presentes en 12.402.
- Appellations: 265/265 presentes en 1.098.
- `tagged_skills`: 28.905 relaciones naturales exactas de 28.910; cinco AA8
  quedan ausentes en 10.x.
- `tagged_buffs`: 49.490/49.526 relaciones naturales se conservan (99,93 %).
- `skill_products`: 1.097/1.097 relaciones naturales se conservan.
- `skill_reagents`: 2.697 relaciones exactas, nueve conflictos y seis filas
  AA8 ausentes; propiedades y balance permanecen separados.
- Loot packs: 4.191/4.195; faltan `12556`, `13079`, `13757`, `13758`.
- Contenido loot: 4.181/4.195; además faltan `7903`, `7931`, `9322`–`9326`,
  `12363`, `12364` y `12399`.
- `skin_color`: 113/114; falta `98`.
- `customizing_item_asset_color`: 880/881; falta `14917`.
- `sphere`: 997/999; faltan `132` y `743`.
- `npc_spawner`: 160/189 (parcial).
- `npc_group`: 316/616 (parcial).

Los catálogos AA10 incluyen 285 tablas `enum_*` con 5.295 filas y 28 tablas
`const_*` con 653 filas. Son candidatos estructurales comparativos; no son
evidencia nativa AA8 por sí solos.

### Conflictos y bloqueos conservados

- `tagged_items` queda `conflict`/`blocked_cache_boundary`, con 28.910 filas
  AA8 en cuarentena y cero comparadas. El rango `game11` coincide exactamente
  con `tagged_skills`. Los consumidores nativos prueban contratos distintos:
  `LoadItemTagsRelation` consume `item_id, tag_id`, mientras
  `LoadSkillTagsRelation` consume `skill_id, tag_id`. Las 33.226 relaciones
  10.x no reemplazan esta superficie.
- `loot_quest_id` permanece bloqueado: el loader AA8 lo exige y `loots` 10.x
  no tiene una columna equivalente verificable.
- `npc_spawner` y `npc_group` no habilitan importación masiva.
- Los cuatro loot IDs problemáticos permanecen `aa8_only`, no se renumeran.
- Ninguna probabilidad, cantidad, fórmula, tiempo, conducta de IA, paquete de
  red, progreso de quest o contenido exclusivo 10.x es promovible.

### Integración posterior permitida

Sólo pueden revisarse como candidatos, uno por uno y contra evidencia AA8:
identidades continuas de items/skills/crafts/appellations; claves relacionales
de `tagged_skills`, `tagged_buffs`, `skill_products` y `skill_reagents`;
catálogos de apariencia de alta cobertura; y formas `enum_*`/`const_*` para
orientar recuperación nativa. No integrar directamente filas, propiedades ni
balance 10.x, ni resolver con ellas ausencias AA8.

## Próximo paso después de V1

Auditar por dominio los 53 conflictos y recuperar el límite original de
`tagged_items` desde el productor/cache AA8. Cualquier promoción al
conocimiento AA8 requiere una frontera posterior explícita, revisión humana y
evidencia nativa; esta V1 no modifica automáticamente ninguna etapa canónica.
