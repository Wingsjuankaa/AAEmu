# Arranque de las Zones nativas AA10 r575

Procedimiento validado para levantar Solzreed completo con el cliente ArcheAge
Returns `10.0.2.13 r575` y conectarlo al World de `rama_10`.

Solzreed está dividido en tres procesos nativos. Levantar sólo uno permite
entrar, pero World devuelve al personaje a selección al cruzar a una partición
no registrada:

| Mapa nativo | Zone key |
|---|---:|
| `w_solzreed_1` | 142 |
| `w_solzreed_2` | 178 |
| `w_solzreed_3` | 179 |

### Pruebas limitadas a Lacton

No inferir la partición nativa desde el nombre o ID del distrito mostrado por
el cliente. En la prueba del 2026-08-15, el personaje guardado en Lacton
(distrito visitado `338`) solicitó explícitamente `zoneId=142` durante
`CSSpawnCharacter`; por tanto, para repetir pruebas en esa posición hay que
levantar únicamente:

```cmd
E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10_worker.cmd w_solzreed_1 142
```

Este es el perfil de arranque por defecto mientras las pruebas permanezcan en
Lacton. No ejecutar `launch_zone_aa10.cmd` en este perfil, porque ese coordinador
abre las tres particiones de Solzreed. La consola debe quedar visible con un
título equivalente a `Zone(w_solzreed_1_0) pid(<pid>)`; no basta con que exista
un proceso oculto.

La confirmación autoritativa es el log de World
`EnterZone ... character ... zoneId=<id>`, no el ID del distrito ni el nombre
visible del asentamiento. Si el personaje vuelve a guardarse en otra
partición, consultar ese log antes de elegir el worker.

Cada partición necesita además su propio `npc_spawners.g`. Si falta, el terreno
carga y el handoff funciona, pero la Zone queda sin NPCs. Los archivos oficiales
están dentro del `game_pak` r575 y deben quedar en:

```text
<Zone root>\game\worlds\main_world\level_design\zone\142\zone_server\npc_spawners.g
<Zone root>\game\worlds\main_world\level_design\zone\178\zone_server\npc_spawners.g
<Zone root>\game\worlds\main_world\level_design\zone\179\zone_server\npc_spawners.g
```

MD5 esperados:

| Zone key | Bytes | MD5 |
|---:|---:|---|
| 142 | 224917 | `BEEEF62550B39D1C5399240D36B13CB6` |
| 178 | 36161 | `2D95095DBA37E4305F2FAA0E0E72175E` |
| 179 | 233609 | `10016F3E3DAF8DC2C9F2CE5B4ABB4166` |

## Comando correcto

Cada Zone debe iniciarse con el nombre base de su mapa:

```cmd
AAEmu.ZoneHost.exe +zone w_solzreed_1
AAEmu.ZoneHost.exe +zone w_solzreed_2
AAEmu.ZoneHost.exe +zone w_solzreed_3
```

No usar `w_solzreed_3_0`: ese es el nombre que puede mostrar la instancia una
vez cargada, pero no es el identificador aceptado por el arranque. El síntoma
del argumento incorrecto es `Couldn't find zone 'w_solzreed_3_0'`.

Tampoco añadir `-devmode devmode.cfg`, duplicar `+zone` ni mezclar argumentos
del cliente Kakao/AA8. La Zone r575 probada sólo necesita el argumento anterior;
la dirección de World se obtiene desde `system.cfg`.

## Rutas y configuración probadas

- Iniciador idempotente: `E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10.cmd`
- Coordinador: `E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10.ps1`
- Worker por consola: `E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10_worker.cmd`
- Zone root: `E:\AAEmu\rama_10\zones\retail-zone-server-r575`
- Ejecutable: `<Zone root>\Bin64\AAEmu.ZoneHost.exe`
- DLL nativa: `<Zone root>\Bin64\x2game-dev_dedicate.dll`
- Guardado/logs: `E:\AAEmu\rama_10\server\AAEmu\.server_files\AAEmu.ZoneHost\zone-<key>`
- Configuración: `<Zone root>\system.cfg`

Contenido requerido de `system.cfg`:

```cfg
world_serveraddr = "192.168.100.20"
world_serverport = 1240
```

Cada worker define además:

```cmd
set "AAEMU_ZONE_SAVE_DIR=E:\AAEmu\rama_10\server\AAEmu\.server_files\AAEmu.ZoneHost\zone-<key>"
set "AAEMU_ZONE_DLL=E:\AAEmu\rama_10\zones\retail-zone-server-r575\Bin64\x2game-dev_dedicate.dll"
set "AAEMU_ZONE_LOG_NAME=zone-<key>"
```

## Secuencia de arranque

Si falta algún spawner, extraerlo sin modificar el `game_pak`:

```powershell
$pak = 'E:\AAEmu\rama_10\zones\retail-zone-server-r575\game_pak'
$root = 'E:\AAEmu\rama_10\zones\retail-zone-server-r575\game\worlds\main_world\level_design\zone'

foreach ($key in 142, 178, 179) {
    $entry = "game/worlds/main_world/level_design/zone/$key/zone_server/npc_spawners.g"
    $target = Join-Path $root "$key\zone_server\npc_spawners.g"
    if (Test-Path -LiteralPath $target) {
        Write-Host "Ya existe: $target"
        continue
    }
    dotnet run --project '.server_files\Tools\PakExtract\PakExtract.csproj' `
      --configuration Release -- $pak $entry $target
}
```

El coordinador valida la presencia y el MD5 de los tres archivos y rechaza el
arranque si alguno falta o no corresponde a r575.

1. Levantar y comprobar `db`, `login` y `game`:

   ```powershell
   Set-Location 'E:\AAEmu\rama_10\server\AAEmu'
   docker compose -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml up -d
   docker compose -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml ps
   ```

2. Confirmar que `game` publica `192.168.100.20:1240` y está `healthy`.
   El healthcheck sólo confirma que el proceso de World está vivo; antes de abrir el cliente hay que
   esperar también su registro en Login:

   ```powershell
   docker compose -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml `
     logs login --since 5m | Select-String 'Registered GameServer GameServerId'
   ```

   Si el cliente pide la lista antes de esa línea, conserva `Under Maintenance` aunque World se
   registre segundos después. En ese caso usar el botón de refresco o reiniciar sólo el cliente con el
   mismo comando directo; no reconstruir los servicios.
3. Ejecutar con doble clic y mantener abiertas las tres consolas:

   ```text
   E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10.cmd
   ```

4. Esperar `ZoneLoaded` para `zoneId=142`, `178` y `179`; el registro debe
   indicar `loadedCount=3` antes de abrir o conectar el cliente.
5. Iniciar el cliente AA10 desde su `Bin64`. El contrato autoritativo es esta
   línea de comandos, tomada del cliente 10.x; no usar ArcheEmu Launcher ni
   argumentos Kakao/AA8:

   ```cmd
   cd /d "E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\Bin64"
   start "" "archeage.exe" -devmode -StrUserName=test -strUserToken=testtoken -sIp=127.0.0.1 -sPort=1237 -gameId=1 +locale en_us
   ```

   `launch_aaemu.bat` es solamente el wrapper local de ese mismo comando y se
   puede abrir con doble clic:

   ```text
   E:\AAEmu\rama_10\runtime\launchers\launch_aaemu.bat
   ```

   Para un arranque automatizado desde Codex, iniciar `archeage.exe`
   directamente con esos argumentos y con `Bin64` como directorio de trabajo;
   no encadenar otro launcher.

   No añadir `-serverId` ni `-selectedServerId`: esos argumentos saltan la
   selección de World y dificultan sobrevivir a reinicios de World/Zone.

### Si no aparece el splash

No cambiar el comando ni probar launchers alternativos. Comprobar primero si
`archeage.exe` continúa vivo. El 2026-08-15 se observó un arranque que terminó
antes del splash con `APPCRASH`, excepción `0xc0000005` en `KERNELBASE.dll`; la
DLL `crysystem.dll` conservaba el hash parcheado correcto y un reintento con la
misma línea directa abrió correctamente la ventana DX11 r575.

Validación mínima antes de inventar otra variante de arranque:

```powershell
Get-CimInstance Win32_Process -Filter "Name='archeage.exe'" |
    Select-Object ProcessId, ExecutablePath, CommandLine

Get-WinEvent -FilterHashtable @{
    LogName = 'Application'
    StartTime = (Get-Date).AddMinutes(-5)
} | Where-Object { $_.Message -match 'archeage\.exe' } | Select-Object -First 5
```

Un reinicio de `game` desconecta las Zones nativas. Después de reiniciar World
hay que cerrar las consolas Zone antiguas, volver a ejecutar
`launch_zone_aa10.cmd` y esperar otra vez los tres `ZoneLoaded`.

### Recuperación de la carrera de arranque

Se observó que, inmediatamente después de reconstruir/recrear World, iniciar las tres Zones al mismo
tiempo puede hacer que 178 y 179 alcancen `ZoneLoaded` juntas y luego cierren con
`recv exception: internal 4 wsa 258` / `client disconnected (reason=1)`. No es falta de spawners: es
una carrera temporal del host nativo. La recuperación validada es mantener 142 activa y relanzar una
sola partición por vez:

```cmd
E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10_worker.cmd w_solzreed_2 178
```

Esperar su `ZoneLoaded` y socket `Established`; recién entonces:

```cmd
E:\AAEmu\rama_10\runtime\launchers\launch_zone_aa10_worker.cmd w_solzreed_3 179
```

El resultado correcto en World es `loadedCount=1`, luego `2`, luego `3`. No relanzar 142 si ya tiene
heartbeat estable: el coordinador es idempotente, pero una consola pausada de un intento fallido puede
parecer una Zone activa cuando el proceso `AAEmu.ZoneHost.exe` ya terminó.

## Validación rápida

Proceso y argumento exacto:

```powershell
Get-CimInstance Win32_Process -Filter "Name='AAEmu.ZoneHost.exe'" |
  Select-Object ProcessId, ExecutablePath, CommandLine
```

Deben aparecer tres procesos, uno por cada `w_solzreed_1`, `w_solzreed_2` y
`w_solzreed_3`.

Conexión de la Zone a World:

```powershell
$zone = Get-CimInstance Win32_Process -Filter "Name='AAEmu.ZoneHost.exe'"
Get-NetTCPConnection -OwningProcess $zone.ProcessId |
  Where-Object RemotePort -eq 1240
```

Deben existir tres conexiones `Established` hacia `192.168.100.20:1240`.

Registro, carga y heartbeats:

```powershell
docker compose -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml `
  logs game --since 5m |
  Select-String 'ZWJoin|WZJoinResponse|ZoneLoaded zoneId=(142|178|179)|ZWHeartbeat'
```

Se consideran señales de éxito:

- `ZWJoin` para IDs `142`, `178` y `179`
- `WZJoinResponse` para las tres zonas
- `ZoneLoaded` para las tres zonas y `loadedCount=3`
- `ZWHeartbeat` continuo
- replicación `ZWSpawnNpc` sin `fail=[1-9]`
- contadores nativos observados: 514 spawners en 142, 166 en 178 y 329 en 179
- heartbeats estabilizados con unidades distintas de cero en las tres Zones

La existencia del proceso por sí sola no prueba que el mapa esté cargado; se
deben comprobar también la conexión TCP, `ZoneLoaded` y los heartbeats.

## Parche de parpadeo de pantallas al iniciar el cliente

Validado el 2026-08-15 exclusivamente para `crysystem.dll` 10.0.2.13 r575. El
script `E:\AAEmu\rama_10\artifacts\client-patches\patch_crysystem_display_flicker.py` sustituye tres
llamadas de prueba a `USER32!ChangeDisplaySettingsExA` con flags
`CDS_TEST|CDS_FULLSCREEN` por un retorno exitoso local. No modifica las llamadas
que aplican realmente un modo de pantalla.

Identidad de la DLL cliente combinada con el parche previo de `system.cfg`:

```text
SHA-256 antes: 7B82ADCE2504D157AF4B5C55532D28E1B0C25D2F8F59285E59F921C43503D8F0
SHA-256 después: 960EB685DFCB509FC78FE3DFEFC23E4D08F5E5ADD6C53A31BEB8C93FF006C88A
Bytes: 1420288
Offsets: 0xB6102, 0xB623E, 0xB65D9
Reemplazo en cada sitio: 33 C0 90 90 90 90
```

Respaldo autoritativo de la DLL inmediatamente anterior al parche:

```text
E:\AAEmu\rama_10\backups\ui-and-client\test-backups\crysystem_display_flicker_20260815\E_AAEmu-Research_test_ArcheAge Returns 10.0.2.13 - 8yx - r575 - 2026-06-18_Bin64_crysystem.dll.20260815T194423Z.bak
```

No ejecutar el script sin argumentos: sus defaults proceden de otro entorno.
Aplicar sólo con `--dll <cliente>\Bin64\crysystem.dll` y un `--backup-root`
explícito. Cerrar antes `archeage.exe` y cualquier Zone que tenga cargada esa
copia de la DLL. Después relanzar Zone y cliente y comparar duración del arranque,
parpadeos y estabilidad de los monitores.
