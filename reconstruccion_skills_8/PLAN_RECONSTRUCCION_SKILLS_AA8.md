# Plan de reconstruccion de habilidades para ArcheAge 8.0

## Objetivo

Reconstruir el sistema de especializaciones, habilidades activas y pasivas de
ArcheAge 8.0.3.12 sobre AAEmu mediante un motor comun orientado por datos. Se
utilizara Battlerage como primera especializacion y corte vertical reutilizable
para las demas ramas.

El objetivo no es codificar cada habilidad manualmente. La meta es adaptar el
backend para interpretar correctamente los datos 8.0 y limitar el codigo
especifico a los tipos de efecto o mecanicas que realmente sean nuevos.

## Contexto confirmado

- Cliente: Kakao 8.0.3.12 r558734.
- Rama: `client_version/8.0.3.12-kakao-r558734-port`.
- Compact del cliente descifrada:
  `D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite`.
- Compact utilizada por el runtime:
  `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-loot-hybrid.sqlite3`.
- Comparacion existente:
  `D:\Proyectos\AAemu\client_kakao\compact-3-vs-8-comparison.json`.
- Analisis estatico de `x2game.dll`:
  `E:\AAEmu-Research\output\ghidra-static`.
- El paquete de barras de accion 8.0 utiliza 217 ranuras. Esto fue confirmado
  directamente en el serializador del cliente.
- La activacion de Shadowplay demostro que el backend historico puede aceptar
  habilidades incompatibles con el nivel de la rama y producir niveles
  invalidos. Por ello, la progresion debe estabilizarse antes de implementar
  efectos individuales.

## Fuentes de verdad

Se utilizara el siguiente orden de autoridad:

1. Compact descifrada del cliente 8.0.
2. Serializadores y estructuras confirmadas en `x2game.dll`.
3. Trafico y comportamiento observado con el cliente 8.0 conectado al AAEmu
   local.
4. Notas historicas y wiki correspondientes a la version 8.0, como validacion
   del comportamiento visible.
5. Compact 3.0, rama `develop` y otras ramas de AAEmu, solamente como
   referencia de implementacion.

La wiki no se utilizara como fuente primaria para tiempos, IDs, animaciones,
relaciones entre efectos o estructuras de red. Esos datos deben proceder del
cliente 8.0.

## Politica de implementacion

- No inferir campos, anchos, cantidades ni orden de paquetes.
- Confirmar las estructuras en el cliente antes de modificar serializadores.
- Cambiar una sola capa o hipotesis por prueba.
- Crear un respaldo de MySQL antes de cualquier migracion persistente.
- No reutilizar directamente tablas 3.0 sin registrar su procedencia.
- No hardcodear una habilidad si la mecanica puede representarse mediante
  datos y un tipo de efecto comun.
- Conservar registros de paquetes durante el desarrollo y retirarlos o bajar
  su nivel al cerrar cada etapa.
- Cada correccion debe incluir una prueba de relog y, cuando corresponda, una
  prueba con un segundo cliente.

## Arquitectura objetivo

El sistema se separara en tres capas:

### 1. Datos 8.0

Responsable de cargar y relacionar, como minimo:

- `skills`;
- `skill_effects`;
- `effects`;
- efectos concretos de dano, curacion, buff y efectos especiales;
- buffs y sus efectos;
- controladores de habilidades;
- reactivos y productos;
- tags, sinergias y condiciones;
- animaciones, proyectiles, tiempos, alcance y costes.

Cada tabla del runtime debera indicar si procede del cliente 8.0, del compact
de servidor antiguo o de una adaptacion generada.

### 2. Protocolo 8.0

Responsable de representar exactamente:

- seleccion e intercambio de especializaciones;
- experiencia y nivel de las ramas;
- aprendizaje, reinicio y mejora de habilidades;
- inicio, casteo, disparo, impacto y fin de una habilidad;
- cooldowns, barras, buffs, dano y resultados;
- sincronizacion inicial y posterior al relog.

### 3. Runtime de mecanicas

Responsable de:

- validacion de objetivo, rango, arma y recursos;
- calculo autoritativo;
- aplicacion de dano, curacion, buffs y debuffs;
- movimiento, cargas, teletransportes y control;
- areas de efecto;
- combos, procs, pasivas y condiciones;
- tareas temporizadas, canalizaciones y repeticion;
- replicacion hacia observadores.

## Fase 0: congelar una linea base estable

### Acciones

- Confirmar que el personaje restaurado puede entrar dos veces consecutivas.
- Confirmar apertura de inventario, habilidades y menu principal.
- Confirmar una habilidad basica, loot y uso de un objeto.
- Guardar un dump de MySQL estable.
- Registrar el hash de compact, `game_pak`, imagen Docker y commit.
- Crear un commit o tag identificable antes de iniciar la reconstruccion.

### Criterio de salida

El cliente puede entrar, salir y volver a entrar sin cierre, fuga de memoria ni
estado persistente inconsistente.

## Fase 1: catalogo automatico y procedencia

### Entregable principal

Crear un extractor reproducible que genere:

```text
reconstruccion_skills_8/generated/
  compact-table-provenance.json
  battlerage-skill-manifest.json
  battlerage-skill-manifest.md
  effect-coverage.json
  effect-coverage.md
```

### Contenido del manifiesto por habilidad

- ID y nombre traducido disponible.
- Especializacion.
- Nivel y puntos requeridos.
- Nivel base y paso de escalado.
- Coste de mana u otros recursos.
- GCD, cooldown, casteo, canalizacion y repeticiones.
- Objetivo, relacion, alcance, angulo y area.
- Animaciones, FX, proyectil y controlador.
- Cadena completa `skill -> skill_effect -> effect -> efecto concreto`.
- Buffs y debuffs relacionados.
- Tags, sinergias, requisitos y consumos.
- Clases del backend necesarias.
- Estado: compatible, adaptacion necesaria, no implementado o desconocido.

### Criterio de salida

Todas las habilidades activas y pasivas de Battlerage estan enumeradas y cada
efecto referenciado tiene una procedencia y un estado de implementacion.

## Fase 2: nucleo de especializaciones 8.0

Esta fase debe completarse antes de reconstruir efectos individuales.

### Trabajo requerido

- Confirmar el mapa numerico de las especializaciones.
- Confirmar el algoritmo de experiencia y nivel de rama.
- Confirmar puntos disponibles y requisitos de aprendizaje.
- Corregir aprendizaje, rechazo, reinicio e intercambio.
- Confirmar los paquetes de exito y error esperados por el cliente.
- Corregir guardado y carga de habilidades y pasivas.
- Garantizar que un fallo no pueda abortar toda la transaccion del personaje.
- Validar barras de accion despues de aprender, retirar o cambiar una rama.
- Confirmar la ventana de habilidades inmediatamente y tras reloguear.

### Pruebas minimas

1. Activar una segunda rama sin aprender habilidades.
2. Salir y volver a entrar dos veces.
3. Aprender una habilidad valida.
4. Intentar una habilidad no disponible.
5. Reiniciar la rama.
6. Cambiar la rama por otra.
7. Repetir los relogs y comprobar MySQL despues de cada operacion.

### Criterio de salida

No existen diferencias entre el estado mostrado por el cliente, la memoria del
servidor y MySQL.

## Fase 3: corte vertical de Battlerage

En lugar de implementar todas las habilidades seguidas, se elegira una muestra
que cubra las primitivas del motor:

1. Ataque instantaneo de dano.
2. Habilidad con casteo.
3. Carga o movimiento.
4. Area de efecto.
5. Buff propio.
6. Debuff o control aplicado al enemigo.
7. Pasiva.
8. Combo condicionado por buff o estado.
9. Canalizacion, toggle o repeticion, si Battlerage dispone de ella.

Por cada caso se implementara primero la primitiva generica. Las habilidades
posteriores que compartan esa primitiva deberan definirse principalmente por
datos.

### Criterios de aceptacion por habilidad

- Se muestra al nivel correcto.
- Se puede aprender y desaprender.
- Persiste despues de reloguear.
- Permanece en la barra de accion.
- Valida objetivo, distancia, arma y recursos.
- Emite inicio, casteo, disparo, impacto y fin correctos.
- Reproduce animacion, sonido y efectos visuales.
- Aplica el resultado autoritativo esperado.
- Activa correctamente combos, procs y pasivas.
- Es visible para un segundo cliente.
- No deja cooldowns, tareas o casteos bloqueados.

## Fase 4: completar Battlerage

- Implementar las habilidades restantes por familias de efectos.
- Comparar resultados con el comportamiento historico 8.0.
- Documentar excepciones que no puedan representarse mediante el motor comun.
- Ejecutar pruebas de regresion sobre las habilidades ya terminadas.
- Probar muerte, resurreccion, cambio de zona y reconexion durante buffs o
  cooldowns.

### Criterio de salida

Battlerage completo puede utilizarse durante una sesion normal y despues de
relogs sin divergencias persistentes.

## Fase 5: expansion a las demas especializaciones

Orden sugerido:

1. Shadowplay, para validar de inmediato la segunda rama que produjo el fallo.
2. Defense o Auramancy, para ampliar buffs y mitigaciones.
3. Sorcery, para proyectiles, casteos y areas.
4. Vitalism, para curaciones y objetivos amistosos.
5. Archery, para distancia, movimiento y autoataques.
6. Las ramas restantes, agrupadas segun primitivas aun no cubiertas.

Cada especializacion reutilizara el extractor, matriz de cobertura, pruebas y
criterios definidos para Battlerage.

## Herramientas de prueba recomendadas

- Comando `/skilltest <skillId>` para iniciar una prueba controlada.
- Comando para otorgar o retirar temporalmente una habilidad sin persistirla.
- Muneco de entrenamiento con registro de dano, buffs, resistencias y tiempos.
- Captura de paquetes filtrada por personaje y skill ID.
- Comparacion automatica entre memoria del servidor y tablas MySQL.
- Pruebas unitarias para calculos y validaciones.
- Pruebas doradas para serializadores confirmados.
- Dos clientes para verificar replicacion y efectos observables.

## Riesgos principales

### Compact hibrida

Una tabla 8.0 puede depender de otra tabla que todavia proceda del servidor
3.0. Se debe generar y revisar el mapa de procedencia antes de interpretar un
valor como definitivo.

### IDs con significado distinto

Un mismo ID o enum puede cambiar de significado entre versiones. No se
portaran enums por nombre sin confirmar sus valores en 8.0.

### Efectos visuales frente a resultados autoritativos

Que el cliente reproduzca una animacion no demuestra que el servidor haya
aplicado correctamente el efecto, y viceversa. Ambos resultados deben probarse
por separado.

### Persistencia parcial

Todos los cambios de especializacion, habilidades y barras deben guardarse en
una transaccion coherente y validar sus rangos antes de escribir.

### Fuentes historicas variables

Una wiki actual puede reflejar balance posterior a 8.0. Toda diferencia debe
resolverse a favor de la compact y el cliente r558734, salvo que se documente
explicitamente una correccion custom.

## Primera tarea al reanudar

Implementar el extractor de la Fase 1 sin modificar todavia el runtime:

1. Enumerar las habilidades activas y pasivas de `ability_id = 1`.
2. Recorrer todas sus relaciones de efectos.
3. Comparar los tipos concretos con las clases existentes en
   `AAEmu.Game/Models/Game/Skills/Effects`.
4. Generar los cuatro informes de manifiesto y cobertura.
5. Revisar manualmente una habilidad simple y una compleja para validar el
   extractor.
6. Con esos resultados, seleccionar la primera habilidad del corte vertical.

Esta primera tarea es de solo lectura sobre las compact y no requiere reiniciar
el servidor ni modificar el personaje.

La ejecución de esta tarea para Battlerage y el procedimiento para repetirla
con otras especializaciones están documentados respectivamente en
`FASE_1_RESULTADOS.md` y `GUIA_REPETIR_FASE_1_ESPECIALIZACIONES.md`.

La implementación técnica de la fase 2, la compact derivada reproducible y el
protocolo de aceptación están documentados en `FASE_2_RESULTADOS.md`.

## Definicion de terminado del proyecto

- Las especializaciones se seleccionan, progresan y persisten correctamente.
- Todas las habilidades y pasivas 8.0 estan catalogadas.
- Los tipos de efecto utilizados tienen una implementacion compatible o una
  excepcion documentada.
- Las habilidades cumplen los criterios funcionales y de red.
- Las pruebas de relog, segundo cliente y persistencia son repetibles.
- Las compact originales permanecen intactas y toda adaptacion es
  reproducible.
