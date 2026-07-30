# Checkpoint — núcleo transversal, etapas 00/10 e importación de items

Cliente autoridad: Kakao `8.0.3.12 r558734`.

Clasificación: `client_forensics_only`.

## Resultado

Se creó `reconstruccion_cliente_8/client_forensics` como núcleo transversal
independiente de AAEmu. El pipeline no lee `COMPACT_DB`, no modifica compacts
runtime y no ejecuta Docker, MySQL ni servicios del servidor.

El entregable migra toda la evidencia de las 21 tablas de
`aa8-item-forensics.sqlite` hacia bases por etapa y proyecta sus identidades,
propiedades y relaciones al esquema canónico.

## Etapas

### Etapa 00

`stage-00-artifacts.sqlite`

- 48 artefactos: 45 registros históricos y tres fuentes de linaje.
- 9.978 superficies revisadas.
- 126 agregados de inventario.
- 59 manifests de revisiones previas.
- 9.978 entidades `surface`.
- 49.890 propiedades.

### Etapa 10

`stage-10-native-data.sqlite`

- 130 consultas.
- 130 resultados cacheados.
- 439.693 filas cacheadas.
- 25 catálogos nativos.
- 106.366 filas de entidades nativas.
- 82.079 entidades únicas.
- 425.464 propiedades tipadas.
- 76 consumers/loaders asociados a consultas.

### Etapa 20

`stage-20-items.sqlite`

- 21.419 items positivos confirmados.
- 21.419 descriptores conservados.
- 5.228 estados lifecycle conservados.
- 331.389 relaciones nativas importadas.
- 95.251 referencias de superficies importadas como evidencia no autoritativa.
- 21.419 relaciones derivadas `item -> has_descriptor`.
- 152.237 entidades.
- 1.698.983 propiedades.
- 448.059 relaciones.
- 98.006 gaps.
- 172.170 observaciones de cobertura, aisladas como `server_observed`.
- 6 regiones opacas.

### Consolidada

`aa8-client-knowledge.sqlite`

- 158.920 entidades.
- 2.174.337 propiedades.
- 448.059 relaciones.
- 439.693 filas cacheadas.
- 106.366 filas nativas.
- 21 tablas fuente con conteos preservados.
- 3 etapas registradas en `stage_lineage`.
- cero propiedades o relaciones huérfanas.

## Determinismo

Dos ejecuciones completas consecutivas produjeron los mismos hashes:

```text
stage-00-artifacts.sqlite
475E5A2B8080F867787EFFA3272B8ED783587D940D879D1517CDB4224A6D29E9

stage-10-native-data.sqlite
4D72CBA88AC0B2F71E6003D1B4C8239D8E1A33D00FF09C7623EA8BEF8C0AAF83

stage-20-items.sqlite
9AC29730D30A16C573AD1FCD66823767DB016E95F55B6A4B7D215994D0E08492

aa8-client-knowledge.sqlite
606897290A79C6488BFBA52B71D2FBAE1CEA7075B4F8238F6EEA0AB8546F7258

manifest.json
D0A4DB740594DE07B149DCBF41C1634CDB57FF81C468C0757C36A3E124595AEF
```

Todas las bases cumplen:

```text
PRAGMA quick_check=ok
PRAGMA integrity_check=ok
```

## Semántica de autoridad

- Datos nativos: `client_native`.
- Endpoints todavía sin catálogo: `client_reference`.
- Resultados de comparación con AAEmu: `server_observed`.
- Referencias numéricas de scripts/XML/assets: `client_reference`.
- Regiones sin descifrar: `opaque`.

La cobertura de servidor heredada se conserva para trazabilidad, pero no
promueve propiedades o relaciones a autoridad cliente.

## Próxima frontera

Construir la etapa 30:

```text
npc
-> template/model
-> face/hair/equipment
-> skills/buffs
-> faction/ai/spawn
-> doodads/quests
```

La etapa debe reutilizar los inventarios y extractos existentes, importar sus
entidades al mismo esquema y registrar como opaco cualquier layout o consumer
todavía no resuelto.
