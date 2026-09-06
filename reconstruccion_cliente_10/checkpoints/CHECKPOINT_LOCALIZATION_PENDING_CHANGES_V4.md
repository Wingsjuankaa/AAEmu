# Lista de cambios pendientes — 2026-09-04

Target rama_10, HEAD bdad11fec1493c43a854369e707de72a20f26f86; padre upstream/client_version/zone-10.0.2_r575. Cambio limitado al editor local es_ES.

- Botón permanente **Cambios pendientes (N)** junto a Preparar parche; despliega un panel que permanece abierto mientras se edita.
- Cada diferencia muestra texto instalado, aprobado, original inglés, identidad, dominio, revisión y acceso directo **Revisar texto**.
- Contador y lista actualizados al entrar, abrir el panel, guardar/restaurar revisiones y terminar aplicar/revertir. Actualización manual disponible para cambios de otras pestañas. No hay sondeo periódico de la base ni traducción automática.
- `GET /api/pending` reutiliza `collect_preview` y `preview_changes`, los mismos selectores, validación de compact y diferencias semánticas que Preparar. No genera manifiestos, copias SQLite ni escrituras en el cliente. Se excluyen valores ya instalados; las sustituciones parciales de nombres aprobadas por política llevan una etiqueta distinta.
- La lectura comparte exclusión con las operaciones de paquete y el mantenimiento; no presenta un resultado obtenido mientras el aplicador escribe. Los errores de lectura invalidan la lista visual anterior.

## Validación y despliegue

35 pruebas Python correctas; tres nuevas verifican paridad con la vista previa, ausencia de preparación al consultar, desaparición tras aplicar, alcance de nombres y rechazo de compact desconocido. JavaScript pasa `node --check`.

Editor reiniciado usando la barrera autenticada de mantenimiento, con el último trabajo terminado. Navegador verificado sobre dos cambios reales guardados por el usuario: `ui_texts/text/1033` revisión 2 y `ui_texts/text/983` revisión 3; ambos de «Melee Precisión» a «Precisión cuerpo a cuerpo». El botón mostró 2 pendientes, comparaciones correctas y abrió 1033 desde Revisar texto conservando el panel. No se guardaron ni aplicaron textos durante esta comprobación.

Estado instalado al desplegar: parche del usuario `8ad9fda9063942a18f05df34e93b4677`; compact `DC66320C475D9D5B68C0BDA7DA2B98B133F8A38BC2755F9465926252653C0698`; game_pak `792BEC7291EE814046F7A3D4F3A63B361ADBF37BAB9A193AC892B24B085A960F`. Estos hashes son el estado manifestado del usuario y no se recalcularon leyendo 69 GB para un cambio exclusivo de interfaz. No se operaron servidores ni Zones.
