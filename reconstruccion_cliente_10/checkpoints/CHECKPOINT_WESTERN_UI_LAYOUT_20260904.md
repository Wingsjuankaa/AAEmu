# UI occidental r575: Folio y tooltip de equipamiento

Fecha: 2026-09-04. Estado: parche aplicado; aceptación visual retail pendiente.

## Problema reproducido

En `ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`, las categorías del
Folio desbordaban sus bandas y el tooltip de equipamiento mezclaba columnas o
forzaba demasiados saltos. El mismo límite también afectaba al texto inglés:
la causa estaba en el layout heredado, no en una traducción concreta.

La fuente r575 demuestra dos límites:

- `crafting_view.lua` crea un Folio occidental de 800 px, pero conserva botones
  de 761/378 px y resta 280/100 px para el arte;
- `tooltip.lua` fija `minWindowWidth = 250` para objetos y comparaciones, aunque
  las habilidades ya usan 300 px.

El ALB de AA8 conserva los mismos valores y sólo sirve como corroboración de
que el problema es heredado. La búsqueda de material oficial en inglés no
produjo capturas equivalentes y versionadas, por lo que no se usaron imágenes
de servidores derivados como autoridad del layout.

## Cambio

- Folio: ancho de 900 px. El botón grande ocupa todo el ancho interno y cada
  botón de dos columnas usa `(ancho interno - 4) / 2`. Las reservas de 280/100
  px para las ilustraciones se conservan.
- Tooltip: armas, armaduras, armaduras de mascotas/mayordomo y accesorios usan
  un mínimo de 360 px. Consumibles, materiales, buffs, habilidades, mapas y
  otros tooltips conservan sus tamaños nativos.

No se abrevia texto, no se modifica `compact.sqlite3` y no cambia protocolo ni
servidor. El ajuste vive en los dos consumidores Bin64 efectivos.

## Entrega y rollback

- Builder: `Scripts/PatchAa10WesternUiLayout.py`.
- Aplicador: `Scripts/ApplyAa10WesternUiLayoutGamePakPatch.ps1`.
- Pruebas: `Scripts/tests/test_patch_aa10_western_ui_layout.py`.
- Manifiesto durable: `WESTERN_UI_LAYOUT_R575_20260904.manifest.json`.
- Respaldo por entrada:
  `E:\AAEmu\rama_10\backups\client-patches\aa10-western-ui-layout-20260904-215513Z`.

El `game_pak` mantuvo 69.430.854.656 bytes y cambió de
`2E6CF6E1191CB5CE2C2EC618C2977FFAED516F8DB7401F9E5F4D38415229D576`
a `F85FCF69359776C2ECCC85870230B4070C72C481EEC6DD9BCD90F591FB0BAF67`.
La segunda aplicación informó `Already patched` para ambas entradas.

El Control Center deriva su caché de ruta, tamaño y `mtime`; no usa una
allowlist cerrada, por lo que el cambio de fecha del paquete selecciona una
caché nueva sin modificar su código.

## Verificación

- Cuatro pruebas focales correctas: transformación exacta, alcance por tipo de
  objeto, rechazo fail-closed y tamaños de entrada.
- Compilación determinista con `luac51.exe`, header x64 r575 restaurado y ALB
  rellenado hasta el tamaño original.
- Reextracción exacta de ambos ALB después de escribir.
- Icono y capa de mapa no relacionados conservaron sus hashes.
- `compact.sqlite3` reextraída: 467.595.264 bytes, SHA-256
  `3BFBB472032DF1BA7EFADBAE1530FA4FB5640B7E710AD4D59254CB88E06B74DD`.
- `dotnet build -c Release`: correcto, 0 errores; suite AAEmu: 1.806/1.806.
- Control Center: typecheck y build correctos, 52 pruebas correctas, una prueba
  de integración real omitida por diseño y smoke SQLite correcto.
- Pendiente: captura retail del Folio y del mismo equipo mostrado por el
  usuario para aceptar visualmente espaciado, anclajes y comparaciones.
