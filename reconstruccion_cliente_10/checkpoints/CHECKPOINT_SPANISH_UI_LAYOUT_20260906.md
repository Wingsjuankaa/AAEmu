# Distribución española principal y anchos de UI r575

Estado: instalado el 2026-09-06; aceptación visual dentro del juego pendiente.

Cliente principal por petición del usuario:
`E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
El cliente sin sufijo queda como referencia original inmutable; `...-es_ES`
es el piloto histórico. El canal interno sigue siendo `+locale en_us`.

## Causa y alcance

La captura de «Lluvia de flechas: Neblina» muestra alcance y reutilización
superpuestos. `tooltip.lua` limita las habilidades a 300 px y usa
`AddAnotherSideLine` para añadir reutilización a la fila de alcance/radio.
Los ajustes occidentales de varios `locale/en_us.lua` están condicionados a
KAKAONA/TRION, por lo que no se aplican automáticamente en Returns.

La tabla `F_PREFIX_SIZE` alimenta ventanas de inventario, correo, habilidades,
misiones, vivienda, comercio, comunidad, portales, opciones y otros módulos.
El inventario estático encuentra 149 referencias a los tamaños ampliados en
136 fuentes con ALB Bin64 presente. Son referencias de código, no 149 ventanas
que se hayan abierto y verificado visualmente. Algunas son subventanas o
variantes regionales; los elementos con medidas propias requieren revisión
visual individual. Se inventariaron 1.144 fuentes Lua del paquete efectivo.

| Tamaño predefinido | Antes | Después |
|---|---:|---:|
| 300 | 300 | 360 |
| 350 | 350 | 430 |
| 430 | 430 | 510 |
| 450 | 450 | 540 |
| 510 | 510 | 600 |
| 600 | 600 | 720 |
| 680 | 680 | 800 |
| 800 | 800 | 900 |

Los presets 900/1200 e iconos conservan su geometría. El Folio mantiene su
parche de 900 px y el mismo hash. El tooltip de equipamiento conserva 360 px.

Otros cambios:

- Habilidades y comparación de rangos: 420 px; lanzamiento y reutilización
  tienen filas propias. Se conservan los valores, los textos y los formatos.
- Buffs, pasivas, consumibles, materiales, sellos y enlaces de misión: 360 px.
  Tooltip genérico: máximo 420 px. La previsualización especializada de 150 px
  conserva su comportamiento.
- El fallback de escala del tooltip actualiza el ancho de sección antes de
  medir nuevamente el texto.
- Opciones: menú lateral 250 px; aviso de reinicio usa el ancho de la página.
- Tabla de grados de oficio: columnas redistribuidas dentro de los 800 px.
- Tienda: las dos fichas por fila calculan su ancho a partir del contenedor.
- Seguimiento de misiones: rejilla 390, título 345, objetivos 340 px, como en
  la configuración occidental r575; selección de diálogo 680 px.

## Implementación reproducible

- `Scripts/PatchAa10SpanishUiLayout.py`: transformaciones exactas y lector del
  bytecode Lua 5.1 x64, incluida la constante entera retail `0xFE`.
- `Scripts/Aa10SpanishUiLayout.contracts.json`: fuente, entradas aceptadas,
  salida determinista, tamaños y hash del compilador.
- `Scripts/ApplyAa10SpanishUiLayout.py`: dry-run, validación r575 y del cliente
  principal, rechazo de hardlinks/ALB sueltos, backups, aplicación y rollback
  transaccional, reextracción y SHA-256 completo.
- `Scripts/tests/test_patch_aa10_spanish_ui_layout.py`: pruebas de fuentes
  efectivas, ejecución Lua de filas, determinismo, deriva e interrupciones.

Desde `server\AAEmu`:

```powershell
python Scripts/ApplyAa10SpanishUiLayout.py
python Scripts/ApplyAa10SpanishUiLayout.py --apply
```

El builder exige las ocho fuentes exactas. Su equivalencia con los ALB
instalados se comprobó comparando instrucciones, constantes y prototipos,
omitiendo únicamente datos de depuración. El tooltip de partida incluye V1.
Para reconstruir desde la referencia original, aplicar V1 antes de V2; no
ejecutar el aplicador V1 sobre V2, pues rechazará correctamente su nuevo hash.
El parche de traducciones de compact debe preservar estos ALB.

## Verificación y límites

- 14 pruebas focales aprobadas, incluidas cuatro pruebas originales V1.
- Ejecución del consumidor real de información de habilidad bajo Lua 5.1:
  maná presente/ausente, alcance propio/a distancia, radio y reutilización
  larga; ninguna llamada superpone dos de esos campos en una fila.
- Ocho ALB dentro del tamaño original; doble compilación idéntica.
- Reextracción de las ocho entradas coincide con los hashes esperados.
- Segunda aplicación: `already_patched`; el SHA-256 completo permanece igual,
  sin escrituras. Manifiesto durable: `SPANISH_UI_LAYOUT_R575_20260906.manifest.json`.
- Icono, capa de mapa y Folio conservan sus hashes.
- Restore/build Release: correctos, cero errores; 1.812 pruebas AAEmu pasan.
- Control Center: typecheck/build, 52 pruebas y smoke SQLite correctos;
  una integración real omitida por diseño. Su caché depende de ruta, tamaño
  y mtime; no hay una allowlist cerrada que actualizar.
- Unluac leyó las ocho salidas. Su reconstrucción textual de los dos grandes
  módulos tooltip no recompila por bloques `if/else` mal reconstruidos. El
  mismo fallo ocurre con los baseline V1/nativo recompilados sin el cambio.
  Se guardó la evidencia; los ALB entregados proceden de fuentes originales
  compiladas, nunca de esas reconstrucciones defectuosas.
- No se modificaron traducciones ni SQLite, y no se reiniciaron servicios.
- No se dispone del controlador nativo de ventanas en esta sesión para
  comprobar el resultado renderizado. No se afirma aceptación visual total.

Prueba retail pendiente: abrir el cliente principal, mostrar la misma
habilidad, y comprobar filas separadas, acentos y descripción; después buffs,
comparación de habilidades/equipo, Opciones, tienda, correo y seguimiento de
misiones. Revisar también anclajes y bordes con la resolución/escala habitual.
El usuario indicó que C/O ya estaban corregidos; verificar que se conservan.

## Identidad y rollback

Paquete: 73.172.008.448 bytes antes y después.

- Antes: `59C44861C0928845B043B21F36C7F2D4ECBA00440958598673B3D3488C4E876C`.
- Después: `F3D915B210C29521FD1581E8042B1E7132E432D17D3010113D3AECF98577672F`.
- Respaldo aplicado:
  `E:\AAEmu\rama_10\backups\client-patches\aa10-spanish-ui-v2-20260906-150030-860928Z`.
- Evidencia/inventario/pruebas:
  `E:\AAEmu\rama_10\localization\aa10-es-es\work\ui-layout-v2`.

El manifiesto aplicado guarda por entrada `before`, `after`, `rollback` y
`verified_sha256`. Con el cliente cerrado, un rollback manual usa
`dotnet Tools/PakEntryReplace/bin/Release/net10.0/PakEntryReplace.dll`
con argumentos `game_pak`, `entry`, `rollback`, `after`, en orden inverso;
reextraer y comprobar cada hash `before`. El aplicador revierte automáticamente
sus escrituras si falla una entrada o un control final, incluida una escritura
que haya fallado después de tocar el paquete.

Las skills `aaemu10-native-reconstruction`, `aa10-client-forensics` y
`aa10-es-es-localization`, sus referencias operativas y scripts de estado
quedan actualizados al cliente principal. Las tres pasaron `quick_validate`;
ambos scripts se ejecutaron y resolvieron correctamente el destino. Respaldo:
`E:\AAEmu\rama_10\backups\skills\aa10-primary-client-20260906`.
