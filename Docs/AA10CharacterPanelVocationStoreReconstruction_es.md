# Reconstrucción AA10 — tienda de Vocación desde Character Info

Fecha: 2026-08-19
Cliente objetivo: ArcheAge Returns 10.0.2.13 r575
Rama objetivo: `rama_10`

## Resultado

Se reactivó la entrada nativa de Vocation Points en la ventana `C` y se cerró su flujo de
compra completo. El mismo resolver corrige la compra directa de Honor, cuyo botón ya era visible
pero cuyo paquete actorless era rechazado por la implementación anterior al no traer NPC ni
doodad.

No se modifica `game_pak`: el botón, la ventana, la lista, el carro y el submit siguen presentes
en los Lua/ALB retail. El cliente los habilita con el feature set publicado por el servidor.

## Autoridad y contrato nativo

La evidencia reproducible está en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\vocation-shop-frontier\README.md`.
Los hechos que gobiernan la implementación son:

1. `characterInfoLivingPoint` es el bit 180 y controla la fila/botón de Vocación.
2. `shopOnUI` es el bit 147 y habilita las tiendas directas de Vocación/Honor.
3. Los open types retail son `1=Vocation` y `2=Honor`.
4. El cliente envía `CSBuyItems` con `npc=0`, `doodad=0`, `shopType=0` y el open type final.
5. `content_configs` kind 29 relaciona id 100 con pack 164 y id 101 con pack 192.

## Implementación

- `Features.json` publica `characterInfoLivingPoint=true`.
- `CharacterPanelStorePolicy` valida el shape actorless exacto y los mismos feature bits que
  usa la UI.
- `NpcManager` carga los packs directos desde `content_configs`; no codifica stock ni precios.
- `CSBuyItemsPacket` usa ese pack sólo si la política lo identifica como Character Info.
- `SCGamePointChangedPacket` serializa el contador de la colección antes del par
  `kind:u8 + amount:i32`; AA10 r575 no acepta el cuerpo legado sin ese contador.
- Las rutas normales por NPC/doodad conservan sus validaciones de actor y distancia.
- El pipeline de compra existente conserva las validaciones de good, grade, currency, price,
  límite, saldo de Vocación/Honor, espacio de bolsa y adquisición autoritativa.

## Validación ejecutada

```text
dotnet test AAEmu.UnitTests\AAEmu.UnitTests.csproj --configuration Release --no-restore
total: 1376
correcto: 1376
error: 0
omitido: 0
```

Las pruebas nuevas cubren:

- mapeo exacto `config 100 -> open type 1` y `config 101 -> open type 2`;
- aceptación del wire actorless retail;
- rechazo de NPC/doodad/shop type no cero, AA Points, compra vacía, buyback y open type ajeno;
- dependencia de `characterInfoLivingPoint` para Vocación;
- bloqueo conjunto mediante `blockSpendableGamePoint`;
- blob completo de features, cuyo byte 22 cambia de `0x81` a `0x91`.
- cuerpo AA10 de `SCGamePointChanged`: `count=1`, `kind` y `amount`, con longitud total de
  seis bytes para una entrada.

También se comprobó por consulta de sólo lectura que las compact retail y runtime contienen las
mismas relaciones y cantidades de goods para los packs 164 y 192.

## Aceptación dentro del cliente

Aceptación dinámica completada el 2026-08-19 con el cliente r575 y `Wingsjuanka` en Western
Hiram Mountains. Se inició exclusivamente el perfil `o_hirama_the_west_2`, Zone 351.

Despliegue aceptado:

- imagen integrada: `aaemu-world:10.0.2.13-r575-local`;
- SHA256 de imagen: `83016b49a5c07e859cb5129df62832a8ad2d76c3b92a2ba51817450d595bbd28`;
- `AAEmu.ZoneHost.exe` SHA256:
  `86C935A4C91C028DCB6AC99F6E2C710E4CEA692C6C1E8E398BC310257AEC457F`;
- proceso de Zone aceptado: PID 50368;
- carga confirmada: 351 merchant packs, 2 character-panel merchant contexts y features
  `shopOnUI` + `characterInfoLivingPoint`.

Secuencia observada sin reiniciar sesión entre cambios:

1. El panel `C` mostró Honor Points `0`, Vocation Badges `30` y ambos botones de tienda.
2. El comando controlado `/vocation 100` actualizó el panel abierto inmediatamente de `30` a
   `130`. Esto valida el contador reconstruido de `SCGamePointChanged` en el cliente AA10.
3. El botón de Vocación abrió el catálogo retail sin NPC ni doodad.
4. Se añadió un Worm Compost al carro: precio `80`, nuevo saldo previsto `50`.
5. La compra finalizó y el chat mostró `Used 80 Vocation Badges. (Current Vocation Badges: 50)`.
6. Sin relog, al cerrar la tienda el mismo panel `C` mostró Vocation Badges `50`.
7. La bolsa mantuvo `76/150` porque el segundo item se apiló; Worm Compost pasó visualmente a
   cantidad `2`. Su template autoritativo es `42260` y su item persistido es `16777347`.
8. El botón de Honor abrió correctamente el catálogo retail de tres páginas, con saldo `0` y
   precios en Honor Points. No se intentó una compra sin fondos.

Evidencia del servidor para la compra final:

```text
20:45:35 BuyItems npc=0, doodad=0, shopType=0, buys=1, buybacks=0,
         useAAPoint=False, openType=1
20:45:35 S->C SCGamePointChangedPacket
20:45:35 C->S CSBuyItemsPacket
```

Resultado: **Vocación desde Character Info queda reconstruida, desplegada y aceptada de extremo
a extremo, incluida la actualización positiva y negativa del saldo sin relog**. Honor comparte
el mismo resolver actorless, su apertura quedó aceptada en el cliente y su compra está cubierta
por pruebas automatizadas; no se consumieron Honor Points porque el personaje tenía saldo cero.
