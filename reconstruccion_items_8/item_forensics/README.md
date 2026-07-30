# AA8 Item Forensics

Inventario reproducible de objetos de ArcheAge Kakao 8.0.3.12 r558734.
La herramienta compara evidencia nativa del cliente con la compact activa y
el backend AAEmu. No importa gameplay histórico 3.0, no modifica la compact
cliente, no activa candidatos y no despliega el servidor.

## Uso

Desde la raíz de `rama_8`:

```powershell
python -B -m item_forensics run-all --deep
python -B -m item_forensics explain 45731
python -B -m item_forensics report
python -B -m item_forensics audit-native-closure
python -B -m item_forensics scan-wiki --scope unresolved
python -B -m item_forensics audit-wiki
python -B -m item_forensics generate-family evolving_material
python -B -m item_forensics verify E:\AAEmu-Research\output\aa8-item-forensics\candidates\<candidato>
```

También se pueden ejecutar las etapas independientemente:

```powershell
python -B -m item_forensics scan-client
python -B -m item_forensics decode-cache --deep
python -B -m item_forensics audit-server
```

Las rutas se resuelven desde
[`config/kakao-r558734.json`](config/kakao-r558734.json), `.env` y las
variables `AAEMU_REPO`, `AAEMU_CLIENT` y `AAEMU_RESEARCH`. Todas poseen
opciones equivalentes en la CLI.

## Superficies revisadas

El barrido no está limitado a `game11`:

- compact cliente y compact runtime activa;
- los 12 streams cacheados `game0…game11`;
- `x2game.dll` de 32 y 64 bits;
- inventario de 363 archivos externos a `game_pak`, incluidas 250 DLL;
- 1.112 scripts Lua decompilados;
- XML y superficies world ya extraídas;
- catálogo de SQL embebido recuperado de binarios;
- índice completo de 377.295 entradas de `game_pak`;
- manifests de búsquedas binarias, contenido, extracción y evidencia negativa.

El pak de 51,5 GB no se vuelve a extraer. Se reutilizan el índice, los
manifests, hashes y árboles ya revisados. Las coincidencias en scripts, XML,
DLL, nombres y assets se conservan como `corroborative`; sólo un loader,
consumer o protocolo nativo puede elevar gameplay a `confirmed`.

## Salidas

Por defecto se escriben fuera de Git en
`E:\AAEmu-Research\output\aa8-item-forensics`:

- `aa8-item-forensics.sqlite`: catálogo, grafo, capacidades, brechas,
  regiones opacas, referencias de superficies y ciclo de vida de
  descriptores.
- `native-closure-audit.json` y `.csv`: reclasificación de descriptores
  pendientes mediante relaciones nativas de crafts, conversiones, tags,
  skills y buffs.
- `manifest.json`: hashes, versiones, contadores y validaciones.
- `report.html`, `report-data.json` y `gaps.csv`.
- `reviewed-surfaces.json`: inventario de DLL, Lua, XML, pak y referencias.
- `ghidra-layout-tasks.json`: consultas que requieren cerrar layout o refs.
- `family-queue.json`: priorización conservadora por familia.
- `candidates/`: paquetes de revisión que nunca son desplegables.

Estados por dimensión: `confirmed`, `missing`, `blocked`, `unknown` y
`not_applicable`.

## Catálogos de dependencias v1.7

La auditoría integra catálogos nativos separados para:

- 27.303 IDs de `buffs`;
- 15.290 IDs de `doodad_almighties`;
- 9.369 crafts habilitados de 11.615 filas totales;
- 36.137 filas de `craft_materials`;
- 11.787 filas de `craft_products`;
- 2.822 relaciones `item_recipes`;
- el grafo completo de conversión: 34.822 reactivos, 6.384 conversiones,
  5.626 productos y sus packs;
- 5.280 tags y 28.910 relaciones `tagged_items`.

Los layouts se validan contra loaders x86 y x64 de `x2game.dll`. Las
referencias internadas todavía opacas no bloquean el alcance numérico de IDs,
pero sí mantienen opacos sus campos textuales.

El resultado de `crafts WHERE enable='t'` comienza en `game11@134099285`.
Su cabecera usa las 11.615 filas de `SELECT COUNT(*) FROM crafts`, pero el
loader filtrado termina correctamente después de 9.369 filas, justo antes de
`craft_line_components`. Esta diferencia de capacidad y filas filtradas era
la causa del falso `native_result_absent` de v1.5.

La tabla consolidada `descriptor_lifecycle` separa presencia, habilitación y
tombstones sin inferir datos inexistentes. Para los 103 items `impl_id=12`:

- 34795→craft 352 y 39040→craft 2 son recipes habilitadas;
- 42805→craft 277 y 43152→craft 278 son recipes deshabilitadas;
- los 99 restantes no aparecen en el resultado nativo no filtrado de
  `item_recipes` y son tombstones de ese descriptor.

Los 99 tombstones no se descartan: 23 siguen activos como reactivos de
conversión, 64 como materiales de craft, uno como consumidor de skill, diez
sólo aparecen en crafts inactivos y uno conserva únicamente metadata. Esta
clasificación describe su rol observado; no restaura un descriptor recipe que
el cliente ya no carga.

`item_armors` también es una consulta no filtrada. Sus seis exclusiones
47855…47860 pertenecen a la categoría nativa 199 (`Synthesis Materials`) y se
conservan como tombstones de armor con rol de catálogo de materiales de
síntesis. Ni el nombre ni la wiki prueban por sí solos el consumidor
conductual de síntesis.

`item_guide_elems` fue recuperada completa: 4.459 filas, 386 guías
referenciadas y 4.459 items distintos. La consulta alimenta relaciones
tipadas `item_to_guide` y `guide_to_item`.

Las tres superficies restantes que antes figuraban como
`native_result_absent` no son resultados perdidos:
`item_smelting_probs`,
`item_grade_enchant_fail_break_reward_categories` e
`item_grade_enchant_fail_break_rewards` pertenecen a la rama secundaria del
loader. La caché observada se ejecutó en modo 0; en ese modo las dos tablas
de rotura retornan antes de emitir SQL y `item_smelting_probs` sólo se carga
en el modo no cero. Se registran como `mode_excluded`. Las probabilidades
reales siguen siendo autoridad del servidor y no se inventan.

El grafo conserva 36.612 destinos item distintos que aparecen en las tablas
de crafts pero no en el catálogo positivo de items. No se descartan ni se
generan: pueden pertenecer a recipes dormidas, eliminadas o no habilitadas y
requieren distinguir su craft habilitado, deshabilitado o tombstone y cerrar
el descriptor nativo que los consume.

`native_entities` y `native_catalogs` alimentan el grafo y la auditoría de la
wiki. No alimentan builders ni promocionan descriptores faltantes.

El inventario completo de SQL/Ghidra se reconstruye de forma determinista:

```powershell
python -B -m reconstruccion_items_8.item_forensics.ghidra_sql_inventory `
  --sql-manifest .\reconstruccion_character_8\generated\client-sql-surfaces-v1-manifest.json `
  --tasks E:\AAEmu-Research\output\aa8-item-forensics\ghidra-all-sql-tasks.tsv `
  --master-dump E:\AAEmu-Research\output\aa8-item-forensics\ghidra-cache-master-loaders.c `
  --loader-dump E:\AAEmu-Research\output\aa8-item-forensics\ghidra-all-sql-loaders-64.txt `
  --sequence E:\AAEmu-Research\output\aa8-item-forensics\ghidra-master-sql-call-sequence.json
```

El resultado actual contiene 977 `SELECT` únicos y 908 llamadas de loader
mapeadas en el cargador maestro. Los artefactos grandes permanecen fuera de
Git y sus hashes se incorporan al manifest.

La verificación focalizada de ciclo de vida cubre seis loaders en ambas
arquitecturas y reconstruye además 55 llamadas SQL del controlador de modo
secundario. Sus tareas declarativas viven en
`config/ghidra-descriptor-lifecycle-tasks.tsv`.

## Cierre de ausencias de descriptor v1.8

Las 109 ausencias físicas de descriptor del catálogo positivo tienen ahora
un ciclo de vida nativo explicado. Esto no crea filas inexistentes ni
confirma por sí solo backend, protocolo, persistencia o aceptación dentro del
cliente.

Para los 26 items `impl_id=27`, el inventario SQL embebido completo y ambos
`x2game.dll` no contienen consultas ni referencias a `item_dyeings` o
`dyeing_colors`. En AA8, `dyeing` es una implementación concreta sin campos
de descriptor propios y utiliza el `use_skill_id` de la fila base:

```text
25 items -> skill 39137
item 43161 -> skill 22727
```

La tabla nativa `dyeable_items` fue recuperada por separado con 292 filas.
Representa equipos objetivo y sus colores, y no intersecta los 26 consumibles
`dyeing`. La ausencia de un descriptor dedicado queda registrada mediante
evidencia negativa reproducible sobre el catálogo SQL y los binarios x86/x64.

`item_accessories` carga 642 filas sin filtro. Los items 45359, 45360 y 45361
son las únicas implementaciones positivas excluidas: conservan metadata de
buff en sus filas base, pero no un descriptor accesorio ni una relación
conductual que permita reconstruirlo. Se clasifican como tombstones
`buff_metadata_only`.

`item_slave_equipments` carga 291 filas sin filtro. Su única exclusión
positiva, item 50121, continúa activa como reactivo del skill 45719 y como
producto del craft 11461. Se clasifica como tombstone
`active_skill_reagent_and_craft_product`, sin inventar un descriptor de
equipamiento de slave.

También se recuperaron las relaciones nativas:

```text
skill_reagents: 2712 filas habilitadas
skill_products: 1097 filas
```

El grafo conserva 3.809 referencias item→skill y 1.678 cierres
skill→item confirmados. Los 2.131 destinos item ausentes permanecen
explícitos como referencias no resueltas; una referencia a skill no equivale
a una definición o conducta de skill confirmada.

El resumen de `descriptor_lifecycle` es:

```text
5228 filas de ciclo de vida
109 ausencias físicas explicadas
 89 con rol alternativo activo
 10 inactivas
 10 conservadas sólo como metadata
  0 sin ciclo de vida concluyente
```

Los once loaders focalizados de esta frontera fueron confirmados en x86 y
x64. La cobertura física por familia sigue mostrando las 109 filas
inexistentes como `missing`; la auditoría de ciclo de vida, en cambio, ya no
contiene ausencias inexplicadas. Esta separación evita confundir
`fila no presente` con `investigación incompleta`.

## Validación

```powershell
python -B -m unittest discover `
  -s reconstruccion_items_8 -t . -p "test*.py" -v

docker run --rm -v "${PWD}:/src" -w /src `
  mcr.microsoft.com/dotnet/sdk:3.1 `
  dotnet test AAEmu.Tests/AAEmu.Tests.csproj
```

Dos ejecuciones completas deben producir el mismo SHA-256 para SQLite. Un
paquete candidato debe superar `verify` y conservar `deployable=false`.

## ArcheRage Wiki corroboration

The scanner starts from the native inventory IDs instead of trusting the
incomplete top-level web indexes. It honors `robots.txt`, requires at least
one second between requests, keeps frozen bodies and hashes for resume, and
does not issue parallel requests:

```powershell
# Missing, unknown, or blocked descriptors first
python -B -m item_forensics scan-wiki --scope unresolved
python -B -m item_forensics audit-wiki

# Complete resumable item inventory
python -B -m item_forensics scan-wiki --scope all

# Concrete closure entities
python -B -m item_forensics scan-wiki --kind quests --id 330
python -B -m item_forensics scan-wiki --kind npcs --id 3597
python -B -m item_forensics scan-wiki --kind doodads --id 14073
python -B -m item_forensics scan-wiki --kind skills --id 48564

# Follow every skill and craft linked by the frozen item pages
python -B -m item_forensics scan-wiki --kind skills --from-audit
python -B -m item_forensics scan-wiki --kind crafts --from-audit
```

Outputs are kept outside Git under `wiki-cache/`,
`aa8-wiki-corroboration.sqlite`, `wiki-audit.json`, and `wiki-audit.csv`.
Every assertion is tagged `authority=false` and
`wiki_archerage_visible`. It can direct a native search but cannot confirm
packets, formulas, probabilities, serializers, persistence, or gameplay.
