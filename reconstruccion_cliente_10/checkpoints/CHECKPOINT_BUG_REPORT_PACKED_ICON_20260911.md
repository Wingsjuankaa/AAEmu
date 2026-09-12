> ACEPTADO EN RETAIL: el usuario confirmó que funciona y mostró el icono y el formulario abierto. Evidencia: codex-clipboard-d0dfdf53-6c80-4012-826e-9f785c32edcd.png.

# Icono de reportes V3: textura empaquetada r575

Target `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`, padre
`upstream/client_version/zone-10.0.2_r575`. Cliente principal español completo.
Estado operativo y rutas de respaldo: `BUG_REPORT_PACKED_ICON_20260911.manifest.json`.

## Evidencia del fallo y corrección

V2 falló en la captura del usuario `codex-clipboard-324282f1-25cf-4447-b352-00eba5a29891.png`:
el botón aparece como cuadro negro. La textura no existía en el índice del PAK;
se había instalado loose. El PNG y el DDS tenían canal alfa, pero el DDS DXT5
generado por Pillow declaraba 268 bytes de linearSize para un nivel de 4096 bytes.
No se ha aislado cuál de estos dos defectos explica el síntoma nativo completo.

V3 conserva el arte y el ALB V2. `BuildAa10BugReportIcon.py` produce BGRA8 de
64×64 y siete niveles mip (21972 bytes), con cabecera/pixel masks/caps como
`game/ui/common/default.dds` efectivo r575. Dibujo a 42×42, cuatro estados,
tooltip «Reportar un error» y apertura del mismo formulario.

La textura se incorpora como `game/ui/custom/aaemu/bug_report.dds` en `game_pak`.
La copia loose V2 se respalda y retira tras verificar la instalación, para que
no pueda ocultar el recurso corregido. No cambia Lua, compact, servidor ni DB.

## Frontera separada de crecimiento de índice

`Aa10PakAppend.py` acepta WIBO y rutas exclusivas `game/ui/custom/aaemu/`.
Autoridad del formato: `AAEmu.Commons/Utils/AAPak/AAPak.cs`, derivado del packer
de ZeromusXYZ. Se revisó también https://github.com/AlchemistMist/AAmistAssetTool
sugerido por el usuario: comparte procedencia de lector/packer y sirve para
conversión de modelos; su README describe la edición PAK como «Half baked».
No se instaló ni se usó ese editor para escribir el cliente.

El builder lee/valida los 523291 registros activos y conserva cada registro
cifrado existente literalmente, incluidos los 53 registros extra. Inserta el
payload en el antiguo inicio de FAT, desplaza el FAT y añade un único registro
antes de los extras. Sólo actualiza el contador en el footer cifrado; conserva
los offsets y payloads originales. Crecimiento: 22528 bytes. No reempaqueta los
92 GB ni reutiliza bloques borrados. El respaldo es el sufijo completo anterior
(175844352 bytes), no una copia completa del cliente.

`ApplyAa10BugReports.py` delega en `ApplyAa10BugReportPackedIcon.py`. Requiere
V2 exacto, cliente cerrado, archivo sin hardlinks, DLL r575 y SHA completo
fijado. Dry-run calcula también el SHA final antes de escribir. Aplica el sufijo,
reextrae DDS y cinco sentinelas, verifica SHA completo y tamaño, retira loose y
permite reejecución sin escritura. Ante fallo de escritura restaura el sufijo;
ante fallo posterior revierte y verifica el hash anterior. Un proceso terminado
abruptamente exige inspección y restauración del respaldo durable.

Identidades:
- PAK antes: `CBDA7C4A6EC9A72305957AE7485FC23C8FFD6A760BC315BBEE84D1A68952F25B`, 92412597248 bytes.
- PAK V3: `A76BD641A549A879E4665E0D564A7A3C075370E03574065AEDC9D9EE56EA2252`, 92412619776 bytes.
- DDS V3: `63C82B467A9386E48D65437E6A5A8B0D614BC0B96859E1B4C26E15C89A8BE81E`.
- ALB sin cambios: `6F593EEE83C8F68013BC3F011DBA385360036D6D783012B4A8673A67EF12ECE1`.

## Validación y aceptación

Cuatro pruebas de la frontera: reapertura AAPak independiente, preservación de
payload/registros/extras, colisiones/layout inválido, idempotencia, drift y
rollback exacto; cabecera, mip chain y alfa DDS. Siete pruebas del formulario.
Además, ensayo con índice real completo en archivo sparse: AAPak reextrae el
icono nuevo y cinco payloads de control copiados (mapa, icono, Folio, alpha y
reportes). El archivo sparse es sólo una proyección de ensayo, no otro cliente.

Control Center: caché por ruta/tamaño/mtime; hash informativo, sin allowlist.
Se validan typecheck, 65 pruebas (1 omitida) y electron-vite build.

Gate retail pendiente: abrir cliente, comprobar que el pergamino aparece con
transparencia, pasar cursor para tooltip y pulsar para abrir el formulario.
Comprobar que los botones nativos vecinos conservan su aspecto. La extracción
y las pruebas no sustituyen esta aceptación del motor gráfico.

Rollback: Python con cryptography, `Scripts/RollbackAa10BugReportPackedIcon.py
<manifest-de-instalación> --apply`. Rechaza cualquier modificación posterior
del paquete; restaura exactamente V2 (incluido su fallo visual). No operar Zones
ni reiniciar Game por esta actualización.
