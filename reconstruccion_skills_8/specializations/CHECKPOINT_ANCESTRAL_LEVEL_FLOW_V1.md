# Checkpoint: flujo de subida ancestral AA8 V1

Fecha de cierre técnico: 2026-08-05 (America/Santiago)

## Resultado

Se reconstruyó el flujo de subida ancestral del cliente Kakao AA8 `8.0.3.12 r558734` sin usar 10.x como autoridad de comportamiento. El servidor ahora:

1. conserva como EXP ancestral la EXP positiva obtenida por un personaje en el tope normal (nivel 55);
2. detiene esa EXP exactamente un punto antes del umbral explícito de la fila ancestral vigente;
3. acepta el C2G vacío `0x125` solamente en ese límite exacto;
4. comprueba y consume el item requerido por la fila AA8;
5. avanza `heir_exp` y `heir_level` y emite `SCHeirLevelUp (0x0AC)` con un único object id BC;
6. rechaza solicitudes anticipadas, repetidas, sin item o con estado persistido inconsistente.

No se concedió EXP retroactiva: las ganancias anteriores no tienen un ledger verificable. El personaje de aceptación debe ganar nuevamente la EXP ancestral bajo este runtime.

## Autoridad y procedencia

### Autoridad AA8

- corpus nativo Stage 15: `E:\AAEmu-Research\output\aa8-native-code\stage-15-native-code.sqlite`
  - SHA-256 declarado: `8A6BD3CED8AB3275614F94CD09A727E45E542F1FFCB1BB7044BB291DBB18F838`
- binario x64 reabierto únicamente para el cierre de vtable/serializador:
  - `E:\AAEmu-Research\dynamic-client\ArcheAge_8.0.3.12_r558734\bin64\x2game.dll`
  - SHA-256: `12229B1DC1EA8BE3453BC792586EC5A56E948CD8F6424132521F9AF7F9A53C4A`
- binario x86 usado para confirmar la entrada G2C:
  - `E:\AAEmu-Research\dynamic-client\ArcheAge_8.0.3.12_r558734\bin32\x2game.dll`
  - SHA-256: `078DB1B94236ECB8BBE21DC5C71CE90C178D51B6BF261C4767D32A44809BDDC3`
- runtime compacto activo:
  - `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-honor-store-v1.sqlite3`
  - tamaño: `140836864` bytes
  - SHA-256: `C9D7E78196CC2563DB61498B566E9785A1850D2D869E4878E22287E6A79BC258`

No se promovieron datos de 10.x ni se modificó `rama_8_modern`.

## Contrato nativo recuperado

### Confirmado por AA8 nativo

- `DLG_TASK_HEIR_LEVEL_UP`: consumidor UI x64 `FUN_3917E5A0` (RVA `0x17E5A0`).
- registro Lua `FUN_396E57F0`:
  - `AskHeirLevelUp` -> `FUN_396DD9D0` (RVA `0x6DD9D0`);
  - `CanHeirLevelUp` -> `FUN_396E1480`;
  - `HeirLevelUpItemInfo` -> `FUN_396E14E0`;
  - `NeedHeirLevelUpItem` -> `FUN_396E16D0`.
- `FUN_396DD9D0` llama al predicado `FUN_395FCDC0` y sólo después al emisor `FUN_395FBDE0`.
- `FUN_395FCDC0` comprueba nivel aplicable, nivel ancestral actual, máximo y la igualdad exacta `total_exp == req_total_exp - 1`.
- el constructor `FUN_395FB7E0` usa opcode C2G `0x125` y no serializa cuerpo: paquete nivel 5 de longitud total 5.
- la entrada x86 de `SCHeirLevelUp` apunta a `FUN_39B6AAB0` (RVA `0xB6AAB0`), que serializa únicamente un object id BC. Offset G2C: `0x0AC`, nivel 5.
- los serializadores vecinos de lista, activación y reset ancestral coinciden con las implementaciones existentes, reduciendo el riesgo de una asignación desplazada.

### Contenido AA8 activo

`heir_levels` contiene 71 filas contiguas, niveles 0..70. Para el primer ascenso:

- fila vigente: nivel ancestral 0;
- item: template `40491`, cantidad `1` (Honorforged Medal);
- límite de espera: `1,094,799` EXP ancestral;
- al confirmar: `heir_exp = 1,094,800`, que resuelve nivel ancestral 1.

### Límite de evidencia

El cliente nativo obtiene el nivel normal habilitante desde una configuración de contenido cuya fila nominal no está disponible en el runtime activo. El valor 55 se clasifica como `server-derived` y está corroborado por el tope normal AA8 activo y la UI en vivo; no se presenta como una constante simbólica recuperada de la tabla nativa.

## Implementación

- `AAEmu.Game/Core/Packets/C2G/CSHeirLevelUpPacket.cs`: solicitud vacía `0x125`.
- `AAEmu.Game/Core/Packets/G2C/SCHeirLevelUpPacket.cs`: respuesta `0x0AC` con object id BC.
- `AAEmu.Game/Core/Packets/C2G/CSOffsets.cs`: nombre semántico del opcode.
- `AAEmu.Game/Core/Network/Game/GameNetwork.cs`: registro nivel 5.
- `AAEmu.Game/Models/Game/Heirs/HeirProgressionPolicy.cs`: política pura de umbrales.
- `AAEmu.Game/GameData/HeirGameData.cs`: catálogo, validación y consultas.
- `AAEmu.Game/Models/Game/Char/CharacterHeirProgression.cs`: acumulación, preflight, consumo y transición.
- `AAEmu.Game/Models/Game/Char/Character.cs`: integración de la ganancia ancestral en `AddExp`.
- `AAEmu.Tests/Aa8HeirProgressionTests.cs`: contrato de wire, límite y elegibilidad.

La transición usa un lock por personaje, valida toda la precondición antes de consumir y deja personaje/items marcados para la persistencia normal ya existente. No se inventó un paquete de error AA8: los rechazos quedan en log hasta recuperar un contrato exacto. Como el guardado es el mecanismo transaccional periódico/desconexión existente, permanece la ventana habitual ante una caída abrupta del proceso entre la mutación en memoria y el siguiente save.

## Verificación automatizada

- pruebas nuevas focalizadas: `3/3`.
- conjunto ancestral con runtime AA8 montado: `14/14`.
- suite completa: `510/510`.
- build Docker de Game: correcto.
- imagen desplegada: `sha256:745dc655dceff4a07c390004e48c1f121f543e55cd5c72df5da2b05fcd7ddc39`.
- assembly desplegado `/app/AAEmu.Game.dll`: SHA-256 `84183AF796C218D21561047AB6B8FC39050FAE31419C7CA249FC91A46B60C130`; contiene los tipos `CSHeirLevelUpPacket` y `HeirProgressionPolicy`.
- `HeirGameData`: Load y PostLoad correctos en el arranque desplegado.
- Game abrió `2239` y Stream `2250`, terminó en `00:01:40.4752903` y se registró correctamente en Login.
- sólo se recreó el contenedor Game; Login y MySQL conservaron sus contenedores y uptime.
- coincidencias críticas (`ERROR`, `FATAL`, excepción no controlada) en el log del arranque: `0`.

Advertencias observadas durante la suite (`NU1701`, warnings del compilador de scripts y una prueba deliberada de captura merchant sin permisos) ya existían o pertenecen a otras superficies; ninguna produjo fallo. Resultado final de la suite: exit code 0.

## Respaldo y estado previo/post-reinicio

Respaldo de las tablas `characters` e `items` antes de recrear Game:

- `E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\backup-before-ancestral-flow-20260805-204738.sql`
- tamaño: `59277` bytes
- SHA-256: `B5A88F946DF49E4DEBEA4E475C5978EBFA83AC3F8075E332887F39628A35F452`

Estado de Dannia inmediatamente después del reinicio, sin mutación de prueba:

- character id `1`, nivel `55`;
- `heir_level = 0`, `heir_exp = 0`;
- EXP normal `7784000`, honor `658000`;
- item id `16777241`, template `40491`, cantidad `1`, Inventory slot `6`.

## Aceptación end-to-end completada

Aceptación en cliente realizada el 2026-08-05, sin editar MySQL ni conceder EXP retroactiva:

1. el cliente acumuló la EXP requerida y mostró la subida disponible;
2. a las `00:56:01Z` Game recibió `C2G 0x125 CSHeirLevelUpPacket`;
3. en el mismo instante emitió `G2C 0x0AC SCHeirLevelUpPacket`;
4. el runtime registró `ancestralLevel=1, ancestralExp=1094800` para Dannia;
5. a las `00:56:38Z` el cliente desconectó limpiamente y la fila se guardó con ese `updated_at`;
6. a las `00:56:47Z` comenzó el relog y a las `00:56:50Z` Dannia recibió nuevamente su estado y `SCHeirSkillListPacket`;
7. la consulta MySQL posterior al relog (`00:57:21Z`) confirmó `heir_level=1`, `heir_exp=1094800`;
8. el inventario persistido confirmó `0` stacks y `0` unidades del template `40491`: se consumió exactamente la única Honorforged Medal disponible;
9. no se observaron rechazos ni errores propios del flujo ancestral.

Durante login/relog sí aparecen errores de protocolo ajenos a esta transición (`0x206`, `0x053`, `0x164`) y un mensaje previo `Looks like we got double count my guy`. No coinciden temporal ni semánticamente con el intercambio ancestral confirmado y quedan fuera de este cierre; deben tratarse en sus superficies correspondientes.

Estado del vertical slice: **aceptado visualmente, confirmado por wire y persistente tras relog**.
