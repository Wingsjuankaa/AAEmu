# Sincronizacion visual de Battle Focus

## Diagnostico confirmado

La prueba en cliente demostro que el servidor aplicaba Battle Focus al combate,
pero Character Info conservaba el porcentaje previo.

No faltaba un paquete adicional de refresco. El lector nativo de
`SCBuffCreated` en `x2game.dll` confirma un campo `stack`, y el grafo de datos
AA8 confirma esta cadena:

`skill 10377 -> effect 37079 -> buff_effect 12188 -> buff 7651 -> stack 1`

El loader del servidor ya conservaba `buff_effects.stack`, pero ese valor se
descartaba al crear el objeto runtime `Buff`. Como consecuencia,
`SCBuffCreatedPacket` enviaba siempre `stack=0`: el cliente mostraba el icono y
la duracion, pero no incorporaba los `unit_modifiers` del buff a sus
estadisticas locales.

## Correccion

- `BuffEffect.Stack` se propaga a `Buff.Stack`.
- Los buffs creados sin `BuffEffect` usan un stack inicial de 1.
- `SCBuffCreatedPacket` serializa el stack nativo.
- No se agrego ningun paquete de refresco supuesto.

## Evidencia y validacion

- `buff_effects.id=12188`, `buff_id=7651`, `stack=1`.
- Buff 7651: atributo 81 `MeleeParryMul=300`.
- Buff 7651: atributo 17 `MeleeCriticalBonus=200`.
- El layout del paquete fue contrastado con el lector AA8
  `FUN_399b2960 -> FUN_399b10a0`.
- La regresion automatica pasa 70/70 pruebas.
- La compact `compact-8.0-runtime-native-combat-stats-v1.sqlite3` permanece
  activa en Docker.

## Resultado esperado

Con la base visual del cliente en 7,8%, Battle Focus rango 2 debe mostrar
aproximadamente:

`7,8% -> 37,8% -> 7,8%`

La formula base autoritativa del servidor sigue siendo una auditoria separada:
antes del buff calcula 2,238% y durante el buff 32,238%. Esta discrepancia no
debe ocultarse ni resolverse copiando formulas 3.0.
