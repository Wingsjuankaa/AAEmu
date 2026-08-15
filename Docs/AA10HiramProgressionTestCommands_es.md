# Prueba manual AA10 — progresión Hiram T1 a T6

Fecha: 2026-08-15

Cliente: ArcheAge Returns `10.0.2.13 r575`

Servidor: `Wingsjuankaa/AAEmu:rama_10`

Este documento contiene los comandos y puntos de control para probar synthesis y awakening desde
Hiram Guardian (T1) hasta Sacred Hiram (T6). Los IDs proceden del compact retail r575.

El menú para cambiar estadísticas queda fuera de esta prueba. Aquí sólo se valida progresión de grado,
awakening, consumo, pity, persistencia y conservación de las tres estadísticas existentes.

## Reglas importantes

- Mantener al menos seis espacios libres en la bolsa. Las infusiones usadas aquí ocupan un slot cada una.
- El paquete de synthesis admite como máximo seis materiales.
- Al acercarse al grado requerido, colocar **una sola infusión por synthesis** para poder comprobar
  con claridad EXP, coste y consumo.
- Cada tier debe detenerse en el límite que exige la siguiente ruta de awakening. La proyección r575
  distribuida tenía `max_evolving_grade=7` obsoleto en T2-T6; el parche local lo corrige a
  T1=7, T2=8, T3=9, T4=11 y T5/T6=12 tanto en cliente como en servidor. El excedente llena la barra
  del grado máximo, pero nunca puede promover el item al grado siguiente.
- En el cliente, la copia autoritativa está dentro de `game_pak`; modificar solamente
  `game/db/compact.sqlite3` no cambia el tooltip porque el paquete tiene prioridad. El despliegue
  validado mantiene ambas copias sincronizadas.
- No seguir sintetizando cuando el item alcance el grado indicado en la tabla, aunque su barra quede
  llena.
- Comprobar después de cada operación que el material se descuente inmediatamente y que las tres
  estadísticas permanezcan iguales.
- Hacer relog después de cada awakening si se quiere validar persistencia tier por tier.

## Oro para toda la prueba

El cliente r575 captura `/gold` como comando local y responde `Requirements not met.` sin enviarlo al
servidor. Para alcanzar el comando AAEmu hay que usar el alias `/addgold`, conservando a continuación
el subcomando, objetivo y cantidad. Para añadir 100,000 de oro al personaje que lo ejecuta:

```text
/addgold add self 100000
```

Para una cantidad exacta con monedas menores, por ejemplo 100,000 oro, 25 plata y 50 cobre:

```text
/addgold add self 100000 25 50
```

No usar `/gold ...`: el cliente lo intercepta antes de que llegue a AAEmu. Tampoco usar
`/addgold 100000`: la ruta activa exige el subcomando y el objetivo. Finalmente, no usar `set` para
fijar el saldo: en esta versión está implementado como suma, igual que `add`.

## Cadena completa

| Tier actual | Grado requerido | Scroll | Éxito | Resultado |
|---|---|---:|---:|---|
| T1 Hiram Guardian | Celestial | `47926` | 100% | T2 Radiant |
| T2 Radiant | Divine | `52021` | 100% | T3 Brilliant |
| T3 Brilliant | Epic | `52022` | 100% | T4 Glorious |
| T4 Glorious | Mythic | `54452` | 100% | T5 Exalted |
| T5 Exalted | Eternal | `53799` | 10% inicial, +10% por fallo | T6 Sacred |

Para los zapatos de tela probados, los templates son:

```text
45342 Hiram Guardian Shoes
45655 Radiant Hiram Guardian Shoes
45848 Brilliant Hiram Guardian Shoes
46858 Glorious Hiram Guardian Shoes
48382 Exalted Hiram Guardian Shoes
53042 Sacred Hiram Guardian Shoes
```

## Catálogo de infusiones

```text
/item add self 48841 1
```

`48841` — Eternal Hiram Infusion, 12,500 EXP. Usar en T1 y T2.

```text
/item add self 51591 6
```

`51591` — Sacred Hiram Infusion, 30,000 EXP cada una. Usar en T3, una por operación al acercarse a
Epic. Repetir el comando si hacen falta más.

```text
/item add self 54328 6
```

`54328` — Ancestral Hiram Infusion, 500,000 EXP cada una. Es la infusión más potente del cliente r575.
Usar normalmente desde T4. También puede usarse una unidad como prueba explícita del límite de grado:
el tier debe quedar en su grado máximo con la barra llena, sin atravesarlo.

## Catálogo de scrolls

```text
/item add self 47926 1
/item add self 52021 1
/item add self 52022 1
/item add self 54452 1
/item add self 53799 10
```

- `47926`: Hiram Awakening Scroll garantizado, T1 -> T2.
- `52021`: Hiram Awakening Scroll Rank 2 garantizado, T2 -> T3.
- `52022`: Hiram Awakening Scroll Rank 3 garantizado, T3 -> T4.
- `54452`: Hiram Awakening Scroll Rank 4 garantizado, T4 -> T5.
- `53799`: Sacred Hiram Awakening Scroll, T5 -> T6. Empieza en 10% y añade 10 puntos porcentuales de
  pity por cada fallo. Diez unidades cubren la secuencia hasta 100% si fallan los primeros nueve intentos.

## Procedimiento paso a paso

### Paso 1 — T1 Hiram Guardian a T2 Radiant

Para los Hiram Guardian Shoes Arcane con `91/1085` EXP:

```text
/item add self 48841 1
```

1. Abrir Bag -> Gear Upgrade -> Synthesis.
2. Colocar los zapatos y exactamente una Eternal Hiram Infusion `48841`.
3. Confirmar una vez.
4. Resultado esperado: Celestial. Si la EXP excede todo el recorrido del T1, debe quedar con la barra
   final llena (`13714/13714` para la categoría Hiram T1), nunca en Divine.
5. Verificar que siguen las mismas tres estadísticas y que la infusión desaparece inmediatamente.

Cuando el item esté en Celestial:

```text
/item add self 47926 1
```

Usar Awakening una vez. Debe quedar Radiant Hiram Guardian Shoes. Detenerse y comprobar nombre,
grado, EXP, tres estadísticas y consumo del scroll.

### Paso 2 — T2 Radiant a T3 Brilliant

Generar infusiones según sea necesario:

```text
/item add self 48841 6
```

Usarlas progresivamente hasta llegar a Divine. Cerca de Divine, confirmar con una sola infusión por
operación. No seguir sintetizando después de alcanzar Divine.

Caso de regresión real: una Radiant Nodachi que parta Heroic con `5632` EXP y consuma una infusión
`48841` más dos `51591` debe terminar Divine con `9326` EXP. Antes del parche quedaba incorrectamente
Celestial con la barra llena.

```text
/item add self 52021 1
```

Usar el scroll una vez. El resultado debe ser Brilliant Hiram Guardian Shoes.

### Paso 3 — T3 Brilliant a T4 Glorious

```text
/item add self 51591 6
```

Usar Sacred Hiram Infusions progresivamente hasta Epic. Colocar sólo una por operación al acercarse al
grado objetivo.

```text
/item add self 52022 1
```

Usar el scroll una vez. El resultado debe ser Glorious Hiram Guardian Shoes.

### Paso 4 — T4 Glorious a T5 Exalted

```text
/item add self 54328 6
```

Usar Ancestral Hiram Infusions de una en una hasta Mythic. El servidor debe saturar la barra de Mythic
sin promover el item por encima del máximo del tier.

```text
/item add self 54452 1
```

Usar el scroll una vez. El resultado debe ser Exalted Hiram Guardian Shoes.

### Paso 5 — T5 Exalted a T6 Sacred

```text
/item add self 54328 6
```

Usar Ancestral Hiram Infusions de una en una hasta Eternal. Detener synthesis en cuanto llegue a ese
grado.

```text
/item add self 53799 10
```

Intentar awakening con un scroll por operación hasta obtener éxito. La probabilidad esperada es 10%,
20%, 30% y así sucesivamente después de cada fallo. El resultado debe ser Sacred Hiram Guardian Shoes.

### Paso 6 — T6 Sacred, máximo final

T6 Sacred es el último tier de esta cadena; no tiene otro awakening.

```text
/item add self 54328 6
```

Usar Ancestral Hiram Infusions para probar la barra final de synthesis. Empezar con una por operación.
Cuando quede demostrado que el grado no se sobrepasa, se pueden colocar hasta seis por confirmación.

## Checklist por operación

- [ ] El número correcto de infusiones o scrolls desaparece inmediatamente.
- [ ] El EXP aumenta exactamente una vez.
- [ ] El grado no atraviesa el requerido para awakening.
- [ ] Las tres estadísticas conservan tipo y orden.
- [ ] El Change Attempts permanece en `5/5`.
- [ ] El awakening produce el nombre del tier siguiente.
- [ ] En T5, cada fallo aumenta el pity en 10 puntos porcentuales.
- [ ] Después de relog, template, grado, EXP, pity y estadísticas permanecen iguales.

## Stop points recomendados

Avisar para revisar logs y MySQL en estos puntos:

1. T1 alcanza Celestial, antes del scroll `47926`.
2. Cada awakening exitoso, antes de comenzar a sintetizar el tier siguiente.
3. Cada fallo del scroll `53799`, antes del siguiente intento.
4. Al llegar a T6 Sacred y nuevamente después del relog final.
