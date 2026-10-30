# Evidencia y modelo relacional AA10

## Estados

- `confirmed`: probado por fuente nativa y consumer/layout.
- `corroborated`: coincide con otra fuente visible, sin elevar autoridad.
- `missing`: destino esperado ausente.
- `tombstone`: identidad histórica conservada sin entidad activa.
- `blocked`: falta una autoridad o existe contradicción.
- `unknown`: aún no investigado.
- `opaque`: superficie localizada pero no decodificada.
- `conflict`: fuentes AA10 autoritativas discrepan.
- `not_applicable`: dimensión no aplicable.

## Tablas núcleo consolidadas

Mantener `artifacts`, `decoders`, `source_databases`, `source_tables`,
`source_columns`, `query_specs`, `native_functions`, `entities`,
`entity_properties`, `relations`, `consumers`, `serializers`, `assets`,
`localizations`, `opaque_regions`, `coverage`, `crosswalk_entities` y
`validation_events`.

Toda arista debe registrar origen/destino tipados, relación dirigida, estado,
obligatoriedad, artefacto, locator, consumer y evidencia JSON. Conservar la
dirección inversa como vista, no como inferencia.

## Full frente a compact

Tratar `game_decrypted.sqlite3` como catálogo completo y `compact.sqlite3` como
proyección ejecutable. Registrar para cada tabla/columna/fila:

- presencia en full y compact;
- schema y afinidad;
- conteos, nulos, duplicados y claves observadas;
- loader/consumer;
- razón confirmada o pendiente de exclusión;
- impacto en servidor.

La ausencia en compact no significa contenido eliminado. Puede ser enum,
metadata de tooling, dato server-side, cache boundary o tabla no cargada por
ese proceso.

## Criterio de cobertura

Exigir todos los IDs y tipos clasificados, cero referencias descartadas, cada
huérfano explicado y cada región opaca con búsqueda reproducible. Registrar
procedencia por campo cuando una fila combine fuentes.
