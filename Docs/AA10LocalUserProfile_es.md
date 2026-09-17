# Perfil local de ArcheAge r575

El parche `local-documents-v1` permite guardar configuración, logs y datos del
usuario en Documentos **predeterminado local**, normalmente
`C:\Users\<usuario>\Documents\ArcheAge`, aunque Documentos actual esté redirigido
a OneDrive. No cambia el registro, la carpeta conocida de Windows ni OneDrive.

## Instalar en otro PC

Paquete: `E:/AAEmu/rama_10/artifacts/client-distribution/local-profile-20260916/AA10-Perfil-local-20260916-r2.zip`.

La revisión r2 corrige el error `GetFullPath: La ruta de acceso no tiene un formato
válido` reportado por davidwings. Se reprodujo con Windows PowerShell 5.1 usando
`-File` sin `-ClientRoot`, tal como hace el CMD: `$PSScriptRoot` en el valor
predeterminado del parámetro quedaba vacío. Se resuelve ahora en el cuerpo del
script. Las pruebas anteriores pasaban `-ClientRoot` explícito y no cubrían esa
entrada. Ocho pruebas verifican ahora también `-File` y ambos CMD desde otro
directorio de trabajo. Reemplazar todos los archivos del paquete anterior y
ejecutar de nuevo; este fallo ocurría antes de modificar la DLL.

1. Cerrar ArcheAge.
2. Extraer todos los archivos del ZIP en la raíz del cliente, junto a `Jugar en LAN.cmd`.
3. Ejecutar `Activar perfil local.cmd`; exigir el mensaje `OK` y comprobar la ruta mostrada.
4. Abrir el launcher habitual. El juego genera los demás archivos del perfil al usarlos.

El instalador crea `system.cfg` con `locale = en_us` si no existe configuración
local. Un perfil local existente se conserva íntegro. No se migran ni leen los
archivos de OneDrive; la configuración gráfica, controles y personalizaciones
anteriores permanecen allí. El perfil nuevo parte de los ajustes predeterminados.

También recupera el manifiesto ausente de la distribución LAN del 15 de septiembre,
o actualiza su única entrada `Bin64/xlcommon.dll`, sin certificar el resto de archivos
del PC receptor. Ejecutar después `Verificar cliente.cmd`. Se rechazan otros
manifiestos o ejecutables; no se reemplazan versiones desconocidas silenciosamente.

La carpeta local y sus antecesores deben ser físicos, fuera de las raíces OneDrive
registradas y no ser enlaces/reparse points. El instalador verifica escritura y
rechaza rutas incompatibles con el límite nativo de 260 caracteres.

## Contrato nativo

`archeage.exe` r575 importa `XlGetSafeSaveGameDir`, `XlCreateJunction` y
`XlSetSaveGameDir` de `xlcommon.dll`. Su arranque obtiene la ruta UTF-16, prepara
el alias del cliente y registra la ruta usada por los consumidores de configuración.

En `xlcommon.dll` x64, `XlGetSafeSaveGameDir` comienza en RVA `0x1BCB0`.
El bloque RVA `0x1BD21`, offset de archivo `0x1B121`, prepara la llamada
`SHGetFolderPathW(NULL, CSIDL_PERSONAL, NULL, flags, output)`. El original usa
`flags=0` (`SHGFP_TYPE_CURRENT`); el parche usa `flags=1` (`SHGFP_TYPE_DEFAULT`).
El resto de la función conserva concatenación de producto `ArcheAge`, normalización
UTF-16 y creación de directorio. No cambia el tamaño del archivo, imports ni secciones.

- SHA-256 original: `D81BA53E5DF0DC6B5031D3D423A6A2720288D6CA40BE0768AAE85E2F30EA4113`.
- SHA-256 parcheado: `513CBCE7C62C734B504ADEB0BF7BB7E52FEAC74166EC67B131A322BE4BD8E565`.
- 25 bytes originales: `4533c9488d8424d00400004533c0418d510533c94889442420`.
- 25 bytes nuevos: `6a014159488d8424d00400004533c06a055a33c94889442420`.

Los pares push/pop balanceados cargan `r9=1` y `rdx=5`; el puntero de salida,
shadow space y alineación al invocar la API permanecen iguales. La diferencia
semántica es únicamente el cuarto argumento. La función conserva la consulta
del producto y el tratamiento de fallos de Windows.

[Microsoft documenta CURRENT y DEFAULT para carpetas redirigidas](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shgetfolderpathw).
El instalador usa DEFAULT con DONT_VERIFY para resolver y crear Documentos antes
del primer arranque. La consulta independiente de `SHGetFolderPathA` en x2game-dev
(VA `0x399104B1`) solicita LocalAppData (`0x1C`), no Documentos; CrySystem no importa
esa API. No se parchean otras consultas de Windows.

## Reproducir y verificar

Desde `E:/AAEmu/rama_10/server/AAEmu`:

```powershell
python Scripts/BuildAa10LocalProfilePatch.py
python Scripts/tests/test_local_profile.py -v
```

Builder determinista: scripts versionados y manifiesto original fijado por hash;
el ZIP no contiene binarios del juego. El instalador aplica los bytes localmente
después de verificar los hashes completos de EXE/DLL, guarda respaldo y reemplaza
atómicamente. El manifiesto baseline está en `Scripts/data/aa10-nuia-lan-20260915.manifest.json`.

Pruebas nativas aisladas con la DLL real: consulta CURRENT de control frente a
DEFAULT parcheada, ruta Unicode, creación de carpeta, sustitución de un junction
existente y conservación del contenido anterior. Solo se simula la respuesta de
Windows a la consulta de carpeta, interceptando su IAT dentro del proceso de prueba.
Pruebas del instalador en Windows PowerShell: inspección sin mutación, aplicación,
repetición, recuperación de manifiesto ausente, reversión, rechazo de DLL/manifiesto
desconocidos y restauración de DLL si falla la escritura del manifiesto.

La llamada a la DLL desplegada con Windows real confirmó
`C:\Users\juank\Documents\ArcheAge` y la existencia del nuevo `system.cfg`.
Se aplicó al cliente principal y a la copia LAN, conservando backups. Las seis pruebas
no arrancaron el juego, ni modificaron Game/Login/DB/Zone. Después se observó
un arranque externo del cliente principal a las 18:49:07 de Chile, PID30212:
su `ArcheAge.log` nuevo se escribió en la carpeta local hasta las 18:51:10.
Esto confirma también el destino en una ejecución real del juego, sin que Codex
iniciara o detuviera ese proceso. Aceptación visual en
davidwings pendiente. El usuario confirmó que el bloqueo de creación de personaje
era general tras sus merges y está corrigiéndolo por separado.

## Revertir

Cerrar ArcheAge y ejecutar `Restaurar perfil original.cmd`. Se verifica el hash,
se restauran los bytes y el manifiesto de la distribución original. Se conservan
el perfil local y el de OneDrive; el siguiente arranque vuelve a consultar la
ubicación actual de Documentos. Backups en `.aa10-local-profile-backup`.

Para el cliente principal, que no es una copia LAN con manifiesto:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Scripts/ClientDistribution/Perfil-local.ps1 -Mode Rollback -NoDistributionManifest -ClientRoot 'E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview'
```
