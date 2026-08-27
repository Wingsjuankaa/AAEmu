# Checkpoint AA10 crafting — ola 2

## Frontera

- Target: `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`.
- Baseline aceptada de ola 1: `e2ef3d7dfa241a305c887b95cb257fb97863146a`.
- Padre exacto: `upstream/client_version/zone-10.0.2_r575` en
  `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- AA8 se usó exclusivamente como `structural_candidate`; no se copiaron
  packets, fórmulas, IDs ni timings.
- Full, compact retail y compact runtime conservan los hashes congelados en el
  checkpoint de ola 1. Los tres pasaron `quick_check` e `integrity_check` al
  regenerar este manifest.

## Evidencia r575

La evidencia reproducible está bajo
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\craft-failure-frontier`.

- `crafting.lua` llama una sola vez a
  `X2Craft:ExecuteBatchCraftByType(craftType, doodadId, count)` y cancela con
  `StopBatchCrafting`.
- `FUN_398b1440` serializa `craftId`, `doodadId` y `count` en
  `CSExecuteCraft` (`0x145`). `FUN_398b8d70` conserva esos tres valores y
  registra los eventos de skill.
- `FUN_398b52d0` publica `CRAFT_STARTED`, decrementa el contador sólo después
  de una skill disparada y mantiene el batch activo mientras queden unidades.
  Un inicio fallido recorre la rama que resetea el batch.
- `FUN_39b0b840` carga `actability_limit`, `cast_delay`, `cost`, `skill_id` y
  el bit `use_only_actability` desde `crafts`.
- `FUN_397f7490` y `FUN_398b1600` comparan `actability_limit` con el grupo de
  actability de la skill. Los bonuses de `unit_attr_id` se incluyen salvo
  cuando `use_only_actability` está activo.
- `FUN_397f7490` usa `craft.cost` como precio base en cobre. El descuento
  contextual sólo existe para una mesa creada por item del propio personaje;
  esas mesas siguen cerradas por el gate de permisos. Las mesas públicas
  promovidas cobran por tanto el coste base exacto.
- `cast_delay` y el contador pertenecen al contrato de batch; cada unidad
  conserva su skill nativa y se continúa mediante una tarea separada después
  del delay de la receta.

## Implementación

- `CharacterCraft` mantiene una receta activa, contador restante y generación.
  Cada unidad revalida contrato, mesa, permiso, dinero, actability, labor,
  materiales y capacidad. Una continuación cancelada o vieja es un no-op.
- `CraftTransactionPlan` incorpora coste, gate/grupo de actability,
  `use_only_actability` y `cast_delay`.
- `Character.TryCommitCraftTransaction` estabiliza cartera y labor mientras
  `ItemContainer` revalida y confirma la bolsa. Dinero, labor, materiales y
  producto cambian únicamente en un commit exitoso.
- El cobro de labor se efectúa dentro de ese commit; `Skill.EndSkill` conserva
  vocation y lifecycle pero recibe cero unidades para impedir doble cobro.
- Los packets posteriores al commit usan los tasks r575
  `CraftActSaved`, `CraftPaySaved` y `CraftPickupProduct`.
- El primer rechazo detiene la serie. `CSStopCasting` también invalida una
  continuación durante `cast_delay`, aunque la timeline anterior ya no exista.
- El comportamiento posterior (grados, rates y backpacks) permanece bloqueado;
  no existe fallback legacy.

## Catálogo cerrado

- Manifest: `generated/aa10-crafting-wave2-manifest.json`.
- SHA-256 manifest:
  `37851AE3E905EC35F560FF62122023838D16DC264D3E0EE1F9329F8F43013EB2`.
- Policy: `AAEmu.Game/Data/aa10-crafting-wave2-policy.json`.
- SHA-256 policy:
  `4A828BE5D3748479C4E4B5C108378CCEC3D259E26E4BC6B917988D59D6E6F800`.
- 9.949 recetas habilitadas: 7.064 `executable_wave2` y 2.885 bloqueadas.
- Quedan bloqueadas, entre otras: 15 sin grupo de actability demostrable, 93
  con grado de material, 1.413 con grado de producto, 91 con rate distinto de
  100 y 389 backpacks.

## Gates estáticos

- Regeneración de ola 1 bit a bit idéntica: SHA-256
  `D86079198C11CAE752F13AC198851923EEE9C886772BF67D30D287D2D7D612C4`.
- Tests de manifests ola 1 + ola 2: 9/9.
- Build Release de la solución: correcto, 0 errores.
- Suite TUnit: 1.549/1.549, 0 fallos.
- Tests nuevos cubren coste/actability, `use_only_actability`, grupo ausente,
  commit conjunto dinero+ítems, pago insuficiente sin mutación, cancelación
  entre unidades y rechazo de una continuación obsoleta.

## Despliegue reversible

- Commit funcional publicado en `origin/rama_10`:
  `4d2f30d97e89647de9832ce771ad551626d38716`.
- Imagen Release desplegada sólo en `Game`:
  `sha256:c827340607135bdf4acbb1015974a5dd2bcf108f2b6a7f11b848fd9b6333c230`.
- Imagen anterior preservada como
  `aaemu-world:rollback-pre-crafting-wave2-20260826`:
  `sha256:fde1982008e1822e835fad98128b5c8a67bc3f6941bcad9bbd9e8c0b7fc22d6b`.
- El contenedor `aaemu10-game-1` quedó `healthy`, con cero reinicios, y el
  loader registró `12402 crafts (9949 enabled, 7064 promoted by AA10 crafting
  policy)`.
- La policy montada dentro del contenedor conserva el SHA-256
  `4A828BE5D3748479C4E4B5C108378CCEC3D259E26E4BC6B917988D59D6E6F800`.
- `DB` y `Login` permanecieron sanos y no se operó `Zone`. La recreación de
  `Game` cortó su conexión existente, por lo que el operador debe reconectarlo
  antes del gate retail.

## Gate retail decisivo — aprobado

El 27-08-2026 se validó la receta r575 `craft=5544` (Handicraft Yarn) en la
Weaving Loom real `doodad=127734`, con `cast_delay=8000`, coste 10 cobre,
labor 10 y actability Tailoring. El estado inicial fue 1.000/1.000/1.000 de
Goat Wool/Yata Fur/Bear Fur y cero Handicraft Yarn.

1. `count=3` produjo tres commits independientes y visibles. El inventario
   quedó 970/985/985 y 30 productos; se cobraron exactamente 30 labor y 30
   cobre, y Tailoring avanzó 3.000 puntos.
2. En una serie de dos se dejó confirmar la primera unidad y se canceló el
   segundo casteo. El estado quedó 960/980/980 y 40 productos; no hubo segunda
   mutación y un intento inmediato de una unidad fue aceptado, terminando en
   950/975/975 y 50 productos.
3. Para el rechazo a mitad de serie se inició `count=3` con labor suficiente y
   se retiró únicamente la labor de prueba durante el segundo casteo. La
   primera unidad confirmó (940/970/970 y 60 productos); la segunda devolvió
   `Insufficient Labor Points`, no hubo tercera y ningún saldo volvió a mutar.
   La labor retirada para la prueba se restauró después del rechazo.
4. El log de Game contiene seis líneas `AA10 craft committed`, la cancelación
   con `craftSession=True` y un único rechazo `NotEnoughLabor`; no contiene
   excepción ni error atribuible a crafting. Los errores de opcode `0x080` y
   la desconexión previa de Zone 351 son ajenos a este gate.
5. Tras una salida limpia y relog, la base conservó dinero
   `11925512056` y labor `8618`. La API y la tabla `items` coincidieron en
   Goat Wool 940 (slot 62), Yata Fur 970 (slot 61), Bear Fur 970 (slot 63) y
   Handicraft Yarn 60 (slot 68). La UI mostró 8.620 labor al entrar por los dos
   puntos de regeneración natural posteriores al relog.
6. Ya conectado de nuevo, `F` abrió el Craft de la misma mesa y `Esc` lo
   cerró: la sesión quedó liberada y no persistió ninguna acción tomada.

Resultado: **ola 2 aceptada**. Repetición, delay, cancelación, coste,
actability, agotamiento a mitad de serie, atomicidad y persistencia superaron
el gate retail sin fallback legacy.
