# Línea de desarrollo — AAEmu para Kakao 8.0.3.12

## Propósito

Este documento define cómo desarrollar y validar la rama
`client_version/8.0.3.12-kakao-r558734-port`. Su objetivo es convertir la
prueba de concepto en un servidor jugable sin mezclar datos, lógica y protocolo
de versiones distintas de forma accidental.

La regla principal es trabajar por mecánicas completas o **cadenas verticales**.
Una función no se considera reparada solo porque el servidor no arroje una
excepción o porque el cambio aparezca después de volver a entrar.

## Arquitectura actual

El despliegue combina tres fuentes diferentes:

1. **Cliente Kakao 8.0.3.12 r558734:** define lo que el cliente conoce y
   espera: IDs, relaciones, tiempos, animaciones, estructuras y protocolo.
2. **Compact servidor 3.0.3.0:** aporta tablas y datos autoritativos que el
   cliente no contiene.
3. **Código AAEmu:** implementa las reglas del servidor y serializa los
   paquetes específicos de 8.0.

La base montada por `aaemu8-game-1` es una compact híbrida generada, no la
compact descifrada directamente:

```text
D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-loot-hybrid.sqlite3
```

La ruta se configura mediante `COMPACT_DB` en `.env` y se monta como
`/app/Data/compact.sqlite3`.

## Política obligatoria de protocolo: no inferir

En esta rama queda prohibido modificar un paquete de red únicamente por
similitud con otra versión de AAEmu. Las ramas `develop`, 1.2, 3.0, 5.0, 8.0
experimental y 10.8 sirven para formular hipótesis, pero no constituyen por sí
solas evidencia del protocolo Kakao 8.0.3.12 r558734.

Antes de cambiar un paquete C2G, G2C, C2S o S2C se debe confirmar en el cliente
8.0, según corresponda:

- opcode y canal de transporte;
- orden exacto de los campos;
- ancho y tipo de cada campo;
- codificación especial (`BC`, `PISC`, posición, fecha, string o bitset);
- campos condicionales y la condición que los habilita;
- cantidad de elementos, stride y tamaño total consumido;
- respuesta o transición que el cliente envía después de procesarlo.

Se acepta como evidencia, de mayor a menor fuerza:

1. Deserializador o serializador identificado directamente en `x2game.dll`
   r558734, conservando dirección y pseudocódigo relevante.
2. Captura binaria completa de una sesión correcta del mismo cliente, con los
   límites del paquete y sus campos reproducibles.
3. Comparación controlada donde una única variación produce una respuesta
   inequívoca del cliente y coincide con el consumo observado en el binario.

La compact descifrada confirma datos e IDs, pero no demuestra por sí sola el
layout de un paquete. Los comentarios heredados y la ausencia de excepciones
tampoco cuentan como confirmación.

Si todavía no existe evidencia suficiente, el cambio permitido es añadir
instrumentación, capturar datos o continuar el análisis estático. No se debe
alterar el payload de producción para "probar suerte". Cada ensayo debe cambiar
una sola variable de protocolo, conservar una ruta de reversión inmediata y
registrar el resultado antes del siguiente cambio.

Los niveles de confianza C y D definidos más adelante pueden usarse para datos
o lógica autoritativa, pero no para declarar correcto un layout de red. Un
paquete solo se considera compatible cuando está confirmado con evidencia A.

## Expediente de incidente: corrupción de estado de personaje (2026-07-21)

Durante las pruebas de consumibles acumulados, barras de acción y selección de
una segunda especialidad, el personaje `Wingsjuanka` dejó de poder entrar al
mundo. La pantalla de carga alcanzaba el 100 % y el proceso del cliente se
cerraba voluntariamente pocos segundos después de recibir `SCUnitStatePacket`.

Se descartaron las siguientes causas:

- El protector de memoria no cerró el proceso: el último intento se estabilizó
  alrededor de 4,18 GiB y no registró `limit-exceeded` ni `taskkill`.
- Windows no registró un crash nativo ni un evento WER para ese cierre.
- `SCUnitStatePacket`, `SCActionSlotsPacket`, `CharacterAbilities` y el stream
  de doodads coincidían con el baseline del branch.
- El contenedor no conservaba variables `AAEMU_DIAGNOSTIC_*`.

La cuenta 1 contenía dos personajes: `Dannia` (id 1), con una cancelación de
borrado inconsistente, y `Wingsjuanka` (id 2). Se respaldó `aaemu_game` y se
eliminaron transaccionalmente ambos personajes junto con sus datos dependientes
de habilidades, especialidades, inventario, opciones, quests y portales. La
cuenta y sus créditos se conservaron. Un personaje creado desde cero pudo entrar
al mundo correctamente, confirmando que la falla estaba acotada al estado
persistido de los personajes y no al protocolo global ni al cliente.

Respaldo recuperable:

```text
E:/AAEmu-Research/backups/aaemu_game_before_character_wipe_20260721-161033.sql
SHA-256: 9748087C9BFE5A122153E5B6614DA4970D15E48E1C2F5453F45BAC6481B2BC67
```

La columna o registro exacto que causó la corrupción no quedó identificado; no
se debe atribuir todavía a barras o especialidades de forma individual. Para
futuras pruebas que modifiquen estado persistente:

1. Crear un respaldo de `aaemu_game` antes del ensayo.
2. Cambiar una sola mecánica y probarla con un personaje desechable.
3. Si la carga vuelve a cerrarse al 100 %, comparar inmediatamente con un
   personaje nuevo antes de modificar paquetes de inicialización.
4. Conservar el personaje afectado o un dump selectivo si se quiere aislar la
   fila exacta; no borrar la evidencia antes de compararla.

## Fuentes de investigación

Los artefactos originales y generados se mantienen fuera del repositorio para
no versionar binarios grandes.

### Cliente y compact descifrada

Directorio base:

```text
D:/Proyectos/AAemu/client_kakao
```

Archivos principales:

- `compact-client-8.0-encrypted.sqlite`: archivo original extraído del cliente.
- `compact-client-8.0-decrypted-container.zip`: contenedor descifrado fiel con
  los doce streams `game*`.
- `compact-client-8.0-decrypted.sqlite`: vista SQLite reconstruida para
  investigación y consultas.
- `compact-3-vs-8-comparison.json`: comparación estructural entre versiones.
- `INFORME_COMPACT_8.md`: algoritmo, validación y límites del descifrado.
- `INFORME_LOOT_COMPAT_8.md`: reconstrucción compatible del loot autoritativo.
- `COMPACT_8_SHA256.txt`: hashes de los artefactos conocidos.

La vista `compact-client-8.0-decrypted.sqlite` permite investigar el cliente,
pero **no debe montarse directamente como compact del servidor**. No contiene
todas las tablas ni los datos autoritativos que AAEmu necesita.

### Herramientas reproducibles

Directorio:

```text
D:/Proyectos/AAemu/client_kakao/compact_research
```

- `compact_decrypt.py`: reproduce el descifrado del contenedor.
- `build_research_sqlite.py`: construye la vista SQLite de investigación.
- `build_loot_compatibility.py`: genera las compact cliente, servidor y runtime
  híbridas.
- `scan_inputs.py`, `analyze_pak_reads.py`, `filter_procmon.py` y
  `extract_procmon_stacks.py`: apoyo para análisis estático y dinámico.
- `ghidra_scripts/`: automatizaciones empleadas durante el análisis de
  `x2game.dll`.

### Baselines

- Compact cliente 3.0 utilizada como base completa:
  `D:/Proyectos/AAemu/client_kakao/compact.sqlite3`.
- Compact servidor heredada:
  `D:/Proyectos/AAemu/rama_kakao/.server_files/kakao-assets/compact.server.sqlite3`.
- Código estable de referencia: rama `develop` del repositorio principal.
- Otras ramas se pueden consultar para conocer estructuras históricas, pero no
  se deben portar archivos completos sin revisar versión de datos y protocolo.

## Qué información aporta la compact descifrada

La compact del cliente permite confirmar, entre otras cosas:

- IDs y atributos de items, skills, effects y buffs.
- Relaciones `item → skill → effect`.
- Tiempos de casteo, cooldowns, animaciones y parámetros visibles.
- Contenido consultado por folios, quests, NPC y sistemas del cliente.
- Nombres y textos localizados.

No garantiza disponer de:

- Loot autoritativo completo.
- Reglas económicas privadas.
- Validaciones antiexploit.
- Lógica de eventos, instancias o progresión ejecutada solo por el servidor.
- Estructura exacta de todos los paquetes de red.

Cuando falte información autoritativa se debe, en este orden:

1. Buscar implementación compatible en `develop`.
2. Relacionar datos heredados mediante IDs estables y evidencia verificable.
3. Reconstruir la regla a partir de paquetes, logs y comportamiento observable.
4. Marcar claramente cualquier inferencia o aproximación.

## Flujo obligatorio para reparar una mecánica

### 1. Definir el caso reproducible

Registrar:

- Personaje y nivel.
- Item, skill, NPC o doodad implicado.
- Acción exacta realizada.
- Resultado esperado y resultado observado.
- Si el cambio aparece después de reloguear.
- Captura y hora aproximada para correlacionar logs.

### 2. Identificar la cadena del cliente

Consultar la compact descifrada para seguir las relaciones relevantes. Para una
skill o consumible, el recorrido normal es:

```text
item
→ use_skill_id
→ skills
→ skill_effects
→ effects
→ tabla del tipo concreto de efecto
→ dato autoritativo o regla del servidor
```

No se deben asumir IDs de 3.0 cuando el cliente 8.0 entrega otros.

### 3. Seguir la ejecución en AAEmu

Comprobar separadamente:

```text
paquete C2G recibido
→ lectura de campos
→ handler
→ validación
→ skill/interacción
→ efecto o manager
→ estado en memoria
→ persistencia MySQL
→ paquete G2C
→ representación del cliente
```

Una transición puede fallar aunque el estado inicial y final sean correctos.
Por ejemplo, el servidor puede descontar labor y persistir dinero, pero el
cliente puede no mostrar casteo ni actualizar el inventario si el paquete G2C
está incompleto.

### 4. Clasificar el cambio

- **Dato de cliente incompatible:** incorporarlo mediante el generador de la
  compact híbrida.
- **Dato autoritativo ausente:** heredarlo o reconstruirlo con procedencia
  explícita.
- **Lógica faltante:** portarla selectivamente desde `develop` o implementarla
  en el manager/efecto correspondiente.
- **Protocolo incorrecto:** corregir el opcode o la serialización para
  r558734; no copiar a ciegas un paquete de 1.2 o 10.8.
- **Estado persistente:** modificar MySQL mediante una migración reproducible,
  nunca confundirlo con contenido estático de la compact.

### 5. Validar la cadena completa

Una mecánica está terminada únicamente cuando cumple todo lo siguiente:

- La acción se ve correctamente en el cliente.
- Ocurre una sola vez y en el orden esperado.
- El servidor aplica el resultado correcto.
- Inventario, dinero, labor, cooldowns y buffs se actualizan inmediatamente.
- El estado sigue siendo correcto después de reloguear.
- No aparecen excepciones ni nuevos paquetes desconocidos relacionados.
- Se repiten las pruebas básicas ya reparadas para detectar regresiones.

## Niveles de confianza de los cambios

Cada reconstrucción de datos debe indicar su procedencia:

- **A — confirmado por cliente 8.0:** fila o relación recuperada directamente.
- **B — mapeo estable:** vínculo entre versiones demostrado por un ID estable.
- **C — compatibilidad heredada:** regla o reward tomado de una versión previa.
- **D — inferido:** comportamiento reconstruido desde observación o paquetes.

Los niveles C y D deben quedar descritos en un manifiesto o informe. No deben
presentarse como datos oficiales recuperados de Kakao.

## Reglas para modificar las compact

- Conservar siempre intactos los archivos originales.
- Escribir los resultados en archivos nuevos.
- Toda transformación debe vivir en un script reproducible.
- Ejecutar `PRAGMA quick_check` y `PRAGMA integrity_check` después de generar.
- Validar consultas representativas del sistema modificado.
- Actualizar hashes y manifiestos.
- No editar manualmente la compact runtime como solución definitiva.
- No sustituir globalmente tablas solo porque sus nombres coincidan entre
  versiones.

Ejemplo ya implementado: la compact 3.0 usaba `skill_effects.end_level = 99`
como límite abierto. Un personaje Kakao nivel 100 quedaba fuera del rango. El
generador normaliza ese centinela a `255` y conserva la corrección en cada
regeneración.

## Construcción y despliegue

### Cambio exclusivo de compact o configuración

No requiere recompilar la imagen. Se debe validar el artefacto y recrear solo
Game para que los managers vuelvan a cargar los datos:

```powershell
docker compose -p aaemu8 up -d --force-recreate --no-deps game
```

### Cambio de código C#

Requiere compilar o reconstruir la imagen Game y después recrear el servicio.
Login y MySQL solo deben reiniciarse si el cambio los afecta explícitamente.

Después de iniciar se debe confirmar:

- `Application started`.
- Puertos Game y Stream escuchando.
- Registro exitoso en Login.
- Hash de `/app/Data/compact.sqlite3` igual al artefacto local.

## Pruebas mínimas de regresión

Después de cada corrección central se debe comprobar:

1. Login, selección de personaje y entrada al mundo.
2. Comando GM simple y actualización inmediata de oro.
3. Creación, incremento, consumo y eliminación de un item.
4. Loot rápido con `F` y ventana de loot con `G`.
5. Skill instantánea y skill con casteo.
6. Daño, muerte y experiencia.
7. Farmer's Coinpurse: casteo, consumo, labor y recompensa.
8. Relog para confirmar persistencia.

## Prioridades de desarrollo

1. Skills, casteos, buffs, efectos y cooldowns.
2. Inventario, ItemTask, consumibles, dinero y stacks.
3. Loot de NPC y loot packs.
4. Nivel, experiencia, labor y actabilidades.
5. Quests y recompensas.
6. Crafting, folios y progresión de recetas.
7. Equipamiento, estadísticas y set effects.
8. NPC, doodads, agricultura y housing.
9. Vehículos, barcos y física.
10. Comercio, subastas, guilds y sistemas sociales.

Antes de avanzar al siguiente bloque se deben estabilizar las dependencias
centrales del bloque actual.

## Estado confirmado al crear este documento

- Cliente 8.0 de 64 bits conecta y entra al mundo.
- AddGold e ItemTask reflejan cambios inmediatos.
- Loot rápido y ventana de loot funcionan después de adaptar IDs de objeto a
  64 bits.
- El layout de `SCSkillFiredPacket` fue confirmado directamente en
  `x2game.dll` r558734: el `tlId` se escribe al inicio y el par
  `skillId`/`fireAnimId` se codifica con PISC cerca del final. Escribir el
  `skillId` crudo al inicio desplaza el paquete y el cliente omite la
  transición visual aunque el servidor aplique el efecto.
- La acción ItemTask 8 (`Remove`) de 8.0 requiere slot, itemId, stack,
  removeReservationTime, templateId, dbSlaveId y type. La acción 14
  (`Seize`) solo debe separar o trasladar un item de su contenedor; no debe
  usarse para representar la destrucción de un consumible.
- La cadena de Farmer's Coinpurse fue identificada hasta el loot pack 8.0.
- Se generó una capa compatible de loot usando IDs de efecto estables.
- Los efectos heredados con límite abierto 99 se normalizan a 255 para nivel
  100.
- El `SkillObject` de 8.0 no termina al completar el payload de su variante:
  siempre incluye un byte final `inputDirection`. Su cabecera usa los seis
  bits bajos para el tipo y conserva los flags `0x40` y `0x80`. Omitir ese
  byte desplaza los tiempos, la animación y los flags de
  `SCSkillStartedPacket` y `SCSkillFiredPacket`, aunque el efecto autoritativo
  llegue a ejecutarse en el servidor.
- `SCUnitDamagedPacket` usa en 8.0 un primer PISC de dos valores (`damage` y
  `absorbed`). Después del segundo PISC y `HoldableId` incluye
  `elementDamage` (Int32), `showElementEffect` (Boolean) y `elementType`
  (UInt32) antes de los bits de impacto. El layout heredado omitía esos campos
  y añadía un valor al primer PISC, por lo que el cliente no podía interpretar
  el impacto ni el resultado del daño.

Pendiente de validar o reparar:

- Animación y transición visual de todos los tipos de casteo.
- Cobertura completa de skills, buffs y consumibles en nivel 100.
- `InvalidCastException` de `DoodadFuncLootItem` cuando el caster es un NPC.
- Paquetes C2G todavía desconocidos observados durante sesiones 8.0.
- Sistemas autoritativos que no existen dentro de la compact del cliente.

## Forma de continuar

Cada nuevo reporte debe convertirse en una cadena vertical documentada. Cuando
quede reparada, el cambio debe incorporarse al generador, al código o a una
migración según corresponda, acompañarse de una prueba de regresión y actualizar
este documento si descubre una regla general nueva.
