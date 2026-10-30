# Intake forense AA10

La skill `aa10-client-forensics` mantiene la autoridad estática y nativa. Leer
su `current-forensic-state.md` antes de afirmar que falta un dato.

Baseline 2026-08-15:

- SQLite completa confirmada: 1,374 tablas, `quick_check=ok`.
- Compact retail: 1,003 tablas; es subconjunto exacto a nivel de nombres.
- 371 tablas existen sólo en full y deben clasificarse antes de llamarlas
  “eliminadas”.
- x2game release, game_pak y proyectos Ghidra release/dev/Zone disponibles.
- Pipeline consolidado AA10 aún no creado.

Mientras no exista `aa10-client-knowledge.sqlite`, consultar directamente la
SQLite completa/compact en modo read-only y registrar SQL, filas, schema y
hashes en el checkpoint del dominio. Abrir una frontera forense cuando falte
consumer, serializer, relación, fórmula o lifecycle; no esconderla en código.

Cuando exista el grafo, generar primero un dossier de relación y uno de función.
Una fila consolidada sólo tiene la autoridad de su procedencia/estado.
