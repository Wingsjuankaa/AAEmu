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

## Gate retail decisivo

Tras el despliegue reversible, el operador controla Zone y valida una receta
promovida con coste y actability mediante una serie de tres unidades:

1. fotografía o anota dinero, labor, proficiency, materiales y producto;
2. confirma `count=3` y verifica tres casteos, con el `cast_delay` visible entre
   ellos, tres productos y cobro exacto de tres costes/labores;
3. repite y cancela durante el segundo casteo: sólo la primera unidad puede
   quedar confirmada y el botón debe permitir un nuevo intento inmediato;
4. inicia otra serie con recursos suficientes para una sola unidad: la segunda
   se rechaza, no existe tercera, y no hay coste/labor/material parcial de la
   unidad rechazada;
5. reloguea y confirma que todos los saldos persisten exactamente.

La ola 2 no se declara aceptada hasta superar ese gate y revisar sus logs. Zone
no se inicia, detiene ni despliega desde este flujo.
