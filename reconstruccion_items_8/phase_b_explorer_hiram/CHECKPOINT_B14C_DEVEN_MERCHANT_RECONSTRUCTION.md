# Checkpoint B14c — reconstrucción corroborada de la tienda de Deven

Fecha: `2026-07-31`

Estado: `aceptacion_completa_jsonl_activo_limpiado`.

## Resultado

La tienda de Deven (`npc_template_id=5342`) queda definida con sus 37
relaciones nativas, en el orden y grado observados en los packs nativos 119 y
120. El servidor usa el pack reconstruido `914119`.

- 3 cofres ya funcionaban: `47868`, `47869`, `51185`.
- 34 relaciones fueron capturadas al rechazarse compras reales.
- 10 templates estaban presentes en el compact AA8 y se promovieron tras
  cerrar su evidencia.
- 24 templates ausentes se materializaron mediante la excepción legada
  corroborada.
- No quedan relaciones bloqueadas para este NPC.

## Excepción de autoridad aplicada

El uso de Compact 3.0 fue autorizado expresamente por el usuario para
materializar contenido que existe en AA8. No se tomó como autoridad autónoma.
La excepción quedó limitada por cuatro pruebas independientes:

1. `game11` contiene exactamente los 37 items en dos resultados nativos
   idénticos, packs 119 y 120.
2. El cliente en vivo mostró la tienda y produjo 34 intentos rechazados sin
   duplicados.
3. La wiki de la versión compatible lista esos items como stock de Deven y
   corrobora identidades, precios y usos visibles.
4. Las dependencias de los 24 templates —24 skills de uso, 41 relaciones de
   efectos y los holdables necesarios— ya existían en el runtime AA8.

Por eso se importaron únicamente 39 filas estáticas: 24 de `items` y 15 de
`item_weapons`. No se importaron skills, efectos, fórmulas, probabilidades,
paquetes, opcodes ni comportamiento legado.

Provenance de la excepción:

```text
legacy_3_0_corroborated
```

Si un valor legado contradice AA8, prevalece AA8. Los nueve wrappers
Illustrious tenían un precio obsoleto de 1 cobre en 3.0 y se fijaron en
`500000` cobre (50 oro), conforme a la tienda AA8 observada, sus wrappers AA8
equivalentes y la wiki. Los precios de los items Honor se conservaron sólo
porque la interfaz AA8 y la wiki los corroboraron.

## Evidencia

```text
captura JSONL:
D:\Proyectos\AAemu\rama_8\runtime-captures\merchant-purchase-reconstruction.jsonl
sha256=A3BADD1D968AC200CEA486E7EFCB557456FDD404D37AB850303F9C30ECB161DA
líneas=34
claves distintas=34

captura visual de tienda:
sha256=7EC0693B049D81EE6CF240B227F1DA35B84B63F01A7357FB5FA553484E2B26F3

wiki NPC:
https://wiki.archerage.to/na-en/db/npcs/5342

ejemplos de items:
https://wiki.archerage.to/na-en/db/items/23862
https://wiki.archerage.to/na-en/db/items/18391
https://wiki.archerage.to/na-en/db/items/18419
https://wiki.archerage.to/na-en/db/items/23894
```

El manifiesto con hashes de `game11`, compact cliente, compact legado, runtime
base, captura y los 34 dossiers es:

```text
reconstruccion_items_8/phase_b_explorer_hiram/manifest-b14c-deven-merchant.json
```

## Runtime

```text
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-point0-merchant-deven-v1.sqlite3
sha256=1625ABD2DA6E6350A0F64B6ADAA90FF61CCD93FE32F480DB3DB282640B998E66
quick_check=ok
integrity_check=ok
merchant_goods pack 914119=37
```

El builder produjo dos copias idénticas byte a byte. La validación específica
comprueba stock, orden, grados, moneda, precios, templates, cobertura y
dependencias de skills.

## Pruebas

```text
test_b14c_deven_merchant_runtime.py: 5/5
MerchantPurchase* dirigido:          11/11
AAEmu.Tests completo:                321/321
ScriptCompiler:                      0 errores, 8 warnings conocidas
skill quick_validate:                válido
```

## Aceptación manual pendiente

Despliegue previo a la prueba:

```text
game recreado sin dependencias=true
login recreado=false
db recreada=false
runtime montado sha256=1625ABD2DA6E6350A0F64B6ADAA90FF61CCD93FE32F480DB3DB282640B998E66
merchant packs cargados=96
ScriptCompiler=0 errores, 8 warnings conocidas
Game 2239=listen
Stream 2250=listen
LoginServer registration=ok
RestartCount=0
captura JSONL antes de comprar=34 líneas
```

Baseline persistido de `Dannia` antes de reconectar:

```text
character_id=1
money=1410069575
honor_point=0
inventario_expandido=50
item 23862=0
item 31693=0
item 18391=0
```

Después de montar el runtime, hacer sólo una compra inicial de un item antes
rechazado, preferentemente `23862` (Cloaked Illustrious Dagger), con un espacio
libre en el bolso. Detenerse inmediatamente para comprobar:

- que apareció exactamente una unidad;
- que se descontaron exactamente 50 oro;
- que no se agregó una nueva relación al JSONL;
- que logs y MySQL coinciden con el inventario visible.

Sólo después de esa inspección continuar con un template AA8 promovido y un
arma Honor. No comprar todavía los 34 en lote durante la primera aceptación.

## Primera compra aceptada

La compra controlada de `23862` fue confirmada por el flujo autoritativo:

```text
hora servidor=03:00:57
character=Dannia
npc_template_id=5342
merchant_pack_id=914119
líneas=1
money=500000
honor=0
vocation=0
resultado=commit
```

Después del commit, el JSONL conservó exactamente 34 líneas y el mismo SHA-256
`A3BADD1D968AC200CEA486E7EFCB557456FDD404D37AB850303F9C30ECB161DA`.
No hubo error ni rechazo del flujo de mercader. La persistencia MySQL todavía
mostraba el baseline porque el personaje continuaba conectado; queda pendiente
salir limpiamente a selección de personaje y volver a inspeccionar dinero e
item antes de autorizar la siguiente compra.

### Persistencia confirmada

Después de salir limpiamente a selección de personaje:

```text
character_id=1
updated_at=2026-08-01 03:03:12
money esperado=1409569575
money persistido=1409569575
item template_id=23862
item instance_id=16777226
slot_type=Inventory
slot=9
count=1
grade=0
filas del template=1
unidades totales=1
```

El guardado persistió exactamente una unidad y un descuento de `500000`
cobre. El JSONL siguió en 34 líneas con el mismo hash. La primera aceptación
legada corroborada queda aprobada. El siguiente stop point es comprar una sola
unidad de `31693` (Cloaked Illustrious Greatsword), perteneciente al grupo de
templates que ya existía en el compact AA8 y fue promovido.

## Segunda compra aceptada

La prueba de `31693` (Cloaked Illustrious Greatsword) alcanzó el commit:

```text
hora servidor=03:07:14
character=Dannia
npc_template_id=5342
merchant_pack_id=914119
líneas=1
money=500000
honor=0
vocation=0
resultado=commit
```

No apareció ningún rechazo del flujo de mercader. El JSONL conservó 34 líneas
y el SHA-256 original. MySQL aún mostraba el baseline posterior a la primera
compra porque el personaje seguía conectado; queda pendiente la salida limpia
y la comprobación de persistencia de `31693` antes de probar un arma Honor.

### Persistencia y estrategia de muestreo

La salida limpia confirmó:

```text
updated_at=2026-08-01 03:08:22
money esperado=1409069575
money persistido=1409069575
item 31693 instance_id=16777227
slot_type=Inventory
slot=10
count=1
grade=0
filas=1
unidades=1
```

Con `23862` y `31693` quedan cubiertas las dos procedencias de templates:
materialización legada corroborada y template AA8 promovido. No se repetirá el
ciclo por cada wrapper. Sólo queda una muestra estructural distinta: `18391`
(Honor's Slashing Dagger), porque se instancia como `ItemWeapon`, depende de
una fila `item_weapons`, usa grado 2 y cuesta `1000000` cobre. Si esa muestra
persiste, se autoriza la prueba en lotes de los items restantes.

## Tercera compra aceptada

La muestra estructural `18391` alcanzó el commit:

```text
hora servidor=03:10:09
character=Dannia
npc_template_id=5342
merchant_pack_id=914119
líneas=1
money=1000000
honor=0
vocation=0
resultado=commit
```

El JSONL mantuvo 34 líneas y el mismo SHA-256. No hubo rechazo ni error del
flujo de compra. Sólo queda un último guardado limpio para verificar que MySQL
persistió la instancia como `ItemWeapon`, template `18391`, grado 2 y una sola
unidad. Tras esa comprobación no se harán más pruebas individuales: los items
restantes se podrán comprar en lotes de hasta 10.

### Persistencia final y autorización de lotes

La salida limpia confirmó la instancia especializada:

```text
updated_at=2026-08-01 03:11:24
money esperado=1408069575
money persistido=1408069575
item 18391 instance_id=16777228
type=AAEmu.Game.Models.Game.Items.Weapon
slot_type=Inventory
slot=11
count=1
grade=2
details_bytes=48
filas=1
unidades=1
```

El bolso tenía 50 slots, 12 ocupados y 38 libres. Hay espacio suficiente para
comprar las 34 entradas de tienda distintas de las tres muestras, incluso si
ninguna apila. Quedan aprobadas las tres clases representativas:

1. template genérico materializado desde legado corroborado, grado 0;
2. template genérico AA8 promovido, grado 0;
3. template legado especializado `ItemWeapon`, grado 2 y detalles persistidos.

Se autoriza comprar el resto del stock en lotes de hasta 10 líneas, sin abrir,
usar, equipar ni vender los objetos durante la prueba. Al finalizar todos los
lotes se hará una sola salida limpia y una auditoría global de las 37
relaciones, commits, dinero, inventario y captura JSONL.

## Auditoría global y limpieza de captura

La compra final reprodujo exactamente las 34 relaciones que habían sido
capturadas originalmente:

```text
commit 03:14:56: líneas=10 money=5000000
commit 03:15:04: líneas=10 money=6000000
commit 03:15:13: líneas=10 money=12000000
commit 03:15:26: líneas=4  money=4400000
total:             líneas=34 money=27400000
```

Persistencia después de salir a selección de personaje:

```text
updated_at=2026-08-01 03:15:44
money antes del lote=1408069575
money esperado=1380669575
money persistido=1380669575
templates capturados esperados=34
templates capturados presentes=34
problemas de filas/unidades=0
problemas de grado=0
problemas de tipo=0
problemas de detalles ItemWeapon=0
items genéricos grado 0=18
ItemWeapon grado 2 con details_bytes=48=16
```

Los tres cofres `47868`, `47869` y `51185` no formaban parte del JSONL porque
ya funcionaban antes de esta reconstrucción. La auditoría final se hizo sobre
las 34 relaciones restauradas.

Antes de limpiar, el archivo activo seguía intacto:

```text
líneas=34
sha256=A3BADD1D968AC200CEA486E7EFCB557456FDD404D37AB850303F9C30ECB161DA
```

Se movió de forma recuperable a:

```text
D:\Proyectos\AAemu\rama_8\runtime-captures\archive\merchant-purchase-reconstruction-deven-5342-restored-20260801T031544.jsonl
líneas=34
sha256=A3BADD1D968AC200CEA486E7EFCB557456FDD404D37AB850303F9C30ECB161DA
```

El archivo activo se recreó vacío y el contenedor confirmó:

```text
/app/runtime-captures/merchant-purchase-reconstruction.jsonl
bytes=0
líneas=0
```

La captura continúa habilitada para descubrir relaciones faltantes de otros
NPC, pero Deven ya no ocupa el archivo activo.
