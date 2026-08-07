# Checkpoint V1: cierre estático de `item_accept_quests`

Fecha de cierre: 2026-07-31

Cliente fijado: Kakao `8.0.3.12 r558734`

## Resultado

El consumer `legacy:item-forensics:query-consumer:33` quedó comprendido sin
instrumentación dinámica. Es `LoadItemAcceptQuestDescs`: carga la relación
`item_id -> quest_id` desde `item_accept_quests` y la conserva en dos arreglos
paralelos del catálogo de items.

La clasificación original mezclaba arquitecturas por una igualdad accidental
de RVA. `0x00A23770` es el cargador en x64, pero esa misma RVA en x86 pertenece
a una búsqueda de índices sin SQL. El cargador x86 real está en `0x00D1B380`.
El índice semántico ahora conserva la función rechazada como evidencia y usa
solamente el par corroborado.

No se ejecutaron decompiladores. No se modificó AAEmu, `.env`, MySQL, compact
runtime ni Docker. No se ejecutó, analizó o instrumentó anticheat y no se usó
red pública.

## Identidad exacta

| Rol | Arquitectura | RVA | SHA-256 de bytes |
|---|---|---:|---|
| cargador confirmado | x64 | `0x00A23770` | `9B92F7511E19A8340782175BC9CAEA74AC0B24D7849FA96EF1BF61A744FA3D00` |
| cargador confirmado | x86 | `0x00D1B380` | `B0A76F01C2B2354C75F29B1F0910FC6B803E5B3443F1582A5134314C37E18D3D` |
| coincidencia por RVA rechazada | x86 | `0x00A23770` | `7AD0BE8A7AFBF07A1FDB1AFCCED6D8E01C970A3F36FFD32988CBCA497FA0329D` |

El par confirmado comparte:

- `SELECT item_id, quest_id FROM item_accept_quests`;
- el identificador de error `LoadItemAcceptQuestDescs`;
- el ciclo `SQLITE_ROW` (`100`) / `SQLITE_DONE` (`101`);
- lectura de las columnas 0 y 1 como enteros de 32 bits;
- dos arreglos paralelos y un contador incrementado por fila;
- publicación/finalización del bloque solamente después de `SQLITE_DONE`.

Las llamadas indirectas eran la interfaz del proveedor SQLite: preparar la
sentencia, avanzar, leer un entero y finalizar. La paridad x86/x64, los códigos
SQLite y los mensajes de error eliminan el bloqueo semántico; no falta observar
una decisión de gameplay en ejecución.

## Valor para el backend

Esta superficie define qué quest se asocia a un item de la familia
`accept_quest`. El resultado nativo anuncia 779 filas. El corpus histórico de
items contiene 643 descriptores confirmados; 37 tienen `quest_id=0`, por lo que
quedan 606 relaciones no nulas hacia 576 quests distintas.

La diferencia entre las 779 filas anunciadas y los 643 descriptores
normalizados es una cuestión separada de cobertura de datos. No representa
código opaco dentro del loader y no justifica captura dinámica para comprender
esta función.

## Overlay y dossier

El overlay admite ahora resoluciones exactas de consumers. Una revisión debe
listar las funciones aceptadas y rechazadas por identidad completa, declarar
método/evidencia y reemplaza los seeds automáticos sólo para esa raíz.

```text
overlay SHA-256: B454F6B560F89B7F120A5041E4347971DDFF3C3C55F214EBCF4CB42F6408D27B

dossier: E:\AAEmu-Research\output\aa8-native-code\semantic-dossiers\item-accept-quests-loader-static-v1.json
bytes: 12.641
SHA-256: 241158C3931F1665509EE24601BD49CA97C3F25CA5E6A17C6CFAD02544556390
```

## Índice semántico reproducible

Dos construcciones consecutivas produjeron el mismo archivo:

```text
path: E:\AAEmu-Research\output\aa8-native-code\native-semantic-index.sqlite
bytes: 599.400.448
SHA-256 build 1: A3C4B4A49E89603ACF31381121301A67E0D8130B20988572E8033DFD9C6E1DAD
SHA-256 build 2: A3C4B4A49E89603ACF31381121301A67E0D8130B20988572E8033DFD9C6E1DAD
manifest SHA-256: 1A31252FB9481BE4A61BC402466EB73F8FA4892BA2340A1F704E121B4353EEDE
```

Cambios frente al cierre Whirlpool:

- raíz `consumer:...:33`: 174 funciones -> 56;
- seeds: x64 correcto + x86 por misma RVA -> x64 correcto + x86 real;
- estado: `blocked_by_indirect_dispatch` -> `understood`;
- `understood`: 69 -> 70;
- `blocked_by_indirect_dispatch`: 260 -> 259;
- enlaces raíz -> función: 477.308 -> 477.190;
- razones de incertidumbre: 17.970 -> 17.859;
- 56 regiones dejaron de aparecer como contexto alcanzable porque sólo estaban
  conectadas por la función x86 falsa; ninguna región crítica fue ocultada.

## Integración consolidada

```text
path: E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite
bytes: 8.843.673.600
SHA-256: 9461C0DCAA69295567004DD5380D517F98E2E88CA37768F5129BBD592327E276
manifest de etapa SHA-256: 5136A1C91EFE24AB3514B99D1F3D1F29CFEBC10CD1632D30218A18DCC47B6973
manifest global SHA-256: D62CBD76AA23D66359F187DE35D2D954C93F03AE31DD47E6921229E316F9E097
```

Validaciones:

- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- 0 referencias semánticas huérfanas;
- 132/132 consumers y 662/662 query specs clasificados;
- 78/78 pruebas aprobadas;
- visor y manifest global regenerados.

## Siguiente acción

Revisar la nueva raíz no cerrada de mayor rango:

```text
rank: 3
root: consumer:stage20:item-grades:order-consumer-x86
consumer: LoadItemGradeOrder
estado automático: blocked_by_opaque_region
cierre: 11 funciones, no truncado
```

Primero se debe comprobar si la región opaca es código causal, una tabla de
datos o alineación. Sólo un bloqueo de conducta real justificaría evidencia
dinámica.
