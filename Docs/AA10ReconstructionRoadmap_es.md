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
| 3 | ArchePass: missions y reroll | CORE IMPLEMENTADO; missions apagadas | Reconstrucción post-lanzamiento | Catálogo, tiers, rewards y configs 277-280 parciales | Persistencia de cuenta, quest points y rollover | Misiones/reroll sobreviven relog y rollover sin doble reward |
| 4 | Item Smelting | IMPLEMENTADO/OCULTO | Reconstrucción retail AA10 | Feature 178, skill 35525, skill-object 20 y resultado 0xCF | Aceptar receta 5; resolver outputs ausentes 29-32 | Resultado/coste/RNG exactos y bloqueos incompletos fail-closed |
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
