# Deflect and Retaliate — reinicio de cooldown AA8

## Síntoma

Al producirse un parry, la pasiva Deflect and Retaliate se activaba y
reiniciaba correctamente Charge y Whirlwind Slash, pero Sunder Earth
continuaba en cooldown.

## Evidencia nativa AA8

La cadena recuperada desde el catálogo AA8 es:

```text
buff pasivo 2610
  -> combat_buff 23 (hit_type 7: parry)
  -> buff 2611
  -> buff_trigger 1379
  -> effect 15029
  -> special_effect 4643 (ResetCooldown)
  -> value1 = skill 10644 (Sunder Earth)
```

La pasiva sí solicitaba reiniciar Sunder Earth. La diferencia está en la fila
nativa de la habilidad:

```text
Charge 11918       cooldown_tag_id = 0
Sunder Earth 10644 cooldown_tag_id = 4156
Whirlwind 13282    cooldown_tag_id = 0
```

El backend enviaba el reinicio por `skill_id`, pero no el reinicio del grupo
compartido `4156`. Por eso el cliente mantenía Sunder Earth deshabilitada.

## Corrección transversal

- `SkillTemplate` carga los tres grupos nativos:
  `cooldown_tag_id`, `second_cooldown_tag_id` y
  `third_cooldown_tag_id`.
- `Character.ResetSkillCooldown` reinicia el ID y todos los tags no nulos de la
  habilidad.
- `Character.ResetAllSkillCooldowns` aplica la misma regla y elimina tags
  duplicados.
- No existe una lista especial para Battlerage ni para esta pasiva.
- La traza `AA8CooldownReset` informa el skill y los tags resueltos.

## Prueba de aceptación

1. Ejecutar `/combatstat set melee_parry 100`.
2. Usar Charge, Whirlwind Slash y Sunder Earth para dejarlas en cooldown.
3. Recibir de frente un ataque melee.
4. Confirmar la activación visual de Deflect and Retaliate.
5. Verificar que las tres habilidades quedan disponibles.
6. Confirmar en el log:

```text
AA8CooldownReset ... skill=10644 tags=[4156]
```

La pasiva conserva su cooldown interno nativo de 12 segundos; una segunda
tirada dentro de esa ventana no debe volver a reiniciar las habilidades.
