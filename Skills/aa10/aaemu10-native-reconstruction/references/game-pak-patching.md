# Parches reproducibles de `game_pak` AA10

Leer esta referencia completa antes de escribir, reemplazar o restaurar
cualquier entrada del `game_pak` del cliente AA10. También aplica cuando la
mutación efectiva sea una compact SQLite, un ALB, Lua compilado, XML, DDS u
otro recurso empaquetado.

## Autorización y frontera

- Target operativo predeterminado desde el 2026-09-06:
  `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
  El original sin sufijo queda como referencia inmutable. La elección del
  principal no elimina la validación de hashes ni autoriza pisar sus parches.
- Modificar el cliente requiere autorización explícita del usuario para la
  tarea actual. Una autorización para servidor o Docker no la implica.
- Antes de escribir, comprobar que el target sea Returns `10.0.2.13-r575`,
  registrar tamaño/SHA-256 del paquete y resolver nombre, tamaño y hash exactos
  de cada entrada.
- Cerrar únicamente `archeage.exe` si mantiene abierto el paquete, avisando al
  usuario. No detener Login, Game, World ni Zones por un parche de cliente.
- Tratar AA8, otros clientes y archivos heredados sólo como candidatos. El
  contenido y consumer promovidos deben estar demostrados por AA10.

## Artefactos que deben quedar versionados

Cada fix debe incorporar en `E:\AAEmu\rama_10\server\AAEmu`:

1. un builder específico en `Scripts/` que valide build, hashes, tamaños y
   firmas exactas, produzca un reemplazo determinista y falle cerrado ante
   deriva;
2. un aplicador reproducible que extraiga las entradas efectivas, conserve
   rollback, ejecute el builder y use `Tools/PakEntryReplace` con hash previo;
3. pruebas focales para la transformación y los rechazos relevantes;
4. checkpoint/manifest con fuente, consumer, hashes de entradas y hash completo
   del paquete antes/después;
5. la prueba retail y su resultado esperado.

La convención durable del repositorio está en
`Docs/AA10GamePakPatchWorkflow_es.md`. El parche de fechas de Housing es la
implementación de referencia:

- `Scripts/PatchAa10HousingDateFormatting.py`;
- `Scripts/ApplyAa10HousingDateGamePakPatch.ps1`.

No versionar `game_pak`, SQLite operacionales, ALB generados, temporales ni
respaldos. Se versionan código, pruebas, hashes y documentación.

## Aplicación segura

1. Ejecutar primero el builder y aplicador en dry-run.
2. Extraer cada entrada con
   `reconstruccion_cliente_10/tools/PakEntryExtract`; nunca usar una copia loose
   como sustituto de la entrada efectiva sin comparar hash y tamaño.
3. Guardar la entrada original en
   `E:\AAEmu\rama_10\backups\client-patches\<patch-id>-<timestamp>`.
4. Exigir reemplazo del mismo tamaño salvo que una frontera separada demuestre
   y pruebe un método seguro de reconstrucción del índice. El método normal es
   `Tools/PakEntryReplace`, que verifica hash previo, recalcula metadata y
   reabre el paquete.
5. En parches multientrada, aplicar de forma fail-closed y revertir en orden
   inverso sólo las entradas que esa ejecución alcanzó a cambiar.
6. Reextraer cada entrada tras la escritura y comparar tamaño/SHA-256 con el
   output determinista del builder.
7. Ejecutar nuevamente el aplicador: debe responder `Already patched` o el
   equivalente probado, sin cambiar el paquete.
8. Emitir `manifest.json` local con HEAD, fecha UTC, paquete antes/después,
   entradas, outputs y rutas de rollback.

## Gates posteriores

UI española vigente (2026-09-06): consultar
`server\AAEmu\reconstruccion_cliente_10\checkpoints\CHECKPOINT_SPANISH_UI_LAYOUT_20260906.md`.
Builder/aplicador V2: `Scripts/PatchAa10SpanishUiLayout.py` y
`Scripts/ApplyAa10SpanishUiLayout.py`. Conserva Folio 900 y equipo 360 px;
amplía presets comunes, habilidades/buffs y filas de alcance/reutilización.
No reaplicar V1 sobre V2; sus hashes difieren por diseño. La aceptación visual
retail de V2 permanece pendiente en el checkpoint, aunque esté instalado.

- El tamaño total de `game_pak` debe permanecer igual en el flujo normal y su
  nuevo SHA-256 completo debe quedar registrado.
- Reabrir el índice con AAPak y extraer al menos una capa de mapa y un icono no
  relacionados con el parche.
- Inspeccionar el código actual de
  `E:\AAEmu\rama_10\tools\AAEmu.ControlCenter` en lugar de asumir una política
  histórica:
  - si existe una allowlist cerrada, añadir sólo la nueva identidad exacta y
    conservar las identidades válidas anteriores;
  - si el hash es informativo para invalidar caché, no inventar una allowlist;
    registrar la identidad en el checkpoint y verificar que la caché se
    regenere por ruta/tamaño/mtime/hash según el contrato actual.
- Ejecutar typecheck, tests y build del panel, además de las pruebas focales del
  parche.
- Probar en retail el consumer positivo y un caso negativo pertinente. No
  commitear ni pushear como aceptado hasta que el gate visual/funcional pase,
  salvo que el usuario pida conservar explícitamente un checkpoint pendiente.

## Rollback

El rollback normal reinserta los respaldos por entrada usando como hash previo
el hash parcheado exacto, reextrae y verifica. Restaurar un paquete completo es
la alternativa de emergencia, no el procedimiento primario. Informar siempre
qué se restauró y conservar el manifiesto de la ejecución fallida.
