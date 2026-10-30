# Fuente y publicación de ZoneHost para Control Center

## Fuentes durables

- Fuente canónica: `E:\AAEmu\rama_10\server\AAEmu\Tools\AAEmu.ZoneHost`.
- Snapshot comunitario: `upstream/`, con licencia y `upstream-manifest.json`.
  Procede de `NickMesser/AAEmuZoneHost`; es tooling separado del padre AAEmu del servidor.
- Build/toolchain: `build-settings.json` y `scripts/`; leer los valores vigentes,
  no congelar en la skill hashes del EXE ni versiones futuras del compilador.
- Guía: `Tools\AAEmu.ZoneHost\README.md` dentro del repositorio.
- Informe: `Docs\AA10ZoneHostSourceIntegration_es.md`.
- Panel: `E:\AAEmu\rama_10\tools\AAEmu.ControlCenter`, guía
  `docs\ZONEHOST_BUILD_UPDATES.md`.

El fuente permite construir el bootstrap Rust y conserva ZoneManager WPF como
referencia. La simulación sigue dentro de las DLLs retail: no interpretar este
repositorio como código completo del motor. Preservar la procedencia del snapshot
y documentar los parches locales; no alterar hashes para disfrazar un cambio como upstream.

## Compilación y publicación autorizada

Preferencia persistente del usuario (2026-09-03): cada build Release de ZoneHost
debe quedar preparado para nuestro Control Center mediante el pipeline existente.
Cuando la tarea incluya compilar una nueva versión, no volver a pedir permiso
para esta publicación automática. Esto no autoriza compilaciones ajenas al alcance
de la tarea ni operaciones del lifecycle de Zones.

Comando normal:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  E:\AAEmu\rama_10\server\AAEmu\Tools\AAEmu.ZoneHost\scripts\Build-ZoneHost.ps1
```

- Usar el wrapper, no dejar sólo un `cargo build` suelto: verifica snapshot,
  compila, registra manifiesto, prueba el parser, audita compatibilidad nativa y publica.
- `Initialize-Toolchain.ps1` prepara Rust aislado si falta, sin alterar PATH global.
- Salida: `E:\AAEmu\rama_10\artifacts\builds\zonehost\release`.
- Destino del panel: `E:\AAEmu\rama_10\zones\retail-zone-server-r575\Bin64\AAEmu.ZoneHost.exe`.
- `-NoPublish` sirve para comparaciones, experimentos o una petición de sólo build;
  Debug nunca se publica automáticamente. No usarlo por defecto para una entrega
  Release que el usuario espera disponible en el panel.
- Para otro perfil explícito, `-RuntimeBinDirectory` selecciona su Bin64 compatible.

El EXE debe permanecer junto a las DLLs: `XlSetWorkingDir(true)` deriva la raíz del
juego desde su ubicación. No apuntar el perfil del panel al directorio de builds.

## Ejecutable ocupado y siguientes arranques

`Publish-ZoneHost.ps1` guarda el candidato por SHA-256 en `Bin64/.zonehost-updates`.
Si el EXE está libre, lo sustituye atómicamente, conserva el previo en `backups/`
y escribe `installed.json`. Si hay procesos usándolo o su ruta no es verificable,
deja `pending.json` sin detenerlos. DLLs cambiadas o candidato corrupto bloquean
la aplicación; resolver la causa y repetir el pipeline, no saltar verificaciones.

Control Center incorpora el consumo de pendientes desde **0.1.6**:
`ZoneHostUpdateService` invoca el publicador con `-ApplyPending` antes de iniciar
una Zone. La nueva versión se aplica cuando todas las que comparten ese EXE lo
hayan liberado. Mientras continúen activas, nuevos inicios usan la versión anterior
y el panel lo informa. No afirmar que un pendiente ya está instalado.

Si el panel abierto es anterior, usar el portable actualizado una vez; no hace
falta reempaquetarlo para cada build de ZoneHost mientras se conserve el contrato.
La publicación no reinicia Zones, cliente, Game ni Docker. La autorización para
iniciar una Zone de prueba sigue siendo independiente y limitada al perfil exacto.

Validar cambios al publicador con `Test-Publication.ps1`; al panel con su build,
tests y smoke SQLite. Consultar manifiestos y hashes reales al informar instalado
frente a pendiente. Publicación, checks estáticos y aceptación de gameplay son gates distintos.

## Docker

El código actual usa Win32 y DLLs PE x64; no es ejecutable nativo Linux. La receta
`docker/Dockerfile.windows.experimental` requiere motor Windows compatible y su
comando predeterminado sólo prueba el parser. La carga real de Zone en contenedor
y Wine siguen sin aceptación documentada en la incorporación inicial; consultar
el informe vigente antes de repetir la investigación o promover una solución.
Comprobar `docker info` y no cambiar de backend el stack Linux activo por inferencia.
Docker no demuestra por sí mismo reducción de memoria de la simulación.
