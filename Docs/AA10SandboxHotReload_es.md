# Recarga del código real del sandbox AA10

La escena vigente es Zone411. El caso real posterior de Disparo de precisión
23592 corrigió geometría y búsqueda de impactos editando dos cuerpos C#:
contador CLR0→2, mismo World396, Native31564, cliente26548 y sesión3225459956;
usuario confirmó daño a30 y44–45 m. Ver
[AA10PrecisionShotRange_es.md](AA10PrecisionShotRange_es.md). Las pruebas con
la sonda y los PIDs antiguos de abajo son la aceptación inicial, no el estado
que deben asumir futuras sesiones. Skills versionadas en Skills/aa10.

El modo de desarrollo ejecuta `AAEmu.World` bajo `dotnet watch` en Debug.
Su referencia de proyecto incluye `AAEmu.Game` y `AAEmu.Commons`: se editan
las implementaciones reales de skills, plots y efectos. No se incorpora una
segunda simulación ni un lenguaje alternativo de mecánicas.

## Arranque de desarrollo

En el contenedor SDK aislado, con el repositorio E montado en `/src` y el
runtime E en `/runtime`, la forma comprobada de los flags de SDK 10 es:

Imagen comprobada en esta entrega: SDK10.0.403, Alpine3.24, runtime10.0.14;
digest `sha256:cc02b814237a76c4735fb6eeee87181597b5e56f2ce458a435e527674d91f4d7`.
El grafo efectivo en el contenedor contiene tres proyectos y4.209 archivos.

```text
dotnet watch --project /src/AAEmu.WorldServer/AAEmu.World/AAEmu.World.csproj
  --configuration Debug --no-launch-profile --non-interactive
  --artifacts-path /runtime/watch-build
```

Es una sola línea/array de argumentos. `run` es el comando predeterminado.
La primera ejecución debe restaurar dependencias en ese árbol de artefactos;
no añadir `--no-restore` antes de que existan sus assets. Las propiedades
evaluadas del proyecto son `net10.0`, `Optimize=false`, `DebugType=portable`
y símbolos habilitados. Una consulta `--list` local con los mismos flags
encontró 4.203 archivos, incluidas `Skill.cs` y la sonda de recarga.

Variables del proceso de watch:

| Variable | Destino |
| --- | --- |
| `GameContentRoot` | `/app/game` |
| `ZoneGameDataRoot` | `/app/game/ClientData/game` |
| `DOTNET_USE_POLLING_FILE_WATCHER` | `1`, para el bind mount de Windows |
| `DOTNET_WATCH_SUPPRESS_LAUNCH_BROWSER` | `1` |
| `HOME`, `DOTNET_CLI_HOME` | `/runtime/dotnet-home` |
| `NUGET_PACKAGES` | `/cache/packages`, bind del caché E |
| `TMPDIR` | `/tmp`, tmpfs RAM privado del contenedor |
| `XDG_RUNTIME_DIR` | `/run/aa10`, tmpfs RAM privado con modo0700 |

Se mantienen DB/Login aislados y los puertos del sandbox. No hacen falta
puertos nuevos del host para DB o Login interno. `GameContentRoot` requiere
Config, Configurations y Data/compact.sqlite3; el SDK base no trae el árbol
publicado de Game. Conservar sus mounts e incluir `NLog.config` explícitamente.
Las opciones World se leen primero desde el directorio del ensamblado World,
que ahora está en `/runtime/watch-build/bin/AAEmu.World/debug`; un antiguo
mount `/app/Config.json` no sustituye ese archivo. Usar overrides de entorno
o el `Config.Local.json` de ese directorio. Posteriormente World establece
`FileManager.AppPath`, cambia cwd al contenido Game e invoca Game.Main.

Game conserva su configuración/credencial privada y carga scripts por
reflexión de forma predeterminada. Limitar `WebApiNetwork.Host` a
`127.0.0.1` dentro del contenedor; sus consultas se realizan por `docker exec`
y no requieren publicar el API. Los outputs y logs deben resolver a binds E.

En SDK10.0.403/runtime10.0.14 los mutex Unix no funcionan sobre el bind Windows.
`/tmp` y `/run/aa10` usan tmpfs y desaparecen con el contenedor, sin escribir
en C. Se conserva `HOME`/`DOTNET_CLI_HOME`, caché NuGet y build en E. Véase el
[cambio de mutex documentado por dotnet/runtime](https://github.com/dotnet/runtime/issues/135726).
Docker Desktop ya usa `E:/DockerDesktopWSL/DockerDesktopWSL`.

## Prueba observable de Hot Reload

`GET /api/mechanics-sandbox/runtime` devuelve:

```json
{"success":true,"pid":42,"hotReloadSupported":true,"runningUnderWatch":true,
 "updateCount":0,"lastUpdateUtc":null,"diagnosticStamp":"aa10-real-runtime-v1",
 "runtimeVersion":".NET 10.0"}
```

La ruta sólo se habilita si el sandbox está activado y vinculado a IDs de
personaje/cuenta no nulos, nombre no vacío y listener API loopback. La
instrumentación permanece inactiva en la configuración ordinaria. No envía
chat, no modifica una skill y no expone tokens o contraseñas.

La sonda `MechanicsSandboxHotReload.DiagnosticStamp()` es un método real de
Game marcado `NoInlining`. Para aceptar la recarga en el entorno vivo:

1. Registrar respuesta, PID World y personaje conectado.
2. Cambiar sólo el literal `aa10-real-runtime-v1` de ese método por un valor
   de prueba. Esperar el aviso de aplicación de Hot Reload.
3. Exigir mismo PID, nuevo `diagnosticStamp`, incremento `updateCount`,
   `lastUpdateUtc` y personaje todavía conectado.
4. Revertir el literal y comprobar otro incremento, mismo PID y estado online.
5. Guardar las respuestas y logs en las capturas E del sandbox.

El contador lo actualiza un `MetadataUpdateHandler` del CLR. Una compilación
correcta por sí sola no acredita la prueba anterior. Las tres pruebas del
controller verifican desactivación, listener no local rechazado y JSON con
campos esperados sin secretos o envoltorio de chat; pasan en Debug y Release.

## Límites del runtime

### Aceptación de esta entrega

Comprobación real guardada en `runtime/sandbox-aa10/captures/`:
`live-acceptance-baseline.json`, `live-acceptance-changed.json` y
`live-acceptance-reverted.json`. La arena visible fue confirmada por el usuario;
no se usaron entradas, capturas ni control del escritorio en esta prueba.

| Etapa | World PID | Cliente PID | Zone PID | Actualizaciones CLR | Tentativa |
| --- | ---: | ---: | ---: | ---: | ---: |
| Antes | 240 | 21824 | 59768 | 1 | 1 |
| Código modificado y reset | 240 | 21824 | 59768 | 2 | 2 |
| Código original restaurado y reset | 240 | 21824 | 59768 | 3 | 3 |

Se modificaron dos cuerpos reales de Game: la sonda sin inline y el mensaje
que el manager ejecuta al completar el reset. El API devolvió la sonda y el
mensaje nuevos tras el reset; después devolvió ambos originales. Se verificó
la continuidad exacta de los sockets Game/Stream por PID y puertos locales,
la fecha de creación de cliente/Zone, cuatro dummies y heartbeat nativo.
Los dos archivos C# quedaron restaurados byte a byte según su SHA-256 previo.
La batería Release con la corrección de sesiones pasó 8.888/8.888 pruebas.

El contador ya estaba en 1 por la corrección anterior de resolución de sesiones.
Ese paso anterior no se acredita como prueba de conservación de una sesión.

### Qué ediciones requieren reiniciar

Los cambios compatibles del cuerpo de un método pueden aplicarse sin
reiniciar. Cambios estructurales, de paquetes, inicialización o DLL nativa
pueden requerir reinicio. En particular, `--non-interactive` **reinicia la
aplicación ante un rude edit**; no significa que descarte ese cambio. Ese
reinicio puede cortar Zone y cliente y requiere recuperar únicamente el
perfil aislado autorizado. No se promete recarga universal ni conservación
de estado ante cualquier edición. Véase el contrato oficial de
[dotnet watch](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-watch).
