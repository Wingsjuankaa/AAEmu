# Battlerage: selección ancestral y extensión de Frenesí

Target `rama_10`, desde `394174370`; padre exacto
`upstream/client_version/zone-10.0.2_r575`, inspeccionado en `7851f67cc`.
No se integraron nuevos commits ni se modificaron los timings de cadenas aceptados
en `f8af778cf`.

## Causas comprobadas

**Ancestrales.** `474f400a4a` añadió la comprobación de habilidades aprendidas
en `ZoneAuthorityHandle`. Las raíces ancestrales se guardan como selecciones
en `heir_skill_activations`, no como habilidades aprendidas. La ruta local ya
reconocía esa diferencia, pero la de Zone rechazaba la selección activa.
El cambio entró en nuestra integración `29d68e3f2` del 18 de septiembre.
Los logs del 20 muestran el rechazo de `36401` y `36404` de Dannia, después de
superar el control de selección ancestral.

Se admite `IsActiveHeirSuccessor` en ese gate. Las variantes no seleccionadas,
un caster ajeno, los hijos sin predecesor aceptado y el GCD siguen rechazándose.
El arreglo es general para selecciones ancestrales; las pruebas nuevas cubren
las dos cadenas de Triple Slash, en las rutas local y Zone.

**Frenesí.** `ec45f7f4f` activó el camino Extend de `OverwriteWith`, que antes
no se alcanzaba. La posterior incorporación de `MaxLifeTime` en `7e384e538`
limitaba la aplicación entrante, pero no la suma de la extensión. Además,
`Template.Start` enviaba otra creación con la duración acumulada, aunque el
cliente la interpreta como una aplicación adicional; `NotifyUpdated` ponía
después el tiempo transcurrido a cero.

El buff de Dannia, índice 62, creado a las 16:02:55 UTC, se retiró a las
16:06:35: unos 220 segundos. No era una prueba de que todo el scheduler de
buffs estuviera detenido; otros índices sí caducaban en ese intervalo.

## Contrato r575

`10455` aplica `182`, `22690` o `22689` según nivel. Los tres tienen duración
20.000 ms, Extend (5), máximo de tiempo restante 40.000 ms, stack máximo 1
y tick 0. El trigger KillAny (22) reaplica el mismo buff. Se conservaron
los datos, condiciones y efectos del cliente.

Binario x64 inmutable `x2game.dll.pre_auroria.bak`, SHA-256
`2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76`,
base `0x39000000`. [Anclajes reproducibles](buff-extension-native-anchors.json):

| RVA | Contrato observado |
|---|---|
| `0xabf110` | Reader Updated: índice, stack, charge, elapsedTime i32, reason u8. |
| `0x346460` → `0x6c5c00` | Updated escribe elapsed en instancia +0x40; no modifica lifetime +0x3c. |
| `0x34c810` → `0x6c93c0` | Created resuelve la unidad y aplica el BuffData. |
| `0xbd5260` | Regla 5: lifetime += duración entrante; si supera el máximo restante, lifetime = elapsed + máximo. Conserva elapsed. |

Reanclar con `python audit_buff_extension.py <ruta del binario inmutable>`.
Las decompilaciones se reproducen con el helper versionado
`../scripts/ghidra/DecompileAddressAndXrefs.java <VA>` sobre el proyecto
`AA10X2GameRelease`, `-readOnly -noanalysis`. Los logs íntegros se conservan
en el directorio de evidencias y sus hashes están en el JSON.

## Implementación

Extend conserva su origen temporal y limita **lo que queda**, no la duración
total desde ese origen. La creación SC lleva sólo la duración de la nueva
aplicación. No se envía el Update que reseteaba el reloj. Los snapshots de
UnitState conservan duración total y tiempo transcurrido coherentes.

Zone suprime las creaciones repetidas con el mismo stack y su Update no lleva
lifetime. Para la extensión se reutiliza la retirada/creación ya existente,
con el tiempo restante completo, el mismo índice y la protección que exige
una creación previa. No se cambió el protocolo ni se envían retiradas a una
Zone que no recibió esa instancia.

`qainspect self|target` añade índice, stack, duración, origen, tiempo restante,
estado y procedencia de cada buff para documentar la prueba sin modificarlo.

## Validación automatizada

Restore y build Release correctos; **5.511 pruebas, cero fallos**.
Cuatro casos de selección/cadena ancestral (dos fallaban antes en Zone).
Tres casos de Frenesí ejecutan AddBuff real, diez extensiones, el modelo del
consumidor nativo sobre los paquetes emitidos, el reemplazo WZ y un deadline
antiguo; una expiración final debe emitir exactamente una retirada SC/WZ.
Las pruebas existentes de Extend comparan ahora el tiempo restante, puesto
que el origen temporal ya no se reinicia. Refresh y permanente siguen cubiertos.

## Prueba real con Dannia: 20 de septiembre, 16:36–17:01 UTC

Cliente r575 es_ES full preview, Zone 142 `w_solzreed_1`, personaje 1007 / objeto
1066, nivel 55 y ancestral 40. Doce activas de Battlerage aprendidas, seis pasivas,
Archery 1/12, Shadowplay 6/12 y un punto libre. Equipo y habilidades aprendidas
conservados. Objetivos efímeros creados con `/spawn npc dummy` (NPC 7512).
El dummy lleva buffs permanentes 6613 y **1250, inmunidad de control**.

Los lanzamientos de esta tabla se realizaron desde el cliente (barra/libro),
excepto el ensayo adicional del límite de Frenesí, identificado expresamente.
Las cifras de daño son observaciones de ese equipo/objetivo, no una certificación
comparativa de las fórmulas. Los tiempos son UTC; Chile = UTC−3.

| Caso | Evidencia observada | Alcance / pendiente |
|---|---|---|
| Triple Slash Rayo | 16:37:52–54, 36401 → 36402 → 36403; daños 1269/2129/1380 y finalización | Tres entradas reales admitidas. No certifica todas las sinergias ni área. |
| Triple Slash Terremoto | 16:43:28–31, 36404 → 36405 → 36406; daños 4182/2528/4661, plots 2855/2856/2857 terminados | Ambas variantes que estaban rechazadas ahora se ejecutan. |
| Whirlwind Slash | 16:43:47–50, 13282 → 32040 → 32049; daños 1816/4794/3680 y cooldown visible tras el tercero | Regresión de tres etapas superada; varios enemigos pendiente. |
| Carga | 16:36:56, 11918; movimiento 2,0 → 0,8 m, daño 2541 y finalización | Falta toda la matriz de rangos/obstáculos/pasiva. |
| Hendir la tierra | 16:46:20–21, 10644; canalización visible, plot 649, daño 4861 | Área y variantes no certificadas. |
| Golpe preciso | 16:49:51, 12026; daño 5396 | No se compararon frontal/espalda ni variantes. |
| Golpe del tigre | 16:49:30, 13315; movimiento 2 → 0 m, daño 3610, plot 17 finalizado | Un objetivo; selección sucesiva/multitarget pendiente. |
| Concentración de combate | 16:56:08, 10377; buff 7651, 20 s; retirada WZ 16:56:28 | 7651 corresponde al efecto 37079, tramo 41–70. No se certifican todos los modificadores. |
| Rugido aterrador | 16:45:03, 18308 admitido, animación y creación propia índice 51 | Área, obstáculos y todos los debuffs no certificados. |
| Romper ataduras | Sin root: rechazo de requisitos; con root 82 aplicado por GM desde el dummy, 16:59:01: desaparece antes de su deadline | 82 pertenece al tag 27 exigido por DispelEffect 2633. Habilidad real 12034 ejecutó la limpieza; no fue una retirada GM. |
| Tras las líneas enemigas | 16:57:38, 23587; destino demasiado cercano rechazado; segundo destino ejecuta salto/aterrizaje; dummy queda a 14,2 m | **Advertencia real:** shape 5047 sin radio provoca fallback de 40 m. Salto probado; área de impacto no aceptada. |
| Martillo | 16:56:39, daño 3136 con inmunidad. Retirada GM temporal de 1250; 16:58:01 daño 9858 sin stun observado; repetición 16:59:23 daño 5893 + buff 22532 índice 4, retirado 16:59:26 | Hay un caso positivo a 14,2 m y uno discrepante: no se certifica el gate de impacto. Ver nota siguiente. |
| Endless Arrow | 17:00:02–04, 14835 → 14836 → 14837; daños 2428/2433/2425 y plots terminados | Regresión adicional de repetición. 10082 es Stealth; no confundir su ID con Endless Arrow. |

El stun 22532 observado duró 2580 ms. La fila r575 contiene base 1500 ms **más
20 ms por nivel**, por lo que la anterior descripción «1500 ms» era incompleta.
No se cambió esa fórmula. El gate `ConditionCombatDiceResult` vuelve a tirar
`RollCombatDice` y sustituye `HitTypes`, en vez de limitarse a consultar el
resultado ya producido. Es una frontera existente que puede explicar diferencias,
pero **esta sesión no demuestra su causalidad ni autoriza inventar una máscara**.
Cerrar el consumidor nativo y la relación con DamageEffect antes de corregirlo.
La inmunidad 1250 del dummy se restauró al finalizar el ensayo.

### Frenesí: reloj, extensión y desaparición

- Cast real 16:46:38.699: buff 22689 índice 53, 20.000 ms; contador visible,
  retirada WZ a las 16:46:58 y ausencia posterior tanto en UI como en `qainspect`.
- Cast real 16:50:16.570: índice 59. Cuatro muertes GM controladas de dummies
  dispararon KillAny a las 16:50:17, 16:50:43, 16:51:15 y 16:51:17. Se mantuvieron
  índice y origen temporal; la última observación fue Duration 99.996 ms,
  Remaining 38.714 ms, coherente con UI. Retirada final 16:51:56; captura posterior
  `frenzy-extended-expired.png` sin buff. Las parejas WZ Remove/Create durante la
  extensión son reemplazos del temporizador, no expiraciones anticipadas.
- Ensayo controlado adicional con `resetcd self` + `useskill 10455` y dos muertes
  GM consecutivas: índice 65, origen 16:55:39.922, Duration 42.442 ms, Remaining
  39.598 ms a las 16:55:42.765; UI **39 s**. Se alcanzó realmente el límite nativo
  de 40 s restantes; retirada final WZ 16:56:22. No se usó este comando GM como
  prueba del gate de aprendizaje ancestral.
- En intentos previos, la muerte llegó después de los 20 s: se conservan en el
  log y no se cuentan como pruebas de extensión. No se añadió ningún temporizador
  para facilitar la prueba.

### Límites y estado al salir

No se certifican Battlerage completo, todas las variantes de otras habilidades,
inmunidades PvP, combos, pasivas con parry, ni corrección exacta de daños. La matriz
mantiene esos pendientes, incluyendo el área 5047 y la repetición del dado del
martillo. Los datos AA8 no sustituyeron ningún contrato r575.

La comparación SQL de sólo lectura tras cerrar sesión confirma que `skills` y
`heir_skill_activations` son idénticas al inicio: Rayo 36401 restaurado y ningún
hijo de cadena aprendido. Dos cambios ancestrales por UI costaron 4 oro 30 plata
en total. Las nueve muertes GM otorgaron honor (24.400 → 26.200) y experiencia a
esta cuenta de pruebas; no se revirtió su base de datos. No hubo cambios de equipo.
Los dummies son efímeros. El cliente 26824 salió por Alt+F4; el worker CMD 53652,
ZoneHost 32116 y consola 60248 quedaron cerrados, verificación posterior sin ningún
`archeage.exe` ni `AAEmu.ZoneHost.exe`. Docker conserva la corrección desplegada.
La desconexión Zone registrada a las 17:02:02 corresponde a esta limpieza.

Evidencias completas fuera de Git: capturas, `gameplay-world.log`,
`gameplay-commands.jsonl`, comparación del personaje y logs de build/tests.
El manifiesto `ancestral-frenzy-manifest.json` fija sus hashes. Las advertencias de
TowerDef sin spots y quest 4321 sin rank reward se conservan como ajenas a esta
corrección; no se presentan como resueltas.

## Despliegue y rollback

Imagen preparada `b8085e5ae54f0b9138c5f3d9822a5123f00f80e8176d82aad534b267b5350b25`.
DLL Linux en `/app` y `/app/game`:
`8f91eed7c42988a5bd43c494f7061436efbf217fb74cd63aa343ffcb6c2b6b23`.
Compact montada sin cambios:
`85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
Rollback conservado: `aaemu-world:rollback-pre-ancestral-frenzy-20260920`,
imagen `783ac1533c8437b5a2723d08fce93070e8c4cb1137b0f4f5eb25aa6f73b2be1f`.
Evidencias locales: `E:\AAEmu\rama_10\artifacts\battlerage-ancestral-frenzy-20260920`.
