# Checkpoint V1: cierre estático de CWhirlpoolHash::SerializeWith

Fecha de cierre: 2026-07-31

Cliente fijado: Kakao `8.0.3.12 r558734`

## Resultado

La raíz protocolaria de rango 2 no era un packet handler. Es la exportación
`CWhirlpoolHash::SerializeWith` de `xlcommon.dll`, disponible en x86 y x64.
Su comportamiento y su cierre quedaron comprendidos estáticamente; no se
requiere captura dinámica.

También se demostró que las dos regiones que la clasificación automática
consideraba bloqueadores críticos son tablas de salto e índices de
`xl_vsprintf`, junto con bytes de alineación. Se conservaron en Stage 15 como
regiones ejecutables originalmente no clasificadas, pero su impacto semántico
cambió de `critical_blocker` a `reachable_context`.

No se ejecutaron decompiladores. No se modificó AAEmu, `.env`, MySQL, compact
runtime ni Docker. No se ejecutó, analizó o instrumentó anticheat y no se usó
red pública.

## Función recuperada

| Arquitectura | Módulo | RVA | SHA-256 de bytes |
|---|---|---:|---|
| x86 | `xlcommon.dll` | `0x000252A0` | `5EBB79661945AA936D60D406640E8D10810160AD8A4D52583D9ACE8176857D8B` |
| x64 | `xlcommon.dll` | `0x00028E00` | `D867AAE27822E68717D7D7602FE77F580789854D978176FE4B3ECC50F969D15F` |

La función:

1. recorre exactamente 64 bytes del objeto `CWhirlpoolHash`;
2. genera los nombres `wp00` a `wp63` mediante `xl_sprintf("%.2i")`;
3. entrega cada byte al wrapper `ISerialize`;
4. usa el slot virtual x86 `0x48` y el equivalente x64 `0x90`, diferencia
   explicada por el ancho de puntero.

Esto serializa un digest Whirlpool de 512 bits. La función es una utilidad
genérica de hash; el cierre no demuestra que forme parte de un opcode de juego
concreto. Sus exports, estructura de bucle y cadena de llamadas coinciden en
ambas arquitecturas.

## Falsas regiones opacas

### x86

```text
región: code-region:0f61478d127a3c16b50a20dc50ccdc76
RVA: 0x000206A6-0x00020740
bytes: 154
SHA-256 de región: DF8F64D44EF8DA2F39D636CCD4237A14297F744958BBC671B05F074C451E243F
consumer: xl_vsprintf RVA 0x00020300
```

Las referencias desde `xl_vsprintf` prueban:

- `0x20350 -> 0x206C0`: tabla de índices;
- `0x20357 -> 0x206A8`: tabla de destinos;
- `0x20469 -> 0x20708`: tabla de índices;
- `0x20470 -> 0x206D4`: tabla de destinos.

El intervalo incluye además `MOV EDI,EDI`/alineación. No contiene una función
faltante.

### x64

```text
región: code-region:e771043dfba322b80358853bbed9c887
RVA: 0x0002492B-0x000249A0
bytes: 117
SHA-256 de región: 149FA501ABDC6B7155A48E67E1BA0D4262D4F31B9B6C40EE799A752C2C51EF51
consumer: xl_vsprintf RVA 0x00024590
```

`xl_vsprintf` carga la tabla de índices desde `0x24960`, la tabla de destinos
relativos desde `0x2492C` y salta al destino calculado. El final son bytes
`INT3` de padding. Tampoco existe una función faltante.

## Overlay y dossiers

El overlay ahora valida también las regiones por:

- `region_key`;
- módulo y arquitectura;
- SHA-256 del binario;
- RVA inicial/final;
- evidencia funcional exacta.

```text
overlay SHA-256: 73052654A0D8A5DD81D5CAB8E941E0DAB64AAEC2E73E146A9C58046835FF972D
```

Dossiers:

```text
E:\AAEmu-Research\output\aa8-native-code\semantic-dossiers\whirlpool-hash-serialize-x86-static-v1.json
bytes: 15.401
SHA-256: 3BE7F1064B0BE060D8352809A48824F5E70A94DED747EF9D950DE22144779E6B

E:\AAEmu-Research\output\aa8-native-code\semantic-dossiers\whirlpool-hash-serialize-x64-static-v1.json
bytes: 15.214
SHA-256: E89D68674CF9C330931A7C59615ECE3DDA7F06B7399DBA7B3B0F6D2F04AA4DBA
```

## Índice semántico reproducible

Dos construcciones consecutivas produjeron el mismo archivo:

```text
path: E:\AAEmu-Research\output\aa8-native-code\native-semantic-index.sqlite
bytes: 599.642.112
SHA-256 build 1: A75C631892DCA0B5A3ACEBCDCC172795E842104B122DC99E3B7033B3DE39E38B
SHA-256 build 2: A75C631892DCA0B5A3ACEBCDCC172795E842104B122DC99E3B7033B3DE39E38B
manifest SHA-256: AB85059E207FFC9538FF600841A2BC24222A52A3B52CE712F2B472388DD27458
```

Cambios exactos frente a la frontera anterior:

- `understood`: 67 → 69;
- `blocked_by_opaque_region`: 605 → 603;
- razones de incertidumbre: 17.972 → 17.970;
- `critical_blocker`: 1.334 → 1.332;
- `reachable_context`: 325 → 327;
- regiones nativas totales: 50.011, sin eliminar ninguna.

## Integración consolidada

```text
path: E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite
bytes: 8.843.673.600
SHA-256: 4C23209C0D785336B856FE35C55929C5BB18127A01B2AA084EBDDEFA15C03DC0
manifest de etapa SHA-256: 7EE89BBC231B6BF20A4C73E20CA1D2CB15CA3409BE938F76EA2D2A7A89D60B93
manifest global SHA-256: ACB1757B5FDC31860ADE991F72C7063F07943B5045C21D96D988481B76C973FD
```

Validaciones:

- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- 0 referencias semánticas huérfanas;
- 77/77 pruebas aprobadas;
- visor y manifest global regenerados.

## Siguiente acción

Revisar el consumer de rango 3:

```text
root: consumer:legacy:item-forensics:query-consumer:33
locator: x2game.dll FUN_39a23770
estado automático: blocked_by_indirect_dispatch
cierre: 174 funciones, no truncado
```

Se debe identificar primero la consulta/entidad que consume, resolver sus dos
seeds x86/x64 y determinar si el dispatch indirecto es causal o contexto
compartido. Sólo un bloqueo de ejecución real justificaría instrumentación.
