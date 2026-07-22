# Fase 2: núcleo de especializaciones 8.0

## Estado

La implementación técnica del núcleo de la fase 2 está desplegada en el
entorno `aaemu8`. El servidor carga la compact derivada, registra 35.501
habilidades y escucha nuevamente en los puertos `2239` y `2250`.

Falta ejecutar el protocolo funcional dentro del cliente para cerrar la fase:
selección de una segunda rama, aprendizaje, rechazo, reinicio, intercambio y
dos relogs.

## Evidencia confirmada en el cliente

- `AbilityStates::CanSwapAbility` exige tres posiciones, una rama antigua
  activa y una rama nueva inactiva.
- `AbilityStates::ActivateAbility` inicializa la experiencia de una rama nueva
  con el promedio entero de las ramas activas.
- Las filas nativas de `levels` contienen puntos de habilidad acumulados, no
  un incremento que deba sumarse otra vez por cada nivel.
- `passive_buffs.req_points` representa los puntos previamente invertidos en
  la rama. El costo real está en `passive_buffs.skill_points`.
- El paquete cliente-servidor de reinicio usa el offset `0x192`. Se confirmó
  mediante `FUN_395feee0` en `x2game.dll` y la entrada contigua ya presente
  como `off_3A0BB590` en la tabla del port.
- Las estructuras de aprendizaje, reinicio e intercambio coinciden con los
  argumentos observados en las funciones Lua. No se agregaron campos de red
  inferidos.

Referencias:

```text
E:\AAEmu-Research\output\ghidra-static\phase2-ability-entrypoints.c
E:\AAEmu-Research\output\ghidra-static\phase2-ability-lua-actions.c
E:\AAEmu-Research\output\ghidra-static\phase2-ability-wire-actions.c
E:\AAEmu-Research\output\ghidra-static\phase2-levels-loader.c
```

## Compact derivada

Docker utiliza ahora:

```text
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-phase2-native-skills-v2.sqlite3
SHA-256: 9E005D98DC6C12B9618978B7729D466517FE5A270E61712DFFCC519C51A4B0F0
```

Comando reproducible:

```powershell
python reconstruccion_skills_8\build_phase2_compact.py `
  --runtime-compact D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-loot-hybrid.sqlite3 `
  --client-compact E:\AAEmu-Research\output\compact-client-8.0-decrypted.sqlite `
  --client-game-stream E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-phase2-native-skills.sqlite3 `
  --manifest reconstruccion_skills_8\generated\phase2-native-skills-compact-manifest.json `
  --verify
```

La SQLite descifrada es una vista delta y omite habilidades base como Triple
Slash `18132`. La consulta cacheada completa de `skills` fue recuperada de
`game11` usando el orden de 161 columnas y los tipos confirmados en
`x2game.dll`. El generador hace una unión reproducible:

- 24.175 filas históricas que constituyen la base;
- 33.466 filas nativas válidas del cliente 8.0;
- 22.140 IDs compartidos con la base;
- 2.035 IDs históricos adicionales conservados por compatibilidad;
- 35.501 IDs únicos en la salida.

Los campos de gameplay compartidos proceden de `game11`. Las columnas
exclusivas del backend antiguo, por ejemplo `need_learn`, se conservan de la
base. `name` y `desc` mantienen el valor histórico porque el caché puede
codificarlos como referencias a su tabla de strings. La fila espuria
`1952543349` que había entrado por el borde anterior del caché fue descartada
mediante validación semántica de todos los campos booleanos.

También se recuperaron directamente desde `game11`:

- 101 filas de `levels`;
- 278 filas de `passive_buffs`;
- nivel 55: 20 puntos acumulados y 7.784.000 de experiencia total;
- pasiva `244`: buff `7544`, requisito 8 y costo 0.

`PRAGMA quick_check` e `integrity_check` devuelven `ok`. El manifiesto está en
`generated/phase2-native-skills-compact-manifest.json`.

## Cambios del núcleo

### Progresión

- Se corrigió el nivel desde experiencia. El código anterior devolvía el nivel
  siguiente por usar `return lv--`.
- Los puntos disponibles ahora leen el valor acumulado de la fila del nivel;
  antes se multiplicaba por el nivel del personaje.
- La experiencia de una rama nueva usa el promedio confirmado por el cliente.
- Se eliminó la asignación no confirmada de 42.000 EXP a todas las ramas
  inactivas.

### Aprendizaje y pasivas

- Se valida que la plantilla exista y que su rama esté activa.
- Se validan nivel de rama, puntos disponibles y puntos ya invertidos en esa
  rama antes de modificar memoria.
- `req_points` se trata como requisito y `skill_points` como costo.
- Un ID desconocido, nivel inválido o buff inexistente se rechaza sin mutar el
  personaje ni abortar su guardado.
- La fórmula usa enteros con signo y no puede producir los niveles 253/255 que
  anteriormente corrompían personajes.

### Selección e intercambio

- Toda la solicitud se valida antes de retirar habilidades o cambiar ramas.
- Se rechazan ramas inexistentes, ya activas o posiciones antiguas inválidas.
- Después de una selección correcta se reconstruyen los órdenes y se agregan
  las habilidades automáticas conocidas por el backend.
- `CSSwapAbilityPacket` comprueba que el `objId` corresponde al personaje de
  la conexión.

### Persistencia

- La carga restaura el nivel persistido exacto; ya no vuelve a ejecutar el
  flujo de aprendizaje ni recalcula el registro.
- Los niveles persistidos fuera del rango posible se omiten y registran.
- El guardado reemplaza el conjunto completo dentro de la transacción externa.
  Un error revierte el borrado y las inserciones conjuntamente.

## Respaldo y validación

Respaldo previo al despliegue:

```text
D:\Proyectos\AAemu\backups\phase2_skills_8\aaemu8-before-phase2.sql
SHA-256: A77141BBCDB7A1957F183313274A70B71165A8D621D7DD10AE59F69E8B5A270A
```

Validaciones realizadas:

- build local de `AAEmu.Game`: correcto;
- build Docker de `aaemu-game:0.0.2.0-alpha`: correcto;
- 23 pruebas xUnit: correctas;
- cinco pruebas nuevas de progresión: correctas;
- carga real: `Loaded 35502 skills`;
- redes Game y Stream iniciadas y registro en Login correcto;
- `Wingsjuank`: rama 1, habilidad `18132`, nivel persistido 1.

El error periódico de `TaskManager` que intenta convertir un NPC en Character
es anterior a esta fase y no está relacionado con especializaciones.

## Protocolo de aceptación en el cliente

1. Entrar y confirmar inventario, habilidades, menú ESC y barra de acción.
2. Activar Shadowplay como segunda rama sin aprender habilidades.
3. Ir a selección de personaje y entrar dos veces.
4. Aprender una habilidad disponible y colocarla en la barra.
5. Intentar una habilidad cuyo nivel o requisito aún no se cumpla; no debe
   cambiar memoria, interfaz ni MySQL.
6. Reiniciar Shadowplay. Esto valida el offset confirmado `0x192`.
7. Volver a activarla, aprender una habilidad y cambiarla por otra rama.
8. Repetir dos relogs y comprobar que rama, habilidades, pasivas y barra
   coincidan con MySQL.

### Hallazgo de la primera prueba de progresión

Al alcanzar nivel 3, aprender `11918` y reloguear, el cliente se cerraba dos
segundos después de recibir `SCUnitStatePacket`. MySQL conservaba un estado
válido: Battlerage activo y las habilidades `18132` y `11918`, ambas en nivel
1. El servidor tampoco registraba una excepción.

El lector confirmado en `x2game.dll` procesa las IDs aprendidas y las pasivas
en bloques PISC de hasta cuatro valores que comparten un solo encabezado de
compresión. El backend emitía un encabezado independiente por cada ID. Una
sola habilidad funcionaba por coincidencia, pero la segunda se interpretaba
como parte de los datos siguientes y desplazaba el resto del paquete.

Se corrigió `SCUnitStatePacket` para agrupar tanto habilidades como pasivas en
bloques de hasta cuatro. La regresión usa las IDs reales `18132` y `11918` y
confirma la secuencia `05-D4-46-8E-2E`. Las 24 pruebas pasan. El personaje se
conservó en nivel 3 para repetir directamente el ingreso y la persistencia.

### Hallazgo de la prueba de nivel 10

El cliente ofreció Battle Focus `10377` al alcanzar nivel 10, pero el servidor
rechazó cada intento porque la fila heredada indicaba `ability_level = 45` y
`level_step = 10`. La fila nativa recuperada de `game11` confirma
`ability_level = 10`, `level_step = 31`, `req_points = 0` y
`skill_points = 1`.

No se aplicó un parche aislado: se reconstruyeron los campos de gameplay de
las 33.466 habilidades nativas. La nueva compact pasa `quick_check` e
`integrity_check`, contiene 35.501 filas y tiene SHA-256
`51EB37C17544B40387CFC718EF67E0B4965D4F90A17508F020B216C9EEEC0EFE`.

### Hallazgo de selección de especialidades

Kakao 8.0 envía `objId = 0` en `CSSwapAbilityPacket` para referirse al
personaje activo. Se acepta ese sentinel o el `ObjId` real, pero se siguen
rechazando IDs ajenos. La captura confirmó además los campos `old`, `new` y
`auap` sin inferir offsets.

La primera selección de Shadowplay persistió correctamente, pero el cliente
ocultó visualmente las habilidades de Battlerage hasta el relog. El servidor
enviaba los tres estados como pares diferentes. Se portó el arreglo upstream
`891b96ed` (`Fixed specialization selection`): `SCAbilitySwappedPacket`
repite tres veces el par solicitado `old → new`. Una regresión byte a byte
confirma para `30 → 8` la carga útil
`3C-7E-00-1E-08-1E-08-1E-08`. Las 28 pruebas pasan.

### Hallazgo de habilidades iniciales modernas

Swiftblade se activó como habilidad `12` y sus skills manuales funcionaron,
pero no recibió automáticamente su primera habilidad `40331`. `game11`
confirma `ability_level = 1`, `auto_learn = 1`, `show = 1` y costo 1. La
columna `need_learn`, usada por el backend para construir
`_startAbilitySkills`, ya no forma parte del resultado nativo y había quedado
en cero para filas inexistentes en 3.0.

El generador deriva `need_learn = 1` únicamente para filas nativas nuevas de
una especialidad de combate, visibles y con costo positivo. Se reconstruyen
50 filas; se excluyen explícitamente las 3.753 skills generales/NPC con
`ability_id = 0` y las variantes ocultas. Las anclas modernas verificadas son
Malediction `39007`, Swiftblade `40331`, Gunslinger `44196` y Spelldance
`47961`.

## Límites pendientes

- Los paquetes de error visual para cada rechazo deben confirmarse todavía;
  por ahora el servidor rechaza de forma segura y deja registro.
- 52 de las 278 pasivas nativas apuntan a buffs que aún no existen en la
  compact runtime histórica. Ninguna de las seis pasivas Battlerage está en
  ese grupo. Su importación completa corresponde al siguiente corte de datos.
- La fase no se marca cerrada hasta completar la aceptación dentro del cliente
  y comparar MySQL tras los relogs.
