# Creación nativa de personajes AA8

Este dominio reconstruye la creación de personajes de Kakao 8.0.3.12 sin
activar filas históricas 3.0.

La validación manual incremental del punto 0 y sus reparaciones por lotes se
registran en `POINT0_FAILURE_BACKLOG_V1.md`. El despliegue reproducible del lote
P0-A se documenta en `CHECKPOINT_POINT0_REPAIR_STACK_V1.md`; la tercera
iteración del ataque básico de rifle queda en
`CHECKPOINT_POINT0_RIFLE_STACK_V3.md`.

P0-A fue aceptado manualmente como satisfactorio el 2026-07-31. La evidencia
final de creación, posiciones de barra, reconexión y runtime acumulativo queda
en `generated/point0-repair-stack-v1-acceptance-manifest.json`.

## Extracción

```powershell
python .\extract_native_character_creation.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --runtime-compact D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b14-explorer-hiram-t1.sqlite3 `
  --x2game E:\AAEmu-Research\input\x2game.dll `
  --output .\generated
```

El extractor registra rangos, layouts, hashes, matriz raza/género/habilidad y
todos los bloqueos de autoridad. `build_native_character_runtime.py` se niega
a crear un runtime mientras el manifiesto no sea desplegable.

El catálogo de servidor requiere cuatro tablas derivadas que solo se pueden
emitir cuando se cierre su evidencia:

- `native_character_creation_spawns`;
- `native_character_creation_inventory`;
- `native_character_creation_supply_slots`;
- `native_character_creation_action_slots` (217 filas por combinación).

El barrido completo de XML se resume de forma reproducible con:

```powershell
python .\summarize_gamepak_world_evidence.py `
  --index E:\AAEmu-Research\output\gamepak-aa8-full-index-v1.csv `
  --xml-root E:\AAEmu-Research\output\gamepak-aa8-all-xml-v1 `
  --entity-root E:\AAEmu-Research\output\gamepak-aa8-all-client-entities-v1 `
  --mission-root E:\AAEmu-Research\output\gamepak-aa8-all-world-mission-v1 `
  --output .\generated\gamepak-full-xml-world-evidence-v1-manifest.json
```

El mundo `login2` completo —incluidos sus DAT/CTC— y los binarios jugables
32/64-bit se resumen con `summarize_client_binary_evidence.py`. Su salida es
`generated/client-binary-creation-evidence-v1-manifest.json`.

## Barrido global reproducible

El barrido de cierre no se limita a rutas elegidas por nombre. Sus inventarios
y conclusiones quedan separados para no convertir una coincidencia en
autoridad:

- `global-client-surfaces-v1-manifest.json`: índice completo del `game_pak`,
  compact, todos los streams `game*` y binarios de foco;
- `client-filesystem-global-v1-manifest.json`: cada archivo del cliente
  desempaquetado fuera del `game_pak`;
- `client-sql-surfaces-v1-manifest.json`: todo el SQL ASCII embebido en
  `x2game.dll` de 32 y 64 bits;
- `gamepak-lua-architecture-comparison-v1-manifest.json`: los 1112 scripts de
  ambas arquitecturas, decompilados y comparados;
- `gamepak-global-review-surfaces-v1-manifest.json`: extracción íntegra de todo
  contenedor estructurado/textual y de todos los DAT/CTC de mundo;
- `gamepak-supplemental-review-surfaces-v1-manifest.json`: formatos poco
  comunes revisables que no pertenecen a las clases masivas;
- `gamepak-global-content-scan-v1-manifest.json`: verificación MD5 y búsqueda
  de contenido sobre esa extracción;
- `cached-result-streams-global-v1-manifest.json`: hash y búsqueda byte a byte
  sobre todos los resultados descifrados `game*`;
- `global-client-creation-sweep-v1-manifest.json`: conclusión, fuentes
  decompiladas, bloqueos actuales y catálogo reutilizable para dominios futuros.

Los assets raster, geometría, animación, audio y navegación también permanecen
contabilizados por el índice completo. No se tratan como autoridad de bootstrap
porque no pueden definir por sí solos una relación de estado del servidor.

No se debe sustituir una evidencia ausente con `CharTemplates.json`, compact
3.0, nombres de objetos o aproximaciones visuales.

## Bootstrap aceptado v2

El baseline forense v1 permanece inalterado. Las decisiones que el operador
aceptó para completar el bootstrap —transformaciones iniciales, orden libre de
suministros, capacidad 50/50 y autorregistro de la habilidad inicial— se
mantienen separadas en `accepted-character-bootstrap-v2-policy.json` y se
clasifican como `server_derived_accepted`, nunca como filas nativas.

La derivación, construcción y verificación reproducibles son:

```powershell
python .\derive_accepted_character_bootstrap_v2.py

python .\build_native_character_runtime.py `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b14-explorer-hiram-t1.sqlite3 `
  --data .\generated\native-character-creation-v2-data.json `
  --manifest .\generated\native-character-creation-v2-manifest.json `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-character-creation-v2.sqlite3

python .\verify_native_character_creation_v2.py `
  --runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-character-creation-v2.sqlite3 `
  --manifest .\generated\native-character-creation-v2-manifest.json
```

El estado reproducible, hashes, despliegue y aceptación visible pendiente se
registran en `CHECKPOINT_NATIVE_CHARACTER_CREATION_V2.md`.
