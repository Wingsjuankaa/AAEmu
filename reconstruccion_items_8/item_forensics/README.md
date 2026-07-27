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
  regiones opacas y referencias de superficies.
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

## Catálogos de dependencias v1.6

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

La clausura de conversión demostró que los items 31789…31808 son reactivos
de las conversiones 440…442 y producen 40091…40093. El barrido exhaustivo
también recuperó `tagged_items`: los seis items 47855…47860 y el diseño 35945
tienen metadatos nativos, pero un tag no prueba su descriptor ni un consumidor
conductual. Por eso se clasifican como
`native_metadata_confirmed_consumer_unresolved`, no como completos.

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
