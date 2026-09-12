# Garden: interferencia de pulsos y puntuación

El usuario confirma el cruce desde Gatekeeper Hall y aporta el video `20260909-0125-43.4953110.mp4` (27 s). Se observan muertes con 73000 EXP y botín, contador «Solicitud de hadas» en 0, ataques intermitentes y NPCs sin respuesta útil. El usuario confirma además que los casteos se cancelan solos continuamente.

## Evidencia

- Buff 25655, trigger 13605, evento 12, effect 84380, SpecialEffect33/SkillUse ejecuta skill 44268 cada segundo. Skill44268: plot4848, plot_only, skip_validate_source, ignore_global_cooldown, casting/channeling=0. Full y runtime confirman estos flags.
- La implementación anterior pasaba el proc por `Plot.RunAsync`: cancelaba el plot en casteo/canalización y sobrescribía `Unit.ActivePlotState`. También disparaba indiscriminadamente RemoveOn.UseSkill. El padre exacto conserva esta misma implementación.
- Logs 01:24–01:26:45 UTC: alrededor de 220000 rechazos por cada uno de los trece requisitos ZoneScoreLevel de plot4848 (13 ramas, rangos0..12). El log capturado ocupa 478272082 bytes. Hay solicitudes de IA nativa: skill43871 de NPC19593, skill43691 de NPC19609. No se atribuye la falta de daño a una Zone ausente.
- Tras muertes aparecen `Unknown special effect: ChangeZoneScore`. El handler181 y el estado de puntuación no existían. Los paquetes Update/Reset ya estaban declarados, sin productor.
- Garden: content2/zone_group133, quest10056, kind3 persistente, reset_quest_removed=true. Niveles acumulados: 0,2500,5400,8600,12600,16900,21600,27000,33100,40000,47500,55800,64800. El máximo de score es el dato de catálogo, no el último umbral.

Artefactos: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/garden-combat-20260909`. Incluyen frames, warnings agregados, combat-filtered.log, score-contract.json y decompilados de lectura. El log completo queda en artifacts/garden-combat-20260909.log. El helper FindGardenScore reutiliza Ghidra en readOnly/noanalysis.

Consumer nativo r575: DLL Zone SHA8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A, x64, base0x39000000. GetZoneScore wrapper RVA0x98F310 llama RVA0x4E4230: obtiene puntuación acumulada, recorre req_score, publica curLevel y resto del siguiente umbral. RVA0x4E4490 suma delta o asigna lista inicial; RVA0x4E45A0 pone cero; ambos notifican UI. Esta evidencia es del binario Zone que incluye consumidores cliente, no se atribuye como RVA del x2game release operacional. No se portó una implementación AA8 (sólo existen offsets antiguos allí).

## Cambios

1. Se conserva origen de buffs en SkillUse y sus descendientes. Los procs instantáneos con skip_validate_source e ignore_global_cooldown se ejecutan con un PlotState propio, sin cancelar ni sustituir el estado del casteo activo y sin el RemoveOn.UseSkill previo. No hay ramas por ID de skill, cambios de timings ni supresión de paquetes.
2. GardenScoreGameData carga umbrales y vínculo de misión desde compact. ChangeZoneScore admite exclusivamente la variante autorada de Garden `(kind=3,mode=1,unit=0,delta)`; aplica diferencia firmada, limitada a0..max, sólo con la misión activa. El contador usa los paquetes nativos existentes. La puntuación se guarda con el personaje y se resincroniza al entrar. Retirar su misión pone cero; retirar otra no afecta.
3. ZoneScoreLevel resuelve las trece ramas de igualdad (value2=2) del plot de rango. NPCs no se tratan como jugadores con puntuación. No se inventan los otros operadores a partir de enum_comparison_operators: es otro enum. Comparaciones0/1 y requisito ZoneScore131 siguen pendientes de consumer exacto; también quedan fuera otros kinds y variantes de SpecialEffect181. No se declara reconstruida toda la mecánica de Garden ni sus recompensas avanzadas.
4. Nueva tabla aditiva `character_zone_scores`, migration SQL/updates/2026-09-09_aaemu_game_zone_scores.sql. Sin cambios de game_pak ni compact.

## Validación y despliegue

Build Release y 2734 pruebas aprobadas (0fallos/0omitidas). Regresión: cinco procs consecutivos conservan casteo/canalización, cancelar el proc no cancela el casteo; habilidades normales no se reclasifican. Puntuación: exige misión, actualización concurrente sin pérdida, clamp y overflow, umbrales acumulados, reset de misión correcto, body de delta negativo. El test del body no prueba por sí solo el transporte ni la UI.

Respaldo SQL previo e imagen en `E:/AAEmu/rama_10/backups/garden-combat-20260909`; rollback tag `aaemu-world:rollback-garden-combat-20260909`. La migración sólo añade tabla: para rollback funcional basta recrear Game con la imagen anterior y conservar la tabla/puntos. No restaurar toda la DB sobre progreso posterior salvo recuperación explícita. No se operó lifecycle de Zones.

Aceptación retail pendiente: relanzar perfiles378/379/382, entrar con Dannia, completar casteo largo mientras corre el pulso, comprobar NPC19593/19609 en combate, matar uno y observar incremento de puntuación, luego relog y comprobar persistencia. La respuesta ofensiva de los NPCs requiere esta nueva prueba: las solicitudes existen, pero no se afirma aún que toda su cadena de efectos haya quedado resuelta.

Despliegue comprobado: nueva imagen1195e847, DLL eaff4a6e; catálogo GardenScore cargado y postloaded; Game listo01:54:21UTC, healthy, 0restarts y API World verificada. Los perfiles Zone quedaron detenidos tras recrear Game y se indicó al usuario relanzarlos; aceptación del nuevo combate/contador pendiente.

## Corrección de diagnóstico 2026-09-11
El usuario rechaza la aceptación retail: combate sigue interrumpiéndose y rank0 parpadea. Trigger13605/event12 es Started, no OnTick: buff26390 elimina/recrea25655 cada segundo porque se omitían los unit_reqs de BuffTickEffect4486/4489. Ver CHECKPOINT_GARDEN_BUFF_TICK_20260911.md.
