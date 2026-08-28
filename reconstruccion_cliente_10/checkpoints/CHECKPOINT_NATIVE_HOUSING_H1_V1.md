# Checkpoint nativo: housing AA10 r575, ola H1

## Estado de promoción

Housing H1 queda implementada sobre `rama_10`, baseline
`26cc6d70fc82bde28d8c8f0d166a32f0f7e61508`. El gate retail de plantación
quedó aceptado el 2026-08-28 y la persistencia visible tras relog también quedó
confirmada. La autorización cruzada se separó explícitamente como ola H2 y no
forma parte del gate de colocación H1 ya aceptado. La ola no declara reconstruidos los bindings interiores
todavía no resueltos ni los lifecycle de demolición, recuperación, venta e
impuestos que correspondan a olas posteriores.

El servidor ya no acepta una plantación sólo porque la posición central cae en
una zona con un nombre compatible. H1 exige que el diseño y el objeto de bolsa
coincidan exactamente, que la huella circular completa quepa dentro de un
polígono nativo r575, que la categoría sea válida para el grupo de esa área,
que la altura sea admisible y que no exista solapamiento con otra casa.
Toda evidencia ausente falla cerrada y no consume objetos ni dinero.

## Identidad y frontera forense

| Fuente | SHA-256 |
|---|---|
| full `game_decrypted.sqlite3` | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` |
| compact retail r575 | `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849` |
| runtime `compact.sqlite3` | `DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD` |
| `x2game.dll` r575 | `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734` |
| índice de `game_pak` | `EA4D8EAFB4F32C70CAA3666C79904F9B5D5223CCB6E20C1A1C4001231AD59DD8` |

La línea padre exacta es
`AAEmu/AAEmu:client_version/zone-10.0.2_r575` en
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. AA8 se usó solamente como
`structural_candidate`; el manifest declara cero valores AA8 copiados.

El extractor por lotes y el generador reproducible están en
`reconstruccion_cliente_10/tools/PakBatchExtract` y
`reconstruccion_cliente_10/housing_h1/build_aa10_housing_area_shapes_h1.py`.
Los XML extraídos permanecen fuera de Git bajo la frontera forense. Dos
generaciones consecutivas produjeron los mismos hashes:

- catálogo runtime: `7018FD00FE4440B3767B9273AF70AEA7461BDD1F4E243968015ACCCD442D89DE`;
- manifest: `820747CCFB6B5A3DFAF1016A9DA9ABC930856B29F7B6C1F7F8CDADA0F3FF226F`.

## Cobertura y evidencia negativa

| Métrica AA10 | Cantidad |
|---|---:|
| templates de housing | 837 |
| templates unidos a `housing_sizes` | 837 |
| tamaños/radios nativos | 17 |
| relaciones exactas objeto–diseño | 556 |
| áreas runtime activas | 846 |
| archivos cliente `housing_area.xml` | 134 |
| shapes promovidas | 776 |
| áreas únicas promovidas | 775 |
| puntos promovidos | 17.944 |
| áreas activas sin shape demostrable | 71 |

Las 71 áreas sin polígono no recurren al chequeo heredado por nombre: quedan
bloqueadas. El área cliente 208 no tiene relación runtime activa y se conserva
como evidencia diagnóstica. Existen 19 diferencias entre el nombre físico de
zone y el nombre histórico de `housing_areas`; no afectan la promoción porque
la unión autorizante usa el `AreaId` nativo exacto, no una coincidencia textual.

## Contratos cerrados en H1

- `housings.housing_size_id` se une a `housing_sizes.garden_radius`; ya no se
  simula `GardenRadius = 0`.
- `item_housings.completion` decide si la casa nace terminada o abre la fase de
  construcción; el objeto concreto de bolsa debe pertenecer al diseño pedido.
- La forma de cada área procede de `LevelDesignShape` en `game_pak`; se aplica
  transformación de celda, entidad y quaternion antes de generar el polígono.
- La huella completa debe caber en una sola forma autorizada para su categoría.
- Se rechazan posiciones y rotaciones no finitas, altura fuera del envelope
  AA10 y solapamientos circulares entre propiedades; dos huellas tangentes no
  se consideran solapadas.
- El cliente r575 ejecuta `OverlappedGridChecker` y `OverlappedObbChecker`
  antes de emitir `CSCreateHouse`. No se promueve el chequeo AA8 que trataba
  todo `Unit` del mundo como estructura: en el runtime Zone-authoritative
  producía falsos positivos después de que el consumer AA10 aceptara la vista
  previa. El servidor conserva la validación autoritativa casa-contra-casa.
- Diseño, certificados bound/unbound y wallet se prevalidan y confirman bajo
  locks comunes. Las tareas de inventario se publican sólo tras registrar la
  casa; todo rechazo previo conserva íntegros objetos, certificados y saldo.
- La primera propiedad ya calcula el impuesto de construcción; desapareció el
  retorno falso que permitía coste cero por no tener casas anteriores.
- Cambio de permisos exige propietario y una identidad real de familia/gremio.
  Venta y cancelación de venta exigen propietario. La decoración exige objeto
  exacto en la bolsa, relación objeto–diseño, propietario y transform finito.

## Verificación estática

- `dotnet restore AAEmu.slnx`: correcto;
- compilación `Release` de la solución: correcta, cero errores;
- suite completa: 1.588/1.588 pruebas correctas;
- pruebas focales H1: 8/8 correctas;
- checks forenses Python: correctos;
- generación doble determinista: correcta;
- `PRAGMA quick_check` e `integrity_check`: `ok` en full, compact retail y
  runtime;
- las tres propiedades del operador ya persistidas en `(13890,14234)`,
  `(13924,14196)` y `(13940,14196)` caben por huella completa en el área 52 y
  sus categorías están autorizadas. Las dos granjas tangentes a 16 metros
  siguen siendo válidas.

## Corrección del gate dinámico 2026-08-28

El primer intento superpuesto fue rechazado sin mutación. El segundo intento,
en `(13962,14198)`, fue aceptado por el builder nativo y emitió
`CSCreateHouse`, pero el servidor lo rechazó mediante un chequeo importado de
AA8 que recorría todas las unidades vivas. La casa solicitada usa radio 14 y
la propiedad más cercana, en `(13940,14196)`, radio 8: la distancia entre
centros es `22,09`, mayor que la suma `22`, por lo que no existe
solapamiento. Se eliminó ese blocker AA8 no demostrado y se añadió esta
coordenada como regresión estática. El gate retail positivo debe repetirse
antes de aprobar H1.

La corrección quedó validada adicionalmente con compilación `Release` sin
errores, 9/9 pruebas focales de placement/manager y 1.592/1.592 pruebas de la
suite completa.

El segundo intento retail, ahora con el diseño 313, expuso otro falso positivo
independiente. Los doce `Archeum Lodestone` persistidos usan
`housing_size_id=1`, cuyo `garden_radius` nativo es exactamente cero. La
primitiva circular interpretaba ese cero como dato inválido y devolvía
solapamiento sin considerar la distancia, por lo que la primera de esas
estructuras bloqueaba cualquier plano en cualquier coordenada. En AA10 ese cero
representa ausencia de huella circular, no una huella infinita. Se conserva el
fail-closed para radios negativos/no finitos y el gate previo sigue exigiendo
radio positivo a toda nueva vivienda de jugador.

Los paquetes observados fueron diseño 313 en `(13960,14196)` y
`(13976,14208)`. Su radio es 11; ninguno solapa las tres propiedades de jugador
persistidas. La regresión queda cubierta por 10/10 pruebas focales y
1.593/1.593 pruebas completas, con build `Release` sin errores.

## Aceptación retail de plantación 2026-08-28

El operador confirmó primero el rechazo sin consumo sobre una propiedad
existente y después la plantación válida del mismo diseño 313 en terreno libre.
El intento aceptado emitió una sola petición en `(13948,14216,119.25115)`, una
tarea `HouseCreation`, una tarea `HouseBuilding`, `SCHouseData` y el relay
`WZUnitState/WZHouseState` a la Zone 142. MySQL contiene exactamente una fila
nueva: housing 16, template 313, owner 7 (`Dannia`), permiso privado y
`current_step=-1`. El plano 15603 ya no está en el inventario y quedan 940 Tax
Certificates 31891 tras el coste de 60 indicado por el request. No se observó
`SCErrorMsgPacket` ni una segunda creación en esta aceptación.

A las `15:38:53` el operador relogueó con Dannia. Durante el nuevo spawn, Game
volvió a enviar `SCUnitState` para el objeto 1065 (`Stone Rose Manor`) seguido
de `SCHouseState`; la casa fue visible en retail. La fila 16 permaneció con
template 313, owner/co-owner 7, posición `(13948,14216,119.251)`, rotación 0,
permiso privado y fase `-1`. Esto aprueba el gate de persistencia/relog sin una
segunda mutación.

## Gate retail decisivo de H1

Con una escritura legítima en la bolsa y suficientes certificados:

1. intentar plantar con toda la huella fuera del borde o superpuesta a otra
   propiedad: debe rechazar antes de consumir;
2. mover la vista previa a una posición libre dentro de la misma área y
   confirmar: debe crear una sola propiedad y descontar exactamente una
   escritura y el coste mostrado;
3. reloguear: la propiedad, posición, rotación, owner, permiso y fase deben
   persistir;
4. con otro personaje, intentar cambiar permisos, decorar, vender o cancelar
   la venta: toda mutación debe ser rechazada;
5. con el propietario, repetir esas operaciones permitidas y confirmar que sí
   avanzan.

La evidencia decisiva para aprobar H1 es la combinación **rechazo sin mutación
en borde/overlap + plantación válida con consumo exacto + persistencia tras
relog + autorización negativa con otro personaje**.

## Despliegue para aceptación

- imagen activa del host combinado World/Game (el gate de solución se compiló
  aparte en `Release`; el Dockerfile canónico publica actualmente en `Debug`):
  `sha256:119066fa927fe0afb608b73ae08cd319b45c008590bcfc93ea46e239f9a7e449`;
- rollback inmediato anterior a la corrección de radios cero conservado como
  `aaemu-world:rollback-pre-housing-h1-zero-radius-20260828`, imagen
  `sha256:55be7749242d4a32ed85d1d71a7de47357620588e863a9b20d527c08ee6726c5`;
- rollback inmediato anterior a la corrección de overlap conservado como
  `aaemu-world:rollback-pre-housing-h1-overlap-20260828`, imagen
  `sha256:3636f783db392ed6cf370c1d6ba005add4f3d00a62b5e9f148dc390bf4ce55eb`;
- rollback previo conservado como
  `aaemu-world:rollback-pre-housing-h1-20260827`, imagen
  `sha256:908c5a647fa803079e77236bfc3403d7a2763388665c19648a18ecdc4a4d0be4`;
- catálogo montado en runtime con hash
  `7018FD00FE4440B3767B9273AF70AEA7461BDD1F4E243968015ACCCD442D89DE`;
- el overlay canónico monta read-only el cliente r575 completo en
  `/app/game/ClientData`, sin duplicar ni alterar sus assets;
- el healthcheck canónico verifica que el PID 1 ejecuta `AAEmu.World.dll` y
  contempla 180 segundos de arranque;
- contenedor `aaemu10-game-1`: `healthy`, cero reinicios tras el recreado final;
- loader runtime: 776 shapes, 775 áreas y un mundo; 837 templates; 1.706
  offsets de binding resueltos y 2.267 pendientes para otra ola;
- 15 propiedades persistidas cargadas; Game inició en 81,57 segundos, abrió
  Game/Stream/WebAPI y registró la sesión en Login;
- ZoneAuthority quedó activo en `192.168.100.20:1240`. El despliegue inicial
  omitió por error el overlay AA10 y fue corregido antes de la aceptación;
- Codex no inició, detuvo ni relanzó ninguna Zone. Tras la corrección de radios
  cero, el recreado de Game desconectó la Zone 142 y el operador debe relanzarla
  desde Control Center antes de repetir el gate retail.
