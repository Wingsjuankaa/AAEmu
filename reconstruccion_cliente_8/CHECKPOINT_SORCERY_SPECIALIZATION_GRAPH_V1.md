# Checkpoint forense Sorcery: grafo independiente V1

Fecha: 2026-08-05  
Cliente autoridad: ArcheAge Kakao `8.0.3.12 r558734`  
Especialización: Sorcery (`ability_id=7`)

## Resultado

Se construyó un grafo forense independiente desde Stage 50/60/70/90, la
consolidada AA8 y el catálogo nativo. No usa el runtime del servidor para
decidir qué es una fila AA8 ni permite que la wiki o 10.x creen membresía
nativa.

- 40 raíces skill nativas AA8 y 6 pasivas.
- 10 de las 40 filas tienen `show=1`; la visibilidad no se interpreta como
  disponibilidad ni reemplaza la evidencia de protocolo.
- 4.218 filas en clausuras y 4.763 aristas.
- 154 pasos de efecto, 85 contratos de buff, 444 condiciones y 522 outcomes.
- 331 bindings de presentación.
- 360 casos de reconstrucción: 322 `confirmed`, 38 `not_applicable`.
- cero filas de clausura sin clasificar, cero gaps y 40/40 estados downstream
  `enabled`.
- `quick_check=ok`, `integrity_check=ok` y cinco eventos de validación
  confirmados.

## Hallazgo de cobertura

La comparación contra la auditoría ejecutable V3 detectó que su versión
anterior sólo enumeraba las 24 raíces públicas. Faltaban como entrypoints
independientes, aunque sus datos y backend ya existían:

- login-stage: `12789`, `12790`, `12791`;
- contexto Magic Circle: `42012`, `43464`, `43465`.

La auditoría V3 ahora parte de 30 entrypoints: 12 base, 12 Heir, 3 login-stage
y 3 contextuales. Su cierre contiene 43 skills y cubre las 40 raíces nativas
del grafo.

Los tres IDs adicionales quedan clasificados sin promoción silenciosa:

- `10151` y `10153`: candidatos parent tombstone confirmados por protocolo
  AA8 y presentes en el runtime; el grafo no contiene una fila raíz AA8 y el
  crosswalk los clasifica `aa10_only`. Sus propiedades candidatas no se
  convierten en autoridad AA8.
- `15317`: hija interna AA8 exacta con `ability_id=0`, alcanzada por el cierre
  dirigido de Meteor; no es una raíz de Sorcery.

La reconciliación reproducible es
`../reconstruccion_skills_8/sorcery/generated/sorcery-forensic-runtime-reconciliation-v1.json`.

## Corrección de estado downstream

El catálogo todavía declaraba `ResetAoeDiminishingEffect` y
`ExtendChargeEffect` como semántica pendiente. Esa lista había quedado
obsoleta respecto del servidor actual: el primero reinicia el contador del
`PlotCast` y el segundo implementa el contrato AA8 de Insulating Lens. Se
regeneró el catálogo desde `game11` y el compact AA8; Sorcery pasó de 36/40 a
40/40 `enabled` sin modificar ninguna fila de balance.

## Artefactos congelados

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| `sorcery-specialization-graph-v1.sqlite3` | 5.562.368 | `540E0AE0C5660719060E03A7B8D924FDDF63F045F3E931E4F80431464B494EF7` |
| `sorcery-specialization-graph-v1.manifest.json` | 4.745 | `EE9047529F3421CCF8C5B99D9FCE03A5C40ADF95326A537662DAD74EDC90B1C2` |
| `sorcery-specialization-summary.json` | 1.001 | `CF709C5192EB8B6691D92F06214464E08E6ECC5E5324F8598C192D52A3804254` |
| `sorcery-specialization-test-matrix.csv` | 66.276 | `74C93F6CA586E8C7D5D0429F4D3A22A459576E674CE246917A204B7BD61AE64B` |
| `sorcery-specialization-gaps.csv` | 105 | `0E8BCB11D185210C1870013A3F5040DDFF8EB2D74D90CA76973F000792283F1C` |
| `native-combat-catalog-v1.json` | 67.899.848 | `EEDCAC18F504D3557DDE46A4315EB88329CD5D73059EBD99B5840648AECCD3AE` |
| `sorcery-executable-semantics-audit-v3.json` | 294.142 | `F8652AE0941A8A2C27CB2DECF3B4A4907C8D97E3C983E0EA24BAF7CE5FADDF60` |
| `sorcery-forensic-runtime-reconciliation-v1.json` | 12.736 | `8EA1184754FF7B0BB4C0FE69BBF361CDABE02C76EE06B2D4785F2D96A541F47F` |

## Integración canónica reproducible

La incorporación de los snapshots tipados de Sorcery al corpus wiki cambió
de forma legítima Stage 70 y, por linaje, Stage 90, el índice semántico y la
consolidada. No se importaron filas 10.x ni se alteró balance AA8.

| Artefacto canónico | Bytes | SHA-256 |
|---|---:|---|
| Stage 70 | 271.962.112 | `5FA87F3512B0C09DC54470E88BF53CC24EB0DBFF8B69091DB4DCDE99DA107488` |
| manifest Stage 70 | — | `69083130718153387537EF1D3B5628C08E82E7234B864FD6F6AB31755E88269F` |
| Stage 90 | 295.059.456 | `E76BCE018C6DECAA9712E86F4BC32862F395C5D37B69822E910A377184EE8932` |
| manifest Stage 90 | — | `AD240912A00924F9073E69D8D20EF5F5ECE3BC1C94A5F3C30FCAF72721B9D1E9` |
| índice semántico nativo | 599.400.448 | `A3C635159666F5CCEC43EF8EBC8F05243D2DC7930EB6A36E5C55D851821784B7` |
| manifest semántico | — | `7AA3E38A30BC8FF2BA66F21FFF42F312C0428719587DA235ADA2F94818057AEA` |
| consolidada AA8 | 8.909.357.056 | `A3AB85F0F033407845651AD9277EFBBB4E772A1A8FCD20D973C2DCB5A3848559` |
| manifest local consolidada | — | `FA03DD9846A4A1CF76D0E5DA7B9D2E5F87541326228217E3050C2C7384B33127` |
| manifest global | — | `7036A75423CC495BBD826CF09F058D554CEB8327E2987C42A4698A793336A2CD` |

Cada artefacto se construyó dos veces con resultado byte a byte idéntico.
Los validadores oficiales confirmaron 392 raíces Stage 90, 2.946 raíces
semánticas, cero huérfanos, `quick_check=ok` e `integrity_check=ok`.

## Gate conductual

La evidencia estática y automatizada queda cerrada. La certificación visual y
conductual continúa en `SORCERY_LIVE_ACCEPTANCE_PROTOCOL_V2.md`, incluyendo
ahora los tres retornos de Magic Circle. Las skills login-stage se validan en
la presentación de acceso/creación y no se fuerzan como botones del mundo.
