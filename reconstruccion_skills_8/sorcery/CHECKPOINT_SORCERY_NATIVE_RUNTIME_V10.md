# Checkpoint Sorcery V10: cierre del carrier AoE de Freezing Earth

Fecha: 2026-08-05  
Cliente autoridad: ArcheAge Kakao `8.0.3.12 r558734`  
Rama: `client_version/8.0.3.12-kakao-r558734-port`

## Resultado

La prueba viva de Freezing Earth (`10151`) descubrió que el runtime V9 no
contenía la forma de área `aoe_shapes:11815`. La skill se aceptaba, reproducía
animación/FX y consumía 256 MP, pero el plot lanzaba `NullReferenceException`
en `WorldManager.GetAroundByShape` antes del daño y de los buffs. El fallo se
reprodujo tanto contra el dummy `13013` como contra un NPC hostil normal, por
lo que no era inmunidad ni relación de facción del objetivo.

V10 restaura la fila AA8 exacta y convierte las formas AoE usadas por plots en
dependencias obligatorias de la auditoría ejecutable. El cierre vuelve a
mostrar 30/30 raíces sin filas ausentes ni blockers.

## Cadena ejecutable reparada

```text
skill 10151 Freezing Earth
  -> plot 3096
  -> events 25974 -> 25975 -> 25976
  -> event 25977 target_update_method_id=5
  -> target_update_method_param1=11815
  -> aoe_shapes 11815 (sphere, radius 8.7)
  -> event 25978 damage effect 10232
  -> hit/effect branch 25981 -> 25980/25979
```

En V9, `GetAreaShapeById(11815)` devolvía `null`; la ejecución se cortaba en
`PlotTargetInfo.UpdateAreaTarget` y no alcanzaba `25978`.

## Autoridad de la fila restaurada

La fila se promueve desde evidencia nativa AA8, no desde propiedades 10.x:

- Stage 60 locator: `stage60:query:6:aoe_shapes`, `row_index=9856`.
- Stage 60 SHA-256:
  `423E8872C8AAAEFA46ABB0E04FB299A17F56722ECDCDF97C2888F7AC9061AB02`.
- SHA de fila AA8:
  `44BC30CE2F95E949DA5DCF52BB16E639DB5AEDF6BFEDE1DB4C84BEE4A4BCE5D2`.
- Crosswalk: `exact_id_exact_relation`, `relation_state=stable`,
  `property_state=exact`, `balance_state=exact_or_absent`.
- Columnas exactas: `adjust_angle`, `area_target_kind_id`, `calc_distance`,
  `kind_id`, `value1`, `value2`, `value3`.
- La fila normalizada 10.x r575 coincide campo por campo y se usa solamente
  como corroboración obligatoria.

Fila AA8:

```json
{"id":11815,"kind_id":1,"value1":8.7,"value2":0.0,"value3":0.0,"adjust_angle":0,"calc_distance":0,"area_target_kind_id":0}
```

La proyección runtime conserva `area_target_kind_id=0` en la columna histórica
del emulador `target_update_method_id`; el loader de `WorldManager` utiliza el
ID, tipo y tres dimensiones, por lo que no se inventa ninguna semántica.

## Corrección de la auditoría

La auditoría V3 recorría roots, plots, eventos, efectos, condiciones, buffs,
triggers, controllers y skills hijas, pero omitía el carrier
`plot_events.target_update_method_param1 -> aoe_shapes.id` para métodos de
target `5/6/7`. Esto permitía un falso cierre estático.

Ahora cada evento de área agrega una arista `area_shape` y exige la fila. La
prueba de control sobre V9 produce exactamente:

```text
blocked_root_count=1
roots_with_blockers=[10151]
missing_rows=[{"table":"aoe_shapes","id":11815}]
```

Sobre V10:

- 43 formas AoE únicas alcanzables, 43 presentes;
- `10151` contiene `aoe_shapes:11815` en su closure;
- `blocked_root_count=0`;
- cero raíces con filas ausentes.

## Artefactos reproducibles

| Artefacto | SHA-256 |
|---|---|
| Runtime V10 | `FB77DC60360C1BF5B9D683C945CD11FCA4736034B75EB16D1C5C4FBBFF065876` |
| Manifiesto V10 | `01107087AE406EDC35EDC262E02D6637F7FCC8546764B1AB64A0699923A435F7` |
| Auditoría ejecutable V3 regenerada | `C4CE11F5B2DDF8DFE666628B3A006CFCC20C3FF8178D94E002987FB8E9EC02C3` |
| Matriz V3 regenerada | `36F9F9D96E6400CF907CDCD4F3E8FA510FA162B422ED2AA6BC018C64940D5604` |

Constructor: `build_sorcery_runtime_v10.py`. La receta congela hashes de V9,
Stage 60, crosswalk y SQLite 10.x, valida las tres fuentes antes de copiar,
inserta una sola fila y ejecuta `quick_check` e `integrity_check`.

## Validación automatizada

- 3/3 pruebas V10: fila exacta, relación del plot y reproducibilidad binaria.
- 9/9 pruebas de auditoría V3, incluida la dependencia `area_shape`.
- Runtime: `quick_check=ok`, `integrity_check=ok`.
- Auditoría: 30 roots, 43 formas AoE, cero blockers y cero filas ausentes.

## Aceptación viva

V10 quedó desplegado read-only como `/app/Data/compact.sqlite3`; el SHA dentro
del contenedor coincide con `FB77DC...65876`. Se conservó la imagen de código
`sha256:0cc7dd0b449bc2474a524f95eb4b61a130acace74adb966e49741c712dba7565`.
Game abrió `2239/2250`, inició Network/StreamNetwork y se registró ante Login
el 2026-08-05 a las `22:52:44` sin errores de carga.

Después de desplegar V10, el usuario confirmó que Freezing Earth funciona
contra un NPC hostil normal. La sesión contiene cuatro ejecuciones completas:

- cuatro `Success`, sin rechazos;
- cuatro recorridos por `25977 -> 25978 -> 25981 -> 25979`;
- daño `506`, `511`, `506` y `508`;
- cuatro aplicaciones de `buff 94` y dos ramas condicionales `25980` con
  `buff 21990`;
- cuatro cierres `plot_ended cancelled=False`;
- cero `PlotTree Main Loop Error`.

El aprendizaje sobrevivió el reinicio de Game y la reconexión del cliente. Se
confirman los tres gates manuales de `10151`: visual/efecto, segunda ejecución
y relog.

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-freezing-earth-after-v10.json
SHA-256: 2E5700E6AF961EE975FE628ED06C9B6A55851CB6B94456BB26DAF65D8A5F1F17

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-freezing-earth-after-v10.csv
SHA-256: 4FD89762C9AD2EC2EF72846A7A0302513F548B9516C17C6144CEB6E0385C0C63
```

Freezing Earth queda cerrada estructural, automatizada y visualmente en V10.

## Preparación de la matriz ancestral — 2026-08-05

Después de aceptar las activas base, se revalidó el sistema Heir sobre la misma
compact V10 sin modificar Honor, medallas, MySQL ni el personaje:

- `heir_levels`: 71 filas, niveles `0..70`, pasos `0..12`;
- seis familias Sorcery y doce sucesores presentes;
- cero successors sin fila `skills`;
- `quick_check=ok`, `integrity_check=ok`;
- 11/11 pruebas focalizadas de protocolo, layouts, selección y nivel efectivo;
- 496/496 pruebas C# de la suite integrada actual;
- el Game activo cargó y postcargó `HeirGameData`, emitió
  `SCHeirSkillListPacket 0x02D` y no registró excepción Heir.

Los pasos Sorcery se abren en Ancestral `1/4/7/10/13/16`. La primera
transición manual queda limitada a Heir `19`, sucesor `36474`, un único cast
contra el dummy `13013`. Se deben revisar lifecycle, coste, daño, active type y
persistencia antes de autorizar el cambio a `36475`. El flujo exacto y sus
puntos de parada están en `SORCERY_LIVE_ACCEPTANCE_PROTOCOL_V2.md`.
