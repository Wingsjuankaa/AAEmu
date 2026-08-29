# Checkpoint AA10: evolución de Housing

> Continuación 2026-08-28: el remodelado a plantilla 437 quedó probado hasta su
> etapa final. La ausencia de componentes tras construir se diagnosticó como la
> barrera global `PendingWavePromotion` del catálogo H3, no como un fallo de la
> transacción de remodelado. La reparación y su gate están documentados en
> `../housing_h4/AA10_HOUSING_H4_CHECKPOINT.md`.

## Frontera

- Cliente: ArcheAge Returns 10.0.2.13 r575.
- Baseline de implementación: `rama_10` en `d1b148c77a2f56384335abe9198967387a118336`.
- Fuentes autoritativas: SQLite full/compact/runtime, `x2game.dll` y Lua extraído de `game_pak`.
- AA8 y cualquier implementación heredada se consideran solamente candidatos estructurales.
- No se modifica `compact.sqlite3` ni `game_pak` para habilitar la mecánica.

El catálogo reproducible se genera con:

```powershell
python reconstruccion_cliente_10/housing_rebuilding/build_aa10_housing_rebuilding_manifest.py `
  E:/AAEmu/rama_10/data/sqlite/authoritative/game_decrypted.sqlite3 `
  reconstruccion_cliente_10/housing_rebuilding/generated/aa10-housing-rebuilding-manifest.json
```

## Contrato r575 demostrado

- Feature client/server: `rebuildHouse`, bit 111.
- `CSRebuildHouseTaxInfo` (`0x1AB`): `tl:u16`. El miembro nativo ocupa cuatro bytes,
  pero r575 lo escribe por el slot de serialización `u16`; el cuerpo wire mide exactamente dos bytes.
- `SCRebuildHouseTaxInfo` (`0x2BA`): `tl:u16`, `dr:i32`, `count:u32`, máximo 100; cada entrada es `bt:i32`, `vt:bool`, `pd:f64`, `wp:i32`, `dtr:i32`.
- `StartRebuild` usa `CSStartSkill`, skill-object tipo 7 y un único target
  `housings.id:u32` antes de `inputDirection`. En la aceptación dinámica,
  seleccionar Tradesman's Manor desde la fuente 313 envió `437`; dentro del
  pack 15 esa clave resuelve la definición interna 8.
- Skills nativas: 28828 y 28829, ambas con efecto especial 122 (`RebuildHousing`) y casteo de 6000 ms.
- El cliente calcula el preview desde las propiedades tributables informadas por el servidor, pero el servidor vuelve a validar impuestos, ruta, propiedad, estado, materiales y pago al confirmar.
- `SCHouseTaxInfo.weeksWithoutPay` es `u8` en r575 (serializer `FUN_39a9cdb0`,
  consumer `FUN_39623dc0`). Para una vivienda pagada el valor canónico es `0`;
  el sentinel heredado `-1` cruza el wire como `255` y bloquea el predicado Lua
  `weeksWithoutPay < 1` aunque la UI muestre correctamente `[Prepay n/5]`.

## Política de promoción

- Las definiciones con target, consumer nativo y materiales válidos son ejecutables.
- Las rutas 171 y 174 quedan bloqueadas por `TerritorialSubsystemRequired` porque sus targets 641/644 no traen materiales y pertenecen al subsistema territorial.
- La definición 187 (target 632) queda bloqueada por `MissingMaterials`; AA10 no proporciona ningún coste que permita ejecutarla con seguridad.
- La definición 186 queda bloqueada por `MissingSkillConsumer` (`skill_id=2`, target dummy 1).
- Toda ruta desconocida, manipulada o que no pertenezca al pack de la vivienda se rechaza antes de mutar.
- La evolución exige vivienda terminada, mismo personaje/cuenta propietario, fuera de venta y sin decoración colocada. Los bindings estructurales se retiran y el target se reconstruye por etapas con su catálogo propio.

## Transacción

El planner es inmutable. En el commit se revalidan labor, actability, materiales y certificados bajo los locks de vivienda/labor/inventario. Sólo después del consumo confirmado se cambia la plantilla conservando identidad, dueño, posición, permisos y protección fiscal. La casa vuelve a fase de construcción del target y se retransmite en orden de retirada hijos→padre y creación padre→hijos.

## Gate retail

1. Abrir la placa de una vivienda cuyo template tenga pack y ver el botón de evolución.
2. Seleccionar una ruta: preview, materiales, impuestos y modelo deben corresponder al target.
3. Sin materiales o certificados suficientes, el botón/commit debe rechazar sin consumo ni cambio de casa.
4. Con recursos, el casteo dura 6 segundos y se puede cancelar sin mutación.
5. Al completar, se consumen exactamente recursos/certificados; la misma vivienda cambia al primer paso constructivo del target.
6. Completar construcción, reloguear y reiniciar Game: target, dueño, posición, protección y bindings permanecen sin duplicados.
7. Doble petición o repetición de la ruta ya aplicada no produce segundo consumo.

## Gate estático y despliegue candidato

- `dotnet restore AAEmu.slnx`: aprobado.
- `dotnet build AAEmu.slnx -c Release --no-restore`: aprobado, sin errores.
- Suite unitaria completa: 1.619/1.619 aprobadas.
- Pruebas focales: wire SC, skill-object tipo 7 y planner transaccional, 7/7 aprobadas.
- Manifest reproducible: 223 definiciones, 177 packs, 219 ejecutables y 4 bloqueos explícitos.
- SHA-256 del manifest: `F20FD8A0566ED84995B2432E5B5E748E4920FAFB995019CE201B9DE8E1A361B9`.
- `quick_check` e `integrity_check`: `ok` en full autoritativa, compact retail y runtime.
- Imagen candidata desplegada: `sha256:2ea32cd8d2632b56a5657b9ed2361b4016135821a20de80ecd08b34fe82f126f`.
- Rollback previo: `aaemu-world:rollback-pre-housing-rebuilding-20260828`, `sha256:7b83b9ced4b4c14bb06918528831e3f8a54bb4c4e054e34b1f7b47d306d845e2`.
- Game arrancó sano, sin reinicios, cargó el catálogo esperado y volvió a registrarse en Login.
- Las Zones no fueron iniciadas, detenidas ni reiniciadas durante el despliegue.
- Corrección de despliegue: el bind mount `.server_files/AAEmu.Game/Configurations`
  ocultaba inicialmente el `Features.json` incluido en la imagen. Se sincronizó
  `rebuildHouse=true` en el runtime efectivo y se validó `fset[13]=0x80` junto
  con `Enabled Features: rebuildHouse` antes de repetir el gate retail.
- Estado de promoción: pendiente de aceptación retail antes de commit y push.

## Corrección del gate fiscal interno

La primera aceptación mostró el botón `Remodel`, pero deshabilitado con el
tooltip combinado de venta/deuda/asedio. La vivienda 16 no estaba en venta,
tenía `[Prepay 5/5]` y Solzreed no pertenece a los cuatro `siege_zones` AA10.
La causa era el signedness del byte fiscal: el servidor enviaba `-1`, r575 lo
promovía a `255`, y el propio Lua rechazaba la operación. `HousingTaxState` y
`SCHouseTaxInfoPacket` usan ahora `u8` y emiten `0` para una propiedad pagada.
La suite completa volvió a aprobar 1.619/1.619 pruebas. Imagen candidata del
arreglo fiscal: `sha256:b1238b23eee48323cdad98b02db3141f05a4595008c63f98ff0ec43117eb7224`.

## Corrección del gate de alcance autoritativo

El cliente completaba el casteo visual de la skill 28829, pero Game registraba
`TooFarRange` a 5,77–6,38 m y nunca alcanzaba el efecto 122. Las skills 28828 y
28829 tienen `max_range=4`, mientras la plantilla 313 usa `housing_size_id=5`,
cuyo `garden_radius` AA10 es 11 m. El runtime ya cargaba ese radio, pero
`BaseUnit.GetDistanceTo(House)` lo multiplicaba por un literal heredado `0f` y
medía incorrectamente desde el origen central de la mansión.

La distancia de interacción vuelve a medirse desde el borde de la huella
demostrada (`max(distancia_al_centro - garden_radius * scale, 0)`). Así, la
placa y el perímetro quedan dentro de los 4 m nativos sin habilitar peticiones
remotas: una solicitud más allá de `garden_radius + max_range` conserva el
rechazo autoritativo. Dos pruebas cubren ambos lados del límite y la suite
completa aprueba 1.622/1.622 pruebas.

Imagen candidata desplegada para este gate:
`sha256:ea8dc703aaa1abbd22289b6896a00915c2962c7825b1983f0ec53a3ef8507cd6`.
Rollback: `aaemu-world:rollback-pre-housing-rebuild-range-20260828`,
`sha256:a218f3f105e1600482bdd79e784a4881dd31ebceacc6a08b819e7743092bd2bc`.
Game cargó las 223 definiciones/177 packs, mantuvo `rebuildHouse` habilitado,
reconcilió las 17 viviendas y volvió a registrarse en Login. Las Zones no se
iniciaron, detuvieron ni reiniciaron durante el despliegue.

## Corrección de identidad de ruta en StartRebuild

La primera ejecución que superó el gate de alcance llegó al efecto 122 con
`targetHousing=437`, pero fue rechazada como `RouteDoesNotBelongToSource`. La
captura r575 demuestra que el `u32` del skill-object tipo 7 no es
`housing_rebuildings.id`: es el `rebuilding_housing_type` que Lua obtiene de
`GetHousingRebuildingBaseInfo`, es decir, el target `housings.id`. Para la
fuente 313/pack 15, Tradesman's Manor resuelve `target housing 437` a la
definición interna 8, posición 3.

El selector ahora busca el target exclusivamente dentro del pack de la fuente.
La full contiene 2.958 relaciones y ninguna repite un target dentro del mismo
pack, por lo que la clave es inequívoca sin fallback. El target 437 tiene modelo
final 1760, paso constructivo 0/modelo 1088/skill 29291 y 10 bindings; sus cinco
materiales coinciden con el menú retail. La regresión exacta comprueba que 437
selecciona la definición 8 y que enviar el ID interno 8 no autoriza la ruta. La
suite completa aprueba 1.623/1.623 pruebas.

Imagen candidata desplegada para este gate:
`sha256:d69276e68809757073a87bea5a872ef9c86a2f7673062a20311c53131416e185`.
Rollback: `aaemu-world:rollback-pre-housing-rebuild-target-id-20260828`,
`sha256:ea8dc703aaa1abbd22289b6896a00915c2962c7825b1983f0ec53a3ef8507cd6`.
Game cargó el catálogo, mantuvo `rebuildHouse`, cargó las 17 viviendas y se
registró en Login. Las Zones no fueron operadas durante el despliegue.

## Requisito final de construcción del target 437

La aceptación del cambio de plantilla dejó Tradesman's Manor en su paso
constructivo `0/1`, pero la ventana `Build` no mostraba icono ni requisito. No
era una ausencia de packs en los datos. Full, compact retail y runtime
coinciden en el contrato siguiente:

- `housing_build_steps.id=938`, `housing_id=437`, `step=0`, `model_id=1088`,
  `skill_id=29291`, `num_actions=1`;
- la skill 29291 (`완공시키기`, completar construcción) tiene casteo de 4 s;
- su efecto 46498 consume exactamente `item_id=8329 x1`, sin
  `consume_source_item`;
- el item 8329 es `곤의 황금 망치` (Gon's Golden Hammer), descrito por AA10
  como el martillo usado para completar viviendas construidas o remodeladas.

Por tanto, esta ruta concreta no pide lumber/stone/iron packs en su último
paso. Esos packs pertenecen a otros pasos ordinarios —por ejemplo, las skills
14574, 14575 y 14641 consumen respectivamente los bundles 17683, 17684 y
17685—. Los cinco materiales de remodelación y los certificados ya fueron
consumidos por la transacción inicial.

El icono estaba vacío porque Game no implementaba el consumer de
`CSStartInteraction` para `House`. El cliente r575 espera
`SC_WORLD_INTERACTION_SKILL_LIST` (`0xAC`), confirmado en el x2game.dll
operativo SHA-256 `405242...`: vtable `39e3bd48`, serializer
`FUN_39ab6c90` y lista anidada `FUN_39ab1bf0`. Su body exacto es:

1. target/source como handles BC;
2. source/target BC, `interactionType:u32`, `pickObj:BC`;
3. `count:i32` con máximo 10, `extraInfo:i32`, skills `u32[]`;
4. `mouseButton:u8`, `modifierKeys:i32`.

Game responde ahora con la skill activa del paso y el cliente puede resolver
el Golden Hammer desde su propio catálogo. Además, `Skill.ApplyEffects`
rechaza antes de aplicar cualquier efecto cuando un `consume_item_id` no está
ni en inventario ni equipado; antes omitía silenciosamente el consumo y podía
completar la casa sin el martillo o pack requerido.

Gate estático de esta corrección:

- packet golden y selección de step: 4 regresiones nuevas;
- suite completa: 1.627/1.627;
- manifest: 3/3;
- full autoritativa, compact retail y runtime: `quick_check=ok`,
  `integrity_check=ok`.

Imagen candidata desplegada para el requisito final:
`sha256:d7e1cc55ec92eae5b386212f0736c59384711d2fcd5eb4beb7bd7f811a4783ca`.
Rollback: `aaemu-world:rollback-pre-housing-build-requirements-20260828`,
`sha256:d69276e68809757073a87bea5a872ef9c86a2f7673062a20311c53131416e185`.
Game cargó las 17 viviendas, 223 definiciones/177 packs, mantuvo
`rebuildHouse`, inició sus redes y se registró correctamente en Login. Las
Zones no fueron iniciadas, detenidas ni reiniciadas durante el despliegue.
