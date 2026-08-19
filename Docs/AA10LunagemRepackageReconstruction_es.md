# Reconstrucción AA10: Transmuter y reempaquetado de Lunagem

Checkpoint estático y de implementación del 2026-08-19 para ArcheAge Returns 10.0.2.13 r575.

## Resultado

La mecánica queda reconstruida de extremo a extremo en el servidor:

1. una Lunagem extraída se convierte con un **Transmuter** en su caja normal y vendible;
2. el Transmuter y la Lunagem objetivo se consumen como instancias exactas;
3. la caja se puede abrir y presenta el selector retail de stat;
4. la opción elegida llega a la bolsa sin riesgo de perder la caja si la entrega no cabe.

El cierre dinámico dentro del cliente quedó **aprobado** el mismo 2026-08-19 contra el cliente
10.0.2.13 r575. Se desplegó únicamente Game y se mantuvo una sola Zone, la 351
`o_hirama_the_west_2`, correspondiente a la posición persistida del personaje.

## Contrato r575

| Entidad | ID | Función |
|---|---:|---|
| Transmuter | item 42876 | Consumible de reempaquetado |
| Skill del Transmuter | 35945 | Casteo de 3 s, 500 labor base |
| Special effect | tipo 49 | `ItemConversion`, `value1=8` |
| Set de conversión | 8 | `repackage` |
| Lunagem de prueba | item 44684 | Glorious Fireglow Lunagem: Healing |
| Ruta | item_conv 4579 | `repackage_socket_red_3T` |
| Reagent pack | 4579 | Contiene 44681..44690 |
| Product pack | 4652 | Probabilidad 10000/10000 |
| Caja resultante | item 44773 | Glorious Fireglow Lunagem vendible |
| Skill de apertura | 38063 | Selector de variante |
| Selective effect | 391 | Una elección, consume una caja |

La opción cuarta del selector vuelve a entregar 44684. El catálogo prueba además 24 rutas
`repackage_socket%`, 202 Lunagem de entrada y 24 cajas de salida.

## Causa del fallo

El cargador antiguo escribía `item_conv_rpack_id` y `item_conv_ppack_id` en un campo común llamado
`ConversionId` y buscaba productos comparando ambos IDs directamente. Esas claves pertenecen a
espacios distintos. En el caso de 44684, el rpack 4579 debe atravesar `item_convs.id=4579` y llegar
al ppack 4652. La comparación rota encontraba por coincidencia numérica el ppack 4579, de otra ruta,
y resolvía el item 44104.

También se ignoraban las tablas de miembros, los sets, pesos y grados. `_conversionSets` se creaba
vacío, de modo que el servidor nunca podía verificar realmente `value1=8`.

## Implementación

- `ItemConversionGameData` carga el grafo `set -> route -> rpack/ppack -> reagent/product`.
- La resolución prioriza reactivos explícitos sobre filtros genéricos, valida el set, aplica chance,
  pesos, rangos inclusivos y grado de producto; `item_grade_id=-1` hereda el grado de origen.
- `ItemConversion` verifica que caster y target sean las instancias seleccionadas dentro de la bolsa,
  comprueba labor y capacidad, desactiva el consumo automático y hace una única mutación lógica.
- `ItemContainer` incorpora consumo exacto por instancia/cantidad y entrega con grado en lotes
  preflighted.
- `CSInvokeItemSelectiveItemEffectPacket` preflighta y confirma consumo más recompensa; ya no destruye
  primero la caja para luego descubrir que no puede entregar la opción.
- Las recompensas se publican una por paquete porque r575 sólo procesa de forma fiable el primer body
  variable `Take` en una lista; el commit del estado del servidor sigue siendo atómico.

## Validación automatizada

- Build Release de `AAEmu.slnx`: 0 errores.
- Suite TUnit: 1344/1344 correctas, 0 errores, 0 omitidas.
- Prueba contra la SQLite autoritativa local: set 8 + item 44684 resuelve ruta 4579 y entrega
  exactamente item 44773 x1, grado heredado.
- Pruebas negativas: un set incorrecto no convierte; un ppack con el mismo número que el rpack no se
  cruza accidentalmente.
- Prueba de distribución: selección ponderada, cantidad máxima inclusiva y grado explícito.
- Pruebas de seguridad: rutas ambiguas se rechazan y dos stacks decrementados se publican como dos
  cuerpos `Take` independientes para r575.
- `git diff --check`: sin errores.

## Aceptación dinámica dentro del cliente

Prueba ejecutada el 2026-08-19 con `Wingsjuanka` en Western Hiram Mountains, Zone 351:

1. Se entregaron por el canal administrativo normal un Transmuter 42876 y una
   Glorious Fireglow Lunagem: Healing 44684.
2. El cliente abrió el flujo **Recloak** al usar el Transmuter sobre la gema. Tras confirmar,
   mostró la retirada de ambos inputs, la adquisición de Glorious Fireglow Lunagem y el consumo de
   500 labor: 2.569 -> 2.069.
3. El snapshot vivo confirmó `instance=16777336`, `template=44773`, slot 64, cantidad 1, grado 5 y
   `Flags=None`. El objeto empaquetado no quedó soulbound.
4. Al usar 44773, el cliente abrió **Uncloak** con las diez variantes. Se eligió **Healing**, opción
   4; el servidor consumió la caja y entregó 44684.
5. El resultado final fue `instance=16777336`, `template=44684`, slot 64, cantidad 1, grado 5 y
   `Flags=SoulBound`. No quedaron instancias 42876 ni 44773.
6. Se salió a selección de personaje, donde el cliente mostró 2.071 labor tras regeneración, y se
   volvió a entrar a la misma Zone. El snapshot vivo y la búsqueda visual de `Healing` conservaron
   exactamente 44684 en el slot 64: persistencia aprobada, sin duplicación.

Trazas canónicas de Game:

```text
15:06:42 [INFO] SpecialEffectAction - AA10 item conversion: character=Wingsjuanka, source=16777336/42876, target=16777338/44684, set=8, route=4579, products=44773x1@5, labor=500
15:08:29 [INFO] PacketMarshaler - CSInvokeItemSelectiveItemEffect Wingsjuanka: slot=Inventory/64 try=1 picks=[4]
15:08:29 [INFO] PacketMarshaler - CSInvokeItemSelectiveItemEffect: Wingsjuanka consumed item 16777336/44773 x1, received [44684x1@0]
```

El runtime usado fue la imagen Game
`sha256:8e359a6eea44577b68ff44aac9cc78740f11d454a125b86612eec0c25f402adc`; Login, DB y Game
permanecieron saludables. La única instancia `AAEmu.ZoneHost.exe` fue PID 36476, perfil
`o_hirama_the_west_2`; no se levantó ninguna otra Zone. No hubo crash ni error de la mecánica.

La evidencia fuente está en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\lunagem-repackage-frontier`.
