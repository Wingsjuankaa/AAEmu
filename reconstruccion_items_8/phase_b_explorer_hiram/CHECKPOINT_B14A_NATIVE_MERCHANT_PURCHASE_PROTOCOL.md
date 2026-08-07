# Checkpoint B14a — protocolo nativo de compra en mercader AA8

Fecha: 2026-07-31

Estado: `listo_para_retest_controlado`.

## Alcance

Se reconstruyó transversalmente la compra en comercios NPC para el cliente
Kakao 8.0.3.12 r558734. No se añadió una excepción para Deven ni para el item
47868: todos los NPC merchants que tengan un stock autoritativo cargado pasan
por el mismo paquete y por `MerchantPurchaseService`.

El runtime SQLite no cambió. Continúa montado:

```text
compact-8.0-runtime-point0-quest-use-proxy-v6.sqlite3
sha256=6C8797A8F133DEDC4E1247B737160E5EB4818BF19A841A351238EAEAC0091C15
```

## Evidencia de protocolo

La captura local produjo dos paquetes idénticos:

```text
opcode=0x0F0, level=5
b9 90 00 00 00 00 00 00 00 00 01 00 fc ba 00 00 00 01 00 00 00 00 00 00
```

Su contenido es:

```text
npcObjId=37049
doodadObjId=0
unknownId=0
nBuy=1
nBuyBack=0
itemId=47868
grade=0
count=1
currency=0
useAAPoint=false
openType=0
```

Stage 15 confirma el contrato nativo:

- binario x86 SHA-256
  `078DB1B94236ECB8BBE21DC5C71CE90C178D51B6BF261C4767D32A44809BDDC3`;
- constructor x86 RVA `0x00830970`: asigna opcode `0x0F0`;
- serializer x86 RVA `0x00B6F700`: `nBuy`, `nBuyb`, máximo 16,
  `useAAPoint`, `openType`;
- serializer de línea x86 RVA `0x00D4A400`: item `UInt32`, grade `Byte`,
  stack `Int32`, currency `Byte`;
- serializer x64 RVA `0x00996A40`, SHA-256
  `12229B1DC1EA8BE3453BC792586EC5A56E948CD8F6424132521F9AF7F9A53C4A`;
- equivalencia x86/x64 corroborada por el conjunto único de strings
  `useAAPoint`, `nbuyb`, `openType`.

La wiki de ArcheRage sólo corroboró que el NPC 5342 ofrece el item 47868. El
precio autoritativo permanece en el runtime AA8:
`merchant pack 914119 -> item 47868, grade 0, currency 0, price 250`.

## Implementación

- `CSBuyItemsPacket` fue reasignado de `0x188` a `0x0F0`.
- El placeholder `off_3A0D7D80` fue retirado.
- El parser ahora consume el byte final nativo `openType`.
- Compra y recompra aceptan como máximo las 16 líneas del array nativo.
- Payloads truncados, sobredimensionados o con bytes no consumidos fallan
  cerrados antes de cualquier mutación.
- Grado, moneda, precio, stock, fondos y capacidad siguen siendo validados
  contra datos del servidor; `useAAPoint` y `openType` no son autoridad de
  precio.
- La creación del item y el descuento conservan el commit atómico existente.

## Validación automatizada

```text
MerchantPurchaseProtocolTests: 4/4
AAEmu.Tests: 318/318
ScriptCompiler: 0 errores, 8 warnings conocidas
git diff --check: correcto
```

Los fixtures cubren la captura real, opcode/nivel, compra múltiple, recompra,
`openType` y rechazo de más de 16 líneas.

## Despliegue

```text
imagen game activa:
sha256:5e182ff1e12e887f69e0288df6287d5e21bbd74b710d652bf47031775aa5becf

imagen game anterior conservada:
sha256:6c5bc0b0b28848c86c69b92e1f5e6566aaa790f39c61792f28e52e954aaec660

backup MySQL:
D:\Proyectos\AAemu\backups\pre-aa8-merchant-purchase-v1-20260731-0130.sql
sha256=4D95E8D3389A45D7CA883217B4990A1D954612D64405834E8822BB72935112A9
```

Sólo se reconstruyó y recreó `game`. El contenedor quedó activo, el compact
montado conserva su hash, los puertos 2239/2250 escuchan, Login registró
GameServer 1, ScriptCompiler terminó sin errores y no aparecieron errores o
fatales nuevos durante el arranque.

## Retest manual controlado

1. Entrar con Dannia y abrir el comercio de Deven, NPC template 5342.
2. Comprar exactamente una `Explorer's 1H Weapon Crate`, item 47868, por 250
   copper.
3. No abrir la caja, no comprar un segundo item y no reloguear.
4. Auditar logs, saldo e instancia persistida antes de continuar.

