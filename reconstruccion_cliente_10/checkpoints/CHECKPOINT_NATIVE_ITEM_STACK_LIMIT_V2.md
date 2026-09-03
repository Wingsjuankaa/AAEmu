# CHECKPOINT_NATIVE_ITEM_STACK_LIMIT_V2

Estado: implementado y validado estáticamente; despliegue y aceptación dinámica
por encima de `10.000` pendientes.

## Frontera

- Build: ArcheAge Returns 10.0.2.13 r575 x64.
- Plantillas objetivo: límites retail exactos `1.000` o `9.999`.
- Resultado: `99.999` unidades máximas por stack.
- No objetivo: modificar límites retail distintos de esos dos grupos.

## Evidencia AA10

- Cliente: 2.531 IDs objetivo; SHA-256 de la lista ordenada
  `14C1BA767C5E3A077FCCDB177C146423DFFB493502B8B7B0CC63E7B68D6223BE`.
- Runtime: 2.771 IDs objetivo; SHA-256
  `8146AEA01F997FBF357EB3299F8D7F693ECDFAD348B9A37F3A255ADA61D28C8D`.
- El grupo adicional contiene 55 plantillas cliente y 59 runtime con límite
  retail `9.999`, incluidos Tax Certificate `31891` y Bound Tax Certificate
  `31892`.
- Cliente, `ItemTemplate.MaxCount`, `Item.Count`, wire y persistencia usan
  enteros de 32 bits; `99.999` no exige un cambio de ABI ni de packet.

## Transformación

```sql
UPDATE items
SET max_stack_size = 99999
WHERE max_stack_size IN (1000, 9999);
```

La actualización sólo ocurre después de verificar los conjuntos exactos de
IDs. El builder acepta retail intacto, v1 y v2; rechaza otra identidad o estado
parcial, ejecuta `quick_check`, compara todas las parejas
`(id, max_stack_size)` y exige tamaño físico idéntico.

## Gates ejecutados

- 5 pruebas focales Python: pass, incluida migración v1 -> v2.
- 13 pruebas Python de `Scripts/tests`: pass.
- Dry-run sobre las tres SQLite v1: pass; 55/55/59 filas por cambiar.
- Tamaños preservados y hashes deterministas calibrados: pass.
- Restore y build Release: pass.
- Suite AAEmu: 1.686 pass; conserva dos fallos de infraestructura no
  relacionados (`%db_port%` sin sustituir y
  `MoneyTest/UnableToFindRecipient`).

## Gates pendientes

- Aplicación real e idempotencia sobre `game_pak`, cliente suelto y runtime.
- `quick_check`, distribución final y extracción de entradas no relacionadas.
- Reinicio/health de Game y relanzamiento autorizado de Zone 142.
- Un único stack de Tax Certificate superior a `10.000`, relog y confirmación
  en UI, Web API y MySQL.
