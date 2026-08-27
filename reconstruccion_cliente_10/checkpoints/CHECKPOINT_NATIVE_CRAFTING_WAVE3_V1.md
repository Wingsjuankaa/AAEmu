# Checkpoint AA10 crafting — ola 3

## Frontera

- Target: `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`.
- Baseline aceptada de ola 2: `fc30df0ae12a998033228f197934cc84e84c992a`.
- Padre exacto: `upstream/client_version/zone-10.0.2_r575` en
  `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- Implementación de grados/rates: `d5ca611f8`; corrección retail y cierre de
  catálogo: `f553b7f00`.
- AA8 se mantuvo como `structural_candidate`; no se copiaron fórmulas, IDs,
  packets ni timings.

## Fuentes congeladas

| Fuente | SHA-256 | Bytes | Estado SQLite |
|---|---|---:|---|
| full | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` | 552178688 | `quick_check=ok`, `integrity_check=ok` |
| compact retail | `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849` | 440827904 | `quick_check=ok`, `integrity_check=ok` |
| compact runtime | `DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD` | 552178688 | `quick_check=ok`, `integrity_check=ok` |

## Contrato implementado

- `require_grade=-1` acepta cualquier grado; con valor concreto exige igualdad,
  salvo `upper_grade`, que acepta ese grado o superior.
- `use_grade` fija `item_grade_id`. Sin grado fijo, el producto hereda primero
  el material `main_grade` y después el material de la misma implementación con
  mayor grado.
- La selección de stacks conserva orden determinista y la transacción consume
  exactamente los stacks que justificaron el grado resuelto.
- Rates 50/100/200 usan un RNG inyectable con roll entero `[0,99]`; 100 y 200
  son éxito garantizado. Se eliminó el 5 % mágico heredado. Un fallo de rate
  consume los materiales/pagos de la unidad, no crea el producto y no rompe la
  atomicidad de las demás filas de producto.
- El grado explícito resuelto por crafting llega hasta `ItemManager` y
  `ItemContainer` sin ser reemplazado por `fixed_grade`/default, incluso cuando
  el template del producto no es gradable. Las adquisiciones ordinarias
  conservan su normalización anterior.

## Catálogo fail-closed

- Manifest: `generated/aa10-crafting-wave3-manifest.json`.
- SHA-256 manifest:
  `E18920813EA63E06F11E9890119ABCACBD0DE1D75E40BCA546D86D0C5E356ED7`.
- Policy: `AAEmu.Game/Data/aa10-crafting-wave3-policy.json`.
- SHA-256 policy:
  `214056D64F2BBA159E6CF11C984CF251F969DE570D415D8CD9BCEEC05D5D0FD6`.
- Partición cerrada: 9.949 habilitadas, 8.451 `executable_wave3` y 1.498
  bloqueadas.
- Las 389 recetas con producto backpack siguen diferidas a ola 4.
- Las 90 recetas con `rate=50` apuntan exclusivamente a
  `doodad_func_craft_start_id` 6/8/10/18, ausentes de
  `doodad_func_craft_starts` r575. La única receta `rate=200` es el craft 11197,
  una ruta de desarrollo cuyo título nativo indica que no funciona. Las 91
  quedan bloqueadas por `missing_native_rate_consumer`: el motor probabilístico
  está reconstruido y probado, pero no se inventa una entrada ejecutable.

## Gates estáticos

- `dotnet restore AAEmu.slnx`: correcto.
- build Release de la solución: correcto, 0 errores.
- suite TUnit: 1.557/1.557, 0 fallos.
- auditorías de manifests: 13/13.
- Tests focales cubren grado fijo, main-grade, same-impl, límites exactos y
  superiores, stacks múltiples, RNG 49/50, 50/50, 100/200 garantizados, fallo
  que consume sin premio, y preservación de grado explícito en template no
  gradable.

## Gate retail decisivo — aprobado

Se ejecutaron dos contratos distintos sobre Zone r575 real y estación nativa:

1. El craft 56 (`Faded Sword of Honor`) produjo el item 26060 con
   `use_grade=true`, `item_grade_id=3`; tras consumir 150 materiales, 500 labor
   y 1 cobre, el producto se mostró y persistió en grado 3.
2. El craft 11031 (`Blazing Sunridge Ingot`) se ejecutó en Smelter doodad 557
   con Sunridge Ingot grado 7 como `main_grade`, más 9 Anya Ingot, 25 Dragon
   Essence Stabilizer y 6 Flaming Log. Consumió exactamente 85 labor y 10
   cobre. El primer intento anterior a la corrección dejó una pila histórica
   `item=28969 grade=0 count=2`, demostrando el defecto. Tras desplegar el fix,
   una repetición creó una fila separada `item=28969 grade=7 count=1`; los
   cuatro materiales quedaron agotados y el dinero pasó de `11925512045` a
   `11925512035`. La salida limpia confirmó la persistencia del grado 7.

No se alteró la pila histórica de grado 0. Esa coexistencia hace que la prueba
sea decisiva contra una normalización tardía o una lectura visual engañosa.

## Despliegue reversible

- Imagen desplegada en `Game`:
  `sha256:240c88f813e39686374ad122116dace62fbd100d7d9be2fe31e6c3c15c267619`.
- Rollback preservado como
  `aaemu-world:rollback-pre-crafting-wave3-acceptance-20260827`:
  `sha256:aab07e6e2830cc4ad1533b205f7f6d3b5af099006f9bfb8166c7900879b20c09`.
- `aaemu10-game-1` quedó healthy, con cero reinicios; DB y Login permanecieron
  healthy.
- El loader registró `12402 crafts (9949 enabled, 8451 promoted by AA10
  crafting policy)` y la policy montada conservó SHA-256
  `214056D64F2BBA159E6CF11C984CF251F969DE570D415D8CD9BCEEC05D5D0FD6`.
- Se reinició únicamente `o_the_great_reeds`; el heartbeat quedó estable en
  740 unidades y la Zone cargó en 4,94 s.

Con estos gates, la ola 3 queda aceptada. Craft Orders continúa fuera de
alcance y backpacks/tradepacks pasan a la ola 4.
