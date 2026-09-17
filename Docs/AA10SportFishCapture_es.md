# Pesca: salto y recuperación del pack — 2026-09-16

Target `rama_10`, padre comprobado `upstream/client_version/zone-10.0.2_r575`
`b439e1cc0d4bb96647d11dcb76da61b0246a53e1`. Se conservan los cambios locales de otras tareas.

## Botín corregido

La captura 13093, objeto de mundo 7965, murió a las 22:37:53 UTC mediante `/kill`.
World emitió muerte y estado de botín. Al recogerlo, `CSLootOpenBagPacket` llegó a
`LootingContainer.TryDistributeLootToPlayer`, línea 705 anterior, y falló con
`AcquireDefaultItem(); Unable to add new items`. El comando GM sí pasa por la muerte y generación de botín normales.

Los datos r575 enlazan 13093 → loot pack 7782 → item 27612, y 12979 → 7764 → 27457.
Ambos son `item_backpacks.backpack_type_id=6` (Fish). `IsAutoEquipTradePack` sólo
aceptaba TradePack/TradeGoods; la entrega terminaba en una bolsa que prohíbe esos packs.
Se incluye Fish en la ruta de equipamiento y se conserva el peso, longitud y detalle
del pez generado. La comprobación de bolsa llena se deja para botín de bolsa;
la mochila comprueba por separado si puede apartar el ala. Si falla el equipamiento,
se restaura el ala anterior. Una solicitud repetida sobre una entrada ya retirada no entrega otro pez.

AA8 conserva una regla demasiado amplia (cualquier mochila sin bind-on-equip):
es un comparador estructural; no se copia. Se mantiene la exclusión de alas/banderas.
Clasificación del cambio: `server-required`, sustentado por SQLite AA10 y el error real.

## Salto: protección de login huérfana en Zone

La habilidad 21289 es Hostile; las otras acciones 21096–21099 son Self. La
validación nativa rechazaba 21289 con InvalidTarget (34), porque Dannia conservaba
el buff 2423 LoggedOn en Zone después de que World lo retirase a los 20 segundos.
No depende del rango GM, ni requiere cambiar AI, probabilidades o máscaras de objetivo.

ReplaceZoneUnit limpiaba ZoneBuffRegistry antes de WZUnitState, pero no registraba
los buffs incluidos en ese snapshot. Al caducar 2423, RelayBuffRemovedToZone
suprimía la retirada porque WasCreated devolvía false. El snapshot sí había creado
la entrada nativa; también podían duplicarse buffs posteriores por el mismo olvido.

El serializador ahora devuelve los índices y stacks realmente escritos (respetando
límites 32/20/28 y exclusión de pasivos). Tras enviar el snapshot, PlayerEnterService
registra esas entradas y su RelayedToZone. Reenvía la retirada de entradas que hayan
terminado durante la serialización para cubrir esa carrera. Se reconstruye el estado
actual del personaje antes del reemplazo. El cambio afecta el lifecycle general de
buffs iniciales y de reentrada; no modifica la protección ni su duración nativa.

Evidencia: World `/buff view` sin 2423; ReadProcessMemory en Zone con 2423 y
contador de restricción 1. Sólo el descriptor 2423 entre los buffs activos tenía
el bit de restricción. Lectura de memoria posterior al diagnóstico sin inyección.

DLL x64 x2game-dev_dedicate.dll SHA-256
`8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`, base `0x39000000`.
Anclas RVA: validación AI `0x325cd0`; validación objetivo `0x25a0b0`;
actualización contador BuffMan `0xd2c030`; retirada de buff `0x450420`;
recepción UnitState `0x36b560` y creación `0x36b3c0`.
El gate está en Unit+0x86a0+0x97; descriptor+0x463 bit 1. Excepción tag 3252.
Exports y captura en `forensics/output/aa10-client-forensics/fishing-combat-20260916`.

## Incidente del diagnóstico y limpieza

La instrumentación temporal Frida provocó una caída de Zone142 a las 23:21:32 UTC
(20:21 local). Windows WER identifica frida-agent.dll, excepción 0xc0000409.
Se informó al usuario. El nuevo proceso volvió a conectar; no se repitió la inyección.
`trace-validation.py` está deshabilitado; el diagnóstico restante usa solamente
ReadProcessMemory. No se ejecutaron órdenes de inicio/parada/reinicio de Zone.

Se restauró system.cfg al SHA-256 original
`ec179b437a60fcbcbaff1e88e1e0bb53d54c040085658da6bfadec7554de0e8e` y se retiró
fishing_diagnostic.cfg. No quedan cambios de configuración ni binarios nativos.

## Verificación y entrega

Restore y build Release correctos. Suite: 4.638 pruebas, cero fallos/omitidas.
FishLootTests cubre recogida individual y total con bolsa llena, peso/longitud,
persistencia del detalle, repetición, mochila ocupada y ala sin espacio.
UnitStateBuffSnapshotTests cubre igualdad con registros wire, límites, pasivos,
registro por instancia de Zone, stack y elegibilidad de retirada de LoggedOn.

Pack desplegado y aceptado por el usuario: «Sí, recibí el pack»; recogida observada
23:15:24 UTC. Imagen previa al arreglo del salto:
`sha256:ad5d5587b08ac18ed0785eed8c799026a1329aba42f523b615cfc646308b3ae6`.
Rollback del salto: `aaemu-world:rollback-fish-jump-20260916`.
No hubo cambios en DB, compact ni cliente español.

Snapshot desplegado: `sha256:2cefec6a0f928673ed2f48d55e35e04697b4d0ad136abb85d7805055787ba724`.
Aceptación retail del salto confirmada por el usuario: «efectivamente ya funciona
la tirada hacia arriba». Quedan cerrados ambos síntomas: salto/Gran carrete y
recogida del pack. Esta aceptación es funcional; no se atribuye una nueva lectura
de memoria ni una captura de paquetes a esta confirmación.
El usuario controla Zone142 w_solzreed_1.
El reporte 6 trata requisitos de cañas, no este fallo; no se cambia su estado.

La prueba del salto se aplazó inicialmente y se completó con la confirmación anterior.
