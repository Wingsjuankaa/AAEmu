# Estadísticas de combate nativas AA8

Este directorio reconstruye `unit_modifiers` desde el resultado cacheado por el
cliente Kakao 8.0 en `game11`. La compact 3.0 no participa en la extracción.

## Fuente confirmada

`x2game.dll`, función `FUN_3997ab60`, carga:

```sql
SELECT owner_type, owner_id, dynamic_value, linear_level_bonus,
       unit_attribute_id, unit_modifier_type_id, value
FROM unit_modifiers
WHERE enable = 't'
```

El resultado nativo contiene 49.095 filas. `value` es de 64 bits y los IDs de
atributo llegan hasta 261. `BonusTemplate` conserva el valor exacto como
`Int64` y `UnitAttribute` usa `UInt16`. Las propiedades antiguas de `Unit`
continúan siendo de 32 bits: sólo tres modificadores nativos exceden ese rango
y se saturan en el límite de aplicación, sin alterar el valor almacenado ni el
manifiesto. Esta deuda queda aislada y no afecta Battle Focus.

`dynamic_value` sólo aparece en 149 filas de los atributos de recurso de combate
215 y 221. Su layout está confirmado, pero no se interpreta como un bono fijo:
queda preservado y aislado hasta reconstruir su evaluador específico.

## Flujo reproducible

```powershell
python extract_native_combat_stats.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --output generated\native-unit-modifiers-v1.json `
  --verify

python extract_native_unit_formulas.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --output generated\native-unit-formulas-v1.json `
  --verify

python build_native_combat_stats_runtime.py `
  --runtime-carrier D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-combat-v2.sqlite3 `
  --catalog generated\native-unit-modifiers-v1.json `
  --formula-catalog generated\native-unit-formulas-v1.json `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-combat-stats-v2.sqlite3 `
  --manifest generated\native-combat-stats-v2.manifest.json `
  --verify
```

La construcción debe repetirse con un segundo nombre de salida. Ambos archivos
deben producir el mismo SHA-256 antes del despliegue.

## Matriz visible

| UI / prueba | Atributos AA8 | Backend | Consumidor | Estado |
| --- | --- | --- | --- | --- |
| Precisión melee | 18 / 78 | `MeleeAccuracy` | `Skill.RollCombatDice` | fórmula y modificadores AA8 |
| Precisión ranged | 23 / 83 | `RangedAccuracy` | `Skill.RollCombatDice` | fórmula y modificadores AA8 |
| Precisión magic | 28 / 88 | `SpellAccuracy` | `Skill.RollCombatDice` | fórmula y modificadores AA8 |
| Crítico melee | 16 / 77 | `MeleeCritical` | `DamageEffect` | override y consumo reparados |
| Crítico ranged | 25 / 82 | `RangedCritical` | `DamageEffect` | override y consumo reparados |
| Crítico magic | 30 / 86 | `SpellCritical` | `DamageEffect` | override y consumo reparados |
| Crítico heal | 174 / 185 | `HealCritical` | `HealEffect` | override y consumo reparados |
| Daño crítico melee | 17 | `MeleeCriticalBonus` | `DamageEffect` | Battle Focus confirmado |
| Parry melee | 22 / 81 | `MeleeParryRate` | `Skill.RollCombatDice` | fórmula AA8 y Battle Focus confirmados |
| Parry ranged | 153 / 154 | `RangedParryRate` | `Skill.RollCombatDice` | fórmula y modificadores AA8 |
| Block | 177 / 179 | `BlockRate` | `Skill.RollCombatDice` | fórmula y modificadores AA8 |
| Dodge | 178 / 180 | `DodgeRate` | `Skill.RollCombatDice` | fórmula y modificadores AA8 |

Las fórmulas no aparecen en la SQLite descifrada, pero sí en el resultado
nativo cacheado de `game11`. Sus loaders y layouts fueron confirmados en
`x2game.dll` (`FUN_39a73350` y `FUN_39a730a0`). El runtime v2 sustituye las
357 fórmulas y 3.009 variables heredadas por 480 fórmulas y 3.600 variables
AA8. Las 480 compilan en el arranque y no existe fallback de `unit_formulas`
a 3.0.

La activación se divide deliberadamente en dos pasos:

1. desplegar instrumentación y `/combatstat` sobre el runtime estable;
2. cambiar a `compact-8.0-runtime-native-combat-stats-v2.sqlite3` sólo después
   de verificar Battle Focus y parry controlado en el cliente.

El loader admite temporalmente runtimes sin la columna `dynamic_value` y la
interpreta como cero. Esto permite probar el primer paso sin reemplazar la
compact activa. No convierte filas históricas en datos nativos ni altera el
artefacto AA8 generado.

## Cobertura de Character Info / Details

El catálogo JSON relaciona las estadísticas probabilísticas y sus consumidores
de combate. El resto de la ventana se clasifica así:

| Grupo visible | Atributos AA8 principales | Estado |
| --- | --- | --- |
| Fuerza, agilidad, stamina, inteligencia, espíritu | 0–4 | fórmulas y modificadores AA8 |
| Ataque melee, ranged, magic y healing | 96/33, 98/34, 87/35, 173/175 | aportes AA8 separados del arma |
| Defensa física y mágica | 8, 64 | fórmulas y modificadores AA8 |
| Velocidad de movimiento y casteo | 10, 71 | modificadores AA8; consumidores existentes |
| Velocidad de ataque | 54, 55, 119, 218 | layout AA8 confirmado; integración transversal pendiente |
| Precisión, crítico, parry, block y dodge | 16–31, 77–88, 153–185 | cargados y conectados a combate |
| Resilience y reducción crítica | 182, 183 | propiedades existentes; semántica de UI pendiente de prueba |
| Daño recibido melee/ranged/magic/siege | 58, 142–149 | modificadores y consumidores existentes |
| Daño PvE recibido | 199–202 | AA8 confirmado; consumidor anti-NPC pendiente |
| Penetración física y mágica | 57, 184 | propiedades existentes |

“Pendiente” significa que no se usó una fórmula 3.0 como sustituto. El
manifiesto conserva esa clasificación para continuar la reconstrucción desde
`x2game.dll`.

## Battle Focus

Para un personaje en el rango del buff `7651`:

- atributo 81, valor 300: `+30` puntos porcentuales de parry;
- atributo 17, valor 200: `+20` puntos porcentuales de daño crítico melee;
- duración nativa: 20 segundos.

El servidor registra `AA8BattleFocus` al aplicar y retirar el buff. Las tiradas
relevantes se registran como `AA8CombatDice`. El comando `/combatstat` permite
forzar temporalmente probabilidades entre 1% y 100%; nunca persiste datos ni
altera buffs, equipo o compact.
