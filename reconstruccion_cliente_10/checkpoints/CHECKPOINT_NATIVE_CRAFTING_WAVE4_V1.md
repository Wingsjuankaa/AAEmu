# Checkpoint AA10 crafting — ola 4

## Frontera

- Target: `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`.
- Baseline aceptada de ola 3:
  `6054192ca2a3d6906776bcd6bcd15392617aae44`.
- Padre exacto: `upstream/client_version/zone-10.0.2_r575` en
  `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- Implementación de backpacks/tradepacks: `3b48f66bd`.
- AA8 se mantuvo como `structural_candidate`; no se copiaron fórmulas, IDs,
  packets ni timings.

## Fuentes congeladas

| Fuente | SHA-256 | Bytes | Estado SQLite |
|---|---|---:|---|
| full | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` | 552178688 | `quick_check=ok`, `integrity_check=ok` |
| compact retail | `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849` | 440827904 | `quick_check=ok`, `integrity_check=ok` |
| compact runtime | `DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD` | 552178688 | `quick_check=ok`, `integrity_check=ok` |

## Contrato implementado

- Los productos autoequipables se determinan por su `BackpackTemplate`; no se
  usa `craft_pack_crafts` como sustituto de la semántica del item.
- El planner distingue slot vacío, glider y backpack ocupado. Un pack ocupado
  o el estado de gliding fallan antes del casteo y sin mutación.
- Con slot vacío, el producto se equipa directamente. Con glider equipado, la
  capacidad se simula después del consumo: el glider pasa a una ranura de bolsa
  liberada y el producto ocupa equipment slot 26 bajo el mismo lock.
- La transacción de bolsa/equipment consume materiales, mueve el glider y crea
  el pack sin publicar estados parciales. El producto conserva crafter,
  `created_at` y persistencia ordinaria.
- La revalidación se repite en el commit para cerrar carreras entre el inicio y
  el final del casteo.

## Catálogo fail-closed

- Manifest: `generated/aa10-crafting-wave4-manifest.json`.
- SHA-256 manifest:
  `F2BCEDD347D230E99571F1E1FC9DA3C3507CDF36A8FB932C64140A5A739332B7`.
- Policy: `AAEmu.Game/Data/aa10-crafting-wave4-policy.json`.
- SHA-256 policy:
  `4BF6110F8EE37F775EDFB549A6F6AE3EAAC6B8CCE2019F357353EF954A9D68BA`.
- Partición cerrada: 9.949 habilitadas, 8.835 `executable_wave4` y 1.114
  bloqueadas.
- Bloqueos explícitos: `missing_actability_group` 15,
  `missing_craft_effect` 4, `missing_material_item` 13, `missing_materials`
  702, `missing_native_rate_consumer` 91, `missing_product_item` 1,
  `missing_products` 180, `missing_skill` 87 y
  `retail_compact_craft_contract_mismatch` 282.
- No queda ningún bloqueo genérico `backpack_deferred`.

## Gates estáticos

- `dotnet restore AAEmu.slnx`: correcto.
- build Release de la solución: correcto, 0 errores.
- suite TUnit: 1.563/1.563, 0 fallos.
- auditorías de manifests: 17/17.
- Tests focales cubren autoequip vacío, pack ocupado, gliding, reemplazo de
  glider, capacidad liberada por consumo y rechazo atómico sin espacio.

## Gate retail decisivo — aprobado

Se usó el craft 4007 (`[Trade Pack] Stone Pack`) sobre Zone r575 real, skill
14582 y Stonemason Workbench template 559. El contrato exige 100 Stone Brick,
25 labor, 1 cobre, cast de 10 segundos y produce el backpack 17684.

1. Con slot vacío, el craft terminó y el servidor registró
   `materials=1, products=1, failedProducts=0, cost=1, labor=25`. El pack quedó
   equipado y sobrevivió un relog con `made_unit_id=8` y su `created_at`.
2. Con el pack equipado, la repetición fue rechazada instantáneamente con
   `BackpackOccupied`, antes de iniciar skill y sin consumir material, labor ni
   dinero.
3. Tras retirar el pack, se equipó el item retail 14677 (`Experimental
   Glider`). El nuevo craft inició normalmente, consumió exactamente 100 Stone
   Brick, 25 labor y 1 cobre; el cliente informó `Removed: Experimental Glider`
   y luego `Acquired: Stone Pack`.
4. Después de cerrar limpiamente el cliente, la DB persistió el resultado:
   Stone Pack nuevo `item=16777465`, `container=65554`, `slot_type=1`,
   `slot=26`, `made_unit_id=8`; Experimental Glider `item=16777467`,
   `container=65555`, `slot_type=2`, `slot=4`. El dinero quedó en `999999998`.

La combinación de rechazo pre-cast, intercambio glider→bolsa, autoequip,
persistencia y relog hace el gate decisivo contra una validación meramente
visual o un intercambio parcial.

## Despliegue reversible

- Imagen desplegada en `Game`:
  `sha256:f82a42e65c6b8796ad28793af9d258e2ae0971457e52307e409c60a7807a5b74`.
- Rollback preservado como
  `aaemu-world:rollback-pre-crafting-wave4-acceptance-20260827`:
  `sha256:240c88f813e39686374ad122116dace62fbd100d7d9be2fe31e6c3c15c267619`.
- `aaemu10-game-1` quedó healthy; DB y Login permanecieron healthy.
- El loader registró `12402 crafts (9949 enabled, 8835 promoted by AA10
  crafting policy)`.
- Se reinició únicamente `o_the_great_reeds`; el heartbeat y la carga de Zone
  288 quedaron estables.

Con estos gates, la ola 4 queda aceptada. Craft Orders continúa fuera de
alcance y la cobertura final del catálogo pasa a la ola 5.
