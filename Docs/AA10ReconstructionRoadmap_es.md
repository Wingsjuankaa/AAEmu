# Roadmap visible de reconstrucción AA10

Fecha de corte: 2026-09-03
Target: ArcheAge Returns 10.0.2.13 r575, branch `rama_10`
Backlog exhaustivo: [AA10ReconstructionBacklog_es.md](AA10ReconstructionBacklog_es.md)

Este documento es la cola operativa. Una mecánica sólo avanza a `ACEPTADA` cuando tiene autoridad
AA10, negativos, persistencia, wire, cliente retail y regresión. `Implementada` no significa
`aceptada`: el feature sólo se expone después de los gates estáticos y automáticos para una
aceptación retail controlada.

| Orden | Mecánica | Estado | Clasificación | Evidencia actual | Dependencias | Criterio de aceptación |
|---:|---|---|---|---|---|---|
| 1 | Item Lock | NÚCLEO RETAIL ACEPTADO; bit 45 ON | Reconstrucción retail AA10 | SQLite, compact, Lua `item_lock`, localización, cuatro C2G, serializer, políticas, pruebas y aceptación visible del usuario | Ampliar matriz de unlock/bulk sin reabrir el núcleo aceptado | Badge visible, relog y venta bloqueada confirmados; conservar regresión de 72 h y bulk |
| 2 | Loot Gacha | ACEPTADA Y CERRADA; bit 160 ON | Reconstrucción retail AA10 | Feature 160, Lua, tipo 16, opcodes 0x2E2-0x2E4, catálogo 11/24/30, persistencia, cast, countdown, stock agregado y tiers 3–8 aceptados | Conservar regresión de catálogo, pity y multi-stack | Seis asociaciones metálicas, `Max=269`, UI, rewards y probabilidades nativas confirmadas |
| 3 | ArchePass: missions y reroll | CICLO VALIDADO CERRADO POR USUARIO; pendientes delimitados abajo | Reconstrucción post-lanzamiento | Registro/cambio, puntos, claims, premium y cuarta misión aceptados; almacenamiento reparado; 1756 tests | Reroll, rollover y completado final permanecen en backlog, fuera del cierre validado | Conservar gates aceptados sin declarar probadas las rutas restantes |
| 4 | Item Smelting | EN INVESTIGACIÓN; IMPLEMENTADO/OCULTO | Reconstrucción retail AA10 | Feature 178, skill 35525, skill-object 20 y resultado 0xCF | Resolver outputs43482/43489 y selector29; receta5 sólo es fixture, no ruta retail probada | Resultado/coste/RNG exactos y bloqueos incompletos fail-closed |
| 5 | Housing H2/H5-B | PARCIAL | Reconstrucción retail AA10 | Catálogo, paquetes, políticas y checkpoints housing | Ownership cross-account, persistencia y recovery | Colocar/reconstruir/recuperar con relog y rollback exacto |
| 6 | Gaps de quests | PARCIAL | Reconstrucción legacy y AA10 | Objetivos, handlers y campaña Phase 6 | Primitivas de interacción y persistencia | E2E con repetición, relog y rewards idempotentes |
| 7 | Primitivas compartidas | PENDIENTE | Infraestructura server-required | TODO de Projectile, Resurrection y TeleportToUnit | Contratos nativos por consumer | Consumidor principal y uno no relacionado pasan A/B y suite |
| 8 | Community + Craft Orders | APAGADO RECONSTRUIBLE | Reconstrucción post-lanzamiento | Tablas `resident_*`, `craft_order_*`, UI/wiki | Mail escrow, Community state y recovery | Escrow idempotente, cancel/expiry/relog sin pérdida ni duplicación |

## Regla de continuación

El orden 1-8 queda fijado. El resto conserva el ranking del backlog exhaustivo. Sólo se salta una
entrada si su checkpoint demuestra un blocker externo o nativo; el motivo y el siguiente gate se
registran aquí antes de comenzar otra mecánica.

## Item Lock: salida aceptada

- Imagen desplegada: `sha256:bc4de4a6163afd09851bc41f0eebedd5eef1791273015de5d751dd4f29c981fb`.
  El primer arranque confirmó el bit apagado; después se reactivó en fuente y runtime para la
  aceptación controlada del usuario. Zone no fue iniciada ni relanzada por Codex.
- Segundo arranque: Game healthy, `Server started!`, fset byte 5 `0x29`, `itemSecure` habilitado y
  GameServer 1 registrado nuevamente en Login.
- Dossier: [AA10ItemLockReconstruction_es.md](AA10ItemLockReconstruction_es.md).
- Checkpoint: [CHECKPOINT_NATIVE_ITEM_LOCK_V1.md](../reconstruccion_cliente_10/checkpoints/CHECKPOINT_NATIVE_ITEM_LOCK_V1.md).
- Aceptación del usuario (2026-09-03): el item muestra el lock, conserva el estado al reloguear y
  la tienda rechaza su venta. El ciclo extendido de unlock/bulk permanece como regresión, no como
  bloqueo para continuar la cola.

## Loot Gacha: salida actual

- Imagen con `Max` multi-stack corregido desplegada:
  `sha256:251f07433478e1cb6abdc89d0c1e5b2c3514559ead66d2c64daa7c112cbc3c46`;
  rollback inmediato `aaemu-world:rollback-pre-gacha-multistack-fix-20260903-082033`.
- Build completo sin errores, 1.723/1.723 pruebas, migración persistente aplicada y arranque
  Game healthy con `lootGacha` habilitado. Login y DB no fueron recreados; Zone no fue operado por
  Codex.
- Dossier: [AA10LootGachaReconstruction_es.md](AA10LootGachaReconstruction_es.md).
- Checkpoint: [CHECKPOINT_NATIVE_LOOT_GACHA_V1.md](../reconstruccion_cliente_10/checkpoints/CHECKPOINT_NATIVE_LOOT_GACHA_V1.md).
- El primer gate confirmó ventana, consumo y reward. Reveló que `leftCount` se interpretaba como
  stock (9), dejando al cliente en estado de trabajo. La evidencia nativa cerró el contrato como
  rondas pendientes y se desplegó el countdown `N-1 ... 0`.
- El segundo gate confirmó unidad, lote 3 y reactivación de Confirm. `Max` con 300 reveló un límite
  servidor de debug incorrecto: la UI retail usa el menor stack completo. La corrección quedó
  validada y desplegada.
- El tercer gate confirmó lotes 11 y 20. `Max` 269 reveló que las cajas estaban repartidas como
  100+100+69 y el servidor revalidaba una sola instancia. Lua usa el total por template; el
  preflight/consumo multi-stack quedó corregido, cubierto por regresión 269 válido/270 inválido y
  desplegado en Game healthy con registro Login correcto. Login/DB no fueron recreados y Zone no
  fue operado.
- El usuario confirmó después `Max=269`: consumo multi-stack, rewards y finalización de UI
  correctos. Ese gate queda aceptado.
- Gate final aceptado por el usuario: las seis asociaciones metálicas activas de los packs 3–8,
  correspondientes a las dos familias cobre/plata/oro, abrieron correctamente con sus llaves.
- Auditoría final de Silver: 100 aperturas entregaron 108 Superior Glow Lunarite, 3 Moonpoint y
  `1.123g 88s`. El resultado es compatible con el catálogo y las tasas r575: la media teórica del
  pack base es 109,34 lunarite por 100, el pity común ocurre cada 20 rondas y el raro conserva
  `0,0025%` desde ronda 30 con pity en 300. No se detectó una reducción ni un desvío servidor.
- Loot Gacha queda cerrada. La siguiente entrada operativa es ArchePass: misiones y reroll.

## ArchePass: registro visible

- Primer corte desplegado para aceptación retail: la respuesta a `CSArchePassBuy` ahora usa
  `SCUpdateArchePassPacket` con estado `Owned` y el `reason=6` nativo que genera
  `ARCHE_PASS_BUY`. La carga/reconexión conserva la página completa `SCArchePassesPacket`.
- Imagen desplegada: `sha256:472f1457dfdfed9dc36c102b46e454479fcef0e63b97a385ea6e44aa55b608e0`;
  rollback inmediato `aaemu-world:rollback-pre-archepass-buy-ui-20260903-132900`.
- Build Release correcto y suite completa `1724/1724`. El arranque cargó 97 pases/3.028 tiers,
  mantuvo `arche_pass` habilitado, levantó Game healthy y registró GameServer en Login.
  Login y DB conservaron sus contenedores; Zone no fue iniciada ni relanzada por Codex.
- Gate manual pendiente: comprar/registrar un pase en un personaje sin pase abierto y confirmar
  que el panel lo muestra y selecciona inmediatamente, además de conservarlo tras relog.
- Diagnóstico del primer gate: `Dannia` ya tenía el pase 48 persistido como `Owned`. El servidor
  imponía erróneamente una sola entrada registrada y rechazaba el segundo pase antes del cobro.
  `X2ArchePass:IsFull()` en r575 cuenta `Owned/Progress` y sólo se llena en seis; la UI muestra el
  mismo límite. La política corregida admite seis registrados y mantiene como invariante separado
  un único pase activo (`Progress`).
- Segundo corte desplegado: build integral Release y `1730/1730` pruebas correctas; imagen
  `sha256:452cc81cd99700314677793da6f19c9cccfce2c08bc74f73bcf01cfdf1d9705d`,
  rollback `aaemu-world:rollback-pre-archepass-capacity-fix-20260903-112653`. Game quedó healthy,
  cargó 97 pases/3.028 tiers y registró GameServer 1. Login/DB fueron preservados; Zone no fue
  iniciada ni relanzada por Codex.
- El segundo gate envió dos veces `CSArchePassBuy(type=88)` y fue rechazado antes de cobro/packet.
  `Adventurer Growth` es la única fila AA10 con `ed_year=23`; el loader la promovía sin autoridad
  a 2023. `GetStatus` r575 no aplica esa promoción y el cliente muestra `23.03.30`, conserva el
  estado comprable y transmite la solicitud. Se retiró sólo esa normalización; los cinco pases
  habilitados con fecha completa ya vencida siguen cerrados. Build/suite del candidato:
  `1731/1731`.
- Tercer corte desplegado: imagen
  `sha256:053337a5d35b5a503b758fb7a8c59fe8e803bca2cf8bd8035f1276539d0df8c7`, rollback
  `aaemu-world:rollback-pre-archepass-type88-date-fix-20260903-114605`. El loader pasó de 28 a
  29 pases comprables, Game quedó healthy y registró GameServer 1; Login/DB fueron preservados y
  Zone no fue operada por Codex.
- El tercer gate sí registró type 88: `15:57:32` confirmó commit `Owned`, ocupación `2/6`,
  `SCUpdateArchePass 0x33F` y persistencia junto al type 48. El segundo clic fue rechazado como
  duplicado. La UI siguió atrasada porque el serializer común confundía layout x64 en memoria con
  wire. `FUN_39a3d7e0` (RVA `0xA3D7E0`) exige type, lastRewardTier,
  lastPremiumRewardTier, point, premium y status; `FUN_39aba690` (RVA `0xABA690`) añade
  `reason, diffPoint, allDone`. El cuarto corte corrige tanto `0x33D` como `0x33F` y fija sus bytes
  exactos con fixtures; aceptación visible pendiente tras el despliegue.
- Cuarto corte desplegado: build/suite `1731/1731`, imagen
  `sha256:fdf9a0a20225cdf09f783b5699e8be72c09a734ef077869f1f53d39f16e16330`, rollback
  `aaemu-world:rollback-pre-archepass-wire-order-20260903-120528`. Game cargó 97 pases/3.028
  tiers (29 comprables), quedó healthy y registrado en Login. DB conservó type 48 y 88 para
  Dannia; Login/DB no fueron recreados y Zone no fue operada por Codex.
- El cuarto gate mostró type 88 con la marca amarilla `Owned`. `CSArchePassStart 0x1FA` avanzó
  correctamente la persistencia a `Progress`, pero la respuesta de éxito era una página `0x33D`
  y no emitía el evento de UI. El quinto corte cambia sólo ese éxito a `SCUpdateArchePass 0x33F`
  con `reason=4`, contrato que dispara `ARCHE_PASS_STARTED`; fixture binario añadido y aceptación
  visible pendiente.
- Quinto corte desplegado: build/suite `1732/1732`, imagen
  `sha256:2df0ca029159bee06870eac1434e98d2ed9f65d137668cff4665a3834db8bc51`, rollback
  `aaemu-world:rollback-pre-archepass-start-event-20260903-124946`. Game cargó 97 pases/3.028
  tiers (29 comprables), quedó healthy y registrado en Login. La persistencia conserva type 48
  `Owned` y type 88 `Progress`; Login/DB no fueron recreados y Zone no fue operada por Codex.
  Gate pendiente: relanzar Zone manualmente, entrar con Dannia y abrir directamente Daily
  Schedule → ArchePass sin volver a pagar ni pulsar Start; el panel debe poblarse desde el estado
  `Progress` persistido.
- El gate posterior compró `Hellwraith Kirin` (type 19): la estrella amarilla y el log de
  `18:09:59` confirman `Owned`, cobro único y `SCUpdateArchePass reason=6`. El panel conservó el
  type 88 activo porque Buy y Start son dos fases nativas. El mismo botón de la ventana llama
  `BuyPass` si el estado es invalid/dropped y `StartPass` en el segundo clic si es `Owned`.
- Sexto corte desplegado para permitir el cambio real de pase: el anterior pasa `Progress → Owned`
  sin perder progreso y el seleccionado pasa `Owned → Progress`; se envían `reason=5` y luego
  `reason=4` para refrescar selector y panel. Build/suite `1736/1736`, imagen
  `sha256:f8a698878264e1eee4db6effc17f5aca2a057163a0d09ac02e1877a9bb155284`, rollback
  `aaemu-world:rollback-pre-archepass-switch-20260903-141820`. Game está healthy y registrado en
  Login; Login/DB fueron preservados y Zone no fue operada. Gate: seleccionar Hellwraith Kirin,
  pulsar de nuevo el botón habilitado, confirmar Start y comprobar el cambio inmediato del panel.

## ArchePass: cierre del ciclo validado y continuación — 2026-09-03

El usuario acepta el desbloqueo premium y solicita commit/push y continuar la cola.
Logs20:25:54: realStep53/request1 → Ready, coste0;20:25:55: request2 → Progress,
group168/quest10120. Quedan aceptados registro/cambio, puntos/tier en vivo,
claims normales y premium probados, upgrade en vivo y acceso a la cuarta misión.
Los reinicios anteriores conservaron las titularidades50/51/52 y progreso persistido.
Build Release y1756/1756 tests; imagen vigente fd6330cdbd072e1a9fbde4091e2f1a7c0407306688641fab01aca8712c20adf5.

Este cierre no afirma que reroll, rollover diario/semanal, finalización/borrado de
pase o todos los negativos E2E estén aceptados. CSArchePassChangeMission continúa
cerrado por falta de valores autoritativos de configuración; esos pendientes se
conservan en el dossier y backlog. No se alteran sus límites para dar por terminado
el ciclo. Siguiente trabajo: Item Smelting, empezando por la bifurcación entre
outputs nativos reconstruibles y pestaña retirada; feature178 permanece apagada.
