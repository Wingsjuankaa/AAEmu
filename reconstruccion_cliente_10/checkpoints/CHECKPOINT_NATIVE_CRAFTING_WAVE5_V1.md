# Checkpoint AA10 crafting — ola 5

## Frontera

- Target: `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`.
- Baseline aceptada de ola 4:
  `d357d9b8f0a04aff501da7b4f8c50240009be07f`.
- Padre exacto al iniciar la ola:
  `upstream/client_version/zone-10.0.2_r575` en
  `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- Implementación del cierre de cobertura:
  `9b1febee8`.
- Craft Orders sigue fuera de alcance. AA8 se mantuvo únicamente como
  `structural_candidate`; no se copiaron fórmulas, IDs, packets ni timings.

## Fuentes congeladas

| Fuente | SHA-256 | Estado SQLite |
|---|---|---|
| full | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` | `quick_check=ok`, `integrity_check=ok` |
| compact retail | `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849` | `quick_check=ok`, `integrity_check=ok` |
| compact runtime | `DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD` | `quick_check=ok`, `integrity_check=ok` |

## Cierre fail-closed del catálogo

- Manifest: `generated/aa10-crafting-wave5-manifest.json`.
- SHA-256 manifest:
  `A8FEEA21D7C2992BF7DB24EFA1307F02FB3E7E144514AEB9A6C896A3009CA25C`.
- Policy: `AAEmu.Game/Data/aa10-crafting-wave5-policy.json`.
- SHA-256 policy:
  `D258EDE2113F0A2B4BCC7A582FDF7F4BC725D899D4332A045FB6670236859C70`.
- Partición total de las 9.949 recetas habilitadas: 7.306 ejecutables y 2.643
  bloqueadas por evidencia negativa explícita.
- Bloqueos: `missing_native_consumer` 2.445,
  `retail_compact_craft_contract_mismatch` 282, `missing_materials` 702,
  `missing_products` 180, `missing_native_rate_consumer` 91,
  `missing_skill` 87, `missing_actability_group` 15,
  `missing_material_item` 13, `missing_craft_effect` 4 y
  `missing_product_item` 1. Una receta puede acumular más de un bloqueo.
- Cada entrada declara `native_consumers` y
  `excluded_consumer_evidence`; ninguna receta sin consumer demostrado cae al
  flujo heredado.

## Evidencia de consumers

Sobre las 9.949 recetas habilitadas, las relaciones nativas demostradas son:

| Consumer | Recetas |
|---|---:|
| `doodad_craft_pack` | 4.974 |
| `item_recipe` | 2.699 |
| `folio_craft_line` | 537 |
| `live_doodad_craft_start` | 7 |
| `item_craft_link` | 5 |

La unión contiene 7.504 recetas; 2.445 carecen de consumer nativo. Se excluyen
deliberadamente 59 relaciones `butler_specialty_trade_todo`, porque el packet
de ejecución continúa marcado TODO, y 265 relaciones
`quest_progress_observer`, que sólo observan progreso de quest y no ejecutan el
craft.

## Gates estáticos

- `dotnet restore AAEmu.slnx`: correcto; sólo warnings conocidos de
  vulnerabilidades de dependencias.
- build Release: correcto, 0 errores y 170 warnings.
- suite TUnit: 1.563/1.563, 0 fallos.
- auditorías Python de manifests: 21/21.
- El loader exige la policy v5 y registró
  `12402 crafts (9949 enabled, 7306 promoted by AA10 crafting policy)`.
- Casos de referencia: craft 56 ejecutable con consumers
  `doodad_craft_pack,item_recipe`; craft 4007 ejecutable mediante
  `doodad_craft_pack`; craft 11031 ejecutable mediante
  `doodad_craft_pack,folio_craft_line`.

## Gate retail decisivo — aprobado

El cliente retail r575 entró contra el despliegue v5 y confirmó primero que el
Stone Pack de la ola 4 seguía equipado después del relog. Luego se ejecutó de
nuevo el craft 4007 (`[Trade Pack] Stone Pack`) sobre Zone 288 real, skill
14582 y Stonemason Workbench template 559.

1. Con el backpack libre y 100 Stone Brick, el cast de 10 segundos terminó.
   El cliente informó 71.200 XP, 25 labor, +2.500 Masonry, consumo de 100 Stone
   Brick y 1 cobre, y adquisición del Stone Pack.
2. Con el nuevo pack equipado se entregaron otros 100 Stone Brick y se pulsó
   Confirm. El rechazo `Already carrying a pack.` apareció en aproximadamente
   un segundo, antes de cualquier barra de casteo.
3. Tras cerrar limpiamente el cliente, la base persistió el nuevo pack como
   item `16777469`, template `17684`, container `65554`, `slot_type=1`,
   `slot=26`, `made_unit_id=8`, owner 8 y `created_at=2026-08-27 13:15:04`.
4. El rechazo no mutó la economía: permanecen 100 Stone Brick, 91 labor y
   `999999997` de dinero. La posición quedó guardada en Zone 288.

Este gate demuestra que la policy final mantiene un consumer promovido real,
con transacción, autoequip y persistencia, y que el bloqueo de backpack se
evalúa pre-cast sin consumo parcial.

## Despliegue reversible

- Imagen desplegada en `Game`:
  `sha256:cd5d95a28c19ced7476a025d5d94a1815b1b500c47c3b1d7248ecd97f37e87ca`.
- Rollback conservado como
  `aaemu-world:rollback-pre-crafting-wave5-acceptance-20260827`:
  `sha256:f82a42e65c6b8796ad28793af9d258e2ae0971457e52307e409c60a7807a5b74`.
- `aaemu10-game-1`, DB y Login quedaron healthy.
- Zone `o_the_great_reeds` se reinició conservando su DLL, save dir y wrapper
  exactos; cargó en 4,94 segundos y el heartbeat confirmó 740 unidades.

Con los gates estáticos, el gate retail y la partición cerrada del catálogo,
la reconstrucción nativa del crafting AA10 queda completada en sus cinco olas.
