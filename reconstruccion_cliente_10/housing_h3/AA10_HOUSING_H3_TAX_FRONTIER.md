# AA10 Housing H3 — frontera fiscal de la placa

Fecha: 2026-08-28

Cliente: ArcheAge Returns 10.0.2.13 r575

`x2game.dll` SHA-256: `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`

## Defecto observado

La placa de la casa 16 mostraba `Not paid`, el importe bruto `150000` y el botón
Prepay deshabilitado pese a que el pago por correo ya había extendido
`protected_until` desde siete a catorce días. La base de datos demostraba que el
pago sí se había aplicado; el defecto estaba en el estado SC enviado al cliente.

## Contrato nativo confirmado

La evidencia focal reproducible se conserva fuera de Git en:

`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\housing-h3-tax-frontier`

- `FUN_39a9cdb0` serializa `SCHouseTaxInfoPacket`: `tl`, tasas, dos importes
  `u64`, `due`, `isAlreadyPaid`, `weeksWithoutPay`, `weeksPrepay`,
  `isHeavyTaxHouse`, `taxType`.
- `FUN_3933c3f0` entrega esos campos sin invertirlos al consumer de housing.
- `FUN_39623dc0` conserva `due` y calcula el siguiente periodo como
  `due + 604800` segundos.
- `FUN_39822520` registra `MAX_PREPAID_WEEKS = 5`.
- Los enums nativos son `HOUSING_TAX_SEAL = 1` y
  `HOUSING_TAX_CONTRIBUTION = 2`.
- El Lua retail habilita Prepay sólo para el propietario, con
  `isAlreadyPaid=true`, menos de cinco periodos prepagados y una casa que no
  está en venta.

Archivos de evidencia principales:

- `ghidra-tax-decompile.log`
- `ghidra-tax-registration.log`
- `ghidra-tax-consumer.log`
- `ghidra-tax-client-registration.log`
- `ghidra-tax-event.log`

## Corrección promovida

- `HousingTaxState` deriva de forma pura pago, mora y prepago desde el deadline
  persistido, sin estado inventado en memoria.
- El paquete envía `isAlreadyPaid` con su semántica nativa, no el antiguo
  `requiresPayment` invertido.
- Cuando el servidor usa certificados se envía `taxType=1`; la contribución en
  moneda usa `taxType=2`.
- Prepay se bloquea en venta, fuera de estado pagado y al alcanzar 5/5.
- Pago, inventario y extensión se serializan por vivienda; materiales repetidos
  se revalidan y consumen como un batch antes de publicar tareas.

El año que la UI antepone a `Protected Until` es el año calendario (`2026 yr`),
no una duración de dos mil años. Las viviendas residenciales examinadas tienen
deadlines de 2026; los deadlines 2043 pertenecen a Archeum Lodestones
territoriales sin propietario y quedan fuera de H3.

## Aceptación retail y localización inglesa

El usuario confirmó en retail el 2026-08-28 que pago, Prepay, límite 5/5 y
persistencia tras relog funcionan. La captura final mostró `Protected Until`
como 16 de octubre de 2026 después de cinco extensiones desde el 11 de
septiembre: `2026-09-11 + (5 * 7 días) = 2026-10-16`.

El Lua AA10 llamaba
`locale.time.GetDateToDateFormat(taxInfo.dueTime)` sin filtro, por lo que el año
calendario formaba parte del panel con sintaxis de duración. La presentación
poco natural `2026 yr Month: 10 16 d PM 12 h 35 muntil` procede de combinar el
formatter genérico con las cadenas `en_us` del compact retail. Cambiar esas
cadenas globales no es seguro: también alimentan duraciones, tooltips y timers.

El defecto `client_en_us_localization_defect` se corrigió de forma acotada en
los consumers de Housing:

- `maintain_window.alb` usa el formatter calendario nativo y no agrega el
  sufijo redundante `until` a una fila ya titulada `Protected Until`;
- `maintain_window_view.alb` usa el mismo formatter para la fecha mostrada al
  prepagarse impuestos;
- timestamps, pagos, periodos y localizaciones globales permanecen intactos.

La API elegida no procede de AA8: el source AA10 r575
`game/scripts/x2ui/baselib/locale_helper.lua`, SHA-256
`CE03C1BAE303FA2BB4DDA9BB7A605B70076276CDCF54E3A300C249EA1129EE6A`,
define `GetDateToSimpleDateFormat(df)` como consumer de
`baselibLocale.GetSimpleDate` con los seis campos del timestamp.

El builder exacto es `Scripts/PatchAa10HousingDateFormatting.py`; la extracción,
rollback, reinserción y verificación reproducibles están en
`Scripts/ApplyAa10HousingDateGamePakPatch.ps1`. El `game_pak` conservó
`68.963.258.880` bytes y cambió de
`AB3B86E694CFC0141453AD9B734BABEE67019C58D8E0B52498036ABC0DCBCBF0` a
`31784B61D91E6E26A87CA67997EADAC77047E1095E2588620BAD40A4D68E1315`.
La segunda ejecución fue idempotente. Aceptación visual retail: **aprobada el
2026-08-28**. La placa mostró `2026. 10. 16. 12:35:05`, sin unidades de duración
ni el sufijo concatenado `until`.
