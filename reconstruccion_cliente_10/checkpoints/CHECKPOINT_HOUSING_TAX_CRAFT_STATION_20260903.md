# Housing / crafting — placas de impuestos AA10 (2026-09-03)

Target `rama_10`, HEAD base `41570558459efad934065d3ea348bffc52f45162`;
padre exacto `upstream/client_version/zone-10.0.2_r575`, `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.

## Reproducción y causa

Dannia reprodujo el error en retail. Log Game 22:48:04:

```text
CSExecuteCraft, craftId : 76 , objId : 101010, count : 1
Rejected AA10 craft before skill start: character=1007, craft=76,
skill=16767, failure=StationUnavailable, blocker=None, result=NoPerm
```

La creación del objeto 101010 registra template9405 y fase26178. El rechazo no fue
`PermissionDenied`: el validador exigía igualdad literal con `req_doodad_id=2392`.
Ambos fallos se presentan como NoPerm. No hubo casteo ni commit en ese intento.
La captura corresponde a **Bound Tax Certificate (receta76)**, no a Tax Certificate9267.

Full r575 y compact retail actual coinciden en esta cadena:

```text
craft76 -> req_doodad2392, skill16767
doodad9405 -> phase26178 -> func22855 (DoodadFuncCraftPack, perm0/Public)
 -> actual_func408 -> craft_pack3 -> craft_pack_crafts11050 -> craft76
```

Identidad full: `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`.
Identidad compact: `F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B`.
La captura más esos datos prueban que esta variante ofrece la receta. No se toma
la limitación de igualdad literal de AA8 como contrato AA10. Upstream padre
conserva comprobaciones antiguas de permisos, no una solución transferible segura.

## Arreglo

- Reconocer una estación alternativa sólo mediante su CraftPack activo y la
  pertenencia cargada de la receta; no añadir excepción por ID ni cambiar SQLite.
- Evaluar permiso de la función de crafting coincidente, no el primer callback
  de la placa (que también puede contener administración/Butler).
- Conservar fail-closed para permisos de función no públicos no reconstruidos.
- Revalidar acceso antes del cast, por unidad del lote y antes del commit.
  La restricción inicial de parcela para taxes fue incorrecta: queda sustituida
  por la excepción pública acotada documentada abajo. Otros crafts conservan el gate.
- Mantener la ruta canónica de estaciones y las transacciones existentes.
- Registrar template, estación requerida, fase y casa en futuros rechazos.

## Validación

Restore y build completo Release: correctos, cero errores. Advertencias preexistentes
de código/dependencias (incluyendo advisories NuGet) no corregidas por este cambio.
Suite completa: **1762/1762**, cero fallos/omitidas. Seis regresiones nuevas cubren
placa9405, catálogo incorrecto/ausente, estación inexistente, permisos de función,
revocación de acceso Housing y salida de fase. `git diff --check` correcto.

No se modifica cliente, configuración, esquema SQL, inventarios ni balance.
H2 cross-account y H5-B no quedan globalmente aceptados por este arreglo.

## Despliegue y aceptación

Imagen construida: `sha256:92a41248a630a6d2d986ca1f6ddd27e18b140a0e6de797f46acd1e57fa63474d`.
Rollback: `aaemu-world:rollback-pre-housing-tax-station-20260903`, imagen
`sha256:fd6330cdbd072e1a9fbde4091e2f1a7c0407306688641fab01aca8712c20adf5`.
Game detenido limpiamente22:57:43 (exit0): `SaveManager` guardó un personaje,
sin excepción de guardado. Backup posterior al stop:
`E:\AAEmu\rama_10\backups\housing-tax-station-20260903\aaemu_game.sql`, 205129 bytes,
SHA256 `2E807E523EF16D6D84B8C37DDE7334CA3C6D9ABE58D8328635870C05A68FFBA8`.
Se recreó sólo Game con `--no-deps --no-build`; Login/DB no se reinician.
SHA256 DLL idéntico en `/app` y `/app/game`:
`189a4c8edaf63851a6357c8fedc4390802f49df2d91e6414ce2f5d58c89c15a2`.
Imagen vigente coincide con la candidata. Housing reconciliado22:59:27;
`Server started!`22:59:28 (74,75s), GameServer1 registrado en Login.
Game healthy, cero reinicios. Login/DB conservan sus mismos IDs y estado healthy.
Los errores de Smelting29–32 son anteriores y su feature sigue OFF; no se reabre
esa mecánica. La desconexión Zone durante el reinicio es esperada y no se operó su lifecycle.
Zone queda bajo control del usuario.

## Aceptación retail — 2026-09-03

El usuario confirma «perfecto ya funciona». Game registra dos ejecuciones de
Dannia (character1007), craft76, estación101010, cantidad1:

- Solicitud23:07:45, commit23:07:51.
- Solicitud23:07:55, commit23:08:00.
- Ambas: `materials=1, products=1, failedProducts=0, cost=1, labor=55, remaining=0`.

El fallo de reconocimiento de placa queda **ACEPTADO Y CERRADO**: repetición
positiva y resultado visible confirmados. Los contadores materials/products del log
representan entradas del plan, no cantidades unitarias de objetos.
Esto no acredita lotes, persistencia tras otro reinicio ni la matriz cross-account:
esos gates de Housing permanecen abiertos. No hubo nuevo despliegue en este cierre.

## Corrección cross-account — 2026-09-03 (build UTC 20260904)

El usuario probó con Test/cuenta test2 y confirma que siembra e interacciones
privadas entre cuentas se rechazan como esperaba. La excepción incorrecta es
fabricar impuestos: retail deja abrir el catálogo de la placa ajena, pero Game
23:54:32–23:54:39 rechaza `character=1000, craft=76, station=101010,
template=9405, required=2392, phase=26178, house=16, failure=PermissionDenied`.
Esto es un fallo distinto al reconocimiento de estación ya cerrado.

Full y compact (hashes arriba) coinciden: pack3 contiene **exclusivamente**
craft76 (skill16767) y craft9267 (skill34912). Ambas requieren placa2392;
func22855 de fase26178 ofrece pack3 con perm0/Public. Conservan sus costes,
productos, materiales, labor y requisitos de profesión; no se copian cifras web.

Corroboración externa consultada 2026-09-03, separada de la autoridad AA10:

- ArcheRage NA/en, [Tax Certificate, craft9267](https://wiki.archerage.to/na-en/db/crafts/9267):
  catálogo regional actual, versión exacta no declarada; confirma placas alternativas.
  Clase `persistent_candidate`, no autoridad para balance/permisos AA10.
- [Craft taxes. 8x8 or 16x16?](https://www.reddit.com/r/archeage/comments/djkziw),
  discusión de 2019/Unchained: el índice de búsqueda recupera explícitamente
  que una parcela no necesita estar pública para fabricar taxes; página directa
  no recuperable (timeout). Clase `persistent_candidate`, indicio histórico auxiliar.
- El usuario confirma ese comportamiento histórico y pide conservarlo.

Implementación: `CraftStationValidator` permite omitir **sólo** el permiso de
parcela para recipes76/9267, req2392, membresía cargada pack3 y oferta activa
pack3/Public. No basta el ID, la plantilla canónica ni una función pública ajena.
Sin estación o tras abandonar la fase pública, rechaza. Las recetas restantes
mantienen permisos, aunque pertenezcan al mismo catálogo. No cambia HousingPolicy,
siembra, cofres, Doodad.Use, demolición ni permisos de cuentas.

También se corrige el segundo gate de `Skill.Use`: sólo puede delegar en
`CharacterCraft.CanStartStationSkill` para la misma instancia de Skill que la
sesión está iniciando, misma receta/skill/estación y unidades restantes. Revalida
el validador central; no existe bypass por ID de skill ni flag del cliente.
La referencia temporal se limpia en `finally`. `CraftEffect` continúa revalidando
antes del commit y no ejecuta funciones administrativas de la placa.

Se agregan pruebas de ambas recetas/placas privadas, otros crafts, catálogo/fase
incorrectos, membresía ausente, estación inexistente y prohibición de tomar
prestada una sesión de taxes mediante otra Skill. Aceptación retail de la
excepción pública pendiente del nuevo despliegue.

### Validación y despliegue de la excepción pública

Build Release: cero errores. Suite final **1771/1771**, sin omitidas; cinco
pruebas nuevas de taxes y cuatro del arreglo concurrente de nombre de dueño.
La suite se repitió sobre una copia aislada de HEAD con los cambios de Housing
y el arreglo de packs ya desplegado (sin revertirlo). La primera prueba de la
copia falló por nombre de carpeta esperado `AAEmu` y normalización LF de un
manifiesto; al conservar el nombre y los bytes de la fixture canónica, pasó
completa. No se relajaron aserciones. Advertencias preexistentes no resueltas.

La imagen aislada inicial `00ca2348…` **no se desplegó**: durante la validación,
otro trabajo actualizó Game con el fix de nombre de dueño. Se conservó ese
baseline, se recompiló y se volvieron a ejecutar todas las pruebas.

- Candidata final: `aaemu-world:tax-public-20260904`, SHA256
  `b8992f44d6b1d3ae26a19aca94a247c9520e7760d884ee3eb489c33d1ab34c35`.
- Rollback inmediato: `aaemu-world:rollback-pre-public-taxes-with-pack-fix-20260904`,
  `6567891de2710dcd278e6d4d8f21ce96498ef87e1ad2a92fe546d3347cf35b99`.
- Parada limpia Game 00:08:48 UTC: SaveManager termina sin error, salida0.
- Backup SQL posterior: `E:\AAEmu\rama_10\backups\tax-public-20260904\aaemu_game.sql`,
  212578 bytes, SHA256 `F925E54D17B37295B69A6BDB09E4440BA114E985BED6EE8C3C7C349D523D7354`.
- Sólo Game recreado `--no-deps --no-build`, inicio00:09:11 UTC. Login/DB
  conservan IDs y estado healthy. No se operó ninguna Zone.
- DLL `/app/AAEmu.Game.dll` y `/app/game/AAEmu.Game.dll` idénticas:
  `15f44580f35a72bc446ed06d72357935b57922e01e2fdb3c65adadec1d3bc44c`.
- Snapshot de fuentes/pruebas: `E:\AAEmu\rama_10\backups\tax-public-20260904\AAEmu`.
- Housing reconciliado00:10:26 UTC; `Server started!`, registro Login y WebAPI
  disponibles00:10:27. Imagen final verificada, healthy, restart0. Sólo aparecen
  los errores ya conocidos de Smelting29–32 (feature OFF), no nuevos errores de taxes.

Siguiente aceptación: Test en la misma placa ajena privada, Bound Tax Certificate,
cantidad1; debe castear y dar producto sin cambiar privacidad. Parar ahí y revisar
commit/coste/labor. Después repetir siembra privada para comprobar rechazo intacto.

### Aceptación retail y cierre de los arreglos

El usuario aprueba los arreglos y solicita commits/push separados. Game registra
dos commits exitosos de Test1000/craft76/estación101010 a las **00:13:06 y
00:13:29 UTC del 2026-09-04**: materials1, products1, failedProducts0, cost1,
labor55, remaining0. Queda **ACEPTADO** el crafting de taxes en placa ajena
privada. La prueba previa de siembra cross-account fue aprobada por el usuario;
no se atribuye una segunda prueba de siembra posterior al despliegue sin captura.
H5-B y la matriz restante de Housing no se cierran por esta aceptación.
