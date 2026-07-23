# Auditoría transversal de estadísticas AA8

## Resultado

El runtime activo usa:

`compact-8.0-runtime-native-combat-stats-v2.sqlite3`

SHA-256:

`BCC563B22201B51A7280B9EB3C1E01780AA2E999625874205EE725ECB57206DE`

La compact contiene:

- 49.095 modificadores de unidad nativos;
- 480 fórmulas nativas;
- 3.600 variables nativas de fórmula;
- cero filas históricas en `unit_modifiers`;
- cero fórmulas históricas en `unit_formulas`;
- cero variables históricas en `unit_formula_variables`.

Dos construcciones independientes produjeron el mismo SHA-256. `quick_check`
e `integrity_check` devolvieron `ok`.

## Fuentes

| Datos | Fuente | Confirmación |
| --- | --- | --- |
| `unit_modifiers` | `game11` | `x2game.dll` `FUN_3997ab60` |
| `unit_formulas` | `game11` | `x2game.dll` `FUN_39a73350` |
| `unit_formula_variables` | `game11` | `x2game.dll` `FUN_39a730a0` |
| Fórmula visible | datos estructurados y cliente local | Character Info de AA8 |

No se usó la compact 3.0 para generar estos tres dominios.

## Cambios transversales

- El evaluador admite `log`, requerido por tres fórmulas AA8.
- `heir_level` usa `Character.HierLevel`; los tipos antiguos que aún no
  modelan nivel ancestral usan cero de forma explícita.
- Precisión usa la fórmula AA8 `BaseMissPercent` en lugar del 10% histórico
  codificado en C#.
- Crítico, parry, ranged parry, block y dodge usan sus fórmulas AA8.
- Los bonos de daño crítico parten de las fórmulas AA8 35, 36, 37 y 44, no
  de una constante C#.
- El ataque aportado por las estadísticas se obtiene exclusivamente desde
  `MeleeDpsInc`, `RangedDpsInc`, `SpellDpsInc` y `HealDpsInc`.
- `Dps`, `RangedDps`, `MDps` y `HDps` representan el aporte del arma; ya no
  duplican el aporte de Strength, Agility, Intelligence o Spirit.
- Las curaciones consumen `HDps + HDpsInc`, manteniendo la separación nativa
  entre arma y aporte de estadística.

## Verificación con Dannia

Valores observados:

- nivel 55;
- Strength 189;
- Agility 212;
- Stamina 174;
- Intelligence 199;
- Spirit 172;
- sin nivel ancestral.

Resultados nativos sin bonos temporales:

| Estadística | Resultado AA8 | UI observada |
| --- | ---: | ---: |
| Parry | 7,7669% | 7,8% |
| Dodge | 2,3232% | 2,3% |
| Magic Attack aportado por Intelligence | 49,75 | 49,75 |
| Healing Power aportado por Spirit | 43,00 | 43,00 |
| Armor base aportada por Stamina | 174 | incluida en 856 |
| Magic Resist base aportado por Spirit | 172 | incluido en 1.122 |

Con Battle Focus rango 2:

- Parry: 7,7669% → 37,7669%;
- Melee Critical Damage: 50% → 70%.

## Matriz de estado

| Grupo | Datos AA8 | Fórmula AA8 | Consumidor servidor | Estado |
| --- | --- | --- | --- | --- |
| Atributos primarios | sí | sí | `Character` | activo |
| HP, MP y regeneración | sí | sí | `Character` | activo |
| Ataque melee/ranged/magic/heal | sí | sí | daño/curación | activo |
| Armor y Magic Resist | sí | sí | daño y UI | activo |
| Accuracy | sí | sí | tiradas de impacto | activo |
| Critical Rate | sí | sí | daño/curación | activo |
| Critical Damage | sí | sí | daño/curación | activo |
| Parry, Ranged Parry, Block, Dodge | sí | sí | tiradas defensivas | activo |
| Cast Time y Move Speed | sí | no requieren `unit_formula` | skill/movimiento | modificadores activos |
| Resilience, Toughness y penetración | sí | no requieren `unit_formula` | daño | modificadores activos |
| Daño recibido por tipo | sí | sí, cuando corresponde | `DamageEffect` | activo |
| Fórmulas kind 47–68 sin consumidor actual | sí | sí | pendiente de identificar | aisladas |

“Pendiente de identificar” no activa un fallback histórico. Las fórmulas se
conservan nativas y compiladas, pero no se les asigna una semántica inventada.

## Prueba en cliente

1. Entrar con Dannia y ejecutar `/combatstat show`.
2. Comparar Melee Parry y Dodge con la ventana `C`.
3. Activar Battle Focus rango 2.
4. Abrir `C` y confirmar Parry aproximado de 37,8%.
5. Ejecutar nuevamente `/combatstat show` y confirmar el mismo valor.
6. Esperar 20 segundos y verificar el regreso exacto al valor base.
7. Probar ataques y curaciones antes y después de equipar un arma para
   confirmar que el aporte del arma no duplica el aporte del atributo.

## Validación de despliegue

- 70/70 pruebas automatizadas superadas.
- 480/480 fórmulas compiladas sin errores.
- scripts compilados con 0 errores y 2 advertencias históricas.
- Game Network en 2239 y Stream Network en 2250.
- Game registrado correctamente en LoginServer.

Permanece un `InvalidCastException` histórico de `DoodadFuncLootItem`
(`Npc` a `Character`). No está relacionado con las estadísticas ni con esta
compact.
