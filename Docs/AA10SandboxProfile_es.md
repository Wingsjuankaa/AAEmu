# Perfil nativo exclusivo del sandbox en E

El cliente del sandbox usa una copia física independiente. El parche
`Scripts/PatchAa10SandboxProfile.py` redirige únicamente su export
`?XlGetSafeSaveGameDir@@YA_NPEAGH@Z` a la ruta E indicada por el launcher.
No modifica el cliente español principal, el original, las traducciones,
`game_pak`, fórmulas o protocolo del juego. Es una adaptación diagnóstica del
perfil; no es una reconstrucción del comportamiento de una skill.

## Autoridad y límite binario

Entrada admitida: `xlcommon.dll` de 2.434.048 bytes, SHA-256
`513cbce7c62c734b504adeb0bf7bb7e52feac74166ec67b131a322be4bd8e565`.
El export PE r575 apunta a RVA `0x1BCB0`; su entrada `.pdata` cubre
`[0x1BCB0,0x1BEA0)`, 496 bytes, offset de archivo `0x1B0B0`.
La firma y el contrato de buffer se reutilizan del análisis/prueba nativa
de `Scripts/tests/test_local_profile.py` y `Docs/AA10LocalUserProfile_es.md`.

La implementación conserva el prólogo original de 18 bytes, su frame de
stack y metadatos unwind, y reemplaza sólo el resto de esa misma función.
No utiliza una cueva de código ni añade secciones o relocaciones. El builder
comprueba export, máquina x64, sección ejecutable, frontera `.pdata`,
prólogo y ausencia de relocaciones dentro del reemplazo. El archivo final
tiene el mismo tamaño y sus bytes fuera de esos 496 permanecen idénticos.

El nuevo cuerpo copia el path UTF-16 con NUL sólo si el buffer no es nulo
y su capacidad firmada incluye toda la cadena. Rechaza capacidades negativas
o insuficientes sin escribir. No llama a `SHGetFolderPathW` ni crea carpetas:
el launcher debe crear el perfil y su `system.cfg` antes de abrir el cliente.
Sólo se admiten rutas absolutas E de hasta 199 unidades UTF-16 sin NUL.

## Aplicación reproducible

```powershell
python -B Scripts/PatchAa10SandboxProfile.py `
  --client-root E:\AAEmu\rama_10\runtime\sandbox-aa10\client `
  --profile-path E:\AAEmu\rama_10\runtime\sandbox-aa10\profile `
  --mode apply
```

`inspect` es el modo predeterminado y no escribe. `apply` exige la DLL de
origen exacta o el resultado exacto que el mismo builder produciría para esa
ruta. El respaldo y manifiesto se conservan dentro de la copia, bajo
`.aa10-sandbox-profile-backup`; el marcador del launcher es
`.aa10-sandbox-profile.json`. Incluye `profilePath`, `originalSha256`,
`currentSha256` y `patchId`. Repetir no reescribe artefactos idénticos.
`rollback` restaura la DLL aprobada y elimina el marcador activo; conserva
el respaldo y el perfil para recuperación. Un manifiesto, marcador o backup
desconocido bloquea la operación antes de tocar la DLL.

El builder rechaza copias bajo los clientes principal/original, paths C,
componentes reparse/junction y DLLs con varios hardlinks. Las escrituras son
atómicas y un error al escribir manifiesto o marcador restaura el estado
previo. No se altera el perfil Windows ni se redirigen carpetas del sistema.

## Validación

```powershell
$env:TEMP = 'E:\AAEmu\rama_10\runtime\sandbox-aa10\temp'
$env:TMP = $env:TEMP
python -B Scripts/tests/test_sandbox_profile.py -v
```

Once pruebas pasan sobre la DLL r575 real, incluidas ejecución nativa en un
proceso hijo aislado, acentos/ñ/emoji, buffer exacto, cola preservada, rechazos
sin escritura, cero consultas de carpetas Windows, determinismo, rollback,
idempotencia, hashes desconocidos, rechazo del principal y hardlinks, y
recuperación ante errores de manifiesto/marcador y conservación de cambios
concurrentes detectados antes de publicar. Los temporales de las
pruebas residen en `E:/AAEmu/rama_10/artifacts/tests/sandbox-profile`.
Esto verifica el export de perfil; el arranque completo del cliente requiere
además la aceptación del launcher y la observación de sus archivos efectivos.
