# Checkpoint V3: corpus nativo estático cerrado e integrado

Fecha de cierre: 2026-07-31

Cliente fijado: Kakao `8.0.3.12 r558734`

## Resultado

La frontera estática del corpus nativo quedó cerrada, reproducible, validada e
integrada lateralmente al grafo forense principal.

El pseudocódigo, instrucciones, tipos, llamadas y votos por motor permanecen
exclusivamente en:

`E:\AAEmu-Research\output\aa8-native-code\stage-15-native-code.sqlite`

La consolidada incorpora el linaje, los artefactos, la cobertura, las regiones
opacas y los enlaces `consumer -> function_key`, sin duplicar los 15,27 GiB de
pseudocódigo:

`E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite`

No se modificó AAEmu, `.env`, MySQL, compact runtime ni Docker. No se analizó,
ejecutó o instrumentó anticheat y no se utilizó red pública.

## Estado de ejecuciones

- Reko x86 y x64: `confirmed`; no hay procesos activos.
- Ghidra: 55 ejecuciones `confirmed`.
- Rizin: 53 ejecuciones `confirmed`.
- angr: 2 ejecuciones `confirmed`.
- rev.ng: 2 ejecuciones `failed`, agrupadas como fallos globales reproducibles.
- Cobertura requerida: 110/110 ejecuciones terminales:
  108 `confirmed` y 2 `failed`.
- Manifiestos pendientes: 0.
- Stage 15: `confirmed`, 100 %, no stale.

Las cuatro tandas declarativas terminaron con Ghidra y Rizin:

| Tanda | Ejecuciones | Terminales | Estado |
|---|---:|---:|---|
| `gameplay-1` | 26 | 26 | confirmed |
| `engine-core-2` | 16 | 16 | confirmed |
| `xl-support-3` | 20 | 20 | confirmed |
| `presentation-4` | 32 | 32 | confirmed |

## Stage 15 canónico

- Tamaño: `16.398.442.496` bytes.
- SHA-256:
  `8A6BD3CED8AB3275614F94CD09A727E45E542F1FFCB1BB7044BB291DBB18F838`.
- 202 binarios.
- 387.437 funciones.
- 114 ejecuciones de motor.
- 1.316.514 resultados/estados de decompilación.
- 21.215.286 instrucciones.
- 3.462.990 bloques básicos.
- 1.087.833 llamadas.
- 1.388.972 referencias de datos.
- 597.512 nombres con procedencia.
- 133.940 strings y 182.866 asociaciones función/string.
- 7.569 tipos y 51.392 campos.
- 4.306 vtables y 225.424 slots.
- 3.410 evidencias de equivalencia x86/x64.
- 6.702 entradas accionables o agrupadas en la cola de revisión.
- 50.011 regiones opacas ejecutables, todas enumeradas.
- 60 enlaces nativos a 60 consumers y 50 funciones.
- 0 ejecuciones dinámicas registradas.

Validación:

- `PRAGMA quick_check = ok`.
- `PRAGMA integrity_check = ok`.
- 0 violaciones de claves foráneas.
- 0 secciones ejecutables con partición incompleta.
- 0 resultados obligatorios ausentes.
- 0 ejecuciones sobre anticheat.

## Barrera de determinismo

Dos construcciones limpias consecutivas con el código final produjeron:

```text
SQLite SHA-256:
8A6BD3CED8AB3275614F94CD09A727E45E542F1FFCB1BB7044BB291DBB18F838

Manifest SHA-256:
66BC40D332A307D79AA5AA75D4A81E6C780E49DCFDC8F131513DF592EDA5F80B
```

Reporte:

`E:\AAEmu-Research\output\aa8-native-code\stage-15-determinism-v3.json`

SHA-256:
`45416D32680C0D58108660092123BC5FEE8AE18177692F08EB3DD1081D1965A2`.

La copia preservada de la segunda construcción limpia conserva el mismo SHA:

`E:\AAEmu-Research\output\aa8-native-code\stage-15-native-code.determinism-run-2.sqlite`

## Equivalencias x86/x64

Artefacto:

`E:\AAEmu-Research\output\aa8-native-code\diff-native-architectures.json`

SHA-256:
`31C83743088CCD3D989BDC2EFFAB4396612EAF3F6878433FD7002D7D4A8A27D2`.

Resultado:

- 3.410 evidencias.
- 3.386 pares únicos.
- 22 `confirmed`.
- 3.304 `corroborated`.
- 84 evidencias `candidate`.
- 0 `ambiguous`.
- 0 pares de la misma arquitectura.
- 0 claves duplicadas.
- 0 evidencias JSON inválidas.

Las 42 decisiones del overlay siguen conservadas como revisión explícita; no
propagan nombres candidatos automáticamente.

## Dossiers dorados y chat

- 50 dossiers únicos: 25 x86 y 25 x64.
- 50 JSON y 50 HTML.
- 0 archivos ausentes.
- 0 hashes o identidades discordantes.

Manifest:

`E:\AAEmu-Research\output\aa8-native-code\dossiers\golden-anchors-v3.manifest.json`

SHA-256:
`EB38E9999BA96ABFDEACDEFA739543B2E1E14BA24BA3A2F5F7C55D2D6A39A33B`.

El par `chat_bubble_kind` quedó concluido:

- x64 RVA `0x006EC170`;
- x86 RVA `0x000F7AA0`;
- nombre semántico corroborado:
  `X2.Chat.DispatchChatBubbleByKind`;
- equivalencia confirmada por alcance forense compartido;
- ambas funciones realizan dispatch virtual calculado, por lo que cero llamadas
  directas recuperadas es el resultado esperado;
- x86 conserva una región `opaque_critical` explícita de 24 bytes en
  `0x00FA1A18..0x00FA1A30`.

Conclusión JSON:

`E:\AAEmu-Research\output\aa8-native-code\dossiers\chat-bubble-kind-conclusion-v3.json`

SHA-256:
`084AD04574E15AD783F6C9BBAA9D28055AD47F910FBC8E40DF7E4C22C0E514ED`.

## Cola de revisión

La cola final de 6.702 filas se distribuye en:

- 6.586 desacuerdos de límites de función;
- 48 fallos de decompilador accionables;
- 42 revisiones de equivalencia;
- 26 regiones opacas conectadas con funciones críticas.

Los fallos masivos de rev.ng quedaron agrupados por ejecución y causa, sin
eliminar el estado individual por función. No se revisarán manualmente regiones
opacas sin consumer o impacto demostrado.

## Integración en la consolidada

La consolidada final usa schema 3 y herramienta `0.34.0`.

- Tamaño: `8.454.717.440` bytes.
- SHA-256:
  `46AAE6B02D2A51E2D11D62615FBEABE10A9C85C01A9700385C8C8245BE32AA5D`.
- Manifest de etapa SHA-256:
  `FEBB6B22D2C589361AFB4910F936DFE1ECC30F2BB40CB975506E501E68F84E6A`.
- Manifest global SHA-256:
  `4C556F5EE653F19BFB9ACC0D112C795FECE300FE720A79E941DE7CE30087C277`.
- 10 etapas de linaje.
- Stage 15 apunta a `stage:15` y conserva exactamente el SHA canónico.
- 1.024 artefactos.
- 691.231 filas de cobertura.
- 50.102 regiones opacas históricas; 50.101 activas.
- 60 enlaces `native_code_evidence_links`.
- 0 enlaces con consumer huérfano.

Validación independiente:

- `quick_check = ok`;
- `integrity_check = ok`;
- 0 propiedades, relaciones, cached rows, wiki, blockers, work queue o enlaces
  nativos huérfanos;
- 31 tablas;
- 10 filas de linaje.

El manifest global enumera Stage 15 con su ruta externa y SHA. Las
exportaciones `opaque-regions.json`, `coverage-summary.csv` y el visor se
regeneraron desde esta consolidada.

## Implementación y pruebas

- Nueva tabla lateral `native_code_evidence_links`.
- Cada enlace materializa `consumer_key`, `function_key`, scope, locator,
  estado, procedencia y evidencia.
- La consolidación rechaza Stage 15 si build, SHA, integridad o política de
  anticheat no coinciden con el manifest.
- La validación exige linaje `{0,10,15,20,30,40,50,60,70,90}` y que Stage 15
  apunte a `stage:15`.
- 43/43 pruebas del grafo aprobadas.
- 24/24 pruebas del corpus nativo aprobadas.
- Validación independiente de Stage 15 y consolidada aprobada.

## Próxima frontera

La frontera estática declarada quedó cerrada. La siguiente acción es evidencia
dinámica aislada y dirigida:

1. crear/verificar una copia separada por hashes;
2. mantener red pública ausente y anticheat sin iniciar;
3. registrar escenarios pequeños: inicio, selección de personaje, carga de
   mundo, NPC, quest, item y skill;
4. mapear cada hit a módulo + RVA + `function_key`;
5. priorizar las 26 regiones `opaque_critical` y funciones críticas realmente
   ejecutadas;
6. conservar trazas grandes únicamente en `E:\AAEmu-Research`.

Esta fase agregará evidencia de qué rutas se ejecutan; no vuelve a decompilar
el cliente ni convierte inferencias en autoridad nativa.
