# Localización contextual r575 es_ES

Implementación y despliegue local del editor, registro de nombres y primer corte de correcciones. Checkpoint principal: `E:/AAEmu/rama_10/localization/aa10-es-es/CHECKPOINT_CONTEXTUAL_V2.md`.

- Editor: http://127.0.0.1:18775. Launcher: `Editar traducciones es_ES.cmd` en el cliente español completo.
- Builder: `Scripts/PatchAa10ContextualLocalization.py`.
- Aplicador: `Scripts/ApplyAa10ContextualLocalization.py prepare|apply|rollback [id]`.
- 2.114 nombres conservados por política y 24 revisiones puntuales de referencias; 1.665 celdas cambiadas sobre el preview anterior. Idioma de runtime sigue siendo en_us.
- Compact final: `26CF7EB91AAEEFD1B3B9C5C42DFB335317F8A29A5AF39D9DFB9ED6A10FB95369`.
- game_pak final: `3EE9953855900BE8628C06A3CC46AA9F22174502780C814B641673803B051218`, 69.430.854.656 bytes.
- Backup final: `E:/AAEmu/rama_10/backups/client-patches/contextual-13a81d7234fa4bb3a01c42f97fe737b1`.
- 1.003 tablas verificadas; Folio/tooltip y recursos de mapa/icono conservados. Se probó rollback real y segunda aplicación sin cambios.
- 25 pruebas Python y 1.812 pruebas AAEmu correctas; Release/restore correctos. Control Center: build/typecheck, 52 pruebas correctas y 1 omitida.
- Modelo Qwen3-14B Q4_K_M portable verificado: propuesta editorial únicamente. Evaluación final de 300 entradas: 13 bloqueadas, incluidas 10 por controles estructurales; no se promueve una traducción masiva sin cerrar el gate semántico.

La prueba retail de este corte queda pendiente de interacción del usuario. No se afirma que el editor ni la suite automática demuestren la presentación dentro del juego. No se operaron Zones ni se alteró la configuración de servicios.

El campo Nación usa `GetLoginCharacterFaction` y `GetFactionInfo(...).name` en el consumidor de selección. Crescent Throne y Nuia son entidades diferentes; no se renombraron globalmente.
