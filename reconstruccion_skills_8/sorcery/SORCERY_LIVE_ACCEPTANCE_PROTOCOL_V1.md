# Protocolo de aceptación en vivo Sorcery AA8 V1

Cliente: ArcheAge Kakao 8.0.3.12 r558734  
Runtime: `compact-8.0-runtime-transversal-sorcery-v7.sqlite3`  
SHA-256: `6680B69159285BC817732DAD24707BB1A4B2625C77718FEA9A02E72BD8E17159`  
Objetivo: cerrar la última frontera que una auditoría estática no puede probar:
animación, UX, física cliente, repetición y persistencia.

## Preparación

1. Entrar con una sesión limpia y Sorcery aprendida.
2. Tomar una captura de la ventana de skills, MP, Magic Source y barra de
   acciones.
3. Usar primero un NPC aislado que no sea de quest; después un grupo de tres o
   más NPCs.
4. Probar una sola skill nueva por vez. Tras cada una revisar que el personaje
   siga controlable, que el cooldown termine y que no haya desconexión.
5. No usar `/quest force`, matar NPCs de misión ni aceptar recompensas durante
   esta prueba.

## Contratos visibles congelados

Los tiempos son los valores base de la fila AA8. El cliente puede mostrar el
resultado modificado por equipo, buffs y estadísticas.

| ID | Skill | Cast base | Cooldown base | Contrato principal a observar |
|---:|---|---:|---:|---|
| 10151 | Freezing Earth | instantánea | 28 s | AoE alrededor del caster, Ice Shard y Snare; no depende de una probabilidad |
| 10153 | Insulating Lens | 1,5 s | aplicado al terminar el escudo | escudo de 40 s, inmunidad a Trip, explosión/Snare a 6 m y cooldown final de 30 s |
| 10664 | Meteor Strike | 5 s | 28 s | AoE, daño, Trip y desplazamiento angular |
| 10667 | Freezing Arrow | 1,5 s | 6 s | proyectil, daño y reducción de movimiento |
| 10670 | Arc Lightning | 3,2 s | 12 s | daño, Shock y propagación cercana |
| 10752 | Flamebolt | 1 s inicial | cadena sin cooldown intermedio | tres disparos 10752→24894→24895 y Burning |
| 11314 | Frigid Tracks | 2 s | 40 s | rastro, freeze al pisarlo, expiración del rastro |
| 11939 | Searing Rain | 2,5 s | 13 s | área de 10 m, ejecución multi-tick durante 7 s |
| 11967 | Chain Lightning | instantánea | 30 s | hasta cinco saltos, Shock y daño decreciente |
| 12796 | Magic Circle | instantánea | 21 s | doodad, buff dentro del círculo y desaparición |
| 14774 | Flame Barrier | instantánea | 26 s | pared/área, daño periódico, slow y expiración |
| 23593 | Gods' Whip | 1 s inicial | 21 s | cinco pasos, coste/daño creciente y cierre de doodad |

## Secuencia de prueba

### A. Habilidades de objetivo único y cadenas

1. `10667 Freezing Arrow`: confirmar start/fire/end, impacto único, slow y
   cooldown. Repetir tras terminar el cooldown.
2. `10752 Flamebolt`: mantener pulsada la tecla o ejecutar exactamente tres
   usos; confirmar que aparecen las tres etapas, Burning en la primera y que
   la barra no queda bloqueada.
3. `10670 Arc Lightning`: un NPC aislado y luego dos NPCs separados por menos
   de 2 m; confirmar Shock y propagación sin duplicar el daño sobre el caster.
4. `11967 Chain Lightning`: agrupar hasta cinco NPCs; registrar cantidad de
   saltos y que cada salto posterior sea menor que el anterior.

### B. AoE y control

1. `10151 Freezing Earth`: lanzar con NPCs dentro y fuera de 8 m; confirmar que
   sólo los internos reciben Ice Shard y Snare, sin tirada aleatoria, y que el
   caster permanece controlable.
2. `10664 Meteor Strike`: registrar posición inicial/final de un NPC y de un
   personaje objetivo si se dispone de dos clientes. El NPC debe reconciliar
   su posición; el personaje lo mueve el cliente y no debe recibir doble
   desplazamiento.
3. `11939 Searing Rain`: contar ticks durante 7 s, repetir después del cooldown
   y confirmar que `ResetAoEDiminishing` no deja la segunda ejecución inerte.
4. `14774 Flame Barrier`: cruzar la pared con uno y luego varios NPCs; confirmar
   ticks, slow y desaparición sin dejar un área invisible activa.

### C. Buff, recursos y doodads

1. `10153 Insulating Lens`: anotar MP y estado antes/después, confirmar
   inmunidad a Trip, recibir daño controlado, agotar o dejar expirar el escudo
   de 40 s y comprobar explosión/Snare a 6 m y que el cooldown de 30 s comienza
   al finalizar. Repetir tras el cooldown.
2. `11314 Frigid Tracks`: caminar una ruta corta; hacer que un NPC cruce las
   huellas, confirmar freeze y que cada huella desaparezca.
3. `12796 Magic Circle`: comprobar orientación, buff al entrar/salir, duración
   de 20 s, desaparición y segundo uso limpio. Si se prueban las variantes
   ancestrales, Quake y Flame deben usar doodads distintos `14623/14666`.
4. `23593 Gods' Whip`: ejecutar los cinco pasos y anotar MP/daño por paso.
   Confirmar las transiciones de doodad `13406/13407`, timers de 1 s y
   desaparición final; repetir una vez tras el cooldown.

Las 21 filas de grupos, fases, timers, finals y clouts usadas por estas dos
familias ya no son candidatos estructurales 10.x: v6 las decodifica directamente
del `game11` AA8. Sólo cuatro literales de modelo/nombre se resuelven mediante
la fila 10.x estable que conserva la misma referencia AA8.

## Persistencia y repetición

Después de completar las 12 activas:

1. salir a selección de personaje y volver a entrar;
2. confirmar Sorcery, nivel, puntos, pasivas y barra de acciones;
3. repetir Freezing Earth, Searing Rain, Magic Circle y Gods' Whip;
4. cerrar sesión limpiamente, volver a entrar y confirmar que no quedó un
   cooldown permanente, doodad huérfano ni recurso fuera de rango.

## Evidencia mínima por skill

Registrar:

- ID y nombre;
- captura antes/después cuando exista buff, doodad o movimiento;
- daño/ticks visibles;
- MP y Magic Source antes/después;
- cooldown mostrado;
- si start/fire/end, animación, FX y sonido aparecieron;
- resultado del segundo uso y del uso posterior a relog.

Si una skill desconecta, bloquea la barra, duplica movimiento o deja un doodad
persistente, detener esa familia y conservar inmediatamente los logs de Game.
No continuar encadenando pruebas sobre un estado posiblemente corrupto.

## Extensión ancestral V7

Repetir para las familias `19,20,21,40,52,58` con pasos Heir `1..6`:

1. comprobar que aparecen exactamente dos sucesores;
2. activar y lanzar el primero;
3. cambiar al segundo y observar la confirmación visual;
4. comprobar que el anterior ya no se puede lanzar;
5. reloguear y verificar persistencia;
6. resetear por sucesor, por ability y todos;
7. reloguear después de cada tipo de reset.
