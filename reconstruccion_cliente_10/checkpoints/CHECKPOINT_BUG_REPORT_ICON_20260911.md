> V2 FALLÓ EN RETAIL: el usuario observó un cuadro negro. Historial conservado; corrección V3 en CHECKPOINT_BUG_REPORT_PACKED_ICON_20260911.md.

# Icono de reportes V2 — 2026-09-11

Target `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`, padre exacto
`upstream/client_version/zone-10.0.2_r575`. Extensión custom exclusivamente de
cliente; no cambia servidor, DB, permisos alpha ni lifecycle de Zones.

Sustituye el botón rectangular Reportar por un icono circular de pergamino y
exclamación, dibujado a 42×42 en su misma posición sobre la barra inferior derecha.
Tooltip «Reportar un error». Estados con tinte normal .85, hover 1, pulsado .65
(desplazamiento 1 px) y deshabilitado .4, usando la misma imagen transparente.
El callback `Aa10BugReport.Open` conserva la apertura y todo el formulario V1.

Fuente generada mediante imagegen integrado: PNG RGBA 1254×1254 con alfa real
0–255, `Scripts/assets/bug-report/report-icon-source.png`. Prompt completo,
identidades y versión de Pillow en `Scripts/assets/bug-report/icon.json`.
Conversión mecánica con alfa premultiplicado/Lanczos a 64×64 y DDS DXT5; se
inspeccionaron PNG reducido y DDS decodificado. No se alteró artísticamente la
imagen por código. Respaldo original del generador conservado.

Autoridad r575: `hud/dynamic_action_bar/dynamic_action_bar_view.lua` confirma los
cuatro setters SetNormalBackground/SetHighlightBackground/SetPushedBackground/
SetDisabledBackground; `baselib/listctrl.lua` confirma SetCoords y SetColor.
`battlefield/mini_scoreboard_view_versus_battleship.lua` confirma drawable y
tooltip OnEnter/OnLeave/HideTooltip. La ruta exclusiva de textura loose requiere
aceptación visual real, no se afirma cerrada sólo por existir el DDS.

Se conserva el bytecode nativo de inventario mediante Aa10LuaExtension. El
builder acepta el ALB V1 exacto B058A101... y el V2 exacto; elimina sólo el cierre
custom anterior tras comprobar el hash y verifica que el nativo sin debug sea
idéntico antes de añadir V2. El tamaño del ALB permanece en 44023 bytes.

El aplicador instala DDS antes del ALB dentro del mismo plan de rollback. Falla
ante un DDS previo desconocido, hardlink o ALB loose; reextrae ALB y sentinelas,
comprueba DDS y tamaño del paquete, y registra SHA completo antes/después.
Control Center mantiene caché por ruta/tamaño/mtime; no existe allowlist cerrada.
Pruebas focales de formulario/codec/icono: 7. Control Center: typecheck, tests y build.

Aceptación pendiente del usuario: volver a abrir el cliente, comprobar icono sin
rectángulo negro, hover/tooltip y pulsación, y abrir/cerrar el mismo formulario.
Ver `BUG_REPORT_ICON_20260911.manifest.json` para hashes, instalación y rollback.
Si se revierte, restaurar ALB V1 con el hash V2 previo exacto y retirar sólo el
DDS nuevo verificado; no reiniciar Game ni modificar la DB.
