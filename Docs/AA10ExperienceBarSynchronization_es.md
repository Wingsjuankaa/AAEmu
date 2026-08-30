# Sincronización de la barra de experiencia AA10 r575

## Síntoma

En nivel normal 55 el HUD permanece en `0 / 992.215.056 (0,00%)`, aunque
`characters.heir_exp` aumenta y el personaje obtiene niveles ancestrales. El denominador de la
captura es exactamente `levels[56].total_exp - levels[55].total_exp`; por tanto el HUD está
mostrando la experiencia normal ya topada, no la ancestral.

## Causa nativa

El cliente `x2game.dll` r575 consume `SCExpChanged` (`0x13D`) como
`unitId:bc, delta:i32, addAbilityExp:bool`. Para el jugador local aplica el mismo delta a la
experiencia normal y, cuando `fset[12] & 0x20` (`heirLevel`) está activo, también a la experiencia
ancestral. `SCCharacterState` transporta además la experiencia normal `u32` seguida por
`heirExp:i64`. Esos contratos coinciden con el servidor.

La entrada retail
`game/scriptsbin64/x2ui/hud/main_menu_bar/exp_bar_set.alb` tiene, sin embargo, dos saltos Lua 5.1
incondicionales:

- offset `6982`, `JMP +9`: omite los campos `percent`, `exp` y `totalExp` ancestrales del tooltip;
- offset `8207`, `JMP +29`: omite el porcentaje y color ancestrales de `UpdateExpSet`.

Así, el estado interno y los niveles siguen avanzando, pero la barra consulta siempre
`GetExpInfo()` y nunca proyecta `GetHeirExpInfo()`.

## Reparación

`Scripts/PatchAa10ExperienceBar.py` valida el Lua y el ALB retail por SHA-256, recompila la fuente
que conserva las compuertas correctas `IsEnabledHeirLevel()` y `GetMinHeirLevel()`, restaura el
header Lua de ArcheAge y rellena hasta el tamaño fijo de `16807` bytes.

| Estado | SHA-256 |
|---|---|
| retail | `3831551627119BA57E5B7D360D834EAD2F835D19665DF207CFA89B880B15E6D1` |
| reparado | `2E53830616C656D666C29C2EA39A56AD4C21BCE1A9ED024A935572AA7CEE41F5` |

El `game_pak` operativo reparado conserva `68963258880` bytes y tiene SHA-256 completo
`9DAEA9882FDB78A594D145BE95D087EEC4F2CEF08E47A43B633241A0011A4504`.

El aplicador `Scripts/ApplyAa10ExperienceBarGamePakPatch.ps1` extrae la entrada efectiva, genera el
reemplazo, conserva rollback y manifiesto, reemplaza con `Tools/PakEntryReplace` y reextrae para
validar. Es idempotente y rechaza cualquier variante desconocida.

Dry-run:

```powershell
pwsh Scripts\ApplyAa10ExperienceBarGamePakPatch.ps1
```

Aplicación:

```powershell
pwsh Scripts\ApplyAa10ExperienceBarGamePakPatch.ps1 -Apply
```

`-SkipFullPakHash` permite omitir únicamente el hash de 68+ GB cuando se necesita una comprobación
rápida. El aplicador exige `archeage.exe` cerrado sólo cuando debe escribir la entrada retail; una
ejecución idempotente sobre el hash reparado permanece de solo lectura. La aceptación visual debe
hacerse tras iniciar una sesión nueva: ganar experiencia en nivel 55 debe actualizar inmediatamente
el porcentaje ancestral y el tooltip debe usar el tramo de `heir_levels`, no el sentinel de
`levels[56]`.

## Aceptación retail

Aceptado por el usuario el 30 de agosto de 2026 sobre el cliente Returns r575: después de aplicar
el parche y volver a entrar, la barra y el tooltip reflejaron inmediatamente la experiencia
ancestral ganada. La segunda ejecución del aplicador detectó el hash reparado y no volvió a mutar
la entrada. El Control Center trata el SHA-256 del paquete como identidad informativa de caché y no
mantiene una allowlist bloqueante, por lo que esta nueva identidad no requiere cambios en el panel.

La verificación de integridad posterior abrió el índice de `523291` entradas y extrajo recursos no
relacionados: `game/ui/map/map_resources/main_world/en_us/world.dds` (`689840` bytes, SHA-256
`610A1349E8C9BA9B72800ABC1B0604A9DF337E551CBDFE2F00397D150D25DCB0`) y
`game/ui/icon/icon_item_shotgun_0024.dds` (`1688` bytes, SHA-256
`A162E6CAD29E95453228493EBAD54F71E6534C49545E4266A336117B1D18F0AC`).
