# Checkpoint AA10 Housing H5 — servicios residenciales de crafting

## Frontera y diagnóstico

- Cliente: ArcheAge Returns `10.0.2.13-r575`.
- Rama: `rama_10`.
- HEAD al abrir H5: `d1b148c77a2f56384335abe9198967387a118336`.
- Upstream r575: `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- H3 y el gate estructural H4 se conservan sin ampliar sus contratos.

Los logs de Game demostraron que H4 sí materializó en la casa 16 los doodads
`9346`, `9391`, `4566`, dos `4568` y `9405`. El cliente ejecutó la puerta con
skill `16828`, la chimenea con `29358` y el attachment con `29372`, incluyendo
cambios de fase y timer. Las capturas nuevas corresponden a servicios H5 que
seguían bloqueados por `PendingWavePromotion`, no a una regresión del lifecycle
estructural.

## Política AA10 reproducible

`HousingInteractionPromotionPolicy.ClassifyH5` conserva primero toda decisión
H4. Sólo promueve un binding pendiente cuando su grafo AA10 contiene
`DoodadFuncCraftPack` y existe un consumer nativo cerrado:

```text
doodad_func_groups
  -> doodad_funcs (DoodadFuncCraftPack)
  -> doodad_func_craft_packs
  -> craft_pack_crafts
  -> crafts habilitado y req_doodad_id = doodad_almighty_id
```

La intersección full/compact retail/compact runtime decide la promoción. Una
estación sin ese consumer queda `MissingConsumer`; funciones visuales como
`CraftDirect` o `Timer` no bastan por sí solas. Quest, devote y servicios
territoriales permanecen bloqueados por su causa concreta.

El cliente abre la UI de recetas desde sus metadatos nativos. La confirmación
llega a `CSExecuteCraft` y reutiliza el flujo transaccional reconstruido de
crafting; housing no implementa un segundo camino para inventario, labor o
costes.

## Resultado del catálogo H5

- 837 plantillas catalogadas;
- 4.646 bindings en 631 plantillas;
- 3.889 ejecutables;
- 757 bloqueados;
- 102 bindings `force_db_save` preservados;
- 244 bindings pasan de `PendingWavePromotion` a ejecutables;
- 23 pasan a `MissingConsumer` porque el consumer exige otra estación.

Bloqueos finales:

| razón | cantidad |
|---|---:|
| ejecutable | 3.889 |
| doodad ausente | 6 |
| modelo ausente | 2 |
| posición ausente | 5 |
| transformación inválida | 4 |
| consumer ausente | 106 |
| subsistema territorial | 273 |
| ola posterior | 361 |

Full y runtime contienen 272 estaciones con consumer válido; compact retail
contiene 270. Las únicas divergencias son los doodads `6824` y `10645`; quedan
cerradas y registradas en el manifest, nunca promovidas por fallback.

Hashes deterministas:

- catálogo H5: `267B757C22D26F6E1E32B3E073488F93B524790C5AC3FA6EA22F20F40B776D3B`;
- helpers/modelos: `3A252BCEFC00F75F4C626863BEBB4BCEBF7E771600E5B56DCFC07C53B2FCC247`;
- manifest: `B7C81A4CEE1698490A30BBD053F46FC03F267022D69CDA3325556417E25DB61C`.

Una segunda extracción independiente produjo exactamente los mismos tres
hashes. Las tres SQLite pasan `quick_check=ok` e `integrity_check=ok`.

## Tradesman's Manor, plantilla 437

H5 deja 9 de sus 10 bindings ejecutables:

| attach | doodad | rol | estado |
|---:|---:|---|---|
| 1 | 9346 | chimenea | H4 ejecutable |
| 9 | 9109 | complex processing shelf | H5 ejecutable |
| 10 | 9142 | recipiente/quest | bloqueado hasta demostrar quest |
| 11 | 9307 | trade specialty workbench | H5 ejecutable |
| 12 | 9391 | attachment estructural | H4 ejecutable |
| 36 | 4566 | puerta | H4 ejecutable |
| 37 | 4568 | ventana | H4 ejecutable |
| 38 | 4568 | ventana | H4 ejecutable |
| 45 | 9307 | trade specialty workbench | H5 ejecutable |
| 57 | 9405 | placa/administración | H4 ejecutable |

La estantería `9109` tiene 53 recetas habilitadas demostradas. La mesa `9307`
resuelve por `ZoneReact`; Solzreed (`zone_group_id=5`) selecciona su fase local
y su consumer AA10 de specialty pack.

## Validación automatizada

- Build completo Release: correcto, 0 errores.
- Suite completa TUnit: 1.638/1.638, 0 fallos, 0 omitidas.
- Tests del catálogo: 4.646 bindings, 3.889 ejecutables, 102 persistentes y
  matriz exacta 9/10 para la plantilla 437.
- Tests de política: consumer positivo, consumer inválido, visual sin consumer
  y quest pendiente.

## Gate retail pendiente

1. La estantería interior del attach 9 debe ser seleccionable y F debe abrir su
   UI nativa con recetas.
2. Las mesas de especialidades attach 11/45 deben ser seleccionables; en
   Solzreed deben exponer el pack local demostrado por AA10.
3. Ejecutar una receta positiva si hay materiales; si no, confirmar al menos
   que el preflight negativo no consume materiales, labor ni inventario.
4. Puerta, ventanas, placa, chimenea y attachment H4 continúan funcionando.
5. Relog y reconexión de Zone no eliminan ni duplican servicios.
6. El recipiente de quest attach 10 no debe ofrecer una acción heredada hasta
   completar su grafo nativo.

No hacer commit ni push hasta la aceptación retail.

## Candidato desplegado

- Imagen candidata: `sha256:0ed221912e1d6ce3c1c331cddd814e39bd57d46966e2695119186788385b91cf`.
- Rollback: `aaemu-world:rollback-pre-housing-h5-20260828`, imagen
  `sha256:9a1278f5770e7657890d7776dc90afe65adfe62bd9a240412db41ef40600004e`.
- Catálogo verificado dentro del contenedor:
  `267B757C22D26F6E1E32B3E073488F93B524790C5AC3FA6EA22F20F40B776D3B`.
- Game/World: `healthy`; cargó 4.646 bindings/631 plantillas, cargó las 17
  viviendas y completó `AA10 housing binding reconciliation`.
- Login y DB permanecieron `healthy`. Codex no inició, detuvo ni reinició
  ninguna Zone.
