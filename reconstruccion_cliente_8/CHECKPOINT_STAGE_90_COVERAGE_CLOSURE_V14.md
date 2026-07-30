# Checkpoint V14: identidad y lifecycle nativo de endpoints item

## Alcance

Este checkpoint reconcilia todos los endpoints `item` positivos alcanzados por
relaciones nativas tipadas de Stage 20, Stage 40 y Stage 50 contra el catálogo
nativo completo de `items` del cliente Kakao 8.0.3.12 r558734.

El trabajo es exclusivamente forense. No crea objetos, no implementa
mecánicas, no modifica AAEmu, compact, MySQL ni runtime y no usa wiki o datos
históricos como autoridad.

## Corrección de la frontera V13

Las dos raíces informadas en V13 no eran conjuntos disjuntos:

```text
referenced_endpoint_not_in_decoded_stages: 278 IDs
referenced_endpoint_not_in_prior_stages:  2.289 IDs
intersección:                                  58 IDs
unión real:                                 2.509 IDs
```

De igual forma, 22.257 era la suma del fan-out de ambas raíces. Después de
deduplicar había 18.297 relaciones únicas. La cola permitía descubrir el
problema, pero no describía toda su extensión.

## Autoridad y regla de lifecycle

La autoridad propietaria es la consulta 117:

```sql
SELECT ... FROM items
```

No contiene `WHERE`, filtros de estado ni joins. Su resultado nativo:

- ocupa los offsets `80.917.979..89.076.696`;
- contiene 21.420 filas;
- contiene exactamente 21.419 IDs positivos activos;
- conserva una fila no positiva como anomalía, sin promoverla a objeto;
- tiene digest de filas
  `DA4461BAFED151DB8DF33062068A7D44C1DC107F336BC29880F2E68C597D9909`.

Por tanto:

- un ID positivo presente en ese resultado queda `confirmed/present`;
- un ID positivo alcanzado por una relación nativa exacta pero ausente de ese
  resultado queda `tombstone/tombstone`;
- la relación nativa queda `confirmed` aunque el destino sea tombstone;
- `item:0`, relaciones heurísticas, wiki, assets y servidor quedan fuera de
  esta clasificación.

La ausencia se usa como evidencia únicamente porque el catálogo propietario
está completo y sin filtros. No se generaliza esta regla a consultas parciales.

## Barrido transversal

La misma anomalía existía mucho más allá de las dos raíces de V13:

| Stage | Relaciones nativas no resueltas iniciales | Endpoints positivos ausentes |
|---|---:|---:|
| Stage 20 | 66.924 | 14.698 |
| Stage 40 | 4.779 | 2.290 |
| Stage 50 | 356 | 280 |

La unión contiene 16.139 IDs ausentes únicos. Se cerraron 72.045 relaciones a
tombstones y 14 relaciones a tres IDs activos, para un total de 72.059
relaciones nativas confirmadas.

El procesamiento es secuencial y conserva la autoridad más fuerte:

- Stage 20 materializa 14.698 tombstones y confirma 66.924 relaciones.
- Stage 40 clasifica 2.293 endpoints locales: tres presentes y 2.290
  tombstones; confirma 4.779 relaciones. Otros 942 gaps ya llegan resueltos
  desde Stage 20 y 1.350 quedan superseded localmente.
- Stage 50 recibe la evidencia de Stage 20/40. De sus 280 endpoints y 356
  relaciones iniciales, sólo 102 IDs y 103 relaciones requieren materialización
  local; 178 IDs y 253 relaciones ya llegan fuertes. Se superseden 102 gaps.

Se preservan 1.452 gaps reemplazados como `source_records` auditables, no se
elimina su historia.

## Estado consolidado de items

Entidades:

| Estado/lifecycle | Cantidad |
|---|---:|
| `confirmed/present` | 21.419 |
| `tombstone/tombstone` | 16.153 |
| `confirmed/referenced` | 196 |
| `unknown/referenced` | 121 |
| `unknown/unknown` | 77 |
| `missing/unknown` | 1 |

Los 16.153 tombstones incluyen los 16.139 de esta reconciliación y 14
tombstones ya demostrados por fronteras anteriores.

Relaciones cuyo destino es `item`:

| Estado | Cantidad |
|---|---:|
| `confirmed` | 149.431 |
| `tombstone` | 1.067 |
| `unknown` | 95.251 |
| `missing` | 96 |

Los estados `tombstone` heredados en relaciones pertenecen a semánticas
anteriores. En esta frontera el lifecycle del destino y la existencia de la
arista se modelan por separado: una referencia nativa sobreviviente es
`confirmed`.

Ya no quedan raíces `referenced_endpoint_not_in_decoded_stages` ni
`referenced_endpoint_not_in_prior_stages` para `item`. Las raíces/cola totales
bajan de 436 a 432.

Los blockers nativos de item que permanecen son distintos y explícitos:

- 121 entidades `unknown/referenced`, con fan-out entrante 765;
- el sentinel `item:0`, con 96 relaciones `missing`;
- 77 entidades `unknown/unknown` sin fan-out;
- raíces de assets, wiki y consultas opacas que no autorizan lifecycle.

## Cobertura consolidada

La consolidada contiene 596.106 filas de cobertura:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 362.234 | 60,7667% |
| `corroborated` | 39.424 | 6,6136% |
| `tombstone` | 35.149 | 5,8964% |
| `not_applicable` | 13.416 | 2,2506% |
| `unknown` | 141.992 | 23,8199% |
| `missing` | 3.881 | 0,6511% |
| `blocked` | 10 | 0,0017% |

Estos porcentajes describen filas de evidencia/capacidad, no un porcentaje
único del cliente completo.

Los gaps activos bajan de 114.313 a 111.739. La reducción de 2.574 incluye
propagación entre stages y supersesión local; no debe confundirse con el total
de relaciones cerradas.

## Implementación

- `client_forensics/item_endpoint_lifecycle.py`
  - valida la consulta y resultado propietario completo;
  - clasifica presencia/tombstone sólo para relaciones nativas tipadas;
  - conserva estado previo, procedencia, evidencia y gaps superseded;
  - materializa propiedad, cobertura, catálogo y evento de validación;
  - impone conteos y digests deterministas por stage.
- `client_forensics/build.py`
  - ejecuta la reconciliación en Stage 20, 40 y 50;
  - propaga entidades fuertes de Stage 20 durante consolidación;
  - verifica los 21.419 items activos y ausencia de conflictos de ownership.
- `client_forensics/tests/test_core.py`
  - prueba fixtures de endpoints presentes y tombstone;
  - verifica relaciones confirmadas y retiro auditable de gaps.
- versión de herramienta: `0.21.0`.

Digests de endpoints por stage:

| Stage | SHA-256 |
|---|---|
| Stage 20 | `9319F671C1B797DBE7B835EDF2323ABE3CCE33A98A8220EBBFE53B1D971646B0` |
| Stage 40 | `4DD6F79FB42F24AB48649ECB3F81866B6FCD3982B2D2D7928CE657C4DFF8D265` |
| Stage 50 | `11C7376187B205441D2A518867E8E13EB783B4F0712B61DF91872A753B6FF1BF` |

## Validación

- 27/27 pruebas Python aprobadas.
- Dos builds byte a byte idénticos de Stage 20, 40, 50 y Stage 90.
- Dos consolidaciones explícitas byte a byte idénticas.
- `quick_check=ok` e `integrity_check=ok` en todos los stages afectados y la
  consolidada.
- Cero propiedades, relaciones, cached results, cached rows, blocker impacts o
  entradas de cola huérfanas.

Conteos principales de la consolidada:

- 1.657.484 entidades;
- 6.967.585 propiedades;
- 2.113.623 relaciones;
- 596.106 filas de cobertura;
- 111.739 gaps activos;
- 89 regiones opacas;
- 432 raíces causales y 432 entradas de cola.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-20-items.sqlite` | `DCAFF479F267F2FCFD43952D10E22C66BE624C4F133B2DD94069FECBF7A76E58` |
| `stage-20-items.manifest.json` | `8E08BC71CAC88E51FC189E0F9DAE433C1390E1EFF1E22FF86BC4C6BFF02591EC` |
| `stage-40-quests.sqlite` | `5464BFE81C42BAFF0DF229EC0E5A5FCF949F9A72D77E67CAAB58B335F20749A9` |
| `stage-40-quests.manifest.json` | `DAE2B4E23A499F7E7E4DDA853858AE153EF700AF2ECBEDBE6C584AB633B3EB1A` |
| `stage-50-skills.sqlite` | `3A4E0604EFBDB03DF64868309B26AE7210DC41C420D768DB286C798CF34DC70E` |
| `stage-50-skills.manifest.json` | `55B5CA20C0E57B76B0FF8A45C62166C4637509F0D22742C331133096AB48EDB8` |
| `stage-90-coverage-closure.sqlite` | `F9ECD8A8A3FE01CE21DFEE96FA9DEF208455AC26AD7FF0C00DBC62434F2D0A87` |
| `stage-90-coverage-closure.manifest.json` | `771E666AC2EDF8358DE7EDC125E55DB8B5942FF06201645DFE4B731BA1930D7E` |
| `aa8-client-knowledge.sqlite` | `CE873FE8592D6ABBCA695B3C90BDDA9F788C4FAF5AC7931EB4E5A114D3186CEB` |
| `aa8-client-knowledge.manifest.json` | `31B9EDD00AF0945B85C5D7FB0171464AB780BDCA727303560E81304A47839281` |
| manifest final | `CCF52AA1075809E3E7C41BE278EE91321130F36F3C6FD3D207F07D32EBF52E82` |
| cola CSV | `E3DDFFAA49E97E4D7E0861B3103C752430D832FD998C9DBE1541C28178D6DDF5` |
| visor de cobertura | `06389ACC9321938356410568589C950F205CA4460AEA3AAE66F1F071B3B06D83` |

## Siguiente frontera recomendada

`loot_pack` sigue agotada sin una autoridad nueva. La siguiente frontera útil
es reconciliar identidad y lifecycle de endpoints `skill`.

Existe una consulta nativa completa y sin filtros `SELECT ... FROM skills`,
pero el grafo consolidado todavía contiene:

- 1.577 endpoints en `referenced_endpoint_not_in_decoded_stages`;
- 20.730 referencias entrantes en esa raíz;
- 1.523 skills `unknown/referenced`;
- 34 skills `unknown/present`;
- 26 sentinels o referencias `missing`;
- 652 entidades `localization_only`.

Antes de promover estados se debe repetir el barrido transversal de V14:
deduplicar raíces, separar relaciones nativas exactas de heurísticas y
corroboración, demostrar que el resultado `skills` es realmente propietario y
total, y propagar la autoridad entre stages sin ocultar gaps. El objetivo no es
copiar la lógica de items, sino aplicar el mismo estándar probatorio.
