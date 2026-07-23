# Implementación Battle Focus y estadísticas de combate AA8

## Resultado

La primera etapa está desplegada sobre el runtime estable:

- carga de `unit_attribute_id` como `UInt16`;
- conservación de `unit_modifiers.value` como `Int64` en la plantilla;
- soporte explícito y aislado de `dynamic_value`;
- aplicación y retiro trazable de los cuatro buffs de Battle Focus;
- resolución común de probabilidades para comando, críticos y tiradas de combate;
- overrides GM en memoria, sin persistencia;
- limpieza automática de overrides al relog o desconexión;
- comando `/combatstat` restringido a nivel GM 100.

La compact nativa de estadísticas fue generada y validada, pero no está activa
en esta primera prueba:

`D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-combat-stats-v1.sqlite3`

SHA-256:

`8F123CD3F039054477EA9E1957F71E65026359F61F9571427CF275D2706962CA`

Dos construcciones independientes produjeron ese mismo hash. La copia de
verificación se eliminó después de comparar para recuperar 138.129.408 bytes.

## Datos nativos confirmados

La extracción desde `game11`, según el loader `FUN_3997ab60` de
`x2game.dll`, produjo:

- 49.095 modificadores;
- 149 filas con `dynamic_value`;
- atributos hasta el ID 261;
- cero filas de `unit_modifiers` tomadas de la compact 3.0.

Battle Focus:

| Buff | Parry (atributo 81) | Daño crítico melee (atributo 17) |
| --- | ---: | ---: |
| 404 | +28 puntos | +15 puntos |
| 7651 | +30 puntos | +20 puntos |
| 13612 | +32 puntos | +25 puntos |
| 13613 | +34 puntos | +30 puntos |

Para Dannia con 7,8% base, el buff `7651` debe producir:

`7,8% → 37,8% → 7,8%`

## Comandos de prueba

```text
/combatstat show
/combatstat show target
/combatstat set melee_parry 100
/combatstat set melee_crit 100
/combatstat clear melee_parry
/combatstat clear all
```

Estadísticas admitidas:

```text
melee_accuracy
ranged_accuracy
spell_accuracy
melee_crit
ranged_crit
spell_crit
heal_crit
melee_parry
ranged_parry
block
dodge
```

Los valores válidos son 1–100. El servicio también rechaza valores fuera de
rango aunque se lo invoque fuera del comando. Los overrides no modifican
equipo, buffs, compact ni MySQL.

## Trazas

- `AA8BattleFocus`: valor nativo, nivel, parry y daño crítico antes/después.
- `AA8CombatDice`: atacante, objetivo, tipo de daño, chequeo, porcentaje,
  tirada y resultado.

No se añadió un paquete de refresco de Character Info por suposición. La UI se
considerará confirmada sólo si el cliente muestra 7,8 → 37,8 → 7,8. Aunque la
ventana no refresque, `/combatstat show` y las trazas permiten separar el
cálculo autoritativo del problema visual.

## Validaciones realizadas

- compilación local: correcta;
- pruebas: 69/69;
- scripts runtime: 0 errores;
- servidor: iniciado y escuchando en 2239/2250;
- `PRAGMA quick_check`: `ok`;
- `PRAGMA integrity_check`: `ok`;
- runtime nativo determinista: confirmado.

El cambio de `.env` hacia la nueva compact se hará sólo después de la prueba
vertical de Battle Focus y parry melee frontal al 100%.
