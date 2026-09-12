# Ventana custom de reportes — 2026-09-11

Target `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`, HEAD
`fd53b458573572cc354c8564293f274801d9aa3e`. Padre exacto
`upstream/client_version/zone-10.0.2_r575` (`1017677b40be6508861a8fb74e9d09fa496873c9`).
Estado operativo y hashes: `BUG_REPORTS_20260911.manifest.json`.
Aceptación dentro del cliente pendiente del usuario.

## Alcance pedido

El usuario pidió documentar Alpha y crear una ventana independiente para reportes.
Corrigió la ubicación a abajo a la derecha, junto a los botones generales.
Guías permanentes: `Docs/AA10CustomWindows_es.md`, `Docs/AA10PrivateAlpha_es.md`
y `Docs/AA10BugReports_es.md`, enlazadas desde el README de la raíz canónica.
Sin cambios al ALB de Alpha, llave, compact ni accesos. El usuario conserva
el lifecycle de Zones y la operación del cliente; Codex no los automatiza.

## Implementación

Botón Reportar anclado sobre el grupo `GetRightIconMenuFrame()` en la esquina
inferior derecha. Formulario 700×690: siete categorías, búsqueda con debounce
500 ms para misión/objeto/habilidad/NPC, cuatro resultados por página, selección
de entidad y detalle de 10–600 caracteres. Mundo/Interfaz/Otro no requieren entidad.
Sólo personajes conectados pueden usar el servicio. No requiere autorización alpha.

Catálogo reproducible ES/EN: 9011 misiones, 51011 objetos, 38043 habilidades y
19522 NPC. Evidencia negativa: `game_decrypted.sqlite3` conserva nombres coreanos
para objetos como 98 y no sustituye al catálogo inglés original. Se corrigió el
builder para usar esa compact inglesa fijada por hash y se añadió regresión
`Jarrón decorativo` / `Decorative Vase` / 98. Los nombres sin traducción conservan
el disponible, nunca se inventan traducciones. Nombre máximo observado 871
caracteres, columna `entity_name` de 1024 para no rechazar reportes válidos.

Transporte independiente `aa10br1:`, 20 bytes ASCII por fragmento, máximo 260,
TTL 30 s; dos fragmentos por frame. Respuestas `AA10BR1:` por System -2,
consumer DAILY_MSG comprobado en V7/V8. No se modifican opcodes ni paquetes.
El canal de respuesta heredado puede mostrar texto técnico de protocolo en el
chat de sistema; su ocultación no se ha reconstruido en esta frontera.

MySQL `bug_reports` persiste detalle y contexto JSON autoritativo: personaje,
ubicación, build/MVID, objetivo y estado de misión activa cuando corresponde.
Índices por categoría/entidad/estado/fecha, fingerprint para agrupación y clave
única de reintento por personaje. La confirmación se emite después del INSERT.
Rate limit persistido: 10 s entre nuevos reportes, 30/hora por cuenta.
Reintentar devuelve el mismo ID; reutilizar la clave con otro contenido se
rechaza. No hay reenvío automático ni borrado del detalle ante error/timeout.
`Scripts/BugReports.py` consulta JSON y registra cambios de estado con historial
en `bug_report_updates`. Texto del jugador siempre tratado como datos no confiables.

## Clausura nativa y preservación

El Lua nativo `hud/main_menu_bar/right_button_set.lua` define
`GetRightIconMenuFrame()` y ancla su frame a BOTTOMRIGHT (-5,-10).
`mailbox/mail/write_mail_view.lua` demuestra `W_CTRL.CreateMultiLineEdit`;
`baselib/edit.lua` demuestra `OnTextChanged`, GetText y máximo de texto.
`questcontext/quest_list/quest_context_list.lua:199` demuestra elipsis en botón.
DLL r575 x64: SHA256 `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.

Capacidad descartada: ALB right_button_set 12856, sólo 5261 bytes libres al
quitar debug. No se elimina lógica nativa para hacer espacio. Carrier escogido:
`inventory/sort_inventory.alb` 44023 bytes, nativo sin debug 25216. El appender
conserva bytecode/constantes/cierres y añade una llamada a un cierre sin upvalues
antes del único RETURN final de raíz. Prueba de ejecución verifica que ambos
cierres funcionan y prueba de identidad reconstruye el nativo completo sin debug.
No recompila el Lua fuente nativo: existen discrepancias de fuente/ALB en varios
consumers inspeccionados. Hashes fijados en `Scripts/Aa10BugReports.contracts.json`.

Se revisó el padre: no hay servicio `bugreport` equivalente. AA8 se consultó sólo
como `structural_candidate` del transporte de canales; no se portó ABI/opcode.
No se requiere modificar Zone ni reabrir Item Smelting (fuera de alcance).

## Gates

Restore y Release build correctos; 2776 pruebas del servidor, 6 del formulario,
codec y catálogo; regresión Alpha 9 correctas. Control Center typecheck/build
correctos, 65 tests correctos y 1 omitido. Caché actual por ruta/tamaño/mtime,
SHA informativo; no se añade allowlist. Sentinelas de mapa/icono/Folio verificadas
por el aplicador. Respaldo DB anterior a migración y tag de imagen V9 conservados.
Prueba de almacenamiento real: UTF-8, JSON, restricción de duplicados, historial
y ROLLBACK; cero reportes técnicos retenidos (puede quedar un salto de AUTO_INCREMENT).

## Aceptación pendiente y rollback

Primera prueba del usuario: abrir Reportar, categoría Objeto, buscar 98,
seleccionar Jarrón decorativo, escribir «Prueba del formulario: el objeto se
selecciona y el detalle se guarda.» y enviar una vez. Parar al recibir #N;
Codex consultará ese ID y comparará entidad, texto y ubicación antes del siguiente
caso. Después: búsqueda por misión, rechazo de detalle corto, reintento tras timeout,
relog y regresión de la llave Alpha. No declarar aceptación por suite verde.

Rollback por entrada ALB con respaldo/hash exactos registrados en manifest;
imagen `aaemu10-bug-reports-v1-rollback:20260911` (V9). Conservar las tablas y
reportes al volver a la imagen anterior; no restaurar la DB completa sobre avances
posteriores. Ninguna acción de lifecycle Zone realizada por Codex.
