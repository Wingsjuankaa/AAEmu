# Checkpoint B14 — Explorer → Hiram Guardian T1

Fecha de cierre: 2026-07-25
Autoridad: cliente Kakao 8.0.3.12 (`game11`, compact descifrado y evidencia
confirmada de `x2game.dll`). No se usaron datos de gameplay 3.0.

## Artefacto reproducible

- Generador: `build_phase_b14_runtime.py`.
- Manifiesto: `manifest-b14.json`.
- Base B13d:
  `compact-8.0-runtime-native-equipment-phase-b13d-hiram-infusion-wrappers.sqlite3`
  (`A1E8370FCA25502124CFFE0F383916BCCDFABBDD449F1477399282DC2442F245`).
- Salida B14:
  `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b14-explorer-hiram-t1.sqlite3`.
- SHA-256 B14:
  `02BC7EE9045D2AA4B5746C44760358C316C6C1CBA2B5A78563DBB439A5BBDE99`.
- Dos construcciones consecutivas produjeron el mismo SHA-256.
- `PRAGMA quick_check`: `ok`.
- `PRAGMA integrity_check`: `ok`.
- Referencias habilitadas huérfanas en mappings/selectivos: `0`.

## Cierre de datos

- Grupos de awakening `48`, `49` y `50`: 3 grupos y 184 mappings, todos
  nativos y con éxito de 100%.
- Cierre de equipo/materiales de los mappings: 225 ítems.
- Infusiones:
  - `48845`: grado 2, 50 EXP.
  - `48846`: grado 3, 130 EXP.
  - `48847`: grado 4, 250 EXP.
- Wrappers `48507–48509`: skills `43013–43015`, con sus tres reactivos y
  tres productos.
- Cofres de armadura `48087–48098`: 84 resultados, siete piezas exactas
  por cofre.
- Cofres selectivos de armas:
  - `47868`: 8 opciones nativas.
  - `47869`: 6 opciones nativas.
  - `51185`: 2 opciones nativas (arco y rifle).
- Recompensas de misión: 140 acts nativos, incluyendo supplies normales y
  selectivos; se importaron los 22 contextos ausentes y sus relaciones
  mínimas.
- Vendedores: 504 templates (62 armas, 63 armaduras y 379 generales).
- Stocks B14: 20 goods repartidos en packs equivalentes dedicados de 3, 5
  y 12 entradas.
- El scroll Rank 3 `47952` no se añadió al general merchant.

## Implementación de servidor

- `SelectiveItemCatalogueService` usa `source_item_id` como identidad de la
  acción y `(source_item_id, option_index)` para sus opciones. `skill_id`
  queda como metadato no único y existe compatibilidad de lectura con el
  esquema B13.
- `MerchantPurchaseService` construye un plan autoritativo y valida stock,
  grado, moneda, precio, cantidad, overflow, fondos y capacidad antes de
  confirmar bajo el bloqueo de la bolsa.
- `CSBuyItemsPacket` ya no acepta grado, precio ni moneda como autoridad del
  cliente y rechaza mezclas inválidas de compra/recompra.
- Se corrigió la comprobación de honor/vocation para que falle si falta
  cualquiera de las monedas requeridas.
- Cofres y exchanges de wrappers reservan capacidad y validan la operación
  completa antes de consumir el origen.
- La síntesis reconoce los grupos Explorer `11→12`, `31→32` y `33→34`.
- Se cargan los grupos NPC de aceptación de quest que faltaban en el
  runtime B13.

## Pruebas

- Target de compilación: `netcoreapp3.1`.
- Build de imagen ejecutado con SDK .NET Core `3.1.409-focal`.
- Suite completa: **196 aprobadas, 0 fallidas, 0 omitidas**.
- Incluye las 181 pruebas de regresión, ocho casos B14 para catálogo selectivo,
  compras autoritativas y materiales Explorer, y siete casos para la política
  de slots de personaje usada por esta validación.
- `python -m py_compile` correcto para el generador B14 y el extractor
  selectivo.
- `git diff --check` correcto.

## Despliegue y reversión

- El despliegue B14 reconstruyó `game`; la corrección posterior de slots
  reconstruyó únicamente `login`.
- Imagen `game` activa:
  `sha256:837f23bf5eb1a0fe434f7912b6cc351a6347bc9414dc2b9866ed87dbbc71cdb5`.
- Imagen `game` inmediata anterior conservada:
  `sha256:b6e474d5ffe9196b53c4e76411545366b90f7cf09d21908519055108c5fa05cc`.
- Imagen `login` activa:
  `sha256:7e38fe4ed08e3c96ac9c248ca64c4611f43e9d5cbf9f8322191aa358f6787dc3`.
- Imagen `login` inmediata anterior conservada:
  `sha256:a622d6ca72e39586945d6f9fda9022e12ad1c54b0076d3fad10c97f04f2a51b9`.
- Backup MySQL previo:
  `D:\Proyectos\AAemu\backups\pre-b14-20260725-125252.sql`.
- SHA-256 del backup:
  `9012D0D1FE05BB60279660B57E40F6F73511530FC7649F468510D581EEFADDBC`.
- El compact B13d anterior permanece intacto.
- Hash del compact montado: coincide con el SHA-256 B14.
- Contenedores `db`, `login` y `game`: activos.
- Puertos `2239` y `2250`: accesibles.
- Registro de `game` contra `login`: correcto.
- Errores en el arranque B14 de `game`: `0`.

## Evidencia derivada y límites explícitos

- La tabla servidor `loots` no existe en el cliente. Sus 84 filas se
  materializaron usando la relación nativa skill/effect/loot pack y las
  listas exactas de siete piezas de las descripciones AA8.
- La skill de `51185` colisiona con otra acción. Sus dos opciones se cerraron
  por la descripción AA8 del ítem y la membresía completa de la categoría
  nativa 638; no se dedujeron por nombres históricos.
- Los goods ajenos al cierre B14 de los packs originales no se importaron.
- Los 91 templates vendedores sin instancia verificada no recibieron spawns
  artificiales.
- No se versionaron SQLite generados, dumps, archivos del cliente ni el
  backup. `.env` sólo apunta localmente al runtime desplegado.

## Validación manual pendiente

La única actividad de aceptación que no puede automatizarse desde la sesión
del servidor es recorrer con un personaje nuevo la secuencia completa:
recibir/recomprar Explorer, abrir cofres, sintetizar y despertar
Explorer → Radiant → Brilliant → Hiram T1, relogueando después de cada
transición para comprobar inventario, monedas, stats, apariencia y progreso
de misión.

Para habilitar esta prueba, `MaxCharacters` quedó configurado en `6` tanto en
Login como en Game. Login conserva el wire shape AA8 de `ACJoinResponse` y
anuncia `afs=0x02020406` y `slotCount=4`; Game aplica autoritativamente el mismo
límite antes de asignar el ID, crear inventario o persistir un personaje. El
ajuste no modificó MySQL ni el runtime compact B14.

La primera validación visual mostró seis posiciones, pero cuatro seguían
bloqueadas. La causa se cerró contra `x2game.dll`: el consumidor nativo
`FUN_3966d680` (`0x3966d680`) copia `ACAuthResponse.slotCount` al estado
`+0x16018`, y `FUN_3966c6e0` lo suma al cálculo de slots disponibles. Por eso
el máximo total de seis requiere cuatro slots adicionales desbloqueados sobre
los dos slots base.
