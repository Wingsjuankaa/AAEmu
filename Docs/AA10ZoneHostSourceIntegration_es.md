# Incorporación de la fuente ZoneHost y viabilidad Docker

Fecha: 2026-09-03. Target: `rama_10`, HEAD inicial
`41570558459efad934065d3ea348bffc52f45162`. Padre comprobado local y remotamente:
`upstream/client_version/zone-10.0.2_r575`, SHA `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
Los cambios de Smelting preexistentes se preservan.

## Actualización: publicación automática para Control Center

El usuario solicitó después que cada build quede listo para el panel. Desde esta
actualización, `Build-ZoneHost.ps1` publica Release por defecto. `-NoPublish`
conserva el modo de sólo build, y Debug no se publica. La sección de primera
entrega más abajo describe el estado anterior a esta autorización.

`Publish-ZoneHost.ps1` verifica binario y manifiesto, guarda candidato por hash,
fija hashes de las DLLs y reemplaza el EXE atómicamente con respaldo cuando está
libre. Si está en uso, deja `Bin64/.zonehost-updates/pending.json`. Control Center
0.1.6 consume ese pendiente antes de un arranque posterior cuando todas las Zones
que comparten el ejecutable lo hayan liberado. No se reinician procesos existentes.

Publicación real completada el 2026-09-03 a las 23:13:21 UTC: el ejecutable canónico
quedó en SHA `1A2F91A758E08D2597ED8A6DC8C23B4C65A6C69A2EDE782DA4D9A5E2079F1E03`.
La Zone observada al inicio ya no estaba ejecutándose cuando el publicador comprobó
el estado. Codex no la detuvo ni inició otra. Se conserva el binario previo en:

`E:\AAEmu\rama_10\zones\retail-zone-server-r575\Bin64\.zonehost-updates\backups\20260903T231321315-86C935A4C91C028DCB6AC99F6E2C710E4CEA692C6C1E8E398BC310257AEC457F.exe`.

Pruebas: siete escenarios de publicación sobre fixtures (proceso activo,
visibilidad insuficiente, bloqueo real de archivo, reemplazo/rollback, idempotencia, DLL modificada y
candidato alterado); cinco pruebas del servicio del panel. El build completo
del panel pasa typecheck, 52 tests con uno omitido y smoke SQLite nativo.
La publicación no implica aceptación de gameplay del host nuevo.

## Primera entrega: fuente y evaluación Docker

Se incorpora `Tools/AAEmu.ZoneHost/upstream` con los 32 archivos del commit comunitario
`8801e8272309b53288b63c4869a83f01b42eae14`, licencia y manifiesto normalizado UTF-8/LF.
Hay scripts versionados para instalar Rust de forma aislada, compilar, verificar
integridad, auditar el runtime sin ejecutarlo y preparar un contexto Docker acotado.

Guía: [Tools/AAEmu.ZoneHost/README.md](../Tools/AAEmu.ZoneHost/README.md).
No se cambia la dependencia del servidor .NET, ni se introduce WPF en sus builds Linux.

## Identidad y validación nativa

| Artefacto | SHA-256 |
|---|---|
| ZoneHost actualmente instalado | `86C935A4C91C028DCB6AC99F6E2C710E4CEA692C6C1E8E398BC310257AEC457F` |
| Candidato Release, CRT estático | `1A2F91A758E08D2597ED8A6DC8C23B4C65A6C69A2EDE782DA4D9A5E2079F1E03` |
| x2game-dev_dedicate.dll local | `8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A` |
| CrySystem.dll local | `960EB685DFCB509FC78FE3DFEFC23E4D08F5E5ADD6C53A31BEB8C93FF006C88A` |
| xlcommon.dll local | `D81BA53E5DF0DC6B5031D3D423A6A2720288D6CA40BE0768AAE85E2F30EA4113` |

Toolchain fijada: Rust `1.98.1-x86_64-pc-windows-msvc`; MSVC local `14.51.36231`.
El manifiesto de cada build registra SDK, compilador completo, flags y hashes de inputs.
Dos builds Release en salidas distintas produjeron el mismo SHA-256 indicado arriba.
Los tres probes del parser pasaron: exit 1 esperado antes de invocar `run()`.
El candidato mide 306.176 bytes e importa únicamente KERNEL32, USER32,
api-ms-win-core-synch-l1-2-0 y ntdll; no importa VCRUNTIME140.

Validación adicional completada:

- Integridad de los 32 archivos upstream: correcta.
- Seis checks PE de runtime: correctos, sin cargar DLLs.
- Parser PowerShell de los siete scripts: correcto.
- Esquema Compose experimental: correcto mediante `docker compose config --quiet`.
- Solución .NET: restore y build Release correctos; 179 warnings, cero errores.
- Suite ejecutada: 1.756 pruebas correctas, cero errores u omitidas.
- `dotnet sln list` conserva los ocho proyectos existentes; ZoneHost figura sólo como archivos.
- Ejecutable instalado conserva su SHA-256; Docker continúa en modo Linux.

Logs de la validación .NET en `artifacts/builds/zonehost/server-validation`.
Durante la tarea aparecieron cambios ajenos adicionales de crafting/housing;
se preservaron. La cifra de tests corresponde a la ejecución registrada, no a una
certificación de ediciones concurrentes posteriores.

Auditoría PE reproducible: tres firmas de instrucciones, cave de 128 bytes `CC`,
entrada de vtable de `ShipUnitModel` y export `Prompt` de CrySystem coinciden con
lo que espera este snapshot. Resultado externo:
`E:\AAEmu\rama_10\artifacts\builds\zonehost\native-audit.json`.
No se afirma clausura de ABI ni aceptación dinámica. La versión fuente exacta del
host anterior no se ha demostrado por equivalencia binaria.

Hallazgo: el parche de física de barcos se aplica incondicionalmente en memoria
antes de `CreateGameStartup`. El commit más reciente retiró su documentación,
no su implementación. Se conserva, y se exige prueba específica antes de promover.

## Docker: conclusión y evidencias

| Ruta | Estado | Consecuencia |
|---|---|---|
| Linux nativo | Incompatible con el código y DLLs actuales | `cfg(windows)`, Win32 y PE x64; recompilar Rust para Linux no convierte la DLL |
| Windows containers | Candidato experimental | Requiere motor Windows compatible y probar consola, dependencias y carga real |
| Linux + Wine | Hipótesis sin prueba | Requiere validar Win32/console, DLLs, memoria parcheada, motor, red y estabilidad; no basta ejecutar el EXE |
| ZoneHost Windows + Game/Login/MySQL Linux | Arquitectura actual conservada | Permite usar el nuevo candidato después de aceptación sin migrar servicios |

Docker Desktop actual informa `linux x86_64`. No se cambió de backend ni se
alteraron contenedores. Un mismo daemon no ejecuta esta imagen Windows como
servicio nativo dentro de nuestro stack Linux. Para el experimento usar un motor
Windows separado/VM y comunicarlo con World por su endpoint privado alcanzable.

Imports locales comprobados leyendo PE y corroborados con dumpbin:

- `x2game-dev_dedicate.dll`: MSVCP100/MSVCR100, TBB, xlcommon/xlleveldb,
  USER32, GDI32, GDI+, OLE, Winsock y otras APIs Windows.
- `CrySystem.dll`: MSVC100, TBB, xlcommon, USER32, AVIFIL32 y dbghelp.
- `xlcommon.dll`: MSVC100, TBB, xldiag, USER32/GDI32, Winsock y dbghelp.
- El host usa `AllocConsole`, `CONIN$`, `CONOUT$`, `GetConsoleWindow`, eventos
  locales y `VirtualProtect`. Reasigna stdout/stderr a consola nativa; Docker logs
  no es por sí solo evidencia completa de startup. Persistir save/logs.

La carga dinámica de otros módulos CryEngine requiere una auditoría adicional;
los imports anteriores no constituyen una lista completa de archivos necesarios.
No usar Nano Server como base inicial. La receta parte del API más amplio de
Windows Server; Server Core es una optimización posterior sujeta a pruebas.
La existencia de USER32 no demuestra por sí sola imposibilidad de contenedor;
sí hay que demostrar que el proceso no exige una sesión de escritorio interactiva.

Fuentes oficiales consultadas el 2026-09-03:

- [Microsoft: aplicaciones y limitaciones de Windows containers](https://learn.microsoft.com/en-us/virtualization/windowscontainers/quick-start/lift-shift-to-containers).
- [Microsoft: imágenes base Windows](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/container-base-images).
- [Docker: selección de motor Windows/Linux](https://docs.docker.com/desktop/setup/install/windows-install/).
- [Docker: red y acceso al host](https://docs.docker.com/desktop/features/networking/networking-how-tos/).

## Receta experimental preparada

Desde `Tools/AAEmu.ZoneHost`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/Prepare-DockerContext.ps1
```

Produce un contexto separado con el EXE, manifiesto, licencia, entrypoint y probes.
El contexto excluye retail DLLs, SQLite y game_pak. No construye ni inicia imágenes.

Sólo en el motor Windows compatible del laboratorio:

```powershell
docker build -t aaemu-zonehost:aa10-experimental E:\AAEmu\rama_10\artifacts\builds\zonehost\docker-context
docker run --rm aaemu-zonehost:aa10-experimental
```

El comando por defecto es `Probe`: errores controlados del parser, sin cargar Zone.
Un resultado correcto sólo valida el ejecutable/CRT en esa imagen. La imagen no fue
construida en esta sesión porque el motor disponible es Linux.

Para probar una Zone, el operador prepara una **copia aislada** del árbol nativo,
con Bin64, juego, game_pak, DB, configs y spawner verificado de una única partición.
La copia debe ser independiente de archivos mutables del runtime en uso y contener
el archivo marcador `.aaemu-zonehost-isolated-runtime` en su raíz. No usar el
árbol activo ni un junction que lo exponga. El entrypoint sólo sobrescribe el
ZoneHost de esa copia marcada. Montar el save en otra carpeta persistente.

`docker/compose.windows.experimental.yaml` exige las variables `AA10_ZONE_RUNTIME`,
`AA10_ZONE_SAVE`, `AA10_ZONE_NAME`, `AA10_WORLD_IP` y opcional `AA10_WORLD_PORT`.
El perfil `zone-experiment` es explícito, no publica puertos y no tiene restart automático.
World debe escuchar en una IP alcanzable desde ese motor. `127.0.0.1` apunta al
contenedor, no a nuestro host; tampoco se debe asumir que el nombre de servicio
`game` existe en una red Docker distinta.

La receta no incluye healthcheck ficticio basado en PID. La aceptación exige:
consola y DLLs funcionales, `ZWJoin`/`WZJoinResponse`, `ZoneLoaded` de la partición,
heartbeats sostenidos, NPCs, entrada/salida de personaje y pruebas de persistencia.
El gate de lifecycle de la skill AA10 requiere autorización explícita para esa
prueba y su único perfil; la incorporación de fuente no la ejecuta.

Docker aporta empaquetado, aislamiento y distribución. No elimina los heaps del
motor por Zone; los límites de memoria no sustituyen la optimización del runtime.
Antes de plantear todas las zonas simultáneas medir memoria privada, residente,
commit global y picos de carga. La orquestación actual precarga zonas pero no
implementa todavía descarga por inactividad ni presupuesto de memoria.

## Siguientes fronteras

1. Aceptación del candidato Windows local con un único perfil autorizado.
2. Probes de consola y carga en motor Windows de laboratorio; después gameplay.
3. Instrumentar consumo por fase y catálogo de consola; separar bootstrap de heaps del motor.
4. Diseñar descarga segura de zonas y límites de precarga conservando estado autoritativo.

En la primera entrega no se desplegó el candidato ni se operó una Zone. La incorporación de fuente y la
evaluación Docker están terminadas; la aceptación del runtime y del contenedor son
fronteras separadas, no resultados implícitos de un build correcto.
