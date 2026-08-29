# Checkpoint AA10 Housing H4 — interacciones estructurales residenciales

## Frontera

- Cliente: ArcheAge Returns `10.0.2.13-r575`.
- Rama: `rama_10`.
- HEAD al abrir H4: `d1b148c77a2f56384335abe9198967387a118336`.
- Upstream r575: `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- H3 permanece aceptada y su catálogo se conserva sin cambios.
- AA8, wikis y el JSON heredado no aportan IDs, offsets, posiciones ni wire.

El defecto que abrió H4 no estaba en la finalización del remodelado. La casa 16
quedó convertida a plantilla 437, pero sus diez relaciones AA10 tenían posición
demostrada y `PendingWavePromotion`; por eso el runtime no materializaba ningún
componente. La misma barrera global explicaba el defecto observado en Thatched.

## Política reproducible

`HousingInteractionPromotionPolicy.ClassifyH4` clasifica cada binding a partir
de `housings.category_id`, `attach_point_id` y el conjunto completo de
`actual_func_type` de sus grupos iniciales y de fase.

- categorías residenciales: house, vivienda pequeña/media/grande, mansión,
  farmhouse, farms, garden, floatinghouse, underwater y variantes BM;
- categorías de dominio/castillo: `TerritorialSubsystemRequired`;
- `ItemChangerUiOpen` y UIs Expedition sin consumer: `MissingConsumer`;
- servicios de crafting, quest y similares: `PendingWavePromotion` hasta H5;
- placas, puertas, ventanas, chimeneas, climb, attachment y ciclos estructurales:
  ejecutables en H4 si modelo, helper y transformación están demostrados.

`DoodadFuncBindButler` permanece sin consumer y la feature Butler continúa
apagada. No bloquea la placa AA10 si comparte doodad con `ParentInfo`; una
petición directa a cualquier función de housing sin handler se rechaza antes de
efectos, fase o skill.

El generador exige paridad exacta full/compact/runtime para:

```sql
SELECT id, category_id FROM housings ORDER BY id;
```

y para la unión ordenada de `actual_func_type` de `doodad_funcs` y
`doodad_phase_funcs`, enlazada por `doodad_func_groups.doodad_almighty_id`.

## Generación

```powershell
dotnet run --project reconstruccion_cliente_10\tools\HousingInteractionCatalogBuilder\HousingInteractionCatalogBuilder.csproj -c Release --no-build -- `
  E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3 `
  E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game\db\compact.sqlite3 `
  E:\AAEmu\rama_10\server\AAEmu\.server_files\AAEmu.Game\Data\compact.sqlite3 `
  E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\Bin64\x2game.dll `
  E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game_pak `
  AAEmu.Game\Data\model_attach_points_aa10_h3.json `
  AAEmu.Game\Data\housing_interactions_aa10_h4.json `
  reconstruccion_cliente_10\housing_h4\generated\aa10-housing-h4-manifest.json
```

Métricas:

- 837 plantillas;
- 4.646 bindings en 631 plantillas;
- 3.645 ejecutables H4;
- 1.001 bloqueados: 6 doodads ausentes, 2 modelos, 5 posiciones, 4
  transformaciones, 83 consumers, 273 territoriales y 628 olas posteriores;
- 102 `force_db_save` preservados.

Hashes:

- catálogo H4: `8249BCAD2F6022C3D26252199108B6D201C69B50C1DED8417385A8EAA4F58B91`;
- helpers H3/H4: `3A252BCEFC00F75F4C626863BEBB4BCEBF7E771600E5B56DCFC07C53B2FCC247`;
- manifest: `52706C59FA25867321D657F8B371D9C220F925A4239AB455FDBA0D0DD42C2739`.

Una segunda extracción independiente produjo exactamente los mismos hashes de
catálogo y helpers. Full, compact retail y compact runtime pasan
`quick_check=ok` e `integrity_check=ok`.

## Tradesman's Manor, plantilla 437

Los diez helpers AA10 están demostrados. H4 promueve seis:

| attach | doodad | rol H4 |
|---:|---:|---|
| 1 | 9346 | chimenea / Memory Fireplace |
| 12 | 9391 | attachment estructural |
| 36 | 4566 | puerta |
| 37 | 4568 | ventana |
| 38 | 4568 | ventana |
| 57 | 9405 | placa / administración |

Los attach 9, 10, 11 y 45 son servicios crafting/quest y permanecen en H5. Los
seis H4 tienen coordenadas distintas y ninguno usa fallback al origen.

## Gate retail pendiente

La casa 16 persistió como plantilla 437, pero el reinicio abrupto ocurrió antes
del autosave de la última acción: la fila volvió con `current_step=0`. El usuario
debe completar una vez más el único martillazo después del despliegue candidato.

1. Al completar, aparecen placa, chimenea, attachment, puerta y dos ventanas.
2. F en la placa abre el detalle de la casa correcta.
3. Puerta y ventanas alternan fase/modelo; attachment y chimenea ofrecen sólo
   sus acciones demostradas.
4. Relog no elimina ni duplica componentes.
5. Tras esperar autosave o detener Game limpiamente, reinicio de Game conserva
   la casa completa; el usuario relanza Zone y la reconexión no duplica bindings.

No hacer commit ni push hasta la aceptación retail.

## Candidato desplegado

- Build Release: correcto, 0 errores.
- Suite: 1.633/1.633.
- Imagen candidata: `sha256:9a1278f5770e7657890d7776dc90afe65adfe62bd9a240412db41ef40600004e`.
- Rollback: `aaemu-world:rollback-pre-housing-h4-20260828`, imagen
  `sha256:d7e1cc55ec92eae5b386212f0736c59384711d2fcd5eb4beb7bd7f811a4783ca`.
- Catálogo verificado dentro del contenedor:
  `8249BCAD2F6022C3D26252199108B6D201C69B50C1DED8417385A8EAA4F58B91`.
- Game/World: `healthy`; catálogo 4.646/631 cargado y reconciliación completada.
- Login y DB permanecieron healthy. Ninguna Zone fue iniciada, detenida o
  reiniciada por Codex.
