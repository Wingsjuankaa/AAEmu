# ZoneHost en el desarrollo AA10

Fuente canónica: `E:\AAEmu\rama_10\server\AAEmu\Tools\AAEmu.ZoneHost`.
Se incorpora el snapshot de [NickMesser/AAEmuZoneHost](https://github.com/NickMesser/AAEmuZoneHost)
en commit `8801e8272309b53288b63c4869a83f01b42eae14` (2026-09-02).
El padre del servidor continúa siendo `AAEmu/AAEmu:client_version/zone-10.0.2_r575`.
Este repositorio comunitario es una dependencia de tooling independiente.

## Contenido y alcance

- `upstream/`: los 32 archivos originales, incluyendo el host Rust, ZoneManager WPF,
  documentación y licencia GPL-3.0. No contiene DLLs retail, game_pak ni bases de datos.
- `upstream-manifest.json`: procedencia y SHA-256 de cada archivo, normalizado a
  UTF-8/LF para tolerar `core.autocrlf`. El snapshot no tiene modificaciones funcionales.
- `build-settings.json`: toolchain y target Rust fijados.
- `scripts/`: instalación aislada del compilador, build, integridad y auditoría estática.
- `docker/`: receta Windows **experimental y sin aceptación de runtime**.

El ejecutable del Control Center sigue en `zones/retail-zone-server-r575/Bin64`.
Cada build **Release** verifica y publica automáticamente allí: si está libre,
reemplazo atómico con respaldo; si hay Zones activas, actualización pendiente.
Control Center **0.1.6** la aplica antes de un inicio posterior cuando el ejecutable
esté libre. No inicia, detiene ni reinicia Zones. `-NoPublish` conserva el modo
de sólo compilación; Debug nunca se publica automáticamente.

## Compilar

Requiere Windows x64 y Visual Studio C++ x64 con Windows SDK. `vswhere` selecciona
la instalación y el build registra las versiones exactas de MSVC y SDK utilizadas.
No se fija una ruta de versión de Visual Studio.

Desde esta carpeta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/Initialize-Toolchain.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/Build-ZoneHost.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/Test-Candidate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/Test-NativeRuntime.ps1 `
  -ReportPath E:\AAEmu\rama_10\artifacts\builds\zonehost\native-audit.json
```

`Initialize-Toolchain.ps1` descarga Rust desde su distribución oficial y verifica
el hash fijado del bootstrap antes de ejecutarlo. Usa `artifacts/toolchains/zonehost-rust`;
no altera el PATH global. Requiere red sólo para preparar el compilador. El build
usa Cargo `--offline --frozen`, sin dependencias Rust de terceros.

Salida Release:

```text
E:\AAEmu\rama_10\artifacts\builds\zonehost\release\AAEmu.ZoneHost.exe
E:\AAEmu\rama_10\artifacts\builds\zonehost\release\build-manifest.json
```

Se admiten `-ToolchainRoot`, `-OutputRoot`, `-Configuration Debug`, `-NoPublish`
y `-RuntimeBinDirectory <Bin64>` (por defecto, el runtime canónico del panel).
Los outputs de Cargo siempre quedan fuera de `upstream/`. El build Release utiliza
`/Brepro`, remapeo de la ruta de fuente y CRT estático del host. Esto evita agregar
VCRUNTIME140 como dependencia del host; las DLLs retail conservan sus runtimes propios.
La reproducción byte a byte se exige con el mismo compilador, MSVC, SDK y configuración;
no se promete el mismo hash entre versiones distintas de esas herramientas.

`Test-Candidate.ps1` ejecuta únicamente tres errores de argumentos que se resuelven
antes de cargar DLLs. Verifica el hash del candidato, código de salida y diagnósticos.
No es una prueba de arranque de Zone. `Test-NativeRuntime.ps1` lee PE, imports,
firmas del parche de barcos y RVA exportado de CrySystem sin ejecutar código nativo.

## Publicación automática e integración con Control Center

`Build-ZoneHost.ps1` ejecuta los probes del candidato y la auditoría nativa antes
de llamar a `Publish-ZoneHost.ps1`. El publicador guarda la versión por SHA-256
bajo `Bin64/.zonehost-updates`, con los hashes de las DLLs y el manifiesto.
Una actualización pendiente no se aplica si cambian las DLLs después de compilar.
El cambio del EXE usa reemplazo atómico y conserva el anterior en `backups/`.
La operación repetida es idempotente y no pierde el registro del respaldo.

Si hay Zones activas, el panel informa que sigue usando la versión anterior;
el nuevo build se aplica antes de un inicio posterior cuando todas liberen el EXE.
No necesita cambiar de perfil ni apuntar al directorio de builds. Abrir el nuevo
portable 0.1.6 una vez habilita el consumo de pendientes para futuros builds.

Publicación manual sin recompilar (mismos controles):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/Publish-ZoneHost.ps1
```

Los casos de integridad, proceso activo/desconocido, reemplazo, idempotencia y
rollback se prueban con `scripts/Test-Publication.ps1` sobre un fixture temporal.

El contrato existente permanece: nombre `AAEmu.ZoneHost.exe`, argumento `+zone`,
variables `AAEMU_ZONE_DLL`, `AAEMU_ZONE_SAVE_DIR`, `AAEMU_ZONE_LOG_NAME` y consola
Win32 provista por `AAEmu.ZoneProcessHost`/ConPTY. El panel verifica ruta/proceso;
no contiene una allowlist fija de hashes de ZoneHost que deba actualizarse.

El usuario autorizó la publicación automática de builds en esta integración.
Publicación no equivale a aceptación de gameplay: comprobar spawner, handshake,
`ZoneLoaded`, heartbeats y comportamiento con la partición de prueba autorizada.
No apuntar el perfil
directamente a la carpeta de builds: `XlSetWorkingDir(true)` deriva la raíz del juego
desde la ubicación del ejecutable. La política de lifecycle de la skill AA10 continúa vigente.

El host comunitario aplica **siempre** el parche de física de barcos antes de
`CreateGameStartup`; no existe un switch para desactivarlo en este snapshot.
La integración conserva ese comportamiento. Compatibilidad de bytes no equivale
a aceptación de barcos ni a equivalencia funcional con nuestro ejecutable anterior.

## Desarrollo y actualizaciones

Mantener upstream intacto y las herramientas locales fuera de ese directorio.
Una actualización debe revisar el diff del commit comunitario elegido y regenerar
el manifiesto desde esa fuente identificada; no actualizar sólo hashes para ocultar
cambios locales. Si se modifica Rust, conservar el parche local y su procedencia
explícitos antes de adaptar el pipeline para aplicarlo. La primera integración
establece una base comunitaria compilable sin cambios al host.

ZoneManager se conserva como referencia y proyecto independiente; no se añade como
dependencia de la solución Linux/.NET ni reemplaza nuestro Control Center. No fue
compilado ni iniciado como parte de esta integración del host.

Informe de resultados, Docker y próximos gates:
[AA10ZoneHostSourceIntegration_es.md](../../Docs/AA10ZoneHostSourceIntegration_es.md).
