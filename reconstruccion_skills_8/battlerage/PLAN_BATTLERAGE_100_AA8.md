# Plan de cierre funcional de Battlerage — ArcheAge 8.0

## Objetivo

Dejar Battlerage funcional al 100% contra el cliente Kakao 8.0.3.12
`r558734`, cerrando una habilidad a la vez. El core transversal de habilidades
se considera la base disponible, no el resultado final: cada habilidad debe
respetar los datos, relaciones y comportamiento que el cliente 8.0 define.

No se crearán animaciones, FX, sonidos, desplazamientos, tiempos, fórmulas,
buffs ni combos alternativos. Los recursos ya existen en el cliente; el trabajo
del servidor es cargar las relaciones 8.0 correctas, ejecutar sus primitivas y
emitir el protocolo que activa esos recursos.

## Orden de autoridad

1. `compact-client-8.0-decrypted.sqlite`.
2. Resultados nativos recuperados de `game11`.
3. Consumidores, layouts y comportamiento confirmado en `x2game.dll`.
4. Paquetes y comportamiento observados contra el cliente local.
5. `develop` y la compact 3.0 sólo como referencia de implementación.

Una fila histórica puede ayudar a identificar una primitiva, pero nunca puede
reemplazar un valor 8.0 ni presentarse como evidencia 8.0.

## Alcance canónico

El catálogo se deriva automáticamente de los datos recuperados del cliente y
no de una lista escrita a mano. La línea base actual contiene:

- 42 filas Battlerage en `skills`, incluidas habilidades visibles, auxiliares,
  cadenas y variantes ancestrales;
- 12 habilidades aprendibles y visibles con costo de punto;
- 6 pasivas nativas;
- habilidades automáticas visibles de costo cero y filas internas necesarias;
- todas las relaciones alcanzables de efectos, buffs, plots, controladores,
  animaciones y proyectiles.

La matriz generada debe distinguir explícitamente:

- habilidad raíz visible;
- pasos internos de una cadena;
- variantes ancestrales;
- habilidades auxiliares invocadas por efectos;
- pasivas y buffs asociados;
- dependencias compartidas con otras especialidades.

## Definición de “100%” por habilidad

Una habilidad sólo puede marcarse completa cuando cumple todos los puntos que
le correspondan según los datos 8.0:

1. Aparece, se aprende y consume puntos en el nivel correcto.
2. Persiste tras relog y conserva su posición en la barra.
3. Valida objetivo, relación, distancia, altura, terreno, arma y recursos.
4. Respeta mana, costo especial, GCD, cooldown, repeticiones y cancelación.
5. Emite inicio, casteo, disparo, impacto, transición y fin correctos.
6. Activa las animaciones, FX, sonidos, proyectiles y controladores nativos.
7. Ejecuta exactamente sus daños, curas, buffs, debuffs, dispels y plots.
8. Respeta condiciones, probabilidades, tags, stacks, combos y sinergias.
9. Ejecuta cadenas, desplazamientos y variantes sin bloquear otras skills.
10. Replica el resultado completo a un segundo cliente.
11. Funciona repetidamente, después de relog, muerte y cambio de zona.
12. No corrompe memoria, MySQL, barras, especialidades ni estado de combate.

Si el cliente describe una conducta cuya primitiva aún no está confirmada, la
habilidad queda bloqueada y documentada; no se reemplaza por una aproximación.

## Flujo obligatorio por habilidad

### A. Reconstrucción de datos

- Construir la clausura:
  `skill → skill_effect → effect → concrete effect → buff → relaciones`.
- Incluir plots completos, eventos, condiciones, AoE, eventos siguientes,
  controladores, animaciones, proyectiles y habilidades encadenadas.
- Comparar esa clausura con la compact runtime y enumerar filas ausentes o
  históricas antes de modificar el backend.
- Generar dos veces el artefacto y exigir hashes idénticos.

### B. Cobertura del backend

- Mapear cada tipo de efecto y condición a una implementación existente.
- Si falta una primitiva, identificar primero su layout y consumidor en el
  cliente o una captura observable.
- Implementar la primitiva de forma genérica y añadir pruebas unitarias.
- No crear excepciones por ID salvo que el propio cliente tenga una bifurcación
  confirmada para ese ID.

### C. Protocolo y presentación

- Confirmar los serializadores que consume el cliente para inicio, ejecución,
  plot, controladores, impacto, daño y finalización.
- Añadir regresiones byte a byte cuando cambie un paquete.
- Verificar con un segundo cliente que la presentación no sea sólo local.

### D. Prueba de aceptación

- Probar la habilidad aislada sobre un objetivo controlado.
- Probar todas sus condiciones y variantes alcanzables.
- Repetirla varias veces y reloguear.
- Ejecutar regresión de login, barras, cambio de especialidad, loot,
  consumibles y una habilidad Battlerage ya cerrada.
- Revisar logs, memoria del cliente/servidor y persistencia MySQL.

## Orden de ejecución de Battlerage

El orden se decide por dependencias, no por comodidad:

1. **Triple Slash**: cadena básica completa y sus variantes ancestrales. Es el
   primer corte porque valida daño, buffs, cambio de skill, repetición, GCD,
   plots de área y animaciones encadenadas.
2. **Charge** y sus auxiliares: controlador de movimiento, objetivo y fin.
3. Habilidades de daño/área que reutilizan las primitivas ya validadas.
4. Buffs propios, liberaciones y controles.
5. Movilidad y plots complejos.
6. Habilidades automáticas de costo cero y auxiliares internas.
7. Seis pasivas y sus relaciones completas.
8. Variantes ancestrales restantes, después de cerrar su habilidad raíz.

La matriz generada fijará el orden exacto de los puntos 3 a 8 sin inferir IDs.

## Primer corte: Triple Slash

El cierre incluye al menos las filas raíz/internas `18132`, `18134`, `18131`
y las variantes `36401` a `36406`, además de cualquier dependencia alcanzada
por sus efectos o plots.

La auditoría inicial detectó que la runtime actual conserva relaciones
históricas para `18131/18132/18134`, pero no contiene las relaciones nativas
de `36401–36406`; los plots `2855–2857` tampoco tienen sus eventos. Por ello:

1. Generar una compact Fase 4 partiendo de la runtime estable actual.
2. Insertar únicamente la clausura Battlerage confirmada desde datos 8.0.
3. Validar `quick_check`, `integrity_check`, huérfanos y cobertura del backend.
4. Comparar Triple Slash raíz y ancestral antes/después, campo por campo.
5. Desplegar sólo el contenedor `game` después de respaldo y build limpio.
6. Ejecutar la prueba de aceptación de la cadena de tres golpes.

## Artefactos y control de cambios

- Carpeta: `reconstruccion_skills_8/battlerage/`.
- Manifiesto de clausura: `generated/battlerage-phase4-closure.json`.
- Matriz humana: `MATRIZ_BATTLERAGE.md`.
- Compact versionada: `compact-8.0-runtime-phase4-battlerage-vN.sqlite3`.
- Informe por habilidad con evidencia, estado y prueba realizada.
- Cada lote tendrá hash de entrada/salida y una ruta de rollback.

No se sobrescriben la compact descifrada, `game11`, la compact estable previa
ni el `game_pak`. La compact Docker sólo cambia después de pasar validaciones.

## Criterio de cierre de la especialidad

Battlerage se marca completa cuando todas las habilidades visibles, cadenas,
variantes alcanzables y seis pasivas cumplen la definición de 100%, no quedan
dependencias desconocidas dentro de su clausura y pasa la regresión completa
con uno y dos clientes.
