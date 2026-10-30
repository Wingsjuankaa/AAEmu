# Item Smelting AA10 r575

## Política vigente — 2026-09-03

DEPRECADO / FUERA DE ALCANCE por decisión explícita del usuario. No reconstruir,
auditar, activar ni proponer pruebas de esta mecánica en continuaciones automáticas.
Conservar código/evidencia y feature178 OFF; sólo reabrir por petición explícita.
Los contratos y gates inferiores son históricos, no obligaciones futuras ni aceptación
funcional. No afecta Lunagem, socketing o crafting. Siguiente cola: Housing H2/H5-B.

Leer esta referencia al diagnosticar, modificar, desplegar o probar la pestaña
Smelting del controlador Item Enchant.

## Contrato cerrado

- Evidencia durable:
  `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\item-smelting-frontier`.
- Documento de implementación:
  `E:\AAEmu\rama_10\server\AAEmu\Docs\AA10ItemSmeltingReconstruction_es.md`.
- Feature compartida: `itemSmelting=178`.
- Modo ItemEnchant: 10.
- Skill retail:35525 → skill_effect48479 → effect61510 → SpecialEffect27384
  → type151. Corrección03-09-2026: la afirmación previa de Anim34 era falsa;
  las cuatro fuentes congeladas coinciden y callerRVA121180 comprueba0x97.
- Skill-object tipo 20: `bool autoUseAAPoint`, `u32 smeltingDescId`; después
  sigue el `inputDirection` común.
- Resultado `0xCF`: `s8 result`, `bool resultItemByMail`, `s64 itemId`,
  `s32 type`. No anteponer el byte heredado de AA8/Modern.
- Códigos probados por el Lua retail: `0=Failure`, `1=Success`,
  `2=GreatSuccess`.

## Catálogo y seguridad

- Cargar `item_smeltings`, `item_smelting_probs`, `item_smelting_items` y el
  `item_set_id` relacionado desde la compact efectiva.
- La base RNG es 10,000,000; `prob1/prob2/prob3` corresponden a
  Great Success/Success/Failure.
- Asociar outputs por `item_smelting_id` preservando `ORDER BY id`. Las filas
  están intercaladas globalmente; no asumir tres ids consecutivos.
- El resolver retail `FUN_3998b9c0` elige receta por `item_id + amount`.
  Revalidar ambos contra el target real enviado al cast; no bloquear 1–4 sólo
  por sus nombres históricos de test ni confiar en el `smeltingDescId` cliente.
- Tratar el id enviado por el cliente como solicitud: validar nuevamente skill,
  objetivo, cantidad, catalizador, material set, proficiency, labor, moneda,
  capacidad y templates de los tres outputs.
- El executor dedicado corre actualmente en `Skill.ApplyEffects`; esto NO prueba
  ausencia de SpecialEffect151. Debe tomar propiedad del consumo para impedir un
  segundo gasto automático del catalizador `use_skill_as_reagent`.
- Las recetas 29–32 referencian outputs 43482/43489 ausentes de `items` en la
  evidencia exacta; rechazar antes de RNG/pago/consumo. No inventar templates.
- Hasta cerrar el contrato retail de creación/adjuntos por mail, rechazar
  `BagFull` antes de cobrar y responder sólo `resultItemByMail=false`.

## Aceptación mínima

Receta5 es sólo fixture de backend, NO kit retail seleccionable probado:
target 40000 x1, catalizador 43446 x1, materiales 31010 x2 y
15632 x6, 10,000 copper, 500 labor base, 30% Great/70% Success. El output es
43445 o 43476. Verificar consumo exacto, descuento de labor, moneda, item y
mensaje central.

Despliegue, reinicio de Game y arranque de una Zone son gates separados. Exigir
autorización explícita y levantar únicamente la Zone donde esté el personaje.

## Disponibilidad comprobada (2026-08-19)

- Mantener `itemSmelting=false` por defecto. La implementación existe para
  continuar la reconstrucción, pero no está aceptada para jugadores.
- La prueba dinámica autorizada con `Wingsjuanka` y únicamente la Zone
  `o_hirama_the_west_2` llegó al preflight completo de la UI.
- El cliente seleccionó la receta 29 para target 40000 (también en grade 0) y
  pidió 31013 x2 + 40229 x60; la captura mostró `2/2` y `60/60`.
- Esa receta referencia 43482/43489, inexistentes en todos los compact exactos
  r575 inspeccionados. El servidor debe seguir rechazándola antes de cobro,
  RNG o consumo.
- `Advanced Charm` 43446 abre la herramienta. La etiqueta del segundo slot
  dice `Lunagem Polish`, pero el item 43445 está marcado obsoleto y concede
  1,400 Honor; no tratar el texto del slot como prueba suficiente de contrato.
- Evidencia visual: `E:\AAEmu\rama_10\server\AAEmu\Docs\evidence\item-smelting`.
- Gate histórico archivado (ya no obligatorio): reconstruir 43482/43489 desde evidencia exacta o
  demostrar que la pestaña completa es un remanente retail deshabilitado. No
  habilitar el feature para producción antes de resolver esa bifurcación.

## Auditoría03-09-2026

Ver `CHECKPOINT_ITEM_SMELTING_AVAILABILITY_20260903.md` en el repo.
Cuatro fuentes/dos builds idénticos/quick_check e integrity_check OK.
40000 ausente en items de ambos compacts retail;43482/43489 ausentes incluso
en full. `item_smelting_probs` no proyectada a retail (no inferir retirada sólo
por esa omisión). Historia2017 corrobora desuso, no contratos Returns.
Clasificar como histórica post-lanzamiento, no nueva en AA10.

Proyecto Ghidra2735819 difiere de DLL405242e. Se reanclaron selector98B9C0,
iteradorAF6140 y caller121180 comparando todos sus rangos de código con el PE
vigente. Selector usa primera coincidencia, no menorID ni grado como desempate.
La ruta está BLOQUEADA, no aceptada. Restaurar datos externos o sustituciones
requiere decisión explícita de variante legacy; no habilitar para aparentar cierre.
