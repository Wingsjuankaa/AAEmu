# Checkpoint nativo: housing AA10 r575, ola H2

## Estado

H2 está implementada y validada estáticamente; queda pendiente el gate retail
cruzado antes de promoverla como aceptada. Corrige el falso estado de venta de
propiedades no publicadas y hace autoritativos los permisos al plantar y usar
doodads dentro de una parcela.

## Cambios promovidos

- `SCHouseState` usa los campos `SellPrice` y `SellToPlayerId` en sus offsets
  nativos AA10; impuesto y precio dejan de estar mezclados.
- Game y Zone generan exactamente el mismo body de house state.
- Private permite owner y alters de la cuenta propietaria, pero rechaza otra
  cuenta.
- Family, Guild y Public amplían el acceso de acuerdo con la matriz declarada.
- La colocación no autorizada se rechaza antes de consumir.
- La interacción no autorizada se rechaza antes del casteo y se revalida al
  ejecutar el doodad.
- Los cofres mantienen permisos propios y los doodads ajenos a housing no se
  ven afectados.

## Gates estáticos

- build `AAEmu.UnitTests` Release: correcto, cero errores;
- pruebas focales housing/wire: 17/17 correctas;
- suite completa: 1.601/1.601 correctas;
- serializer Game/Zone: igualdad byte a byte demostrada;
- matriz de permisos: owner, same-account, Private ajeno, Family, Guild,
  Public, AlwaysPublic y construcción sin terminar cubiertos.
- `quick_check` e `integrity_check`: `ok` en full, compact retail y runtime.

## Despliegue para aceptación

- imagen activa combinada World/Game:
  `sha256:42895ea80d403c57e45288dba9dd160c04fc4eff95dd3749ae2412b01276b6f8`;
- rollback inmediato:
  `aaemu-world:rollback-pre-housing-h2-20260828`;
- `aaemu10-game-1`: healthy, cero reinicios;
- arranque funcional: 99,27 segundos, puertos Game 1239, Stream 1250 y WebAPI
  publicados, registro en Login correcto;
- 16 propiedades persistidas cargadas por el runtime; la granja 15 mantiene
  owner 1/account 1/Private y `sell_price=0`, `sell_to=0`;
- Codex no inició, detuvo ni relanzó ninguna Zone. El operador debe relanzar la
  Zone desde Control Center antes del gate retail.

## Gate retail decisivo

1. Reloguear con Dannia y abrir la granja privada de Wingsjuanka: no debe
   aparecer `Sale Info` ni `Purchase`, porque `sell_price=0`.
2. Confirmar que Dannia todavía puede plantar/interactuar: ambos personajes
   son account 1 y ese acceso es nativo.
3. Entrar con `Codexwave` (account 2) y, manteniendo la granja en Private,
   intentar plantar un objeto apilable: debe rechazar antes del casteo/consumo;
   el stack, labor y dinero no cambian.
4. Con `Codexwave`, intentar usar o cosechar un doodad ya situado dentro de la
   granja: debe rechazar sin progreso ni mutación.
5. El propietario cambia el permiso a Public; `Codexwave` repite ambas acciones
   y ahora deben estar permitidas. Al volver a Private deben rechazarse otra vez.

La prueba decisiva combina **venta oculta cuando `sell_price=0` + acceso válido
same-account + rechazo sin consumo desde account 2 + promoción Public y
revocación Private**.

## Aceptación retail parcial 2026-08-28

El operador abrió `Solar Scarecrow Farm` con permiso Private y confirmó que la
sección `Sale Info` ya no aparece y que el botón `Purchase` permanece visible
pero deshabilitado por la UI nativa. MySQL conserva simultáneamente las tres
propiedades de Wingsjuanka con `account_id=1`, `permission=0`, `sell_price=0` y
`sell_to=0`; no hubo mutación de venta. Queda aprobado el subgate de
serialización/visibilidad de venta. La promoción final de H2 sigue pendiente de
la prueba negativa con account 2 y del ciclo Public -> Private.
