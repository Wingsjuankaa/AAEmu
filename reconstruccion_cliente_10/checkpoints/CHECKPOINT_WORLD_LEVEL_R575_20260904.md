# World Level r575 — desactivación

Decisión del usuario: quitarlo si no puede reconstruirse con información nativa
suficiente. Falta el productor original del nivel, cadencia y aplicación
autoritativa de EXP; no se reemplazan por hipótesis. Reconstrucción retirada.

## Cambio aplicado

`system_feature_controls`, entidad 1/control_type=1/condition_type=1001:
`state: 1 -> 0`. Única celda de datos modificada. También cambia el encabezado
transaccional SQLite; solo cambian las páginas del encabezado y de esa tabla.
La compact embedded y la loose conservan sus respectivos tamaños y demás parches.
No se aplicó el borrador de traducción. El catálogo experimental fue archivado.

La cadena nativa se cerró con x2game x64 operativo SHA-256
`405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`,
RVA `B82E30` (loader), `B74930` (selector), `354D60` (predicado).
Los ALB efectivos de HUD/personaje/misiones usan ese predicado. No es una opción
de `SCWorldContent` ni el quinto campo de `SCWorldLevelInfo`; se corrigió aquella
interpretación preliminar.

El cuerpo legado del paquete World Level y su orden posterior al spawn quedan
intactos por compatibilidad. No representa una mecánica reconstruida; sus
consumidores están desactivados por el control nativo del cliente.

## Artefactos

- Dossier: `Docs/AA10WorldLevelReconstruction_es.md`.
- Builder: `Scripts/PatchAa10WorldLevelDisabled.py`.
- Aplicador/rollback: `Scripts/ApplyAa10WorldLevelDisabled.py`.
- Pruebas: `Scripts/tests/test_world_level_disabled.py`.
- Exportador nativo: `reconstruccion_cliente_10/scripts/Aa10WorldLevelNativeAudit.java`.
- Auditoría reproducible: `reconstruccion_cliente_10/scripts/audit_world_level_native.py`.
- Output: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\world-level-frontier`.

Manifiesto de instalación y respaldos:
`E:\AAEmu\rama_10\backups\client-patches\aa10-world-level-disabled-20260904-170706-088361Z\manifest.json`.

| Artefacto | Identidad instalada |
|---|---|
| Embedded, 440823808 bytes | `8F39B0672B60F77B4027259BDFFB714810BF9392045BA81686A028203ADB5223` |
| Loose, 440836096 bytes | `90E5C12A451F1334FF5C1B949982BEE3F1A9E4258F0EFC5FD3FF9D0478591E3C` |
| game_pak, 68963258880 bytes, antes | `8CD6A13F0B7DB62BBC908A43CE191B8DFE351D8C3A42773974C21F17ADDBEFF4` |
| game_pak, después (mismo tamaño) | `8A11B3EAD03E7711B316CEB93573B39C0896BC2A40B631063C915C5A65043676` |

## Validación

- Dry-run con SHA completo e integridad SQLite correcto.
- 4 pruebas focales correctas; builder repetido sobre el resultado: 0 cambios,
  SHA idéntico.
- Restore/build Release correctos; 1804 unitarias correctas; 174 advertencias
  del árbol existente, 0 errores.
- Control Center: typecheck, 52 tests correctos/1 omitido, SQLite smoke y build.
- 15 rangos nativos del cliente comparados con el binario operativo.
- El primer aplicador retenía un handle SQLite de escritura: dos intentos
  rechazados antes de escribir. Se corrigió usando cierre explícito y una
  prueba de liberación de archivo en Windows. Las verificaciones de fallo
  confirman hashes originales; no se perdió ninguna entrada.
- El intento corregido reemplazó y reextrajo correctamente la compact embedded.
- Reapertura AAPak y extracción de mapa `w_white_forest/line.dds` e icono
  `icon_item_shotgun_0024.dds`: MD5 idénticos al índice original. Hash completo
  posterior registrado; paquete conserva sus 68963258880 bytes.
- Segunda ejecución real del aplicador: `Already patched`; SHA del paquete,
  embedded y loose sin cambios. Manifiesto de repetición:
  `aa10-world-level-disabled-20260904-170950-710267Z/manifest.json`.
- Manifiesto compacto versionado: `WORLD_LEVEL_DISABLED_R575_20260904.manifest.json`.

No se ejecutó lifecycle de Zones, no se reinició Docker y no se modificó
persistencia del servidor. Este despliegue consiste en los datos del cliente.
El cliente estaba cerrado al aplicar. Pendiente aceptación visual por el usuario:
abrir el juego, comprobar ausencia del emblema dorado/guía World Level y aceptar
una misión normal. No se declara una sesión retail que no haya ocurrido.

## Rollback

Con el cliente cerrado, ejecutar el aplicador con `--rollback` apuntando al
manifiesto de instalación anterior; revisar su dry-run y agregar `--apply`.
Esto restaura las entradas embedded y loose por sus hashes exactos, no sustituye
todo el paquete ni modifica DB de personajes. La reversión funcional no exige
que los timestamps de metadata del paquete vuelvan al valor anterior.
