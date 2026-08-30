# Regresión de labor y proficiency AA10 r575

## Síntoma reproducido

Al cortar árboles `doodad` template `393`, la skill `13975` entregaba `Log` y 5 Vocation Badges,
pero no descontaba labor, no añadía Logging proficiency y tampoco otorgaba la EXP derivada de
labor.

La traza de Game cerró el contraste:

- antes del saldo inválido, cada cierre emitía `SCExpChanged (0x13D)`,
  `SCCharacterLaborPowerChanged (0x070)` y `SCGamePointChanged (0x1D0)`;
- durante la regresión sólo se emitía `SCGamePointChanged`;
- SQLite AA10 define para skill `13975`: `consume_lp=10`, `actability_group_id=8` y
  `gain_life_point=5`;
- MySQL conservaba `accounts.labor=-3630` y `local_labor=124` para la cuenta afectada.

Un `/labor 20000` había sumado sobre deuda histórica en el servidor mientras el cliente, cuyo
estado inicial ya clampa labor negativa a cero, mostraba el delta completo como saldo positivo.
El gate de `EndSkill` sumaba el valor firmado negativo con el pool local y omitía el cobro. A la
vez, la entrega de Vocation Badges permanecía independiente del resultado del pago.

## Reparación

`LaborBalancePolicy` define una única proyección para ambos pools:

- deuda persistida se normaliza a cero;
- el saldo disponible nunca incluye valores negativos;
- un gasto se planifica de forma completa o no produce deltas;
- se consume primero el pool de cuenta y después el pool local.

`Character.InitializeLaborCache` repara y persiste saldos inválidos al entrar. Los grants quedan
limitados al rango firmado de la columna y `TrySpendLabor` une descuento, proficiency, EXP y evento
de quest bajo el mismo lock.

`Skill.Use` rechaza con `NeedLaborPower` antes del timeline cuando el coste base de
`skills.consume_lp` no puede pagarse. `EndSkill` confirma el coste final —incluidas las unidades
publicadas por efectos multi-item— y sólo concede Vocation Badges de una skill con coste cuando esa
liquidación tuvo éxito. Las skills explícitamente gratuitas conservan su `gain_life_point` authored.

## Aceptación retail 2026-08-30

Se desplegó únicamente Game con la imagen `sha256:41cfce34764f...`; la imagen anterior quedó
preservada como `aaemu-world:rollback-labor-20260830-134849-0f41bcdc0`. DB y Login conservaron
estado. El perfil nativo `w_solzreed_1` completó `ZWJoin`, `WZJoinResponse`, `ZoneLoaded zoneId=142`
y heartbeats estables.

Al entrar Dannia, Game registró `Normalizing invalid account labor for account 1: -3615 -> 0` y
MySQL quedó en `labor=0`, `local_labor=124`. Una única tala retail con skill `13975` produjo:

- `SCExpChanged (0x13D)`;
- `SCCharacterLaborPowerChanged (0x070)`;
- `SCGamePointChanged (0x1D0)`;
- `local_labor: 124 -> 116` (`8 LP`: `consume_lp=10` por el multiplicador `0.80` de Logging
  rango 5);
- Logging proficiency `63600 -> 64400`, Vocation `906 -> 911` y actualización visible de EXP.

La UI retail confirmó los cuatro resultados. Las pruebas unitarias cubren además normalización,
split entre pools y rechazo por saldo combinado insuficiente sin plan de mutación parcial.

No se requiere ningún cambio en `game_pak`: el defecto y su estado autoritativo están en Game/MySQL.
