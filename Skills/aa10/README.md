# Skills AA10 mantenidas con el proyecto

Fuentes versionadas de aaemu10-native-reconstruction, aa10-client-forensics y
aa10-es-es-localization. Las tres conocen el sandbox411 y sus límites; la skill
de reconstrucción mantiene la operación y el flujo de Hot Reload. Forensics
continúa read-only y localización conserva su pipeline de datos/paquetes.

Desde el repositorio canónico E:\AAEmu\rama_10\server\AAEmu:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Scripts/Install-AA10Skills.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Scripts/Install-AA10Skills.ps1 -Apply
```

La primera llamada inspecciona. La segunda enlaza las tres rutas existentes de
Codex a estas fuentes en E y conserva los directorios anteriores bajo
runtime/sandbox-aa10/backups/skills en E. No reemplaza enlaces ajenos. Repetir
con el enlace correcto no modifica nada. Editar estas fuentes actualiza también
la copia instalada; no mantener otra versión divergente en C.

El runtime, paquetes, DLLs, credenciales, snapshots y capturas quedan fuera de
Git. La copia instalada de REA conserva su instalación separada en E y no forma
parte de este paquete AA10.
