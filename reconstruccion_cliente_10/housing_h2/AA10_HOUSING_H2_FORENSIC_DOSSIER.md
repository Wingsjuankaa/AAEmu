# Dossier forense AA10: housing H2, venta y permisos

## Frontera

H2 parte del baseline `26cc6d70fc82bde28d8c8f0d166a32f0f7e61508` y de la
línea padre exacta `AAEmu/AAEmu:client_version/zone-10.0.2_r575` en
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`.

| Fuente | SHA-256 |
|---|---|
| full `game_decrypted.sqlite3` | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` |
| compact retail r575 | `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849` |
| runtime `compact.sqlite3` | `DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD` |
| `x2game.dll` r575 | `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734` |

El análisis AA8 se mantiene sólo como `structural_candidate`. Ningún offset,
campo, packet o permiso de H2 se promovió desde AA8.

## Contrato binario cerrado

El vtable de `SCHouseStatePacket` está en `0x39e6c220`. El wrapper
`FUN_39a8e3a0` invoca al serializer anidado `FUN_39b9ad40`. El orden relevante
demostrado por el consumer r575 es:

1. `pisc(templateId, allStep, currentStep)`;
2. `moneyAmount` `u64`;
3. `ht` `u32`;
4. co-owner, owner, nombre, account y permission;
5. posición, nombre de casa y `allowRecover`;
6. buyer id `u64` y `sellToName`;
7. límites/flags, cinco slots UCC y dos posiciones.

`SCHouseSetForSale` (`FUN_39a9cfe0`) escribe TL, `moneyAmount u64`, buyer id
`u64`, `sellToName` y `houseName`. `CSBuyHouse` (`FUN_39aa8ba0`) envía TL y
`moneyAmount u64`.

El servidor había escrito el impuesto de la vivienda en el primer
`moneyAmount`. En la granja privada observada, ese impuesto era 10 y el cliente
lo interpretó como precio de venta: activó `Sale Info` y `Purchase` aunque
MySQL conservaba `sell_price=0` y `sell_to=0`. También escribía `SellPrice` en
el campo que AA10 interpreta como buyer id. H2 corrige ambos serializers
(`House.Write` y `HousingZoneBridge`) a:

- primer `moneyAmount` = `SellPrice`;
- `ht` = modelo activo;
- `u64` posterior a `allowRecover` = `SellToPlayerId`;
- `isPublic` = permiso Public.

La UI retail extraída (`maintain_window.lua`) consulta
`X2House:GetHouseSaleInfo()` y sólo activa la sección de venta cuando `onSale`
es verdadero; por tanto la serialización incorrecta explica de forma completa
la captura observada.

## Contrato de permisos

La granja pertenece a `Wingsjuanka` (character 1, account 1). `Dannia`
(character 7) también pertenece a account 1. El acceso de alters de la misma
cuenta a la tierra se conserva incluso bajo permiso Private; no es una fuga de
autorización. Esto coincide con el comportamiento histórico documentado para
ArcheAge. Family, Guild y Public amplían el principal; Private rechaza a una
cuenta ajena.

H2 centraliza la matriz en `HousingAccessPolicy` y la aplica en tres fronteras:

- creación de doodad en parcela: antes de crear o consumir el objeto;
- skill contra doodad de housing: antes de iniciar el casteo o cobrar recursos;
- ejecución de función del doodad: revalidación al commit bajo el lock del
  doodad.

Los cofres conservan su selector propio, que puede diferir del permiso de la
casa. Los doodads sin propietario Housing no entran en este gate, por lo que no
se alteran robo, crimen, granjas públicas ni objetivos de quest.

## Evidencia reproducible

- `forensics/output/aa10-client-forensics/housing-h2-frontier-symbols.log`
- `forensics/output/aa10-client-forensics/housing-h2-frontier-vtables.log`
- `forensics/output/aa10-client-forensics/housing-h2-frontier-decompile.log`
- `forensics/output/aa10-client-forensics/housing-h2-house-state-layout.log`
- `forensics/output/aa10-client-forensics/housing-h2-xrefs.log`
- `forensics/output/aa10-client-forensics/housing-h2-frontier/lua`

Corroboración histórica secundaria:

- https://na.archerage.to/forums/threads/land-ownership-and-permissions.11000/

La fuente secundaria sólo apoya la semántica de alters de una cuenta. El wire
contract y la promoción de código proceden del cliente AA10 r575 y del runtime.

## Evidencia negativa y fail-closed

- `sell_price=0` nunca delega al flujo de compra: `BuyHouse` ya rechaza
  `HouseCannotBuyAsNotForSale` antes del pago.
- Una cuenta no incluida en el principal no puede plantar dentro de la parcela;
  el rechazo ocurre antes de `Create`, `ItemUse` y `ConsumeItem`.
- Una interacción que cambie de permiso durante el cast se vuelve a rechazar al
  ejecutar el doodad.
- Un doodad marcado como Housing cuyo house id ya no existe no se vuelve
  público por fallback: el gate central falla cerrado.
