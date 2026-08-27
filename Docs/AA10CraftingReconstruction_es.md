# Reconstrucción de crafting AA10 r575

## Estado

Las cinco olas de promoción fail-closed quedaron aceptadas. La revisión
histórica posterior incorporó fuentes web versionadas para distinguir contenido
persistente, de evento, regional, reutilizado y unused sin sustituir la
autoridad del cliente AA10. No existe fallback al código legacy.

De las 9.949 recetas habilitadas, 7.320 cumplen el contrato final y 2.629 quedan
bloqueadas con motivos explícitos. El catálogo reproducible se encuentra en
`reconstruccion_cliente_10/generated/aa10-crafting-wave5-manifest.json`; se
regenera con `audit_aa10_crafting.py --wave 5`. Game aplica exactamente sus IDs
desde `AAEmu.Game/Data/aa10-crafting-wave5-policy.json`; una política ausente o
incoherente bloquea el arranque.

## Arquitectura

El loader conserva todos los campos AA10 de `crafts`, `craft_materials` y
`craft_products`. `craft_pack_crafts` representa grupos del catálogo, no la
naturaleza del producto. El autoequip de tradepacks se resuelve desde el
`BackpackTemplate` del item.

`CraftTransactionPlanner.TryValidateContract` separa el contrato inmutable de
la receta del estado mutable del personaje. `CraftTransactionPlanner.TryCreate`
es la fase transaccional pura: normaliza filas
duplicadas, detecta overflow, selecciona stacks, comprueba que los items puedan
destruirse y simula la bolsa después de consumir. Devuelve un
`CraftTransactionPlan` inmutable o un `CraftFailure` concreto.

Una lista de materiales vacía no se acepta de forma genérica. La policy final
marca exactamente 14 `materialFreeCraftIds` demostrados —Tax Certificate y 13
ArchePaper— y el loader vuelve a validar que sigan habilitados, sin materiales y
con producto. El planner y el intercambio atómico exigen esa marca; cualquier
otro contrato vacío falla cerrado.

`Character.TryCommitCraftTransaction` estabiliza cartera y labor mientras
`ItemContainer.TryExchangeCraftItems` revalida y confirma el intercambio bajo
el lock de la bolsa. Coste, labor, materiales y productos se confirman juntos;
los packets se publican después. Los tasks nativos son `CraftActSaved`,
`CraftPaySaved` y `CraftPickupProduct`.

`CharacterCraft` representa una única sesión activa y valida en dos fases.
Antes de iniciar la skill comprueba contrato, estación, permiso, labor,
materiales y capacidad. Un rechazo inmediato se expresa como
`SCSkillStarted` fallido con timeline y tiempos de casteo en cero: el cliente
r575 libera el batch sin publicar `CRAFT_STARTED`, por lo que no muestra una
barra inútil. `CraftEffect` vuelve a comprobar el estado mutable y confirma el
intercambio bajo lock para cubrir cambios concurrentes durante el casteo. Sólo
después del commit dispara quests, housing, shipyard o interacción; una falla
tardía cancela la skill sin cobrar labor ni vocation.

La cancelación nativa también libera esa sesión separada. `CSStopCasting`
termina la skill y llama a `CharacterCraft.Cancel(sourceSkill)`; la sesión sólo
se limpia cuando el ID de la skill cancelada coincide con la receta activa. Así
un craft cancelado puede reintentarse inmediatamente sin que un stop tardío de
otra timeline pueda borrar una sesión nueva. Durante la ventana `cast_delay`,
cuando ya no existe `SkillTask`, el mismo packet invalida la generación de la
continuación; cualquier `CraftTask` tardío queda como no-op.

## Política de errores y permisos

Los IDs inválidos, deshabilitados o bloqueados se rechazan sin excepciones. Las
estaciones requeridas deben coincidir exactamente y cualquier permiso distinto
de `Public` permanece cerrado hasta demostrar su contrato AA10.

El consumer r575 de `SCCraftFailedPacket` quedó cerrado: opcode `0x22D`, un
`int32` inicial, un contador `int32` y hasta veinte IDs `int32`. La callback
`FUN_3933fb20` delega en `FUN_398b2150`, que ignora el primer campo y publica
`CRAFT_FAILED` (`0x72`) con links de item. `center_message_manager.lua` sólo
muestra `failed_craft_alert`; este packet no modifica `CraftManagerImpl` ni
emite `CRAFT_ENDED`, por lo que no sirve para liberar el botón Confirm. La rama
de evento de skill `0x16` en `FUN_398b52d0`, en cambio, resetea el manager y
publica `CRAFT_ENDED` cuando el resultado de `SCSkillStarted` no es éxito. Ése
es el cierre nativo usado por los rechazos anteriores al casteo.

## Gate retail y Folio

Cada ampliación de policy requiere checkpoint, build, suite completa, auditoría
SQLite, despliegue reversible y aceptación dinámica independiente. La
aceptación retail incluye además un gate de Folio:

1. cada receta promovida debe ser visible en su ruta de categorías y
   localizable como `Finished Product` mediante su nombre exacto de
   `localized_texts` para el locale probado;
2. su ficha debe mostrar producto, workbench, materiales, coste y labor
   coherentes con el compact retail;
3. cada ingrediente debe ser localizable con el selector `Materials`; sólo se
   exige que aparezca como `Finished Product` cuando también exista una receta
   productora habilitada;
4. una receta que ejecute en servidor pero no pueda descubrirse o cuya ficha
   esté incompleta no supera la ola.

Los nombres traducidos manualmente no sirven como evidencia del buscador. Por
ejemplo, en el locale `en_us` r575 los items 26768, 27545 y 3667 son
`Cashmere Thread`, `Handicraft Yarn` y `Narcissus`, respectivamente.
`Narcissus` es un material recolectado y no posee receta productora.
`Craft Orders` queda fuera de este alcance.

## Operación

La ola 1 se desplegó recreando únicamente Game; DB y Login permanecieron sanos.
La imagen activa es
`sha256:fde1982008e1822e835fad98128b5c8a67bc3f6941bcad9bbd9e8c0b7fc22d6b`.
La versión anterior a la validación `BagFull` pre-cast está preservada como
`aaemu-world:rollback-pre-crafting-wave1-precast-bagfull-fix-20260826`. La
versión anterior a la reparación del lifecycle de bolsa llena está
preservada como
`aaemu-world:rollback-pre-crafting-wave1-fullbag-lifecycle-fix-20260826`; la
versión anterior a la reparación de cancelación está preservada como
`aaemu-world:rollback-pre-crafting-wave1-cancel-fix-20260826`. También se
conserva el rollback original de la ola como
`aaemu-world:rollback-pre-crafting-wave1-20260826`. No se inició ni controló
ningún ZoneHost. El recreado de Game desconectó la Zone existente y el operador
la reconectó desde Control Center. El gate dinámico de cancelación y reintento
quedó aprobado: cuatro cancelaciones liberaron la sesión, no hubo `Busy` ni
`SCErrorMsgPacket`, y una ejecución intercalada produjo el único commit
esperado. También quedaron aprobados material insuficiente —bloqueado por el
cliente antes de emitir `CSExecuteCraft`— y bolsa llena —rechazo servidor
`BagFull` sin commit, labor ni mutación—. El primer cierre dejaba el batch
activo y el segundo lo liberaba al terminar el casteo; la corrección actual usa
el inicio fallido nativo para alertar y liberar antes de mostrar la barra. El
reintento desde el mismo Folio y el múltiples clicks quedaron aprobados: un
rechazo pre-cast no creó timeline; tras liberar espacio se pudo cancelar,
reintentar y completar; varios clicks produjeron una sola petición y un solo
commit. La ola 1 queda cerrada y la ola 2 puede comenzar. La evidencia está en
`reconstruccion_cliente_10/checkpoints/CHECKPOINT_NATIVE_CRAFTING_WAVE1_V1.md`.
