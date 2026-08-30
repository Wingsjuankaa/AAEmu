# AA10 — Prueba completa de progresión Erenor con infusiones y scrolls

## Alcance

Manual práctico para probar un `Erenor Bow` en ArcheAge Returns
`10.0.2.13 r575` contra AAEmu `rama_10`.

La comparación se hizo entre:

- compact efectivo del cliente: SHA-256
  `F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B`;
- compact cargado por Game: SHA-256
  `85024F044F2A0B119776012EE516F90FDD9DB28B4E5581403D40526B1B7D8C65`;
- validadores efectivos `ItemAwakeningCalculator`, `ItemChangeMapping` e
  `ItemEvolving` del servidor.

Las 143 rutas de despertar relevantes, los cinco grupos, los ocho efectos de
scroll, las 169 propiedades de infusión y las cuatro categorías del arco
coinciden entre cliente y runtime.

## Resumen exacto de la ruta del arco

| Etapa | Item | Tramo de síntesis | Grado del scroll | Scroll | Resultado después del éxito |
|---|---:|---|---|---:|---|
| T1 | 43044, Erenor Bow | Arcane `4` → Legendary `10` | Exactamente Legendary `10` | 47032 o 47050 | 47027, Radiant Erenor Bow, continúa en grado `10` |
| T2 | 47027, Radiant Erenor Bow | Legendary `10` → Mythic `11` | Exactamente Mythic `11` | 49173 o 49174 | 48594, Brilliant Erenor Bow, continúa en grado `11` |
| T3 | 48594, Brilliant Erenor Bow | Mythic `11` → Eternal `12` | Exactamente Eternal `12` | 53793 o 53794 | 53095, Refined Erenor Bow, continúa en grado `12` |
| T4 | 53095, Refined Erenor Bow | Eternal `12`, tier final actual | No existe otro scroll r575 | — | Permanece Refined Eternal |

El despertar no reinicia el arco a Arcane. Los grupos tienen
`evolving_exp_inherit='t'` y `target_grade_id=-1`: el servidor convierte el
template y reproduce el XP acumulado sobre la categoría siguiente. Como los
costos previos de estos tiers coinciden, el resultado conserva el grado y el
remanente de la barra.

No es necesario llenar por completo la barra de Legendary/Mythic/Eternal. El
scroll queda habilitado en cuanto el objeto alcanza el grado exacto exigido.

## Grados: lo que muestra el cliente frente a lo que acepta el servidor

| Scroll | Texto del item en el cliente r575 | Mapping aceptado por servidor | Tope efectivo del tier | Veredicto |
|---:|---|---|---|---|
| 47032 / 47050 | Erenor Equipment de Legendary o superior | Grupo 23, `source_grade_id=10` | T1 termina en `10` | Coinciden efectivamente |
| 49173 / 49174 | Radiant Erenor Equipment de Mythic o superior | Grupo 275, `source_grade_id=11` | T2 termina en `11` | Coinciden efectivamente |
| 53793 / 53794 | Brilliant Erenor Equipment de Eternal o superior | Grupo 311, `source_grade_id=12` | T3 termina en `12` | Coinciden efectivamente |
| 49206 | Erenor Cloak de Mythic o superior | Grupo 277, `source_grade_id=11` | Capa T1 termina en `11` | Coinciden efectivamente |
| 52913 | Radiant Erenor Cloak de Mythic o superior | Grupo 305, `source_grade_id=11` | Capa T2 termina en `11` | Coinciden efectivamente |

La frase del cliente “o superior” es más amplia que la igualdad utilizada por
el servidor, pero no crea un rango real adicional: el propio tope de síntesis
impide superar el grado requerido antes de despertar.

Nombres de grado usados por cliente y servidor:

| ID | Nombre r575 |
|---:|---|
| 0 | Basic |
| 1 | Crude |
| 2 | Grand |
| 3 | Rare |
| 4 | Arcane |
| 5 | Heroic |
| 6 | Unique |
| 7 | Celestial |
| 8 | Divine |
| 9 | Epic |
| 10 | Legendary |
| 11 | Mythic |
| 12 | Eternal |

## Scrolls de la progresión principal

Todos consumen una unidad por intento. Los grupos empiezan en 25% de éxito y
agregan 5 puntos porcentuales después de cada fallo: 25%, 30%, 35%, etc.

| Item | Nombre | Skill | Grupo | Labor | Fuente → destino | Temper después del éxito |
|---:|---|---:|---:|---:|---|---|
| 47032 | Erenor Awakening Scroll | 40743 | 23 | 300 | Erenor `10` → Radiant | Pierde aleatoriamente 0–2 por encima de +20; nunca baja de +20 |
| 47050 | Holy Erenor Awakening Scroll | 40750 | 23 | 300 | Erenor `10` → Radiant | Conserva todo el temper |
| 49173 | Radiant Erenor Awakening Scroll | 44397 | 275 | 300 | Radiant `11` → Brilliant | Pierde aleatoriamente 0–2 por encima de +20; nunca baja de +20 |
| 49174 | Blessed Erenor Awakening Scroll | 44421 | 275 | 300 | Radiant `11` → Brilliant | Conserva todo el temper |
| 53793 | Brilliant Erenor Awakening Scroll | 50200 | 311 | 500 | Brilliant `12` → Refined | Pierde aleatoriamente 0–2 por encima de +20; nunca baja de +20 |
| 53794 | Refined Erenor Awakening Scroll | 50201 | 311 | 500 | Brilliant `12` → Refined | Conserva todo el temper |

Los scrolls normales codifican `value2=20`, `value3=0`, `value4=2`. Las
variantes protegidas codifican `0/0/0`.

Para comparar normal contra protegido hacen falta dos arcos equivalentes por
tier. Un arco que ya pasó a Radiant no puede volver a ejecutar el grupo 23.
Para observar la diferencia de temper, ambos objetos deben tener más de +20.

### Scrolls de capa

| Item | Nombre | Skill | Grupo | Labor | Fuente → destino | Éxito |
|---:|---|---:|---:|---:|---|---:|
| 49206 | Erenor Cloak Awakening Scroll | 44423 | 277 | 300 | Erenor Cloak `11` → Radiant Erenor Cloak | 25% + 5% por fallo |
| 52913 | Radiant Erenor Cloak Awakening Scroll | 49283 | 305 | 300 | Radiant Erenor Cloak `11` → Brilliant Erenor Cloak | 25% + 5% por fallo |

El texto de la skill `50200/50201` puede referirse al equipo “Refined” aunque
la fuente seleccionable es Brilliant. El tooltip del item y el mapping del
servidor sí son claros: `48594 Brilliant Erenor Bow` es la fuente y `53095
Refined Erenor Bow` es el destino.

## Infusiones actuales y XP efectivo

### Infusiones universales escalables

Se pueden usar en arma, armadura o accesorio Erenor. La columna es el grado de
la propia infusión, no el grado del arco.

| Item | Nombre | Basic 0 | Crude 1 | Grand 2 | Rare 3 | Arcane 4 | Heroic 5 | Unique 6 | Celestial 7 | Divine 8 | Epic 9 | Legendary 10 | Mythic 11 | Eternal 12 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 48829 | Clear Erenor Infusion | 188 | 0 | 207 | 226 | 244 | 263 | 282 | 301 | 320 | 338 | 357 | 376 | 395 |
| 48830 | Vivid Erenor Infusion | 383 | 0 | 421 | 460 | 498 | 536 | 575 | 613 | 651 | 689 | 728 | 766 | 804 |
| 48831 | Lucid Erenor Infusion | 1.243 | 0 | 1.367 | 1.492 | 1.616 | 1.740 | 1.865 | 1.989 | 2.113 | 2.237 | 2.362 | 2.486 | 2.610 |
| 48832 | Radiant Erenor Infusion | 1.545 | 0 | 1.700 | 1.854 | 2.009 | 2.163 | 2.318 | 2.472 | 2.627 | 2.781 | 2.936 | 3.090 | 3.245 |
| 48833 | Resplendent Erenor Infusion | 1.800 | 0 | 1.980 | 2.160 | 2.340 | 2.520 | 2.700 | 2.880 | 3.060 | 3.240 | 3.420 | 3.600 | 3.780 |
| 48836 | Erenor Infusion | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |

`Crude` es el ID de grado `1`; estas categorías aportan `0 XP` en ese grado.
No debe confundirse con `Basic`, cuyo ID es `0`.

### Infusiones tipadas y aceleradas

| Item | Nombre | Tipo aceptado | Grado útil de la infusión | XP |
|---:|---|---|---|---:|
| 48849 | Erenor Weapon Infusion | Sólo armas | Arcane `4` a Eternal `12` | 2.000 |
| 48850 | Erenor Armor Infusion | Sólo armaduras | Arcane `4` a Eternal `12` | 2.000 |
| 48851 | Erenor Accessory Infusion | Sólo accesorios | Arcane `4` a Eternal `12` | 2.000 |
| 48853 | Mythic Erenor Infusion | Universal | Fijo Mythic `11` | 600 |
| 54329 | Ancestral Erenor Infusion | Universal | Fijo Eternal `12` | 10.000 |
| 48840 | Net Cafe Mythic Erenor Infusion | Universal/evento | Fijo Mythic `11` | 600 |
| 48843 | Net Cafe Eternal Erenor Infusion | Universal/evento | Fijo Eternal `12` | 1.150 |

`48849/48850/48851` aportan `0 XP` en grados `0–3`. Para el arco usar
`48849`, nunca `48850` o `48851`. Las variantes Net Cafe aparecen como `X` en
la localización inglesa y no se recomiendan para el kit normal.

## Cantidades exactas para el arco fabricado

El `Erenor Bow 43044` se fabrica en Arcane `4`, con la barra vacía.

| Tramo | XP que falta al comenzar sin remanente | Con 54329 de 10.000 XP | Con 48849 de 2.000 XP |
|---|---:|---:|---:|
| Arcane `4` → Legendary `10` | 113.626 | 12 | 57 |
| Legendary `10` → Mythic `11` | 45.214 | 4 adicionales gracias al remanente anterior | 23 adicionales gracias al remanente anterior |
| Mythic `11` → Eternal `12` | 59.259 | 6 adicionales gracias al remanente anterior | 30 adicionales gracias al remanente anterior |
| Total T1 Arcane → T3 Eternal | 218.099 | 22 | 110 |

Estas cantidades son exactas para las infusiones indicadas porque sus
categorías tienen bonus XP `0`. El remanente esperado usando `54329` es:

1. después de alcanzar Legendary: 6.374 XP en la barra;
2. después de alcanzar Mythic: 1.160 XP;
3. después de alcanzar Eternal: 1.901 XP.

Detener la síntesis en cuanto aparezca el grado requerido. No es necesario
llenar la barra final antes de usar el scroll.

## Entrega del kit mediante la API administrativa

El siguiente bloque no modifica MySQL directamente. Usar primero `-WhatIf` y
confirmar espacio libre: las infusiones tienen `max_stack_size=1` y cada unidad
puede ocupar una casilla.

```powershell
$erenorCharacter = 'NOMBRE_PERSONAJE'
$giveItems = "$env:USERPROFILE\.codex\skills\aaemu10-native-reconstruction\scripts\give-test-items.ps1"

# Scrolls suficientes para varios fallos. Entregar sólo una variante por ruta
# si se continuará con un único arco.
& $giveItems -Character $erenorCharacter `
  -ItemId @(47032, 47050, 49173, 49174, 53793, 53794) `
  -Count 20 -WhatIf

& $giveItems -Character $erenorCharacter `
  -ItemId @(47032, 47050, 49173, 49174, 53793, 53794) `
  -Count 20

# Etapa T1: entregar sólo 12, sintetizar y liberar espacio.
& $giveItems -Character $erenorCharacter -ItemId 54329 -Count 12 -Grade 12

# Después del primer despertar, etapa T2.
& $giveItems -Character $erenorCharacter -ItemId 54329 -Count 4 -Grade 12

# Después del segundo despertar, etapa T3.
& $giveItems -Character $erenorCharacter -ItemId 54329 -Count 6 -Grade 12
```

Alternativa para probar específicamente la infusión de arma:

```powershell
# Siempre Arcane o superior; a grado Basic aporta 0 XP.
& $giveItems -Character $erenorCharacter -ItemId 48849 -Count 57 -Grade 4
```

No entregar las 110 infusiones tipadas de una vez: su stack máximo es uno.

## Secuencia de aceptación en cliente

### T1 Erenor → T2 Radiant

- [ ] El arco fabricado es `43044 Erenor Bow`, Arcane `4`.
- [ ] La síntesis acepta `54329` o `48849`, y rechaza las infusiones de
  armadura/accesorio `48850/48851`.
- [ ] Al alcanzar Legendary `10`, el cliente habilita `47032` y `47050`.
- [ ] Antes de Legendary, ambos scrolls son rechazados sin consumir scroll ni
  labor.
- [ ] Cada intento válido consume un scroll y 300 labor.
- [ ] Un fallo conserva template, grado y XP, y agrega 5% al próximo intento.
- [ ] Un éxito produce `47027 Radiant Erenor Bow` y conserva grado/remanente.

### T2 Radiant → T3 Brilliant

- [ ] Radiant comienza en Legendary `10`.
- [ ] Al alcanzar Mythic `11`, se habilitan `49173` y `49174`.
- [ ] Antes de Mythic, ambos se rechazan sin mutación parcial.
- [ ] Cada intento válido consume un scroll y 300 labor.
- [ ] Un éxito produce `48594 Brilliant Erenor Bow` en Mythic `11`.

### T3 Brilliant → T4 Refined

- [ ] Brilliant comienza en Mythic `11`.
- [ ] Al alcanzar Eternal `12`, se habilitan `53793` y `53794`.
- [ ] Antes de Eternal, ambos se rechazan sin mutación parcial.
- [ ] Cada intento válido consume un scroll y 500 labor.
- [ ] Un éxito produce `53095 Refined Erenor Bow` en Eternal `12`.
- [ ] Refined queda en su tier final; no debe ofrecer otro despertar r575.

### Comparación de temper

- [ ] Con temper +20 o inferior, el scroll normal no lo reduce.
- [ ] Con temper superior a +20, el scroll normal pierde 0, 1 o 2, sin cruzar
  el piso +20.
- [ ] Holy/Blessed/Refined conserva exactamente el temper previo.
- [ ] Un fallo de despertar no modifica el temper.

## Resultado que debe registrarse

Para cada etapa anotar: template antes/después, grado, XP de barra, temper,
scrolls antes/después, labor, porcentaje mostrado y cantidad de fallos. Si el
cliente ofrece el scroll en un grado distinto de `10/11/12`, si el servidor lo
acepta antes del grado exacto o si el resultado reinicia el grado, registrar
captura y detener la prueba: cualquiera de esos resultados contradice el
contrato r575 documentado aquí.
