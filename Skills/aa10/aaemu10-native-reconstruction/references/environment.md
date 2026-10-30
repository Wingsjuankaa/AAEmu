# Entorno y mapa AA10

| Propósito | Ruta |
|---|---|
| Raíz canónica AA10 | `E:\AAEmu\rama_10` |
| Target código/runtime | `E:\AAEmu\rama_10\server\AAEmu` |
| Fork remoto | `https://github.com/Wingsjuankaa/AAEmu.git`, branch `rama_10` |
| Padre upstream | `https://github.com/AAEmu/AAEmu`, branch `client_version/zone-10.0.2_r575` |
| Cliente principal r575 (desde 2026-09-06) | `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview` |
| Referencia original inmutable | `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575` |
| Piloto español histórico | `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES` |
| SQLite completa | `E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3` |
| Respaldos SQLite clasificados | `E:\AAEmu\rama_10\data\sqlite` |
| Compact del principal, con traducción/parches | `<cliente principal>\game\db\compact.sqlite3` |
| x2game release | `<cliente principal>\Bin64\x2game.dll` |
| game_pak operativo | `<cliente principal>\game_pak` |
| Zone nativa r575 | `E:\AAEmu\rama_10\zones\retail-zone-server-r575` |
| Fuente/build de ZoneHost | `E:\AAEmu\rama_10\server\AAEmu\Tools\AAEmu.ZoneHost` |
| Launchers | `E:\AAEmu\rama_10\runtime\launchers` |
| Control Center | `E:\AAEmu\rama_10\tools\AAEmu.ControlCenter` |
| Forensics AA10 | `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics` |
| Comparador AA8 | `D:\Proyectos\AAemu\rama_8` |
| Grafo AA8 | `E:\AAEmu-Research\output\aa8-client-forensics` |

El principal usa `+locale en_us` para el producto español. Para un baseline
nativo, consultar la referencia original y registrar su hash por separado;
no atribuirle los textos ni la geometría de UI parcheados del principal.

Cliente target: Returns `10.0.2.13`, revisión `r575`, x86-64. SDK del
repositorio: .NET 10 mediante `global.json`. Solución: `AAEmu.slnx`.

El repositorio contiene Login, Game, World/Zone, pruebas unitarias e
integraciones. Leer `docker-compose.yaml`, `.env` y configuraciones actuales en
cada tarea; no congelar puertos o credenciales en la skill. No imprimir ni
cometer valores secretos de `.env`.

Usar `dotnet restore`, build Release y `AAEmu.UnitTests`. Las integraciones
requieren dependencias y datos reales; no ejecutarlas como si fueran unitarias.

Mantener cliente, game_pak, SQLite retail, dumps, `.env`, resultados de tests y
outputs forenses grandes fuera de Git.

## Acceso de clientes LAN y externos

El flujo AA10 r575 validado requiere tres endpoints TCP de jugador: Login
`1237`, Game `1239` y Stream `1250`. Publicar solamente Login/Game permite
llegar al selector de world, pero el cliente cae aproximadamente 20 segundos
después porque `X2EnterWorldResponsePacket` también entrega el puerto Stream.

- Runbook LAN aplicado y rollback:
  `E:\AAEmu\rama_10\tools\AAEmu.LanLauncher\docs\LAN_NETWORK_TEST_ES.md`.
- Plan de pruebas externas mediante Playit:
  `E:\AAEmu\rama_10\tools\AAEmu.LanLauncher\docs\PLAYIT_PUBLIC_TEST_PLAN_ES.md`.

Para acceso externo nunca anunciar la IP privada `192.168.100.20`. Registrar
primero host/IP y puertos públicos asignados. Login permite anunciar Game por
separado; Stream todavía acopla puerto de escucha y puerto anunciado, por lo
que un puerto público distinto de `1250` exige cerrar antes un
`StreamNetwork.AdvertisedPort` probado. No tunelar ZoneAuthority `1240`, Web API
`1280`, MySQL, Adminer, Control Center ni Docker.

`D:\Proyectos\AAemu\rama_10` y las rutas históricas de `E:\AAEmu-Research`
son aliases de compatibilidad. Los chats nuevos deben leer
`E:\AAEmu\rama_10\README.md` y crear todo contenido AA10 nuevo bajo la raíz
canónica.

## Arranque Zone nativa r575 — operación exclusiva del usuario

Para compilar/publicar el ejecutable, seguir
[zonehost-development.md](zonehost-development.md). Release publica por defecto
mediante el wrapper del proyecto, con respaldo o pendiente si está ocupado.
Control Center 0.1.6 incorpora el consumo de pendientes antes del siguiente inicio
con el EXE libre. Esta publicación autorizada no inicia ni detiene Zones y no
cambia la política de lifecycle descrita en `SKILL.md`.

El usuario controla todas las Zones mediante AAEmu Control Center. Codex no
ejecuta los comandos de esta sección ni inicia, detiene, relanza o reconcilia
`AAEmu.ZoneHost.exe`. Puede usar estos datos para diagnóstico read-only,
comprobar el perfil seleccionado y validar `ZoneLoaded`/heartbeats después de
que el usuario realice la operación.

### Método preferido: AAEmu Control Center

El usuario usa el portable o el entorno de desarrollo de
`AAEmu.ControlCenter` para elegir las zonas y lanzarlas. Codex puede validar el
perfil y operar Docker sólo cuando la tarea lo autorice. El perfil canónico ya
combina `docker-compose.yaml` con
`.server_files\docker-compose.aa10.yaml` y apunta a la SQLite autoritativa.

- Elegir world `normal` por defecto; no agrega `serverId`.
- `Iniciar entorno` no elimina volúmenes ni datos.
- Abrir el API interno mediante `docker exec`; no publicar el puerto 1280.
- Consultar `tools\AAEmu.ControlCenter\docs\OPERATIONS.md` ante un diagnóstico.

Los comandos siguientes son referencia operativa para el usuario y evidencia
de diagnóstico; Codex no debe ejecutarlos como fallback.

Para levantar Solzreed completo usar primero el procedimiento probado en
`E:\AAEmu\rama_10\server\AAEmu\Docs\AA10NativeZoneRunbook_es.md`.

Para pruebas limitadas al personaje guardado en Lacton, el perfil por defecto
es **una sola Zone visible**:

```cmd
E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10_worker.cmd w_solzreed_1 142
```

No inferir la partición desde el distrito `338`: el `zoneId=142` fue confirmado
por `CSSpawnCharacter`/`EnterZone`. Exigir `ZoneLoaded zoneId=142`,
`loadedCount=1` y heartbeat antes de abrir el cliente.

El arranque autoritativo del cliente es directo desde su `Bin64`:

```cmd
cd /d "E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview\Bin64"
start "" "archeage.exe" -devmode -StrUserName=test -strUserToken=testtoken -sIp=127.0.0.1 -sPort=1237 -gameId=1 +locale en_us
```

`launch_aaemu.bat` sólo envuelve esa línea. No usar ArcheEmu Launcher, no
mezclar argumentos Kakao/AA8 y no añadir `-serverId` o `-selectedServerId`. Si
no aparece el splash, comprobar proceso y `APPCRASH` antes de variar el comando.

### Perfil Solzreed completo

Usar este perfil sólo cuando la prueba vaya a cruzar particiones del mapa:

- ejecutar `E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10.cmd` y mantener abiertas
  las tres consolas nativas;
- levantar `w_solzreed_1` (142), `w_solzreed_2` (178) y
  `w_solzreed_3` (179), cada una en un proceso separado;
- exigir el `npc_spawners.g` r575 de cada Zone y validar sus MD5 según el
  runbook; una Zone puede cargar terreno y aceptar jugadores aun sin NPCs;
- no usar `w_solzreed_3_0`, argumentos Kakao/AA8 ni `-devmode devmode.cfg`;
- después de reiniciar World, pedir al usuario que relance el perfil y luego
  comprobar los tres `ZoneLoaded`, `loadedCount=3` y heartbeats antes de
  conectar el cliente.

No mezclar perfiles. Para Lacton el usuario levanta sólo
`w_solzreed_1`/142 y se exige `loadedCount=1`; para Solzreed completo usa el
perfil del panel y se exige `loadedCount=3`. Tras reiniciar World, Codex informa
que el perfil debe relanzarse y espera la acción del usuario.
