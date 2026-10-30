# Flujo forense por etapas AA10

Cada etapa genera SQLite, manifest, checkpoint y pruebas. La consolidada se
reconstruye desde etapas y nunca se edita manualmente.

## Etapas

- **00 Artefactos:** hashes, build, arquitectura, inventario de SQLite,
  binarios, pak, worlds, scripts y capturas.
- **10 Full/compact:** schemas, filas, enums, diferencias, nulos, duplicados,
  claves, relaciones y loaders.
- **15 Corpus nativo:** funciones, RTTI, vtables, serializers, handlers,
  fórmulas, SQL, strings, xrefs y opacos de cliente release/dev y Zone exacto.
- **20 Items/economía:** items, equipo, temper, socketing, síntesis, awakening,
  loot, crafting, vendors y transacciones.
- **30 Mundo/actores:** NPCs, modelos, AI, factions, spawns, doodads, housing,
  slaves, mates, rutas y worlds.
- **40 Quests:** contextos, componentes, acts, condiciones, cadenas,
  start/report, rewards, diálogos y mapas.
- **50 Skills/combate:** skills, effects, buffs, plots, projectiles,
  animaciones, fórmulas y protocolo observado; describir, no implementar.
- **60 Assets/UI/localización:** modelos, texturas, iconos, audio, FX, UI y
  strings enlazados a entidades.
- **70 Crosswalk/corroboración:** AA8 y fuentes web compatibles en namespaces
  separados, con diffs campo por campo.
- **80 Consolidación/visor:** grafo, FTS, dossiers, rutas de dependencia y HTML.
- **90 Cierre:** opacos de mayor fan-out, huérfanos, tipos sin consumer,
  layouts pendientes, divergencias native/server y evidencia negativa.

## Gates

Requerir `quick_check`, `integrity_check`, pruebas de decoder, cero descartes
silenciosos, huérfanos explicados, dos builds con SHA-256 idéntico y manifest
sin timestamps no deterministas.
