# Perfil local r575 — 2026-09-16

Target `rama_10`, branch `rama_10`, HEAD `b22b3ccfcfb001d198b8046658b525943e1f56bf`.
Padre consultado `upstream/client_version/zone-10.0.2_r575` en `b439e1cc0d4bb96647d11dcb76da61b0246a53e1`.
El padre no contiene los scripts locales de distribución. Sin integración de ramas.

Petición explícita: evitar OneDrive y crear la configuración de ArcheAge en
Documentos local. Implementado con un parche de 25 bytes en `xlcommon.dll`
RVA0x1BD21: SHGetFolderPathW PERSONAL conserva su identidad pero usa DEFAULT=1.
No cambios en game_pak, SQLite, x2game, traducciones ni servicios.

Fuente, hashes, procedimiento, reversión y pruebas en
`Docs/AA10LocalUserProfile_es.md`. Builder `Scripts/BuildAa10LocalProfilePatch.py`;
instalador `Scripts/ClientDistribution/Perfil-local.ps1`.

La DLL real ejecutó satisfactoriamente el contrato de ruta en prueba aislada
con redirección de Documentos simulada y ruta Unicode; control original usa
CURRENT, parche usa DEFAULT. El junction se redirige sin perder el contenido
anterior. Aplicación/repetición/reversión y rechazos verificados en Windows
PowerShell. La DLL desplegada ejecutada con Windows real devuelve
`C:\Users\juank\Documents\ArcheAge` y el nuevo `system.cfg` contiene `locale = en_us`.

Desplegado con backups al cliente español principal y a la distribución LAN
20260915. ZIP portátil entregable para davidwings, sin binarios; el manifiesto
faltante se recupera y debe verificarse el resto del cliente receptor.
Codex no inició el juego ni operó Zones/servicios. Después del despliegue se
observó un arranque externo a las 18:49:07 de Chile (PID30212, ejecutable principal)
con `ArcheAge.log` creado/actualizado bajo el nuevo Documentos local. Seis pruebas
aprobadas; la aceptación del destino tiene evidencia también del juego real.
Aceptación visual remota
y resultado de creación de personaje pendientes.

## Corrección del instalador r2

David reportó `GetFullPath` con ruta inválida al iniciar el CMD. Reproducido
localmente con Windows PowerShell 5.1 `-File` sin `-ClientRoot`: el valor por
defecto `$PSScriptRoot` se enlazaba vacío. La asignación se trasladó del bloque
param al cuerpo del script, sin alterar el parche nativo ni sus hashes.
Ocho pruebas pasan, incluyendo entrada `-File` sin ruta explícita y aplicación /
reversión mediante los CMD desde otro cwd. En la prueba de los CMD se omite
únicamente la escritura del perfil personal; Inspect sí resuelve Documentos real.
Paquete revisado `AA10-Perfil-local-20260916-r2.zip`; scripts actualizados en la
distribución local. La aceptación remota del instalador corregido queda pendiente.
El usuario aclaró que la creación estaba rota globalmente tras merges y la está
arreglando por separado; no se atribuye a OneDrive ni se modifica en esta tarea.

Distinción de personas: davidwings NO es wingsjuan, el PC diagnosticado el día
anterior. El log aportado de davidwings SHA256
`2C0515351807936ACA11AF17C7A711491B17F471E954D78085FC6864D443A14C`
muestra `creating character` a las 18:26:38/49 sin solicitud correlacionada en
servidor ni error Lua explícito. No demuestra causalidad de OneDrive.
