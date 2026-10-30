# Disparo de precisión: alcance y recarga en caliente

29 de octubre de 2026, America/Santiago. Repositorio canónico
`E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`, HEAD
`9c74824659cc0d144f5e450e3bd7157624e539c3`. Padre consultado:
`upstream/client_version/zone-10.0.2_r575`, SHA
`78533663d9ca93dc4aa610c088359312f91f4293`.

## Problema y corrección

Skill 23592, plot 1226, Disparo de precisión. El usuario mostró el objetivo a
30,3 m y un tooltip español con alcance 0–45 m. El lanzamiento terminaba sin
daño a esa distancia. El reporte 5 de Dannia ya describía casteo sin daño;
la aceptación histórica sólo había cubierto aproximadamente 2–3 m.

El evento 9896 selecciona hasta 20 enemigos mediante la línea 4843, cuyos
valores son 3/25/3; la variante 5037 lleva 2/30/3. El consumidor nativo forma
el OBB mediante límites simétricos y semiextensiones. `ComputeCorridor` usaba
Value2 como longitud completa, y la búsqueda previa de World descartaba
también los candidatos más allá de esa longitud. La línea normal acababa
en 25 m aunque la skill permite seleccionar un objetivo hasta 45 m.

Se corrigieron **ambos** pasos para cubrir la longitud de dos semiextensiones.
Se conservan anchura, altura, orientación, radio corporal, rechazo por detrás
y fallback existente para Value2 cero. No se añadió una excepción por ID,
no se alteraron catálogos, tooltip, daño, cooldowns ni la validación de rango
de lanzamiento. El volumen fijo de esta línea y el alcance de lanzamiento
son parámetros distintos: no se afirma que el volumen de área termine a45 m.

## Evidencia y límites

El extractor read-only `reconstruccion_cliente_10/scripts/audit_precision_shot_range.py`
consulta full autoritativa, compact español principal y ambos catálogos
privados del sandbox. Las cuatro fuentes coinciden en max_range45 y las
formas anteriores. Genera 654 filas de geometría/plot relacionadas, conserva
las ausencias de enums en compact y exige quick_check/integrity_check.
Dos builds producen SQLite idéntica:
`8193e9150eb5d3eb24e514d4d1f683b651d775c4c52ef83dd944af73470604e1`.

Native Zone r575 x64 SHA256:
`8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`.
El consumidor OBB de línea se reancló byte a byte en RVA `0x7b7e60` contra
la DLL real. Loader de aoe_shapes: RVA `0xc02bd0`, descriptor de24 bytes,
kind en+4, valores en+8/+0xc/+0x10. El OBB usa min/max simétricos y la mitad
de su diferencia como semiextensión. La evidencia nativa es de representación
del volumen; no se presenta como reconstrucción completa de la selección del
servidor nativo. `calc_distance`, `adjust_angle` y los endpoints independientes
del PlotObject continúan fuera del cierre de esta reparación.

El padre exacto contiene la misma interpretación de longitud completa; no
aporta un arreglo posterior en el ref local. AA8 ForwardCuboid conserva una
interpretación similar y se clasificó como comparador estructural, sin portar
su implementación. No se usaron timings ni geometría de otras versiones.

## Pruebas y aceptación

- Antes: siete pruebas nuevas, cinco fallan y dos pasan. Reproducen los fallos
  a30/45/50 m, el caso rotado y la búsqueda real de candidatos de World.
- Después: siete pasan, incluidos rechazo lateral, vertical y por detrás,
  límite del volumen y fallback de descriptor cero.
- Restore y build Release de solución terminados sin errores. Persisten
  advertencias anteriores de paquetes y analizadores, fuera de esta reparación.
- Suite completa Release: **8.913/8.913**, sin omitidas.
- El usuario confirmó daño a30 m y después a44–45 m, sin reconectarse.
  Los logs registran los impactos de23592 sobre el dummy282, incluido TL35
  a02:16:11UTC con5233 de daño.

## Despliegue en caliente y alcance operativo

Se editaron dos cuerpos de métodos reales consumidos por dotnet watch.
World mantuvo PID396; contador CLR0→2; Native31564 y sesión3225459956 sin
cambios; cliente26548 conserva PID y fecha de creación. Sandbox1001 mantuvo
obj273. El Native habitual23668 también conservó su identidad.

El código está aplicado al sandbox SDK-watch y queda guardado para futuras
compilaciones. **La imagen del Game habitual no se recreó** en esta prueba.
El reporte5 queda pendiente de repetir con Dannia en ese entorno, sin atribuir
la aceptación del sandbox al personaje o despliegue habitual.

Rollback: restaurar los dos archivos originales del directorio `before` de
la evidencia y dejar que watch aplique sus cuerpos anteriores; comprobar
PID, contador y sesión de nuevo. No requiere tocar el cliente, DB ni Zone.
No se ejecutó rollback porque el candidato pasó pruebas y aceptación.

Todos los artefactos nuevos están bajo E. Evidencia:
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/precision-shot-range-20261029/`.
Incluye imagen recibida, logs nativos, SQLite/manifests deterministas, backups,
pruebas antes/después, identidad de procesos y `delivery-manifest.json`.
