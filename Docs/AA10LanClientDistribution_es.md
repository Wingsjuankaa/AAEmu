# Cliente español para la alpha de Nuia en LAN

## Entrega

Carpeta de distribución independiente:
`E:/AAEmu/rama_10/distributions/AA10-Nuia-Alpha-es_ES-LAN-20260915`.

Copiarla completa al disco local del segundo PC Windows x64 y abrir
`Jugar en LAN.cmd`. Login: `192.168.100.20:1237`. El launcher detecta
`Bin64/archeage.exe` junto al portable, sin depender de la ruta del anfitrión.
El alta automática está habilitada: usar una cuenta distinta para cada jugador.

La distribución incluye los botones de reportes y alpha. El servidor debe
autorizar al personaje nuevo para entregar objetos/monedas; copiar el cliente
no concede ese permiso. No se incluyen credenciales ni perfiles personales.

La carpeta contiene aproximadamente **87,81 GiB**; reservar al menos 90 GiB
en destino. Se entrega como carpeta lista para copiar, sin duplicar otros
94 GB en un archivo comprimido. No se creó una carpeta compartida de Windows
ni se cambió el firewall/router. La entrada efectiva desde el otro PC se
registra como aceptación pendiente.

## Qué son las SQLite

| Archivo del cliente fuente | Decisión | Motivo |
|---|---|---|
| `game/db/compact.sqlite3` | Conservar | Proyección runtime española; requerida también por el diagnóstico del launcher |
| `game/db/game.sqlite3` | Conservar | Catálogo estático del cliente, con personalización de personajes parcheada; no es la DB de cuentas/personajes |
| `game/game_decrypted.sqlite3` | Excluir | Archivo vacío de 0 bytes; marcador de trabajo sin datos |
| `compact.sqlite3.pre-*.bak` | Excluir | Respaldos de desarrollo |

El paquete contiene su propia entrada `game/db/game.sqlite3` cifrada. La copia
suelta está descifrada y fue sincronizada por el parche de personalización
de enana. Se conserva la pareja aprobada; no se intenta sustituirla por la
SQLite autoritativa externa del proyecto. El estado de jugadores reside en
MySQL del servidor.

También se excluyen cachés, logs, respaldos de DLL, ejecutables de ZoneHost,
su directorio de actualizaciones y los accesos/manifiestos del editor de
traducción. Se mantienen las bibliotecas y recursos originales de Bin64 para
no recortar dependencias nativas basándose únicamente en sus nombres.

## Construcción y comprobaciones

- Fuente: cliente principal `ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
- Target de herramientas: `rama_10`, HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`;
  padre consultado `upstream/client_version/zone-10.0.2_r575`,
  `d892934591b7a52ee082a5f9a23b277d074d043d`. Sin integración de ramas.
- Copia física, sin hardlinks; no se modifica el cliente fuente ni ninguna
  entrada del PAK. La identidad completa del PAK se exige contra el checkpoint
  de Alpha HUD V10 y se vuelve a calcular en la copia.
- Cada archivo tiene tamaño/SHA256 en `MANIFEST-SHA256.json`.
- Identidad de launcher, ejecutable, x2game y las dos SQLite fijada por hash.
- Extracción read-only del paquete distribuido: compact, base completa cifrada,
  selección racial, panel alpha, HUD, reportes, iconos, mapa y crafting.
- Comparación compact suelta/empaquetada y `PRAGMA quick_check` read-only.
- Sin cambios de código Game/Login ni despliegue/reinicio de servicios/ZoneHost.
  Esta entrega valida archivos distribuidos, no vuelve a ejecutar la suite de
  gameplay ni declara probada una sesión desde el segundo PC.

```powershell
python Scripts/BuildAa10LanClient.py
python Scripts/BuildAa10LanClient.py --apply
python Scripts/VerifyAa10LanPackage.py
```

El builder rechaza un destino existente y fuentes con hashes distintos. Una
nueva versión exige inspeccionar sus nuevos parches y elegir un destino nuevo.
Un build incompleto conserva `BUILD-INCOMPLETE.txt` y no debe distribuirse.

## Prueba desde el segundo PC

Desde el 16 de septiembre existe un [parche de perfil local](AA10LocalUserProfile_es.md)
para que el cliente use Documentos predeterminado, fuera de OneDrive, conservando
el perfil anterior. El parche ya está aplicado a la copia local de distribución;
en cada PC receptor ejecutar `Activar perfil local.cmd` para preparar su carpeta
y configuración local. El manifiesto actualizado identifica la DLL parcheada.

### Perfil de usuario y OneDrive (hallazgos del 15 de septiembre)

La carpeta del cliente no contiene `Documentos/ArcheAge/system.cfg`, que es
propia del usuario Windows. El anfitrión tiene `locale = en_us`; ese canal
contiene la traducción española. El launcher también lo solicita, pero hay
que comprobar la configuración existente al reutilizar perfiles antiguos.
No copiar la configuración gráfica y los controles del anfitrión.

El diagnóstico del segundo PC detectó `0x8007016A` al leer logs antiguos de
ArcheAge bajo OneDrive. El usuario confirmó que el arranque se desbloqueó al
resolver OneDrive. Esto no se debía a la ausencia de las DLL verificadas.
La disponibilidad de Documentos es necesaria aunque el cliente esté en H:.

Tras arrancar, el usuario reportó toda la UI en chino. Se entrega
`Scripts/ClientDistribution/Configurar-Idioma.ps1` y su wrapper CMD para fijar
únicamente `locale = en_us` en el `system.cfg` del usuario, con juego cerrado,
respaldo y verificación. Conserva codificación, BOM y demás ajustes. Si ya
está en `en_us`, no escribe: revisar perfil exportado del launcher y hashes
del paquete antes de atribuir la causa a ese archivo. La aceptación visual
del ajuste en el segundo PC permanece pendiente.

1. Ejecutar `Comprobar conexion LAN.cmd`: deben responder 1237, 1239 y 1250.
2. Ejecutar `Verificar cliente.cmd` tras la transferencia: compara todos los
   hashes, incluido el PAK completo; puede tardar varios minutos.
3. Abrir `Jugar en LAN.cmd`, usar cuenta propia, seleccionar personaje y entrar
   cuando el anfitrión tenga activa su Zone. Comprobar español y reportes.
4. Tras autorizar al personaje desde el servidor, probar el panel alpha.

El anfitrión ya publica Login/Game/Stream en `192.168.100.20`. La verificación
TCP realizada en el anfitrión no sustituye la prueba desde el segundo equipo.
No se necesita exponer MySQL ni el API administrativo. No es una distribución
configurada para Internet.

## Evidencia y reversión

Inventario, exclusiones, log de copia, manifest y extracción:
`E:/AAEmu/rama_10/artifacts/client-distribution/nuia-lan-20260915`.

El cliente de trabajo permanece intacto. Para volver a él basta utilizar su
launcher habitual. La versión distribuida es independiente, no requiere
restaurar archivos del original ni del servidor.
