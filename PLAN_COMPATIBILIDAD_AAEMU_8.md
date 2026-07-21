# Plan de trabajo: compatibilidad AAEmu 8.0.3.12

## Objetivo

Convertir la rama experimental de AAEmu para el cliente Kakao 8.0.3.12 en una base jugable y verificable, conservando el protocolo 8.0 y reutilizando de forma selectiva la lógica madura de otras ramas.

## Estado inicial confirmado

- Cliente Kakao 8.0.3.12 r558734 de 64 bits conectado correctamente.
- Login, Game y Stream operativos en puertos aislados.
- `game_pak` del cliente 8.0 cargado por el servidor.
- `compact.sqlite3` 3.0.3.0 íntegra y aceptada por el Game Server.
- Creación y entrada al mundo funcionales.
- El servidor recibe skills, calcula daño, muerte, experiencia y loot.
- La rama 8.0 fue publicada como prueba de concepto y todavía contiene estructuras de paquetes incompletas.

## Principio de implementación

No se reemplazará el código 8.0 mediante un merge masivo con 1.2. Cada sistema se dividirá en tres capas:

1. Lógica de servidor reutilizable desde ramas maduras.
2. Datos compatibles entre la compact 3.0.3.0 y el `game_pak` 8.0.
3. Serialización y opcodes específicos del protocolo 8.0.

Cada cambio debe poder probarse de forma independiente y no romper autenticación, entrada al mundo ni sistemas ya validados.

## Fase 1: herramientas de diagnóstico y comandos

### Trabajo

- Corregir todos los errores de compilación de scripts.
- Confirmar que se cargan los comandos registrados.
- Probar un conjunto mínimo: `help`, atributos, posición, items, buffs y teleport.
- Registrar paquetes desconocidos y excepciones con contexto suficiente.

### Criterio de salida

- Cero errores del `ScriptCompiler`.
- Los comandos básicos responden dentro del cliente 8.0.

## Fase 2: circuito mínimo de combate

Antes de iniciar el circuito visual de combate se debe completar la
sincronización incremental de estado. Oro, loot e inventario persisten en el
servidor, pero el cliente 8.0 no refleja los cambios hasta recibir un snapshot
completo al volver a entrar.

### Sincronización incremental prioritaria

1. Cambio de oro mediante `SCItemTaskSuccessPacket`.
2. Creación de un item en un slot vacío.
3. Incremento y reducción de stacks.
4. Movimiento y eliminación de items.
5. Loot completo y consumo de objetos.

El framing, cifrado y contador se validan por separado del payload de cada
`ItemTask`.

### Orden de implementación

1. Autoataque cuerpo a cuerpo.
2. Autoataque con arco y proyectil.
3. Skill instantánea.
4. Skill con tiempo de casteo.
5. Buff y debuff.
6. Daño, muerte, experiencia y loot.

### Paquetes prioritarios

- `CSStartSkillPacket`
- `SCSkillFiredPacket`
- `SCUnitDamagedPacket`
- `SCSkillEndedPacket`
- Paquetes de buffs, proyectiles, estado de unidad y cooldowns.

### Referencias

- Rama 5.0 para correcciones históricas de animación melee y arquería.
- Rama 10.8 para estructuras y comportamientos posteriores.
- Rama 1.2 actual para lógica madura de combate, tiempos, validaciones y autoataque.

### Criterio de salida

- La acción vista por el cliente coincide con el resultado calculado por el servidor.
- Animación, impacto, daño, cooldown y finalización ocurren una sola vez y en orden.

## Fase 3: auditoría de datos 3.0.3.0 frente a 8.0

### Tablas y relaciones prioritarias

- Skills y efectos.
- Buffs y debuffs.
- Animaciones y `fire_anim_id`.
- NPC, skills base y skills aprendidas.
- Items, equipamiento y holdables.
- Quests y recompensas.

### Método

- Inventariar qué datos consume cada manager desde la compact.
- Contrastar IDs con los datos accesibles en el `game_pak` 8.0.
- Mantener la compact 3.0.3.0 cuando los IDs sean compatibles.
- Crear migraciones o una extracción 8.0 solo para las tablas que realmente difieran.

### Criterio de salida

- Informe reproducible de tablas compatibles, incompatibles y todavía no verificadas.
- Sin sustituciones globales de datos basadas únicamente en suposiciones.

## Fase 4: port selectivo de mecánicas

### Prioridad

1. Combate y fórmulas.
2. IA, aggro y movimiento.
3. Inventario, equipo y consumibles.
4. Quests y recompensas.
5. Doodads e interacciones.
6. Housing, comercio, vehículos y sistemas sociales.

### Regla de port

Antes de portar una mecánica se deben identificar:

- Dependencias de código.
- Tablas y columnas requeridas.
- Paquetes C2G y G2C involucrados.
- Diferencias conocidas entre 1.2, 3.0, 5.0, 8.0 y 10.8.

## Fase 5: regresión y estabilidad

- Crear una lista de pruebas por mecánica.
- Conservar capturas de paquetes y logs de un caso correcto.
- Repetir autenticación, lobby y entrada al mundo después de cambios de protocolo.
- Mantener separados los despliegues 1.2, 8.0 y 10.8.
- No declarar una mecánica terminada solo porque no genera excepciones.

## Incidencias iniciales registradas

- Compilación de scripts: constructor obsoleto de `SCChatMessagePacket` en `GetAttribute.cs`.
- Skills procesadas por servidor pero sin animación correcta en cliente.
- `InvalidCastException` al convertir un NPC a `Character` en `DoodadFuncLootItem`.
- Paquete C2G desconocido `0x53` observado durante la sesión.

## Siguiente acción

Completar la Fase 1 y luego capturar una prueba controlada de autoataque para reconstruir `SCSkillFiredPacket` con el formato esperado por el cliente 8.0.
