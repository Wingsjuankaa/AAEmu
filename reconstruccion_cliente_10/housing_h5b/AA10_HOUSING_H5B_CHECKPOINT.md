# Checkpoint AA10 Housing H5-B — agua, parcelas funcionales y refresco de remodelado

## Frontera

- Cliente: ArcheAge Returns `10.0.2.13-r575`.
- Rama: `rama_10`.
- HEAD de apertura: `d1b148c77a2f56384335abe9198967387a118336`.
- Upstream r575: `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- H5-B promueve únicamente proveedores residenciales de agua y grafos cerrados
  de parcelas nativas: maceteros y corrales Rancher. Quest, pack storage y otros
  servicios H5 continúan fuera de esta frontera.

## Evidencia AA10

El consumer se reconstruye mediante la intersección full/compact retail/compact
runtime del grafo:

```text
doodad_funcs (DoodadFuncUse + skill existente)
  -> doodad_func_loot_items (item 15694 Water, rango y percent válidos)
  -> doodad_phase_funcs/DoodadFuncTimer (delay y next_phase válidos)
```

Se exige además que el doodad contenga exactamente `DoodadFuncUse`,
`DoodadFuncLootItem` y `DoodadFuncTimer`. Las tres proyecciones coinciden sin
divergencias y demuestran diez consumers: `5539`, `9344`, `9798`, `10698`,
`13119`, `13492`, `14769`, `17161`, `17637` y `18226`.

De ellos, `9798` no tiene binding y `10698` sólo está ligado a categoría 33 no
residencial. La promoción retail queda por tanto limitada a ocho doodads,
25 bindings y 25 plantillas residenciales. No existe lista manual en runtime:
el builder deriva y deja registrada esta frontera.

La Thatched Farmhouse, plantilla `330`, queda 6/6 ejecutable. Su barril es el
doodad `5539`, attach `9`, helper AA10 demostrado y salida nativa Water `15694`.

La intersección full/compact retail/runtime demuestra además el macetero nativo
`9108`, cuyo grafo cerrado contiene `Use`, `ItemChangerUiOpen`, `ItemChanger`,
`Growth`, `RatioChange`, `Timer` y `LootPack`. Está vinculado 73 veces en 37
plantillas residenciales. La Thatched remodelada, plantilla `434`, aporta dos:
attach points `42` y `43`, ambos con transformación AA10 demostrada. El doodad
`13697` queda fuera por no tener bindings residenciales promovibles.

El corral `9352` comparte ese consumer completo y añade únicamente
`DoodadFuncPlayFlowGraph`, con sus filas visuales demostradas en las tres bases.
Está ligado exactamente tres veces a las plantillas Rancher `403`, `418` y
`433`, siempre en attach point `44`. En particular, `433` usa el modelo AA10
`1756` y el helper sitúa el corral en `(-2.4491308, -4.019658, 1.7156802)`.
Harvester `432` conserva tres campos `9108`; Miner `434` conserva dos campos y
su veta `9350`. No existe sustitución manual de modelos entre variantes.

## Semántica reparada

- probabilidad nativa expresada sobre `0..10000`, con `10000` siempre exitoso;
- `count_min..count_max` inclusivo, por lo que el agua `3..10` puede entregar 10;
- caster no personaje y rangos inválidos fallan cerrados, sin excepción;
- el binding sólo avanza de fase si el ítem fue realmente adquirido;
- inventario lleno conserva la fase para reintentar y devuelve el error normal;
- permisos residenciales continúan validándose antes de programar el skill.
- `DoodadFuncItemChangerUiOpen` sólo abre el flujo nativo del cliente; la
  selección vuelve por `CSDoodadItemChanger`, que revalida fase, skill, item,
  cantidad, distancia y permiso antes de consumir;
- al iniciar una remodelación se retira el agente visible anterior y se recrea
  la casa con el mismo `ObjId` mediante la secuencia normal de alta del cliente:
  unidad, estado de housing, facción, hijos supervivientes, resumen y progreso.
  Esto reemplaza el proveedor de interacciones asociado a la plantilla anterior
  sin borrar ni recrear la vivienda autoritativa.

## Catálogo determinista

- 837 plantillas catalogadas;
- 4.646 bindings en 631 plantillas;
- 3.990 ejecutables y 656 bloqueados;
- 102 bindings `force_db_save` preservados;
- 25 bindings de agua promovidos;
- 76 bindings de parcelas promovidos (`9108` y `9352`) en 37 plantillas;
- 336 permanecen `PendingWavePromotion`.

Hashes reproducidos en dos extracciones independientes:

- catálogo H5-B: `9D21CB25D1F8100BC9AFC5200CDB343D1743FD47A81546EC54623A5C40BAED54`;
- helpers/modelos: `3A252BCEFC00F75F4C626863BEBB4BCEBF7E771600E5B56DCFC07C53B2FCC247`;
- manifest: `3B147F21E46EC68B55B5D3FF74EE0ECF30A296CB34CE5B2DE900EF01D04D40E1`.

## Validación automatizada

- `dotnet restore AAEmu.slnx`: correcto;
- build completo Release: 0 errores;
- suite TUnit actual: 1.657/1.658 pruebas pasan; el único fallo es el histórico
  `MoneyTest`, dependiente de un destinatario ausente en el entorno
  (`UnableToFindRecipient`) y ajeno a Housing;
- suite focal H5-B/remodelado/nombres: 29/29, 0 fallos;
- tests de política: residencial positivo, no residencial negativo, loot no
  demostrado negativo y conservación de H5 crafting;
- tests de loot: percent, borde 9999/10000, máximo inclusivo, rango fijo e
  inválido;
- full, compact retail y compact runtime: `quick_check=ok` e
  `integrity_check=ok`;
- `git diff --check`: sin errores (sólo aviso histórico LF/CRLF de Features).

## Gate retail aprobado — 2026-08-29

1. El barril aparece en la Thatched en su helper correcto y ofrece F.
2. F ejecuta el casteo nativo y entrega entre 3 y 10 Water.
3. El timer repone la interacción y permite volver a usarla.
4. Con inventario lleno no se entrega agua ni se pierde la fase.
5. Click múltiple no duplica entrega ni deja el barril bloqueado.
6. Private rechaza cuenta externa; el propietario continúa habilitado.
7. Relog y reconexión de Zone no eliminan ni duplican el barril.
8. Tras iniciar una nueva remodelación, el martillo, los requisitos y la acción
   G aparecen inmediatamente, sin relog.
9. La Thatched remodelada `434` muestra dos maceteros en los helpers 42/43.
10. Cada macetero abre la selección, consume una sola vez la opción AA10 válida,
    progresa, permite cosechar y vuelve a su fase vacía; item/skill/cantidad o
    permiso inválidos no consumen ni cambian fase.

El usuario aprobó en retail el barril, los maceteros, la recarga inmediata de
requisitos y la acción G sin relog. La ola queda autorizada para commit y push.

## Despliegue

- Imagen candidata anterior, agua aprobada:
  `sha256:5ced9450a1af04730ec6e60bcb6cbf4d59518776e6a7196591bfce73358dffff`.
- Nueva imagen candidata de refresco/maceteros:
  `sha256:737a4d543e4da5026facd23d6e8e4ecaa81b22f48eab0ca5a58771169caa28e7`.
- Rollback inmediato de la candidata de agua ya aprobada:
  `aaemu-world:rollback-pre-housing-h5b-planters-refresh-20260829`, imagen
  `sha256:5ced9450a1af04730ec6e60bcb6cbf4d59518776e6a7196591bfce73358dffff`.
- Rollback: `aaemu-world:rollback-pre-housing-h5b-20260829`, imagen
  `sha256:0ed221912e1d6ce3c1c331cddd814e39bd57d46966e2695119186788385b91cf`.
- Catálogo de la nueva candidata:
  `68C7FC1B32CF0828652BC4085921BF2CF594AA56DE552994A31458C16D905F42`.
- Game/World: `healthy`; cargó 4.646 bindings/631 plantillas, retransmitió las
  17 viviendas y completó `AA10 housing binding reconciliation`.
- Login y DB permanecen `healthy`.

Codex no inició, detuvo ni reinició Zones; la Zone 142 queda bajo control del
usuario y debe ser relanzada por él para el gate retail.

## Corrección final del refresco en tiempo real

La primera candidata H5-B retransmitía únicamente estado sobre la unidad ya
visible. Retail demostró que eso no basta: la transición `330 -> 432` se
confirmaba y persistía, pero la ventana `Build` quedaba sin requisito y el
cliente no ofrecía G hasta relog. El log de la prueba no contenía
`CSStartInteraction`, por lo que el rechazo ocurría antes del consumer de
materiales: el cliente conservaba el proveedor de interacción de la plantilla
anterior.

El consumer nativo muestra que `X2::GameClient::HousingManager` mantiene datos
por vivienda y dispone de un lifecycle explícito de retirada. La reparación
reproduce ese límite observable sin inventar wire ni cambiar identidad:

1. los bindings estructurales anteriores se retiran hijos -> padre;
2. `SCUnitsRemoved` invalida el agente visible asociado al template viejo;
3. se recrean `SCUnitState` y `SCHouseState` con el mismo `ObjId` y el nuevo
   template/paso;
4. se restaura la facción y luego los doodads supervivientes, padre -> hijos;
5. `SCHouseData` y `SCHouseBuildProgress` cierran el snapshot del panel.

La vivienda sigue siendo la misma fila, conserva `Id`, `ObjId`, dueño,
posición, protección y transacción ya confirmada. No se elimina del mundo ni de
la base de datos y la construcción permanece idempotente.

Gate automatizado de esta corrección:

- regresión focal del lifecycle: 3/3;
- restore y build Release: correctos, 0 errores;
- suite completa: 1.652/1.653; único fallo histórico `MoneyTest` por
  `UnableToFindRecipient`;
- catálogo reproducido sin diferencias: 4.646 bindings, 3.987 ejecutables,
  hash `68C7FC1B32CF0828652BC4085921BF2CF594AA56DE552994A31458C16D905F42`;
- manifest reproducido con hash
  `CACAA2F423CF52A9D4F7004F37C04CD0C4CFB6EB477D5D07A485186FEA318B2B`;
- full, compact retail y runtime: `quick_check=ok`,
  `integrity_check=ok`;
- `git diff --check`: sin errores (sólo el aviso LF/CRLF histórico de
  `Features.json`).

Gate retail decisivo aprobado: una nueva remodelación mostró inmediatamente,
sin relog, el martillo/requisito y la acción G.

Despliegue candidato del lifecycle remove -> create:

- imagen: `sha256:b1cf59ff21ffde2b802f7961466354190bf6782a321cfc9ecdc555dca9713558`;
- rollback inmediato:
  `aaemu-world:rollback-pre-housing-rebuild-agent-refresh-20260829`, imagen
  `sha256:737a4d543e4da5026facd23d6e8e4ecaa81b22f48eab0ca5a58771169caa28e7`;
- Game/World: `healthy`, 0 reinicios; cargó 4.646 bindings/631 plantillas,
  837 templates y 223 rutas de remodelación/177 packs;
- reconciliación de bindings completada, redes 1239/1240/1250 iniciadas y
  registro en Login exitoso;
- `rebuildHouse` permanece habilitado en el `fset` efectivo;
- no se inició, detuvo ni reinició ninguna Zone. El disconnect registrado al
  reemplazar Game es el esperado y la Zone debe ser relanzada por el usuario.

## Corrección final — corral Rancher y nombres de variantes

Retail aprobó el refresco inmediato de requisitos de construcción y los dos
maceteros remodelados. La prueba siguiente demostró dos defectos distintos en
las variantes de Thatched:

1. la remodelación `330 -> 433` sí persistía la plantilla Rancher y su modelo
   principal `1756`, pero el binding `433/44/9352` permanecía bloqueado como
   `MissingConsumer`; al faltar el corral, la silueta funcional parecía la de
   Harvester;
2. `TryRebuildHouse` cambiaba template/modelo, pero conservaba el nombre por
   defecto de la plantilla origen. Las casas ya remodeladas también habían
   persistido ese nombre antiguo.

La reparación amplía el cierre del consumer de parcelas sólo cuando el grafo
AA10 es exactamente el del macetero o ese mismo grafo más el
`PlayFlowGraph` demostrado. La intersección full/compact retail/runtime produce
tres consumers nativos (`9108`, `9352`, `13697`), de los cuales sólo `9108` y
`9352` tienen bindings residenciales promovibles: 76 bindings en 37 plantillas.
El corral Rancher queda promovido únicamente para `403`, `418` y `433`.

La política de nombres actualiza el nombre al localizado de destino sólo si el
valor actual está vacío o coincide exactamente con un nombre por defecto de
una plantilla que posee una ruta entrante hacia el destino. Se guardan IDs de
plantilla y se resuelven los nombres después de `PostLoad`, evitando mezclar los
nombres coreanos de la base con la localización inglesa. Los nombres escritos
por jugadores se conservan. En el arranque candidato se normalizaron cuatro
casas legacy; las siguientes remodelaciones cambian el nombre dentro de la
misma transacción lógica.

Validación:

- restore y build Release: correctos, 0 errores;
- focal catálogo/política/nombres: 29/29;
- suite completa: 1.657/1.658; único fallo histórico `MoneyTest` por
  `UnableToFindRecipient`;
- catálogo reproducido dos veces, sin diferencias: hash
  `9D21CB25D1F8100BC9AFC5200CDB343D1743FD47A81546EC54623A5C40BAED54`;
- manifest determinista:
  `3B147F21E46EC68B55B5D3FF74EE0ECF30A296CB34CE5B2DE900EF01D04D40E1`;
- full, compact retail y runtime: `quick_check=ok`,
  `integrity_check=ok`;
- `git diff --check`: correcto; sólo queda el aviso histórico LF/CRLF de
  `Features.json`.

Despliegue candidato:

- imagen: `sha256:342284170557850ac2f0c4c6a7b606c45d77597caa2a9bc5d8170b510a57bed5`;
- rollback de imagen:
  `aaemu-world:rollback-pre-housing-h5b-rancher-name-20260829`, imagen
  `sha256:b1cf59ff21ffde2b802f7961466354190bf6782a321cfc9ecdc555dca9713558`;
- rollback de catálogo:
  `E:\AAEmu\rama_10\backups\feature-reconstruction\aa10-housing-h5b-rancher-name-20260829\housing_interactions_aa10_h5b.before.json`, hash
  `68C7FC1B32CF0828652BC4085921BF2CF594AA56DE552994A31458C16D905F42`;
- Game/World `healthy`, 0 reinicios; cargó 4.646 bindings/631 plantillas,
  normalizó cuatro nombres legacy, reconcilió bindings y se registró en Login;
- Login y DB permanecen `healthy`;
- ninguna Zone fue iniciada, detenida ni reiniciada por Codex.

Gate retail aprobado — 2026-08-29:

1. relanzar la Zone y entrar con la casa `19` ya remodelada;
2. el nombre superior y el panel F deben mostrar `Rancher's Farmhouse`;
3. el corral debe aparecer en su helper nativo y abrir su selección de animales;
4. una selección válida consume una vez, progresa y permite la recolección
   correspondiente; skill/item/cantidad, distancia o permiso inválidos no
   consumen ni cambian fase;
5. Harvester conserva sus campos y Miner conserva campos/veta, con los nombres
   `Harvester's Farmhouse` y `Miner's Farmhouse`;
6. relog y reconexión de Zone no eliminan ni duplican el corral ni revierten el
   nombre.

El usuario confirmó que la variante Rancher, su nombre, corral e interacciones
funcionan correctamente. También quedaron validadas las variantes Thatched ya
probadas y la persistencia tras relog. Commit y push autorizados.
