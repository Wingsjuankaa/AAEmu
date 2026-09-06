# Quest 9173 â€” actores ausentes en Priest's Office

## Incidente y causa

Dannia (1007) completa el objetivo de entrada en Priest's Office de **The Call of
the Hiram**, pero no encuentra a Alcos para el siguiente objetivo. La localizaciÃ³n
persistida/runtime es main_world/instance0, Zone351 `o_hirama_the_west_2`, alrededor
de `(20265.855,29745.934,375.347)`. Zone351 estaba cargada y con heartbeats normales.
Los logs 01:23:55â€“01:24:53 registran entradas/salidas de Sphere2817 y actualizaciÃ³n
de Quest9173; por tanto la detecciÃ³n de Ã¡rea sÃ­ funciona.

Faltaban los placements de los dos actores cliente de esta oficina tanto en el
catÃ¡logo versionado como en el bind mount runtime. Alcos no es un spawn NPC
convencional: es `client_doodad13375`, modelo `npctype://18681`. La entrega posterior
requiere `client_doodad13374`, sacerdotisa `npctype://18680`. No se debe reemplazar
ninguno por un NPC genÃ©rico ni forzar objetivos/completado de quest.

Target: `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`, HEAD al inicio
`bdad11fec1493c43a854369e707de72a20f26f86`. Padre consultado mediante fetch:
`upstream/client_version/zone-10.0.2_r575`, `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
El padre no contiene el overlay; AA8 no aporta un cierre especÃ­fico de este caso.
Se reutiliza el mecanismo AA10 previamente validado para actores como Alcanto.

## Clausura AA10 r575

Full y compact coinciden en todas las consultas relevantes; evidencia reproducible:
`reconstruccion_cliente_10/scripts/audit_hiram_priest_office.py` y
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\hiram-priest-office-frontier\native-contract.json`.

- Quest9173, capÃ­tulo18, race255; Progress39849 exige Sphere2817/act754.
- Progress39998 exige Effect72642/act80, count1.
- Alcos13375 arranca en fase38772. QuestReact43 recibe
  `quest9173 / Progress1 / component39849` y pasa a fase38773 (modelo18681).
- Func35536 de fase38773 usa skill39850, `DoodadFuncUse9921` (sin skill recursiva),
  siguiente fase38836. Skill39850 produce InteractionEffect72642 (`wi19`).
- La fase38836 usa QuestReact52 con component39998 y bubble136. Reacciones de
  abandono/completado conservan el estado individual definido por el cliente.
- Ready39850 exige report doodad13374, act87. Su fase38776 ejecuta ModelChange13
  (`npctype://18680`) y contiene report9173/offer9174 (func quests1133/1134).
- Se conserva la fase **Start38772** de Alcos, no la fase visible38773 global:
  la apariciÃ³n depende del progreso personal mediante el QuestReact existente.

Los templates y los placements exactos vienen del game_pak operacional r575,
extraÃ­dos read-only con `PakDoodadScan`, sin modificar el cliente:

```powershell
dotnet run --no-build --project reconstruccion_cliente_10/tools/PakDoodadScan --configuration Release -- E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game_pak 13374,13375
python reconstruccion_cliente_10/scripts/audit_hiram_priest_office.py
```

Ambos estÃ¡n en `game/worlds/main_world/level_design/cells/019_029/doodad.g`:

| Actor | Doodad | X | Y | Z | Yaw | Start |
|---|---:|---:|---:|---:|---:|---:|
| Sacerdotisa / entrega | 13374 | 20271.144 | 29738.3022 | 375.382 | 41.000077 | 38776 |
| Alcos / hablar | 13375 | 20270.493 | 29746.7012 | 375.233 | 121.000021 | 38772 |

Escala1, roll/pitch0. La auditorÃ­a compara coordenadas, orientaciÃ³n y fase contra
el CSV extraÃ­do, ademÃ¡s de comprobar igualdad de los contratos full/compact.

## Cambio y validaciÃ³n

Se agregan sÃ³lo estos dos placements al overlay
`AAEmu.Game/Data/Worlds/main_world/doodad_spawns_aa10_client_quest_proxies.json`
(29â†’31 actores). La regresiÃ³n `NuiaRacialQuestProxyCatalogTests` incluye ambos
con fase y coordenadas exactas; las pruebas existentes de QuestReact ya cubren la
arista especÃ­fica9173/component39849. No hay cambio de mecÃ¡nicas ni serializers.

Restore correcto, build Release cero errores (175 advertencias), suite completa
**1780/1780**, cero fallos/omitidas. AuditorÃ­a native-contract: pass.
El bind mount previo coincide semÃ¡nticamente con HEAD; se respalda antes de
sincronizar el overlay completo. Datos fuente/client/game_pak sin cambios.

## Despliegue

Aplicado conforme a la preferencia permanente del usuario de terminar desplegando.
SÃ³lo se recreÃ³ Game (`--no-deps --no-build`). Login y DB mantienen contenedores.
Game saliÃ³ limpiamente con exit0 a `2026-09-04T01:33:52.595334258Z`; SaveManager
no tenÃ­a escrituras pendientes. Backup posterior al stop:
`E:\AAEmu\rama_10\backups\hiram-priest-office-20260903\aaemu_game.sql`, SHA256
`5e031fb99dac0c725c44ae8d0378568251039e05e4ab581575bd3ccc790bb7c8`.
En la misma carpeta se conserva el overlay anterior.

- Imagen desplegada: `aaemu-world:10.0.2.13-r575-local`,
  `sha256:29608651f8e07cec3d1df892966f86ddc91ec93c1bab21e47ae11055556c3110`.
- Tag candidata: `aaemu-world:hiram-priest-office-fix-20260903`.
- Rollback: `aaemu-world:rollback-pre-hiram-priest-office-20260903`,
  `sha256:967f4a614fabd00f82dca88002fd65c9d6f627e071bf2fac8ad7acbdef771608`.
- SHA256 overlay idÃ©ntico en fuente, bind mount y `/app/game/Data/Worlds/main_world`:
  `e048e6b1f6e82a79734ab2301ea975b9c086dc01daefdceee6a9f6f8c0c21226`.
- AAEmu.Game.dll idÃ©ntico en `/app` y `/app/game`:
  `58844b1ca40e50ebe9d37348ec564d316478ae9688c61cd7f71ff02d67aa957f`.
- Contenedor Game: `f691a5de997ecf5931001bb9f4b54608f6a4282fcd2cb7d903775ff8ab8940a4`.
- Startup `01:35:31`, 68,05 segundos; **44809 doodads** en main_world,
  exactamente dos mÃ¡s que los44807 del runtime anterior. Ver `startup.log`.

## AceptaciÃ³n pendiente

Codex no operÃ³ Zones. El usuario relanza Zone351 desde Control Center, reconecta
a Dannia y sale/entra de Priest's Office. Se debe observar a Alcos y completar la
interacciÃ³n de hablar; despuÃ©s revisar logs antes de probar entrega/sucesora.
Quest9173 conserva status1 y component39849; la entrada/salida de Sphere2817 puede
poner su contador en1/0 de forma nativa. No se escribieron contadores ni estados de
misiÃ³n en DB. El actor visible, diÃ¡logo y progresiÃ³n final requieren aceptaciÃ³n retail.

## Aceptacion retail confirmada

El usuario confirma que pudo avanzar y aporta captura de Joining Forces (9174).
La DB de Dannia1007 muestra quest9174 Ready3 y quest9173 ya no activa.
Queda aceptada la correccion de Alcos y entrega a la sacerdotisa; el bloqueo
siguiente corresponde al actor Andega13376 ausente, tratado por separado.
