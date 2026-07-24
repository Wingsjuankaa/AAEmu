# Reconstrucción de pasivas Battlerage AA8

## Autoridad

Esta fase usa, en orden:

1. compact descifrada del cliente AA8;
2. resultados nativos de `game11`;
3. layouts confirmados en `x2game.dll`;
4. comportamiento observado con el cliente local.

La compact 3.0 no aporta valores de gameplay. Las relaciones que el cliente
describe pero no materializa en `game11` se identifican explícitamente como
`server_derived`.

## Matriz de las seis pasivas

| Puntos | Pasiva | Buff raíz | Cadena AA8 | Implementación |
|---:|---|---:|---|---|
| 3 | Deflect and Retaliate | 2610 | Parry → buff 2611 → reset de tags de cooldown Battlerage | Cadena existente reparada para los tres cooldown tags; supresión de 12 s data-driven |
| 4 | Reckless Charge | 7542 | Skills con condición/tag 1476 → buff 7543 durante 4 s | Modificadores nativos `IncomingMeleeDamageMul=-150` e `IncomingRangedDamageMul=-150` |
| 5 | Physical Penetration | 2621 | Crítico melee → 2622 → skill interna 16185 → 2624/26966 | -3000 armor con 2H, -1000 en caso contrario; supresión de 12 s data-driven |
| 6 | Attack Speed Training | 811 | Impacto dañino de skill tag 415 → efecto 56457 → buff proc 11344 | Nueva primitiva genérica `passive_procs`; ICD 1 s; hasta 5 stacks de 9 s |
| 7 | Weapon Mastery | 831 | Modificador nativo de skills tag 415 | +10% Damage mediante `skill_modifiers` AA8 |
| 8 | Weapon Training | 7544 | Modificadores del buff y condición de arma | +6 pp melee crit; ranged parry con dual wield o arma 2H |

## Datos nativos incorporados

- `skill_modifiers`: 1571 filas recuperadas del resultado cacheado de
  `game11`, loader `x2game.dll FUN_39979330`.
- Weapon Mastery:
  `owner=Buff:831, attribute=Damage:10, tag=415, type=Percent, value=10`.
- Buff proc de Attack Speed Training `11344` (distinto del Frenzy activo `22689`):
  - duración 9000 ms;
  - máximo 5 stacks;
  - `MeleeCriticalBonus +50` = +5 puntos porcentuales por stack;
  - `AttackSpeedMul +30` por stack.
  - proc nativo de 5% para aplicar Bleeding al objetivo golpeado.
- Weapon Training `7544`:
  `MeleeCriticalMul +60` = +6 puntos porcentuales.
- Reckless Charge `7543`:
  - daño físico melee recibido -15%;
  - daño físico ranged recibido -15%.
- Physical Penetration:
  - `2624`: armor -3000;
  - `26966`: armor -1000.

## Cuarentena explícita

El catálogo contiene nueve modificadores cuyo resultado depende de un buff o
tag del objetivo. Se conservan en la compact con su procedencia nativa, pero el
backend no los ejecuta todavía porque `ApplySkillModifiers` no recibe contexto
del objetivo. También se ignoran owners distintos de `Buff`.

Esto evita aplicar bonificaciones condicionales como si fueran incondicionales.

## Artefactos reproducibles

- Extractor:
  `extract_native_skill_modifiers.py`
- Catálogo:
  `native-skill-modifiers-aa8.json`
- Generador:
  `build_battlerage_passives_runtime.py`
- Manifiesto:
  `passives-runtime-manifest.json`
- Runtime:
  `compact-8.0-runtime-native-combat-passives-v1.sqlite3`

Dos generaciones independientes deben producir el mismo SHA-256. El generador
exige además:

- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- cero modificadores históricos para los roots 811 y 7544;
- relación exacta de Weapon Mastery;
- relación exacta de Attack Speed Training;
- supresión de 12 segundos para 2610 y 2621.

## Protocolo de prueba

1. **Deflect and Retaliate**
   - activar `/combatstat set melee_parry 100`;
   - poner en cooldown skills de ataque Battlerage;
   - recibir un ataque melee frontal;
   - verificar reset completo;
   - comprobar que no vuelve a dispararse durante 12 s.
2. **Reckless Charge**
   - medir daño físico recibido;
   - usar Charge, Tiger Strike y Behind Enemy Lines por separado;
   - durante 4 s debe reducirse 15%;
   - después debe volver exactamente a la base.
3. **Physical Penetration**
   - activar `/combatstat set melee_crit 100`;
   - criticar con dual wield/1H y comprobar -1000 armor;
   - criticar con 2H y comprobar -3000 armor;
   - verificar supresión de 12 s.
4. **Attack Speed Training**
   - impactar repetidamente con skills Battlerage;
   - el buff proc `11344` debe apilar una vez por segundo, hasta 5;
   - cada stack aporta +5 pp de daño crítico melee y +30 attack speed;
   - tras 9 s sin renovar deben desaparecer.
5. **Weapon Mastery**
   - comparar la misma skill Battlerage con y sin la pasiva;
   - el daño base de la skill debe aumentar 10%;
   - skills fuera de Battlerage no deben cambiar.
6. **Weapon Training**
   - confirmar +6 pp de melee crit;
   - con parry controlado al 100%, permitir parry ranged con dual wield y 2H;
   - no permitirlo sin una de esas configuraciones de arma.

Al terminar: limpiar overrides con `/combatstat clear all`.

## Corrección transversal de agentes y condiciones de triggers

Durante la primera prueba se observó que Bleeding se aplicaba repetidamente al
dueño del buff proc `11344`. La traza confirmó dos defectos del ejecutor histórico:

- `target_agent_id=2` se ignoraba y el efecto regresaba al dueño del buff;
- las condiciones `owner/source/target_buff_tag_id` y sus variantes negativas
  se ignoraban, ejecutando simultáneamente las cinco etapas de Bleeding.

El runtime ahora transporta `event source` y `event target` en eventos Attack y
Damage, y resuelve:

- `0`: owner;
- `1`: event source;
- `2`: event target;
- `3`: original source.

Antes de ejecutar el efecto también valida los tags requeridos y excluidos para
owner, source y target. Así se conserva el proc AA8 de 5%, pero sólo se aplica
al enemigo y avanza una etapa válida de Bleeding en vez de disparar todas.
