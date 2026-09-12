# Alpha privada: búsqueda automática y bilingüe — 2026-09-11

Continuación V9: `CHECKPOINT_PRIVATE_ALPHA_POINTS_20260911.md` añade Honor y
Vocación; conserva esta aceptación histórica de la búsqueda V8.

Target `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`, padre exacto
`upstream/client_version/zone-10.0.2_r575`. Se conservan cambios ajenos y el
contratos de V7. V8 modifica el consumidor Lua y corrige la normalización española
en el servidor bajo globalization invariant.

## Comportamiento

V7 requería Buscar o Enter. V8 escucha `OnTextChanged`, espera 500 ms desde el
último cambio y solicita la primera página. Agrupa pulsaciones, mantiene la caja
editable con una solicitud pendiente y descarta una página si pertenece a un
texto anterior. Al editar se limpian las filas y se deshabilita Obtener, evitando
seleccionar resultados obsoletos. Vaciar el campo consulta el catálogo completo.
Buscar y Enter adelantan la consulta respetando un mínimo de 400 ms entre envíos
automáticos; el servidor conserva su límite existente de 350 ms.

No hay reintento automático del mismo envío tras timeout. Ocultar la ventana
impide enviar la consulta diferida; abandonar el mundo borra esa consulta. La
búsqueda no entrega recursos ni objetos. La autorización de V7 permanece intacta.

La búsqueda bilingüe ya existía en el servidor: AlphaCatalog concatena el
catálogo español con `ItemManager.searchString`, creado con nombre original y
todas las traducciones cargadas por LocalizationManager. La búsqueda omite mayúsculas; la prueba nativa V8 detectó que el runtime
Docker no eliminaba las tildes aunque la prueba Windows anterior pasaba. Antes de aplicar V8 se confirmó en retail `Decorative Vase`
→ `Jarrón decorativo`, ID 98, request `6dcbc`. Hay 50.431 filas de nombres ingleses
en la compact original. No se inventan traducciones faltantes: se usa ID u otro
nombre disponible para esos objetos. La presentación conserva el idioma del cliente.

## Contratos y validación

Evento demostrado en Lua AA10 `scripts/x2ui/baselib/edit.lua:50–55`; visibilidad
mediante `IsVisible` en los consumidores AA10 existentes. Reloj GetUiMsec y
remitente System -2/DAILY_MSG conservados desde V7. Evidencia con hash del fuente
en `private-alpha-panel/v8-live-search-contract.json`.

Se factorizaron colocación de widgets y controles de oro/labor, y se acortaron
textos auxiliares para respetar la entrada original de 30.761 bytes. El ALB V8
compilado ocupa exactamente ese tamaño, sin alterar el Lua nativo de inventario
salvo el hook previamente aceptado. Hash:
`12A5F154B6664D73CFCFE305717CC27413898087842F73C6BB7B74F0830FAB60`.
Compact y catálogo no cambian.

Ocho pruebas Lua/parche correctas: ráfaga de escritura, texto modificado durante
una respuesta pendiente, descarte de página vieja, campo vacío, ventana oculta,
salida del mundo y timeout sin repetición, además de permisos, entregas y layout
SQLite de V7. Control Center: typecheck/build correctos, 65 pruebas correctas y
una omitida. `git diff --check` correcto, sólo avisos de finales de línea previos.

Estado de aplicación y aceptación nativa: consultar el manifest de búsqueda.

## Corrección de diacríticos en el runtime Docker

Evidencia nativa inicial: `JARRON` devolvió cero (`a409c`), mientras `Jarrón`
devolvió 49 (`a409d`). El contenedor usa `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1`:
FormD no descompone las letras precompuestas. AlphaRules conserva su filtrado de
marcas combinantes y añade el plegado explícito de vocales españolas, ü y ñ,
con ambas cajas. No se cambió la configuración global ni las traducciones.

Restore/build Release correctos, 2.772 unitarias correctas y las cinco pruebas
PrivateAlpha repetidas en un proceso con globalization invariant: correctas,
incluyendo Jarrón/JARRÓN/JARRON/forma combinante y el alfabeto acentuado español.
Imagen construida `sha256:1e5b8bc880f2694b1cde8fb5891fa2e86903fcf74c0bddd274d9c683348dd953`.
Rollback `aaemu10-private-alpha-v8-rollback:20260911`, imagen previa
`sha256:fb81a5e3f16b9866d1bf93c16c4553a1700ece59d4bae885a9fc5a3e55ec93e1`.
Respaldo DB previo: `E:\AAEmu\rama_10\backups\private-alpha-v8-20260911\aaemu_game.sql`.

## Aceptación nativa del consumidor V8 antes del reinicio de Game

Sin pulsar Buscar ni Enter: `Dec` 507 (`a409a`); `Decorative Vase` ID 98 (`a409b`);
`Jarrón` 49 (`a409d`); página siguiente (`a409e`); editar a `98` devuelve un
resultado y página 1 (`a409f`); borrar muestra 51.010 (`a40a0`); texto inexistente
muestra cero y entregas deshabilitadas (`a40a1`). Se guardaron capturas english,
spanish, id, empty y zero en el directorio forense. Oro, objetos y autorización
SQL idénticos antes/después de estas consultas. La corrección de tildes requiere
aceptación posterior al despliegue, registrada abajo al completarla.

## Cierre desplegado y aceptación final

Cliente V8 aplicado y reextraído mediante
`aa10-private-alpha-20260911-211515-993349Z/manifest.json`; game_pak
`1E6406C8E2D8DEB34552F526009EBE844344870597B43786EBDCB5618C2F8032`,
92.412.597.248 bytes. Idempotencia `aa10-private-alpha-20260911-211838-084265Z`:
`already_patched`, sin modificación. Compact y sentinelas permanecen iguales.

Tras desplegar Game, la Zone anterior finalizó de forma natural con System:Quit
(21:29:30 UTC). Con la autorización de prueba vigente se inició exclusivamente
`launch_zone_aa10_worker.cmd gatekeeper_hall 379`, ventana oculta, PID 57404.
DLL r575 verificada, excepción de spawner opcional de Control Center 0.1.8;
no se creó un spawner artificial. ZoneLoaded 21:32:21.8519332 UTC, sesión
2235109941, heartbeats estables y Dannia dentro de la misma sala.

Aceptación final con cliente PID 37700: apertura autorizada `33fc`; `JARRON`
49 resultados (`33fd`); `Decorative Vase` ID 98 (`33fe`); `Jarrón` los mismos
49 (`33ff`), todo por escritura sin pulsar Buscar/Enter. El cliente queda abierto
con esta última búsqueda. Las consultas y el relog conservan exactamente oro,
objetos y acceso SQL de la captura previa: saldo 11.748.369.695, llave única
16777515 y ambos jarrones previos. La labor local regenerada no se atribuye al panel.

Game running/healthy; hashes de AAEmu.Game.dll idénticos en /app y /app/game.
Logs finales sin errores del panel/SQLite. Capturas `v8-retail-diacritics-fixed.png`,
`v8-retail-english-final.png`, `v8-retail-final.png`; estado y hashes de evidencias
en `PRIVATE_ALPHA_SEARCH_20260911.manifest.json` y `v8-retail-acceptance.json`.
No hay cambios adicionales de permisos, correo, grants ni mecánicas de ítems.
