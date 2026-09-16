# Estadísticas temporales para pruebas GM

`/stats` (`/gmstats`) requiere acceso 100 y modifica sólo al personaje que lo ejecuta.
Las bonificaciones afectan al cálculo de combate de Game. Se eliminan con `reset` o
al volver a entrar con el personaje; no se guardan en DB ni modifican equipo, buffs,
raza, nivel o puntuación de equipo. La ventana C y los textos de habilidades son
calculados por el cliente y pueden mostrar los valores originales. Usar `show`
y el daño real para comprobar el resultado.

```text
/stats damage 900
/stats set strength 1000
/stats set ranged_power 2500
/stats show
/stats reset ranged_power
/stats reset
```

`set` establece la **bonificación GM adicional**, no la estadística total. Repetirlo
reemplaza el valor anterior. Cero quita la bonificación. `damage 900` configura
`melee_damage`, `ranged_damage` y `spell_damage` con +900 puntos porcentuales cada
uno: un modificador base x1 pasa a x10. Los demás buffs/modificadores conservan
su cálculo habitual; no es una garantía de multiplicar por diez el daño final.
Los efectos de daño fijo o daño de asedio no están incluidos en ese grupo.

`/stats list` muestra nombres y límites:

| Nombres | Unidad y rango |
|---|---|
| strength, agility, stamina, intelligence, spirit | 0–100000 puntos adicionales |
| health, mana | 0–1000000 puntos adicionales al máximo |
| armor, resistance | 0–100000 puntos adicionales |
| melee_power, ranged_power, spell_power, healing_power | 0–100000 puntos de potencia adicionales |
| melee_damage, ranged_damage, spell_damage | 0–10000 puntos porcentuales adicionales |

`show` muestra también el atributo calculado del servidor: las potencias se expresan
internamente en milésimas y los tres modificadores de daño como factores (x1, x10).
No se cura automáticamente: al bajar máximos, sólo se recortan HP/MP si exceden
el nuevo máximo. `/heal` sigue siendo independiente.

## Prueba de Anthalon (quest 10101)

Empezar con `/stats damage 900`, atacar normalmente y dejar de atacar al bajar de
50% para permitir su huida de 6 segundos. No usar `/die` ni buscar una muerte
instantánea: el objetivo espera el efecto de la huida. Al terminar, `/stats reset`.

El comando usa la colección de bonificaciones propia de Character, fuera de los
índices de buffs y equipo; no fabrica un buff ni envía paquetes de refresco de
atributos por conjetura. Las correcciones de HP/MP usan el canal existente de
SCUnitPoints y WZUnitPoints. El cliente no necesita parche.
