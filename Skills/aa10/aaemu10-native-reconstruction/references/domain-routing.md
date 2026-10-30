# Routing inicial de dominios AA10

## Estado base

- `rama_10` compila y pasó 1.344 pruebas unitarias el 2026-08-19.
- World/Zone y protocolo 10.0.2.13 avanzan rápidamente en upstream padre.
- Mantener este archivo actualizado después de cada frontera; no congelar el
  número de pruebas o gaps como verdad permanente.

## Prioridades conocidas

1. **Items/Hiram:** synthesis, awakening, progresión Hiram, instalación,
   retirada y extracción de Lunagem, más `ItemEvolvingReRoll`, quedaron cerrados y aceptados
   dinámicamente para r575 en `rama_10`. Para extracción, leer
   `Docs/AA10LunagemExtractionReconstruction_es.md` y el dossier
   `forensics/output/aa10-client-forensics/lunagem-extraction-frontier`: el
   consumible 38568/skill 30673 usa `ItemSocketing value1=2`, skill-object tipo
   11 (`u32 socketIndex, bool extractAll`), índice físico base cero, una piedra y
   500 de labor base por socket; `extractable=false` destruye la gema con
   advertencia retail. La aceptación del 2026-08-19 devolvió `44684` a la bolsa,
   consumió una Mornstone, aplicó 400 de labor por el descuento de Alquimia y
   permitió reinstalar exactamente la misma gema. El guardado normal confirmó
   en MySQL el casco reequipado, la Mornstone restante y la ausencia del item
   temporal; un segundo ingreso reconstruyó el estado sin pérdida ni duplicación.
   Mantener `socketExtract=169`
   habilitado y seguir exigiendo autorización explícita para futuros despliegues
   y para iniciar únicamente la Zone donde esté el personaje. El reempaquetado con Transmuter y la
   reapertura selectiva están cerrados estáticamente y en tests, pero pendientes de aceptación
   dinámica. Leer [lunagem-repackage.md](lunagem-repackage.md): item 42876/skill 35945 usa
   `ItemConversion value1=8`; la prueba 44684 debe recorrer route/rpack 4579 hacia ppack 4652 y
   caja vendible 44773, cuya opción 4 vuelve a entregar 44684. Nunca comparar IDs de rpack y ppack
   directamente. Item Smelting está DEPRECADO / FUERA DE ALCANCE por decisión del
   usuario (2026-09-03); mantener feature178 OFF y omitirlo de prioridades futuras.
   [item-smelting.md](item-smelting.md) conserva evidencia histórica, no un gate
   pendiente. Sólo reabrir por petición explícita; no afecta el resto de Lunagem.
   Migration Scaling / Bless Uthstin tiene cerrado e
   implementado el flujo principal Consume/Preview/Confirm en
   [migration-scaling.md](migration-scaling.md): feature 176, páginas 0x1c,
   normal 42822 (+1/-1) y especial 42325 (+3/-3). Reset, extensión y páginas
   responden fracaso explícito y aún no están promovidos; aceptación dinámica
   del reemplazo principal pendiente.
2. **Housing/doodads:** faltaban primitivas equivalentes a
   `HousingPlacementPolicy`; comprobar si upstream añadió una solución antes de
   portar políticas, bindings, áreas, attachments y recovery AA8.
   Caso aceptado 2026-09-03: leer
   `reconstruccion_cliente_10/checkpoints/CHECKPOINT_HOUSING_TAX_CRAFT_STATION_20260903.md`.
   Dannia/craft76/placa9405 falló por `StationUnavailable`, no por ownership.
   El arreglo reconoce CraftPack activo y receta, permiso de función coincidente
   y acceso Housing, con revalidación pre-cast/commit. Suite1762 correcta;
   usuario confirma éxito y logs23:07:51/23:08:00 prueban dos commits de craft76,
   labor55, sin productos fallidos. La prueba posterior cross-account confirma
   siembra privada rechazada, pero revela otro fallo: taxes deben ser públicos
   incluso en parcela privada. La corrección acota la excepción a craft76/9267,
   req2392 y oferta activa pack3/Public; Skill.Use delega sólo para la instancia
   creada por la sesión de crafting. Consultar la actualización del checkpoint
   para despliegue/aceptación. No abrir permisos de otras recetas ni de Housing.
   H5-B permanece pendiente.
3. **Crafting/economía:** las cinco olas están cerradas y aceptadas. La revisión
   histórica posterior clasifica los bloqueos con fuentes web versionadas sin
   sustituir la autoridad AA10. La policy v5 promueve 7.320/9.949 recetas e
   incluye una allowlist cerrada de 14 contratos intencionalmente sin
   materiales: Tax Certificate 9267 y 13 ArchePaper. Garden Crystal 11234 sigue
   bloqueada por `skill_id=NULL`; Hardwood Raft 11355, por consumer nativo
   ausente. Eventos, conflictos regionales, IDs reutilizados y `unused` no se
   delegan al flujo legacy. Ver
   `reconstruccion_cliente_10/checkpoints/CHECKPOINT_NATIVE_CRAFTING_HISTORICAL_REVIEW_V1.md`.
4. **Items de summon/quest:** el lifecycle de items `SummonMate` quedó cerrado
   estáticamente el 2026-08-27. El manifest AA10 clasifica 552 relaciones y la
   policy v1 promueve 478 contratos retail exactos `item -> use_skill ->
   SpawnPet -> npc`; 71 items ausentes de compact, un NPC retail ausente y dos
   buffs iniciales retail ausentes permanecen bloqueados sin fallback. El
   consumer valida item físico, dueño, bolsa, skill y NPC antes de mutar; el
   doble click está serializado, desconexión/relog captura el estado persistente
   y destruir el item retira el registro sólo cuando el mate no conserva
   equipo. Leer
   `reconstruccion_cliente_10/CHECKPOINT_NATIVE_SUMMON_MATE_V1.md`. Falta la
   aceptación dinámica y cualquier despliegue requiere autorización explícita.
   Otras closures summon/quest deben seguir derivándose de full, compact,
   runtime y consumers AA10; AA8 sólo puede aportar estructura.
5. **Movimiento/teleport:** portar sólo validación genérica y reconciliación de
   visibilidad confirmada por packets/lifecycle AA10.
6. **Skills/combate:** upstream cambia activamente; realizar audit de regresión
   transversal antes de portar autoridad, cooldowns, chains o passive procs.
7. **Vehículos y componentes adjuntos:** cuando una skill de slave funciona de
   forma intermitente o el action bar queda desincronizado, cerrar primero el
   grafo AA10 `slave_bindings -> slave_initial_buffs -> buff_tags -> plot AoE ->
   buff_triggers -> buff_mount_skills`. Los plots pueden seleccionar una tapa,
   vela o torreta hija por type flag y BuffTag aunque el caster sea el vehículo
   padre. Comprobar tanto el índice regional durante movimiento dedicado como
   `source_agent_id`/`target_agent_id`: en r575 los agents nativos observados
   son `0=owner`, `1=event source`, `2=event target`, `3=original source`.
   Preferir una corrección genérica guiada por binding/tag/agent; no hardcodear
   IDs de vehículo o skill. La ausencia de un helper de attach point en pak o
   cache no prueba que el slave hijo no exista en el grafo de transforms.
8. **Auroria / continente `origin`:** Returns r575 distribuye tres gates
   separados. El cliente release compara el target del mapa contra
   `world_groups.id=5`; el parche estructural validado cambia únicamente la
   constante de comparación `5 -> 9999` en `x2game.dll`. En la compact efectiva
   hay que validar y abrir exactamente 30 recursos `o_*`, 31 particiones cuyos
   `zone_groups.target_id=5` y 13 filas Auroria de `conflict_zones`. Activar sólo
   `map_resources.enable` permite dibujar recursos, pero deja portales, entrada
   y ciclos de guerra cerrados en AAEmu. Usar
   `Scripts/PatchAa10AuroriaCatalog.py`, reinsertar la copia cliente dentro de
   `game_pak` con `Tools/PakEntryReplace` y exigir tamaño, hash y
   `PRAGMA quick_check`. No modificar la full autoritativa ni los respaldos
   retail. Después de reiniciar Game, el usuario levanta una sola partición
   Auroria desde Control Center y Codex sólo valida `ZoneLoaded`/heartbeat.

## Rutas

- Datos/relaciones/consumer ausente -> `aa10-client-forensics`.
- Código, tests, SQL runtime, Docker, despliegue -> esta skill.
- Cambio ya presente upstream -> integrar padre; no duplicar.
- Candidato AA8 sin prueba AA10 -> dejar `version_sensitive_blocked`.
