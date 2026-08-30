# Flujo reproducible para parches de `game_pak` AA10

Todo arreglo que modifique una entrada de `game_pak` debe quedar respaldado en
el repositorio por código reproducible. No se acepta como solución permanente
una edición manual del paquete ni un binario de reemplazo sin procedencia.

## Contrato obligatorio

Cada parche debe incluir:

1. un builder específico que valide hashes y tamaños exactos de sus entradas
   AA10 r575, produzca el reemplazo de forma determinista y falle cerrado ante
   cualquier deriva;
2. un script de aplicación que extraiga las entradas efectivas del paquete,
   conserve rollback local, ejecute el builder, reemplace únicamente entradas
   del mismo tamaño mediante `Tools/PakEntryReplace` y las reextraiga para
   verificación;
3. un `manifest.json` local con HEAD, rutas, tamaños y SHA-256 antes/después;
4. una ejecución sin `-Apply` que actúe como dry-run y una segunda ejecución
   idempotente que no vuelva a mutar entradas ya parcheadas;
5. documentación forense de la causa, alcance, consumer y prueba retail.

Los paquetes, bases SQLite, ALB generados y respaldos no se versionan. Se
versionan el builder, el aplicador, las pruebas y los hashes. Si una operación
multientrada falla, el aplicador debe revertir en orden inverso solo aquello que
él mismo cambió.

## Parche de fechas de Housing H3

El builder `Scripts/PatchAa10HousingDateFormatting.py` transforma dos consumers
exactos de Housing:

- `game/scriptsbin64/x2ui/housing/maintain_window.alb`;
- `game/scriptsbin64/x2ui/housing/maintain_window_view.alb`.

La fecha fiscal absoluta usa ahora el formateador calendario nativo y la fila
de detalle no agrega el sufijo redundante `until`. No se alteran timestamps,
semanas fiscales, pagos, periodos de protección ni las cadenas globales de
duración.

Dry-run:

```powershell
pwsh Scripts/ApplyAa10HousingDateGamePakPatch.ps1
```

Aplicación:

```powershell
pwsh Scripts/ApplyAa10HousingDateGamePakPatch.ps1 -Apply
```

El directorio informado al final contiene las entradas previas necesarias para
rollback y el manifiesto verificable. Para compartir el arreglo se comparte el
commit, no el `game_pak` modificado.

## Barra de experiencia ancestral

El builder `Scripts/PatchAa10ExperienceBar.py` elimina los dos saltos incondicionales con los que
el ALB retail omite su tooltip y su barra ancestrales. El aplicador valida la entrada AA10 r575,
preserva tamaño, rollback y manifiesto, y verifica el resultado reextrayéndolo:

```powershell
pwsh Scripts\ApplyAa10ExperienceBarGamePakPatch.ps1
pwsh Scripts\ApplyAa10ExperienceBarGamePakPatch.ps1 -Apply
```

La causa nativa y los hashes están documentados en
`Docs/AA10ExperienceBarSynchronization_es.md`.
