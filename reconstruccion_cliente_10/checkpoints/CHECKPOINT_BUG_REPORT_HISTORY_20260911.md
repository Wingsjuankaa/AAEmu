# Reportes V4: pestaña Mis reportes

Target `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`, padre
`upstream/client_version/zone-10.0.2_r575`. Estado y hashes completos en
`BUG_REPORT_HISTORY_20260911.manifest.json`.

## Aceptación anterior y reporte de prueba

El usuario confirmó «perfecto ya funciona» para el icono empaquetado V3 y mostró
el formulario abierto. Captura `codex-clipboard-d0dfdf53-6c80-4012-826e-9f785c32edcd.png`.
SQL contiene el reporte #3, personaje Dannia/1007, categoría quest, entidad
10029 «¿Dónde está Gladie?», detalle «TEST DE ERROR», estado new, fecha UTC
2026-09-11 23:39:51.394405. Contexto: zona 382, nivel 55, misión Ready. La
consulta es de lectura; no se cambió estado, contenido ni misión.

## Comportamiento V4

Dos pestañas nativas `W_TAB.CreateTab`: Nuevo reporte y Mis reportes. Cuatro
reportes por página, ordenados por fecha e ID descendentes; incluye todos los
estados. Filas con número, categoría, entidad, fecha UTC y estado en español.
Al pulsar se lee el detalle completo (hasta 600 caracteres) en multiline edit
de sólo lectura. Anterior/Siguiente y Actualizar consultan el servidor.
El borrador y su nonce se conservan al cambiar de pestaña. Al cargar otro
personaje se borra la copia local del historial. No se bloquean automáticamente
envíos nuevos similares; se conserva la idempotencia por nonce del envío V1.

Autoridad UI: corpus r575 `components/tab.lua`, `community/expedition/history.lua`
(AddTabs, OnTabChangedProc, EnableTab), `baselib/edit.lua` y
`community/family/family_info_view.lua` (multiline/SetReadOnly/SetMaxTextLength).
El ALB conserva el bytecode nativo del inventario mediante Aa10LuaExtension;
44023 bytes totales. No cambia DDS, compact ni ALB de la ventana alpha.

## Backend y protocolo

`BugReportHistory` usa consultas parametrizadas que incluyen cuenta Y personaje
de la sesión. `mine/<page>` pagina; `read/<id>` requiere el mismo propietario.
No acepta IDs de cuenta/personaje suministrados por el cliente. No retorna
context_json ni developer_notes. Sin migración de esquema, sin escrituras.

Se reutiliza el canal probado AA10BR1. Listado: history, hasta cuatro entry,
listed. Detalle: report, chunk de hasta 120 bytes UTF-8 codificados en hex,
read con contador. El cliente mantiene la correlación hasta el final, rechaza
secuencias incompletas y concatena bytes antes de mostrar Unicode. Espacia
nuevas solicitudes al menos 400 ms después de una respuesta, para respetar el
límite de 350 ms del servidor aun con clics rápidos.

## Pruebas y entrega

- 2777 pruebas de servidor, 0 fallos; restore/build Release correctos.
- 9 pruebas Lua/ALB: pestañas, borrador, páginas vacías, detalle, timeout,
  fragmentos faltantes, clic rápido, loading, nonce y preservación nativa.
- Probe de integración real `Tools/BugReportHistoryProbe`: Find/List recuperan
  #3 para Dannia, niegan otra cuenta y otro personaje, y acotan página extrema.
  Credenciales sólo por stdin. Probe de lectura, sin insertar fixtures en SQL.
- Control Center: typecheck, 65 tests (1 omitido), electron-vite build.
- Aplicador cliente con dry-run, backup de ALB, reextracción y sentinelas
  (mapa/icono/Folio/DDS custom/alpha), tamaño PAK conservado e idempotencia.

Runtime anterior de rollback: `aaemu-world:rollback-bug-report-history-20260911`,
imagen `sha256:2d759bf6a27595b121087b9271e2394248c17bb57ca8a37c4fe0f5d5acd56dc6`.
Imagen nueva `sha256:c5d9e2d7e66849f87bce95b68d1d4af263346b6d60ad16ae918f45e5a54c261d`.
Game DLL de ambas ubicaciones del contenedor:
`E467AC30D16CB7AC1682D07A83C6EE3D478F957BE5FA1284A7C899B5BE426634`.
Se reinició sólo Game; el usuario conserva el control de Zones y del cliente.
Los avisos históricos de Item Smelting están fuera de alcance.

Rollback de interfaz: reinserción del ALB V2 respaldado por la primera
instalación V4, usando el hash V4 vigente como hash previo. No retirar el icono
V3 aceptado. No restaurar DB: V4 no altera el esquema ni los reportes.
La migración V3 quedó separada en `Aa10BugReportPackedIcon.contracts.json` para
que los nuevos contratos V4 no modifiquen el historial del empaquetado.

Gate nativo V4 pendiente: entrar con Dannia, abrir icono → Mis reportes → #3.
Debe mostrar «TEST DE ERROR», estado Nuevo y la misión 10029. Regresar a Nuevo
reporte debe conservar cualquier borrador sin enviarlo. No hace falta crear
otro reporte para esta prueba.
