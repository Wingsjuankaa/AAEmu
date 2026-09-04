# Crash al consultar el dueño de un pack — r575

## Estado

Corrección `client-native` implementada, Release compilado y 1766/1766 pruebas
correctas (0 fallos, 0 omitidas). El usuario autorizó el despliegue y estableció
la preferencia permanente «siempre termina desplegando el cambio».
Game fue actualizado; la aceptación visual retail sigue pendiente. No se operaron Zones.

Target canónico: `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`, HEAD
`41570558459efad934065d3ea348bffc52f45162`. Padre exacto consultado mediante fetch:
`upstream/client_version/zone-10.0.2_r575`,
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. El padre y AA8 conservan el contrato
uint32 heredado; no contienen la corrección. Los cambios locales previos se preservan.

## Evidencia del incidente

El usuario pasó el cursor por un pack de otro personaje mientras jugaba con Test.
La captura muestra `StreamClientImpl: serializer size mismatch` a las 23:55:18.171.
Game registra a las 23:55:18 la petición del dueño 1007/Dannia, esta respuesta y la
desconexión inmediata de Stream:

```text
CT 0x009: 0A 00 09 00 EF 03 00 00 00 00 00 00
TC 0x008 anterior: 0E 00 08 00 EF 03 00 00 06 00 44 61 6E 6E 69 61
TC 0x008 corregido: 12 00 08 00 EF 03 00 00 00 00 00 00 06 00 44 61 6E 6E 69 61
```

La respuesta antigua coloca el nombre cuatro bytes antes de lo requerido: el
cliente incorpora longitud y parte del nombre al identificador y luego interpreta
`6E 6E` como longitud de cadena. No es un rechazo de permisos de Housing ni una
mutación del pack. Que aparezca al consultar otro dueño es coherente con la
necesidad de resolver su nombre; no se ha instrumentado la caché del cliente.

## Contrato nativo

Cliente x86-64 operacional: SHA256
`405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`.
Proyecto Ghidra baseline: SHA256
`2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76`, base `0x39000000`.
`Aa10PackOwnerNameAudit.java` compara todos los bytes de cada función con el PE
operacional antes de emitir su decompilación. Siete funciones coinciden exactamente.

| RVA | Evidencia |
|---|---|
| `0xA9B1E0` | Serializer TC: slot `+0x98` para id en objeto `+0x10`, cadena en `+0x18`; lector `+0x1C8`, límite 128 bytes |
| `0xAACEA0` | Serializer CT: sólo el mismo id/slot `+0x98` |
| `0xA8EEB0` | Asignador TC almacena 8 bytes del id y copia el nombre |
| `0x742E20` | Functor construye TC con opcode 8, invoca serializer y comprueba éxito |
| `0x741AE0` | Deserialización y entrega del mismo TC |
| `0x7425D0`, `0x74A410` | Destructores de TC/CT identificados por sus vtables |

Vtables baseline: TC `0xEC4CF0`, CT `0xEC63D8`, functor TC `0xEC5140`.
El ancho de 8 bytes del slot `+0x98` también está documentado en
`Docs/CHAT_FIX_INTEGRATION.en.md`; la captura CT confirma sus ocho bytes en wire.

Contrato: CT `u64 ownerId`; TC `u64 ownerId + u16 utf8Length + utf8Name`, dentro
del framing Stream existente (`u16 payloadLength + u16 opcode + body`).
Los nombres locales válidos usan el catálogo existente; no se cambia su límite.

No había dossier para estos packets en los índices/corpus consultados. Esta
frontera cierra el dato faltante contra release, sin copiar layouts de AA8.
No corresponde cambiar full/compact ni game_pak: el fallo es de protocolo.

## Implementación y regresiones

- `CTUccCharacterNamePacket` exige cuerpo de ocho bytes y lee uint64 completo.
- La consulta al registro local uint32 comprueba rango antes de convertir; un id
  alto nunca puede devolver el nombre de otro personaje con los mismos 32 bits bajos.
- `TCUccCharNamePacket` emite uint64 y conserva opcode/nombre/framing.
- Nombres desconocidos conservan el comportamiento previo de no enviar respuesta.
- Pruebas: petición capturada a través del handler/framing y repetición; id alto
  y nombre UTF-8; dueño desconocido/id alto sin alias; cuerpo truncado/sobredimensionado.
- `dotnet restore`, `dotnet build --configuration Release --no-restore` y
  `dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore`
  correctos. Build: 174 advertencias, cero errores. No se ejecutaron integraciones
  dependientes de servicios. Esta consulta no cambia inventarios ni persistencia.

Artefactos y manifest:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\pack-owner-name-frontier`.
Incluye logs de símbolos, vtables, reanclaje/decompilación, captura, restore,
build, suite e imagen. El manifest congela hashes de evidencia y fuentes.

## Despliegue realizado y verificación

Imagen candidata: `aaemu-world:pack-owner-name-fix-20260903`,
`sha256:6567891de2710dcd278e6d4d8f21ce96498ef87e1ad2a92fe546d3347cf35b99`.
Construida con el Dockerfile World actual y `CONFIGURATION=Release`.
Imagen anterior preservada para rollback:
`sha256:92a41248a630a6d2d986ca1f6ddd27e18b140a0e6de797f46acd1e57fa63474d`,
tag `aaemu-world:rollback-pre-pack-owner-name-20260903`.

Autorización recibida: «si siempre termina desplegando el cambio». Se registró
como preferencia permanente en la skill AA10, validada con `quick_validate.py`.
Se preservó la imagen anterior, se detuvo Game limpiamente (exit0, guardado sin
datos pendientes) y se respaldó DB tras el guardado. Se recreó únicamente `game`
con `--no-deps --no-build`; Login y DB conservaron sus IDs. Sin cambios de SQL/config.

- Stop limpio: logs `00:05:41`, salida `2026-09-04T00:05:42.976498408Z`.
- Backup: `E:\AAEmu\rama_10\backups\pack-owner-name-20260903\aaemu_game.sql`,
  212629 bytes, SHA256
  `C9BEDF80124EF6E49705378EB026538E9F9DD9B83E0030EB2E920DF7D897FA97`.
- Contenedor nuevo: `ac9f798e28108a8277befe294e259a3df1982fff2b47fd2dd852e6ceb517bd91`.
- Imagen vigente: candidata `6567891d…`, tag operativo `aaemu-world:10.0.2.13-r575-local`.
- `/app/AAEmu.Game.dll` y `/app/game/AAEmu.Game.dll`: SHA256 idéntico
  `a44a3326099c224bcd04c30a67219560eb970eeb282404172bf957055ca8907c`.
- `Server started!` y GameServer1 registrado en Login a las `00:07:22` del log;
  carga 73,38 segundos. Game healthy, cero reinicios.
- Dos conexiones TCP independientes al Stream `127.0.0.1:1250`, a las `00:07:46`,
  enviaron el CT capturado y recibieron exactamente
  `12000800EF03000000000000060044616E6E6961`. Ver `runtime-wire-probe.txt`.
  Esto verifica framing/opcode/body en el runtime desplegado, además de los tests.

Los tiempos anteriores son los emitidos por Docker/Game (UTC); el día local de
la intervención sigue siendo 2026-09-03. Las Zones 142/179 se desconectaron durante
el stop esperado. Su lifecycle continúa bajo control del usuario; no se operaron.

Aceptación pendiente: entrar con Test, pasar el cursor por el mismo pack de
Dannia y comprobar nombre/tooltip sin crash y TC corregido en logs. Después
repetir sobre el segundo pack y volver a consultar tras reconectar el cliente.
No recoger ni transferir packs para esta prueba de consulta.

## Aceptación y cierre

El usuario aprueba los arreglos y solicita commits/push separados. La consulta
CT/TC de dueño vuelve a registrarse00:12:49 UTC del 2026-09-04 y el mismo
personaje Test continúa jugando (crafts00:13:06 y00:13:29); no se reproduce el
crash en la prueba aprobada. La imagen final vigente incorpora también taxes
públicos, conservando este fix: `b8992f44d6b1d3ae26a19aca94a247c9520e7760d884ee3eb489c33d1ab34c35`.
Suite conjunta1771/1771. Aceptación visual aprobada por el usuario; no se presume
una prueba adicional con segundo pack/reconexión distinta de lo reportado.
