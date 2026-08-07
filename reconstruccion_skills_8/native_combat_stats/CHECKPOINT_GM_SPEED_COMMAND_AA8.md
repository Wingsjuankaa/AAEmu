# Checkpoint AA8: comando GM de velocidad

Fecha: 2026-07-30
Build cliente: Kakao 8.0.3.12 r558734
Rama: `client_version/8.0.3.12-kakao-r558734-port`
Base: `214f0dd812e5572646e3ddc854309aace09c679b`
Revisión de rango: `84c940128e8c20951b3a284404685efede4929b0`
## Resultado

Se implementó un comando GM temporal con tres nombres:

- `/speed (target) <1-1000|reset>`
- `/gm_speed (target) <1-1000|reset>`
- `/velocidad (target) <1-1000|reset>`

Cada nivel representa un aumento de 1% sobre la velocidad normal:

- nivel 1: `x1.01`;
- nivel 50: `x1.50`;
- nivel 100: `x2.00`;
- nivel 1000: `x11.00`;
- `reset`: elimina sólo el override creado por este comando.

## Cierre de autoridad nativa

### Vía descartada: `SCUnitGmModeChanged`

La búsqueda inicial localizó `SCUnitGmModeChangedPacket` en el opcode AA8
`0x140`. La decompilación de `x2game.dll` confirmó el layout:

`Bc(unitId) + int32(mode) + byte(value)`

El callback nativo `FUN_39305920` escribe `value` en
`unit + 0x62A8 + mode`. La tabla nativa asociada contiene exactamente nueve
modos:

`invincible`, `cooldown`, `combatlog`, `almighty`, `debug_plot`,
`test_siege`, `live`, `zone_permission`, `test_integration`.

No existe un modo `speed`; usar ese paquete habría supuesto inventar un índice
y arriesgar escritura sobre memoria contigua. Por eso quedó fuera de la
implementación.

### Vía usada: modificador AA8 `MoveSpeedMul`

El compact activo contiene:

- `buffs.id = 3965`;
- nombre nativo: `세트 아이템_이동 속도`;
- `duration = 0`, `system = 1`, `max_stack = 1`;
- un `unit_modifiers` con:
  - `owner_type = Buff`;
  - `owner_id = 3965`;
  - `unit_attribute_id = 10` (`MoveSpeedMul`);
  - `unit_modifier_type_id = 0` (`Value`);
  - `value = 0`;
  - `linear_level_bonus = 100`;
  - `dynamic_value = 0`.

La fórmula runtime AA8 ya implementada calcula:

`value + linear_level_bonus * (AbLevel / 100) = AbLevel`

`MoveSpeedMul` usa base 1000, por lo que 10 unidades nativas equivalen a 1%.
El comando codifica el nivel como `AbLevel = level * 10`.

## Guardas

- Rango estricto 1-1000. El máximo se codifica como `AbLevel = 10000`, dentro
  del rango del campo nativo `ushort`.
- Override no persistente; su índice vive en la instancia de `Character` y se
  pierde al desconectar/recrear la sesión.
- `reset` elimina el buff por índice de instancia, no por ID global.
- Si el personaje ya tiene el buff 3965 por una fuente de juego legítima, el
  comando se niega a reemplazarlo o eliminarlo.
- No se modificó MySQL, `.env`, ningún compact ni datos históricos 3.0.

## Verificación

SDK: .NET Core 3.1.409 en Docker.

- Pruebas focalizadas: 8/8.
- Compilación dinámica de todos los scripts: 0 errores; `Speed` presente en el
  assembly runtime.
- Suite completa: 292/292.
- `git diff --check`: sin errores introducidos por el cambio.

Se reconstruyó la imagen `aaemu-game:0.0.2.0-alpha` y se recreó únicamente el
servicio `game`. El servidor abrió los puertos 2239/2250, conservó el compact
esperado y se registró correctamente en Login.

## Evidencia reproducible

El manifiesto complementario está en
`generated/gm-speed-command-aa8-manifest.json`.
