# Checkpoint V1: cierre estático dirigido de loot pack y gacha

Fecha de cierre: 2026-07-31

Cliente fijado: Kakao `8.0.3.12 r558734`

## Resultado

Se revisó en profundidad la raíz semántica prioritaria `loot_pack` usando el
Stage 15 canónico, sin volver a ejecutar decompiladores. La revisión reemplaza
el diagnóstico automático `blocked_by_opaque_region` por el estado terminal
`blocked_by_missing_native_data`.

La conclusión no declara comprendidas las 1.509 funciones del cierre amplio.
Declara comprendida la cadena funcional relevante y conserva como bloqueo
explícito la ausencia de las filas nativas que contienen la composición y las
probabilidades reales.

No se modificó AAEmu, `.env`, MySQL, compact runtime ni Docker. No se ejecutó,
analizó o instrumentó anticheat y no se utilizó red pública.

## Hallazgos confirmados o corroborados

### Inicializador de nombres de eventos

`x2game.dll` x64 RVA `0x003E7A30` no es un handler de recompensas. Es una
función de inicialización de nombres de eventos/UI que registra, entre otros:

- `GACHA_LOOT_PACK_RESULT`;
- `UPDATE_GACHA_LOOT_MODE`;
- `GACHA_LOOT_PACK_LOG`;
- `LOOT_PACK_ITEM_BROADCAST`.

Sus 863 llamadas apuntan al helper de strings compartidas x64 RVA
`0x000ABFB0`. Esta evidencia elimina la interpretación anterior de esa función
como lógica de selección de loot.

### Resultado gacha recibido desde el servidor

El handler de resultado se recuperó en ambas arquitecturas:

| Arquitectura | Handler | Wrapper de registro | Opcode/ID |
|---|---:|---:|---:|
| x64 | `0x00303A10` | `0x00367440` | `0x28C` (652) |
| x86 | `0x002B7A50` | `0x0034FBE0` | `0x28C` (652) |

El paquete contiene ID, cantidad, hasta 15 entradas de resultado, flag y
código de error. Cada entrada expone al UI/Lua el item completo, `grade` y
`stackSize`. El cliente formatea los links y publica el evento local; no elige
qué recompensa se entrega.

### Broadcast de loot pack

El broadcast se recuperó también en x64/x86:

| Arquitectura | Handler | Wrapper de registro | Opcode/ID |
|---|---:|---:|---:|
| x64 | `0x00306160` | `0x0037CCD0` | `0x18E` (398) |
| x86 | `0x002BA2B0` | `0x003632B0` | `0x18E` (398) |

El mensaje transporta actor, item consumido/origen e item resultante. El
cliente construye links y una notificación localizada; tampoco decide el
resultado.

### Solicitud y presentación cliente

Se fijaron, entre otras, estas funciones x64:

- `0x0019B440`: registro de APIs Lua de gacha;
- `0x0019B1A0`: callback `Execute` y batch count;
- `0x007EB110`: validación de los dos items seleccionados y construcción de la
  acción enviada;
- `0x0012BC80`: callback de estado;
- `0x00760770`: feature flag `lootGacha`;
- `0x007524F0`: proyección visual del item/loot bag.

### Loaders de datos

El binario contiene loaders y layouts para:

```sql
select gacha_loot_pack_id, kind, item_id from gacha_loot_pack_items
select id, gacha_loot_pack_id, add_round, give_term, loot_pack_id, rate, priority from gacha_advanced_loot_packs
select id, loot_pack_id, active from gacha_loot_packs
SELECT id, war_drop FROM loot_packs
```

El loader de `loots` consume además `loot_pack_id`, grupo, item, grado,
cantidades mínima/máxima, tasa, `always_drop`, mensaje global y quest de loot.

## Bloqueo restante exacto

El corpus consolidado contiene 4.195 identidades `loot_pack` y 4.678
referencias desde `gain_loot_pack_item_effects`, pero no contiene las filas
nativas de:

- `loots`;
- `loot_packs`;
- `gacha_loot_pack_items`;
- `gacha_advanced_loot_packs`;
- `gacha_loot_packs`.

Por tanto, el código permite reconstruir el protocolo, el layout, los loaders
y quién toma la decisión, pero no permite enumerar todavía los items ni sus
probabilidades. Una captura dinámica del handler no recuperaría por sí sola el
catálogo completo y no es el siguiente paso correcto para esta raíz.

## Overlay y dossier

Las decisiones viven en:

`config/native-semantic-review-overrides.json`

El builder rechaza una revisión si no coincide exactamente por módulo,
arquitectura, RVA y SHA-256 de bytes. El dossier derivado vive en:

```text
E:\AAEmu-Research\output\aa8-native-code\semantic-dossiers\loot-pack-gacha-static-v1.json
bytes: 181.165
SHA-256: 3E5E727E509794E75692A924B3A9AFF7D7D89D148AD741647A1EF0114A4C9AE1
```

Este dossier fue regenerado posteriormente al añadir snapshots explícitos de
regiones al formato de revisión. La evidencia semántica no cambió; el artefacto
vigente mide 181.191 bytes y tiene SHA-256
`53E2D1720EE05E29B1939F620DE672B2FE95B10AD1AC3F829649A84AB2CCA51E`.

La revisión enumera 20 funciones exactas y no copia pseudocódigo dentro de la
consolidada.

## Índice semántico reproducible

Dos construcciones consecutivas produjeron el mismo archivo:

```text
path: E:\AAEmu-Research\output\aa8-native-code\native-semantic-index.sqlite
bytes: 599.638.016
SHA-256 build 1: 9AAF0DBADD2F4A1B5D9B82A0D688A138EAE7722B10233C51A7CE84831B4CAF22
SHA-256 build 2: 9AAF0DBADD2F4A1B5D9B82A0D688A138EAE7722B10233C51A7CE84831B4CAF22
manifest SHA-256: CF523021981F199F433CB7920862D4D29A8181FEE13A90E8BFCD67ABC3DDF527
overlay SHA-256: 7EF8327B3343B35DFE3AFFF0D2D372800A1AF86B50601F078D9235D28CA79B6B
```

La distribución de cierres cambia exactamente en una raíz:

- `blocked_by_opaque_region`: 606 → 605;
- `blocked_by_missing_native_data`: 102 → 103.

Las 50.011 regiones opacas siguen enumeradas. El avance consiste en saber que
ninguna de ellas es el bloqueo causal de `loot_pack`, no en ocultarlas o
declararlas decompiladas.

## Integración consolidada

```text
path: E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite
bytes: 8.843.673.600
SHA-256: 0118181539737E96EC6883BB26D45782329EB951D88CED7AE6E513CCF8586364
manifest de etapa SHA-256: 720AD9AE8866146A4D3FAA72DA08BF0A0D03693F9EEC002BB64EE878587C0024
manifest global SHA-256: AD18F79CBA8E6D3F5E32C062579A2C475F6920E98B2B5A3E618DECE4C4B0EBF5
```

Validaciones:

- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- 0 referencias semánticas huérfanas;
- 0 violaciones observadas de linaje;
- 77/77 pruebas aprobadas.

## Siguiente acción

Revisar estáticamente la raíz protocolaria de rango 2:

```text
native-symbol:fn:x86:16313361b9c273b596ce832ccf9fe8d1852cfb468e92ba2f87c3bf4a4e428f3f:000252a0:55A3C0BD7C69
```

Primero se debe determinar si su región opaca interrumpe realmente un
serializer/handler o si, como ocurrió con `loot_pack`, el cierre automático es
demasiado amplio. Sólo si la revisión termina bloqueada por conducta en
ejecución corresponderá preparar cobertura dinámica aislada.
