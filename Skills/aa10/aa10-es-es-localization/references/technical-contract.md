# Contrato técnico r575 es_ES

## Locale

El registro nativo del cliente en `x2game.dll` (RVA `0x7ECEA0`) expone KO, ZH_CN, EN_US, JA, ZH_TW, RU, DE, FR, TH, IND y EN_SG. No expone ES. La distribución española debe arrancar con `+locale en_us` y reemplazar el contenido de ese canal dentro de su propia copia.

La tabla `localized_texts` de r575 identifica unidades mediante `tbl_name`, `tbl_column_name` e `idx`. Tiene columnas `ko`, `en_us`, `zh_cn`, `ja`, `ru`, `zh_tw`, `de`, `fr`, `th`, `ind`, `en_sg`, `pt` y `es`. La base operativa contiene 661.919 filas y `es` está vacía.

## Integridad

- Registrar SHA-256 de fuentes y artefactos.
- Abrir SQLite en solo lectura durante inventario.
- Aplicar traducciones por clave compuesta y verificar que se actualizó exactamente una fila.
- Comparar hashes lógicos de todas las columnas ajenas al canal objetivo.
- Ejecutar `PRAGMA integrity_check` tras cada build.
- Verificar dos ejecuciones consecutivas idénticas.

## Empaquetado

El cliente puede consumir copias sueltas y entradas de `game_pak`; mantenerlas sincronizadas. Reextraer las entradas después de empaquetar y comparar su hash con el artefacto aprobado.

El reemplazador actual solo acepta datos que quepan en `size + padding`. Compact usa páginas de 4096 bytes y la base operativa no tiene páginas libres, por lo que una traducción española probablemente crecerá. Medir el piloto antes de decidir. Si excede la capacidad, construir y probar soporte real para tamaño variable.

Los módulos locale Lua/ALB y las imágenes `en_us` con texto forman parte del producto. Conservar contratos de compilación y formatos. Para ALB, compilar, descompilar y comparar estructura antes de aceptar.

## Copia de distribución

El destino operativo principal es
`E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`
(decisión del usuario, 2026-09-06). El cliente original queda como fuente
inmutable; el piloto `...-es_ES` no es el destino por defecto. Al reconstruir
desde el original, preservar/reaplicar los parches del principal registrados
en `server\AAEmu\reconstruccion_cliente_10\checkpoints`.

No usar hardlinks para copiar `game_pak` u otros archivos mutables. Una escritura sobre un hardlink alteraría el cliente original. Usar copia física o clon por bloques probado, y verificar que origen y destino no comparten identidad antes de modificar.
