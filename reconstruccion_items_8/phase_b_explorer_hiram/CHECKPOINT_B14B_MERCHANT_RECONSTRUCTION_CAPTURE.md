# Checkpoint B14b — captura de compras pendientes de reconstrucción

Fecha: `2026-07-31`

Estado: `desplegado_captura_y_deduplicacion_real_verificadas`.

## Objetivo

Se añadió una herramienta pasiva al flujo nativo de compra reconstruido en
B14a. Cuando una compra válida del cliente AA8 no puede prepararse o
confirmarse en el servidor, cada relación mercader–ítem solicitada se conserva
en un JSONL persistente para su reconstrucción posterior en lote.

La herramienta no crea items, no altera precios, no descuenta moneda, no
modifica MySQL y no cambia el compact.

## Autoridad de entrada

El paquete sigue siendo el contrato confirmado en B14a:

```text
CSBuyItemsPacket level=5 opcode=0x0F0
máximo defensivo del servidor=16 líneas
máximo observable del carrito del cliente=10 líneas
línea=itemId UInt32 + grade Byte + count Int32 + currency Byte
```

Referencia forense:

```text
item 47868 dossier:
E:\AAEmu-Research\output\aa8-client-forensics\dossiers\item-47868.json
sha256=822660DBD4F77881266B98119F0810BFA51807E07948B19354165C920440E740
```

El precio no está contenido en la línea enviada por el cliente. La captura
guarda la política que conocía el servidor en ese instante; cualquier precio o
relación ausente debe resolverse después desde compact/game0…game11/x2game y
el grafo AA8, nunca inferirse ni importarse desde compact 3.0.

## Archivo persistente

Host:

```text
D:\Proyectos\AAemu\rama_8\runtime-captures\merchant-purchase-reconstruction.jsonl
```

Contenedor:

```text
/app/runtime-captures/merchant-purchase-reconstruction.jsonl
```

Schema por línea:

```text
AA8_MERCHANT_PURCHASE_RECONSTRUCTION_CAPTURE_V1
```

El directorio está ignorado por Git y montado read/write sólo en `game`. El
formato append-only permite conservar todas las líneas completas si el proceso
se interrumpe durante una escritura posterior. Al reiniciar, las claves ya
guardadas se vuelven a cargar; una última línea JSON dañada se ignora y puede
ser observada nuevamente.

## Deduplificación

La clave estable es:

```text
actorKind
| npcTemplateId
| merchantPackId
| doodadTemplateId
| itemId
| grade
| currencyId
```

`npcObjId` y `doodadObjId` se preservan como evidencia, pero no participan en
la clave porque cambian entre spawns. `count` tampoco participa: la relación
que se debe reconstruir es la misma independientemente de la cantidad.

Si una compra de varias líneas falla atómicamente por una sola línea, se
capturan todas las relaciones del lote. Las que el servidor ya conocía quedan
marcadas mediante la instantánea `serverEvidence` y se pueden excluir del
generador posterior.

## Campos de reconstrucción

Cada relación conserva:

- fecha UTC, batch ID, etapa y motivo exacto del rechazo;
- character ID/nombre sólo para correlación local;
- NPC obj/template/name, bandera merchant y merchant pack;
- doodad obj/template cuando participa;
- `unknownId`, `useAAPoint` y `openType` del paquete observado;
- item ID, grade, count, currency ID y nombre del enum;
- presencia del merchant pack y de la relación exacta de stock;
- price override de stock si el servidor lo conoce;
- presencia/nombre/precios del item template;
- estado, tipo concreto, dependencias faltantes y provenance de cobertura AA8.

## Puntos de captura

Se registra una compra con al menos una línea cuando falla en:

1. validación del contexto NPC/merchant pack;
2. tienda doodad cuya relación autoritativa aún no está cerrada;
3. `MerchantPurchaseService.TryPrepare`;
4. `MerchantPurchaseService.TryCommit`.

Payloads malformados, compra/recompra mezclada y lotes vacíos siguen fallando
cerrados y no producen relaciones falsas.

Una excepción de filesystem sólo genera log de error: nunca cambia el
resultado de la compra. Las claves se confirman en memoria únicamente después
de que el append y `Flush(true)` terminan correctamente.

## Validación

```text
MerchantPurchase* dirigido: 11/11
AAEmu.Tests completo:        321/321
ScriptCompiler:              0 errores, 8 warnings conocidas
docker compose config:       ok
git diff --check (alcance):  ok
```

Las pruebas cubren:

- deduplicación dentro de un lote;
- deduplicación durante el mismo proceso;
- deduplicación después de recrear el servicio;
- persistencia de nuevas relaciones;
- modo deshabilitado;
- reintento correcto después de una escritura fallida.

## Runtime y despliegue

Durante el trabajo `.env` avanzó externamente desde V6 al runtime V7 ya
validado. La herramienta no modificó SQLite. El runtime efectivamente montado
es:

```text
compact-8.0-runtime-point0-quest-doodad-loot-proxy-v7.sqlite3
sha256=6C58249234B000F41B10994703F09D1E9F909C05DBEBC5FE4E6F4B6DBECA1792
quick_check=ok
integrity_check=ok
```

Despliegue:

```text
game image=sha256:b7df77680889d05c2e47069c972065bad766477c2b3165a92ae8ea76d0a8a826
game only recreated=true
capture mount rw=true
capture directory writable=true
merchant packs loaded=96
ScriptCompiler errors=0
Game 2239=listen
Stream 2250=listen
LoginServer registration=ok
RestartCount=0
new ERROR/FATAL=0
```

## Captura manual controlada

1. Entrar con un personaje de prueba y dejar espacio libre en el bolso.
2. Abrir un único NPC mercader.
3. Seleccionar como máximo los 10 espacios visibles del carrito y ejecutar una
   compra. Dividir cualquier lista mayor en lotes sucesivos de 10.
4. Si el lote no llega, detenerse y continuar con otro NPC o con otro lote.
5. Si el lote sí llega, no usar ni abrir los objetos: esa compra era conocida
   por el servidor y pudo descontar la moneda normalmente.
6. No borrar ni editar el JSONL entre sesiones; la deduplicación sobrevive el
   reinicio del contenedor.
7. Al terminar todos los NPC/lotes, detener las compras y solicitar el análisis
   del archivo para construir un runtime nuevo de forma determinista.

## Primera aceptación real

La primera interacción aislada produjo exactamente una relación JSONL:

```text
captured_at_utc=2026-08-01T02:18:30.4805539Z
character=Dannia (1)
npc=Deven (template 5342, obj 43861)
merchant_pack=914119
item=23862
grade=0
count=1
currency=Money (0)
failure_stage=prepare
failure_reason=item 23862 grade 0 currency Money is not in the authoritative stock
```

Instantánea del servidor:

```text
merchant_pack_loaded=true
exact_stock_relation_present=false
item_template_loaded=false
native_coverage_catalogue_available=true
coverage_state=Unknown
coverage_can_create=false
```

La compra fue rechazada antes del commit, se envió resync autoritativo del
inventario y MySQL confirmó `0` filas/`0` unidades del item `23862` para
Dannia. El archivo quedó en `1044` bytes con una sola relación válida.

El dossier generado después de la captura identificó:

```text
item 23862: Cloaked Illustrious Dagger
dossier sha256=DC40C970B4D2DF72D5967C063331E6EF11B319491034284F1F7A32D8C025266B
forensic readiness=profile_complete
lifecycle=tombstone
```

El item conserva localización y relaciones tipadas de craft/conversión, pero
está ausente del resultado nativo positivo completo de `items`. Por lo tanto,
la futura reconstrucción por lotes debe clasificar cada captura y nunca
convertir automáticamente un tombstone visible en una definición runtime.

NPC dossier:

```text
npc 5342 dossier sha256=B3CFD3761304AB63A31B56C80CFC520F27E32F8608175E5181B4D9963115C501
forensic readiness=profile_complete
```

Los opcodes desconocidos `0x206`, `0x53` y `0x164` aparecieron durante el
handshake/spawn antes de la compra. No interfirieron con `CSBuyItemsPacket
0x0F0`, su captura ni el resync; quedan fuera del alcance de este checkpoint.

### Aceptación real de deduplicación

Se repitió una sola vez la misma compra:

```text
captured_relation=npc|5342|914119|0|23862|0|0
second_packet_utc=2026-08-01T02:22:49Z
```

El segundo `CSBuyItemsPacket 0x0F0` llegó, fue parseado con la misma línea y se
rechazó nuevamente en `prepare`. No se emitió un segundo log de
`MerchantPurchaseCaptureService` y el archivo permaneció byte por byte
idéntico:

```text
relations_before=1
relations_after=1
bytes_before=1044
bytes_after=1044
sha256_before=3FA3307414DE44DBFC6929C3480DC89FB7D95CCC6C23B710B102D75042C688F8
sha256_after =3FA3307414DE44DBFC6929C3480DC89FB7D95CCC6C23B710B102D75042C688F8
```

MySQL continuó con `0` filas/`0` unidades del item `23862` para Dannia. El log
`Looks like we got double count my guy` coincidió con el resync al rollover del
contador S→C visible `C:255 -> C:0`; pertenece al diagnóstico genérico de
`GamePacket` y no representa una segunda compra ni una segunda relación JSONL.
