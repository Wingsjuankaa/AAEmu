# Checkpoint V1: triage semántico nativo global

Fecha de cierre: 2026-07-31

Cliente fijado: Kakao `8.0.3.12 r558734`

## Resultado

Se insertó una fase semántica reproducible entre Stage 15 y cualquier captura
dinámica. No se volvió a ejecutar ningún decompilador y no se modificó Stage
15. El índice lateral clasifica el corpus completo, conserva los caminos desde
cada raíz y separa impacto de incertidumbre sin elevar strings o pseudocódigo
a autoridad nativa.

No se modificó AAEmu, `.env`, MySQL, compact runtime ni Docker. No se analizó,
ejecutó o instrumentó anticheat y no se utilizó red pública.

## Índice lateral canónico

```text
path: E:\AAEmu-Research\output\aa8-native-code\native-semantic-index.sqlite
bytes: 599.638.016
SHA-256: 0E5E05EBB64258322899D2C736AE48557D2DD8406233B12FB0CF6FB9751006F2
manifest SHA-256: 4293ADC1D70B6C75FDA4E04D92884662FBC43FB0CED2C62189B8E7C1A27E361C
schema: AA8_NATIVE_SEMANTIC_INDEX_V1 / 1
builder: aa8-client-forensics 0.35.0
```

Linaje obligatorio:

- Stage 15 SHA-256:
  `8A6BD3CED8AB3275614F94CD09A727E45E542F1FFCB1BB7044BB291DBB18F838`;
- manifest Stage 15 SHA-256:
  `66BC40D332A307D79AA5AA75D4A81E6C780E49DCFDC8F131513DF592EDA5F80B`;
- proyección estable de `consumers`, `query_specs` y `blocker_roots`:
  `F39F35A019A4AEA455704B6CF913E8E723C058E5A7B2590089E825431B3AA2B0`.

La proyección evita un ciclo de hashes: integrar los resúmenes semánticos en
la consolidada no cambia las tres superficies fuente usadas por el índice.

## Cobertura global

- 2.944 raíces semánticas.
- 477.308 enlaces raíz → función con dirección, profundidad, impacto y estado.
- 2.944 cierres y 2.944 entradas de cola estable.
- 387.437/387.437 funciones clasificadas.
- 50.011/50.011 regiones opacas clasificadas.
- 17.972 razones de incertidumbre.
- 57.217 sitios de llamada indirecta candidatos; ninguno se promueve a target
  confirmado sin evidencia adicional.
- 0 funciones críticas sin raíz/camino.
- 0 enlaces huérfanos.

Clasificación de funciones:

| Categoría | Funciones |
|---|---:|
| `critical_root` | 3.038 |
| `critical_reachable` | 6.447 |
| `support_reachable` | 11.112 |
| `candidate_signal` | 1.916 |
| `unlinked` | 181.428 |
| `external_or_not_backend_relevant` | 183.496 |

Esto clasifica el 100 % del corpus, pero no afirma que cada función haya sido
comprendida manualmente.

## Consumers y SQL

Los 132 consumers quedaron clasificados:

- 60 enlaces de Stage 15 preservados;
- 63 locators con una función única;
- 3 locators con un par x86/x64 explícito y no ambiguo;
- 6 locators con coincidencia x86/x64 candidata.

Por tanto, los 72 consumers antes pendientes se dividen en 66 resoluciones
exactas/no ambiguas y 6 candidatas, sin ausencias.

Los 662 query specs con SQL quedaron clasificados por igualdad exacta después
de normalizar whitespace, mayúsculas/minúsculas y `;` final:

- 17 con función única;
- 627 con varias funciones/arquitecturas;
- 18 sin función asociada.

Los enlaces SQL son `corroborated`; la coincidencia textual por sí sola nunca
produce `confirmed`.

## Regiones opacas

| Clasificación | Regiones |
|---|---:|
| `critical_blocker` | 1.334 |
| `reachable_context` | 325 |
| `unlinked_no_demonstrated_impact` | 48.352 |

La expansión se basa en calls o referencias de datos desde funciones
alcanzables. Las 48.352 regiones sin impacto demostrado no entran a revisión
manual por defecto.

## Cola y primera tanda

Estados de los 2.944 cierres:

| Estado | Raíces |
|---|---:|
| `understood` | 67 |
| `blocked_by_indirect_dispatch` | 260 |
| `blocked_by_opaque_region` | 606 |
| `blocked_by_missing_native_data` | 102 |
| `not_backend_relevant` | 2 |
| `pending_review` | 1.907 |

La primera tanda contiene 25 dossiers terminales: 17 bloqueados por región
opaca y 8 por dispatch indirecto. Sus tres primeras investigaciones son:

1. `loot_pack`, bloqueada por región opaca;
2. una raíz de protocolo con nombre nativo estructurado, bloqueada por región
   opaca;
3. un consumer de item/loot, bloqueado por dispatch indirecto.

Los 25 JSON autocontenidos viven en:

`E:\AAEmu-Research\output\aa8-native-code\semantic-dossiers`

Cada dossier conserva el SHA del índice, raíz, camino, evidencia, strings,
nombres, indirect calls, regiones opacas y conclusión explícita. Se limita a
250 funciones visibles y declara truncamiento cuando corresponde.

## Barrera de determinismo

Una construcción antes de integrar la consolidada y otra después produjeron
exactamente el mismo archivo:

```text
bytes: 599.638.016
SHA-256: 0E5E05EBB64258322899D2C736AE48557D2DD8406233B12FB0CF6FB9751006F2
```

Ambas usaron el mismo Stage 15 y la misma proyección semántica. Esto confirma
además que la integración no crea un ciclo de regeneración.

Validación independiente:

- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- 0 violaciones de claves foráneas;
- 0 eventos de validación fallidos;
- 0 funciones críticas sin camino;
- 0 referencias huérfanas.

## Integración consolidada

La consolidada final usa schema 4 y herramienta `0.35.0`:

```text
path: E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite
bytes: 8.843.673.600
SHA-256: 52D62872E8DD4DB05E569CECB4C99D5B88566B78559DCC8E0BF5416C14AD1224
manifest de etapa SHA-256: FBE83BDA3DCB75655AC22B6EFBFCD345519FD1FF33D4A882F05F647F8C848A1C
manifest global SHA-256: B4A1888E60F5F728DA36814255F46D9FC6B3BCF572AA73AD4785743A7794CF8B
```

Materializa sólo resúmenes consultables:

- 2.944 raíces;
- 387.437 estados de función;
- 477.308 enlaces sin copiar caminos JSON;
- 50.011 estados de región opaca;
- 2.944 entradas de cola.

El pseudocódigo y los caminos completos permanecen en sus sidecars. La
consolidada conserva 10 etapas de linaje, 60 enlaces nativos originales y 0
huérfanos semánticos.

## Interfaces y visor

Se añadieron:

```text
build-native-semantic-index [--resume]
validate-native-semantic-index
native-semantic-status [--domain <id>] [--tier <id>]
export-native-closure <root-kind> <root-key>
```

`run-all` valida y consume el índice; no lo reconstruye. El visor de código
nativo adjunta el sidecar y permite filtrar por dominio, impacto,
incertidumbre, raíz crítica, opacidad bloqueante, dispatch indirecto y estado
del cierre.

## Pruebas

- 76/76 pruebas aprobadas.
- Cobertura nueva para normalización SQL, VA/RVA, locators múltiples, selección
  de dominio/tier y call graph con ciclos, profundidad y truncamiento.
- Construcción real y validación de todos los conteos canónicos.
- Cero ejecución de decompiladores.
- Cero anticheat y cero red pública.

## Próxima acción segura

No corresponde revisar las 48.352 regiones opacas sin impacto demostrado. La
continuación es revisar la primera tanda por prioridad y preparar evidencia
dinámica únicamente para una raíz cuyo bloqueo dependa de conducta en
ejecución. La captura deberá usar una copia aislada, servicios locales, red
pública ausente y anticheat no iniciado.

