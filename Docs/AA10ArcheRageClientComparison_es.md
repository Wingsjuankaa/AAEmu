# Comparación forense AA10 Returns r575 vs ArcheRage instalado

Fecha del corte: 2026-08-18.

El análisis específico de ArchPass, asistencia, Today Assignment y Event
Center, junto con el plan de reactivación, está conservado en
[AA10LiveOpsFeatureReactivation_es.md](AA10LiveOpsFeatureReactivation_es.md).

## Conclusión

No hay evidencia de que el `compact.sqlite3` actualmente integrado en AAEmu cierre Hiram, ropa interior o Temper por debajo del cliente archivado de ArcheRage r575. La comparación lógica muestra lo contrario: el compact de AAEmu conserva el mismo esquema y las mismas cantidades de filas, pero contiene ampliaciones explícitas de esos límites.

El `game_pak` instalado actualmente por ArcheRage sí contiene 4.193 entradas que no existen en Returns r575, principalmente assets privados, mundos/eventos, iconos y UI. Son candidatos de investigación o port selectivo; no justifican sustituir el `game_pak` ni importar bytecode `.alb` en bloque.

El `compact.sqlite` exacto del ArcheRage instalado fue extraído, pero permanece dentro de un contenedor cifrado diferente al codec AA8 conocido. Hasta reconstruir ese codec no es válido afirmar qué filas mecánicas exclusivas contiene.

El bloqueo no procede del formato vanilla r575. La decompilación del `x2game.dll` Returns muestra la ruta `FUN_39925dc0 → FUN_39a2a850 → FUN_39a2a780 → FUN_39a1d220 → sqlite3_open`: copia la SQLite a un temporal `game_%u.sqlite3` y la abre directamente. En cambio, el `x2game.dll` de ArcheRage tiene secciones `.themida`/`.boot`, código de alta entropía, imports reducidos y ninguna cadena SQLite/compact recuperable. El cifrado del compact vivo es por tanto una personalización protegida de ArcheRage, no un codec AA10 vanilla que pueda trasladarse desde Returns.

## Identidad de las fuentes

### Target AAEmu

- Build: ArcheAge Returns `10.0.2.13 r575`.
- Compact activo: `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game\db\compact.sqlite3`.
- Tamaño: 440.823.808 bytes.
- SHA-256: `F8C7A0268A26D4EFAEC47A2A2B1B525447BF16C274506CD97BF571839B5E6D29`.
- Estado SQLite: `quick_check=ok`, 1.003 tablas.

### ArcheRage instalado

- Ruta: `E:\Rage\ArcheRage.to NA`.
- Versión de `archeage.exe` y `x2game.dll`: `10.0.2.9`.
- `game_pak`: 58.910.795.776 bytes.
- SHA-256 de `game_pak`: `6CCB24F55B0D59BD8CDD9EEAC3A0E73727654545DD3837B3D7AF99D8F2B9EAFB`.
- SHA-256 de `x2game.dll`: `A0BD18EDDF8AB80AC91AF7CED84978A89D8BC653816022383A8FBB6B384DECA1`.
- Entrada extraída: `game/db/compact.sqlite`.
- Contenedor extraído: 61.233.233 bytes, SHA-256 `716A3822C2B40B196CA24C5A1C4AA00C54F812F73E70BD36DC6A560980E62039`.
- Estado: cifrado; no es todavía una SQLite consultable.
- Protección nativa: Themida; el escaneo estático no recupera strings ni xrefs del loader SQLite.

### Compacts comparables

Se usaron además dos fuentes accesibles, siempre distinguiéndolas del cliente vivo:

- Archivo `aa-10.0.2.13r575-compact-multilangual-30072026-(archerage).7z`: compact de 440.823.808 bytes, SHA-256 `68919695CDD12C7B9CB4AC9BEA3828132B83C95D7DCCF46AA3E113CEA756507F`.
- `C:\Users\juank\Downloads\compact.sqlite3`: 441.483.264 bytes, SHA-256 `E32DE0198723A7C6B88004A8C68EC7AFC059B987BB8696B28D400176E5A406A1`.

Ambos pasan `quick_check` e `integrity_check`.

## Comparación lógica de los compacts

El compact archivado de ArcheRage r575 y el compact activo de AAEmu tienen:

- las mismas 1.003 tablas;
- el mismo esquema;
- las mismas cantidades de filas en todas las tablas;
- diferencias lógicas únicamente en `item_rnd_attr_categories` e `items`.

Cambios del baseline archivado hacia AAEmu actual:

| Campo | Cambio | Filas | Interpretación |
|---|---:|---:|---|
| `item_rnd_attr_categories.max_evolving_grade` | 7 → 8 | 12 | Hiram T2 hasta Divine |
| `item_rnd_attr_categories.max_evolving_grade` | 7 → 9 | 12 | Hiram T3 hasta Epic |
| `item_rnd_attr_categories.max_evolving_grade` | 7 → 11 | 12 | Hiram T4 hasta Mythic |
| `item_rnd_attr_categories.max_evolving_grade` | 7 → 12 | 25 | Hiram T5/T6 y ropa interior hasta Eternal |
| `items.max_enchant_scale_id` | 12 → 30 | 6.461 | restauración de escalas de Temper hasta +30 |

El compact de `Downloads` conserva el mismo esquema y las mismas cantidades de filas que el archivado. Su única tabla distinta es `localized_texts`: 84.616 filas, con 54.503 cambios en `en_us` y 38.701 en `ru`; no cambia `es` ni ninguna tabla mecánica.

## Auditoría de topes Celestial

La existencia de propiedades hasta grado 12 no demuestra por sí sola que una categoría deba sintetizarse directamente hasta Eternal. El audit encontró 380 categorías de equipo cuya escalera de propiedades supera `max_evolving_grade`:

| Clasificación | Categorías | Lectura |
|---|---:|---|
| Puerta de Awakening esperada | 219 | Hay mapping saliente habilitado; subir el cap rompería la progresión por tier. |
| Frontera con mapping deshabilitado | 40 | Candidato prioritario a reconstrucción; los datos de transición existen, pero el grupo está deshabilitado. |
| Terminal sin mapping | 103 | Candidato incompleto o legacy; no existe transición saliente que pruebe la intención. |
| Test/material/cosmético | 18 | Excluir de un parche mecánico masivo. |

Las 40 fronteras más fuertes incluyen:

- Kraken (`item_change_mapping_group` 13);
- Red Dragon (grupo 14);
- Mistsong/Library (grupos 4, 8 y 28);
- capas Erenor y sus pasos Radiant/3T (grupos 277 y 305).

También aparecen candidatos terminales como equipo de mascotas, equipo de instancias antiguas y Black Dragon. En estos casos subir `max_evolving_grade` a 12 sería especulativo: puede crear UI disponible sin costos, targets, materiales o handlers coherentes.

## Diferencias del game_pak

Comparación determinista por nombre, tamaño y MD5 interno:

| Métrica | Cantidad |
|---|---:|
| Entradas ArcheRage | 406.943 |
| Entradas Returns | 523.291 |
| Comunes | 402.750 |
| Comunes idénticas | 353.263 |
| Comunes modificadas | 49.487 |
| Sólo ArcheRage | 4.193 |
| Sólo Returns | 120.541 |
| Sólo ArcheRage bajo prefijos relevantes | 3.076 |

Contenido exclusivo de ArcheRage con mayor interés:

- 1.110 iconos bajo `game/ui/icon`, principalmente `arcustom`;
- 554 entradas bajo `game/custom/objects`;
- mundos/eventos privados: Hanuimaru, Capture Flag Arena y Wonderland;
- 52 assets bajo `game/objects/item`;
- 49 sonidos bajo `game/sounds/archeragecustom`;
- 14 entradas UI en `game/scriptsbin64/x2ui`, de las cuales 13 son `.alb`.

Hay además 7.637 entradas comunes modificadas dentro de prefijos relevantes. Entre ellas están módulos de Awakening, Evolving y Grade Enchant. Como ArcheRage es `10.0.2.9` y Returns es `10.0.2.13`, esos `.alb` sólo sirven como candidatos semánticos: requieren decompilación, diff de lógica y prueba contra las APIs de `x2game.dll` r575.

## Qué conviene rescatar

1. **Primero, el codec del compact vivo.** Es el único paso que permite una comparación mecánica exacta con el ArcheRage instalado, sin confundirlo con archivos archivados o descargados.
2. **Después, las 40 fronteras con mappings deshabilitados.** Deben validarse grupo por grupo contra targets, materiales, costos, skills/UI y soporte de servidor antes de habilitarlas.
3. **Assets privados de forma selectiva.** Iconos, modelos, sonidos y mundos pueden inventariarse y cruzarse con sus IDs de DB. Un asset aislado no crea una mecánica utilizable.
4. **UI como referencia, no como reemplazo.** Decompilar sólo los `.alb` relevantes y portar lógica compatible a r575.

No se recomienda reemplazar el `game_pak`, importar todos los límites de grado ni activar todos los mappings deshabilitados.

## Evidencia y reproducción

Resultados grandes:

- `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\archerage-comparison-20260818\compact-comparison.json`
- `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\archerage-comparison-20260818\equipment-grade-cap-audit.csv`
- `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\archerage-comparison-20260818\equipment-grade-cap-audit.json`
- `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\archerage-comparison-20260818\pak-index-comparison.json`
- listas completas `*-only*.txt` y `common-changed*.txt` en el mismo directorio.
- `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\archerage-10.0.2.9\static-scan.json`
- decompilación del loader vanilla r575 bajo `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\returns-r575-compact-native`.

Herramientas reproducibles:

- `reconstruccion_cliente_10/scripts/compare_compacts.py`
- `reconstruccion_cliente_10/scripts/audit_equipment_caps.py`
- `reconstruccion_cliente_10/scripts/compare_pak_indexes.py`
- `reconstruccion_cliente_10/tools/PakEntryExtract`
- `reconstruccion_cliente_10/tools/PakIndexExport`

Todo el trabajo fue de sólo lectura sobre los clientes y las SQLite de origen. No se modificó ni desplegó el runtime, MySQL, `.env` o el `game_pak`.

Los tres análisis se ejecutaron dos veces en directorios independientes. Los nueve artefactos equivalentes produjeron SHA-256 idénticos. Los dos proyectos auxiliares C# compilaron en Release sin advertencias ni errores en ejecuciones repetidas.
