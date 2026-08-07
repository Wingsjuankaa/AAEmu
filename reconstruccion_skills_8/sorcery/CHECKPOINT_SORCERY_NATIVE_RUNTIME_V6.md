# Checkpoint Sorcery AA8 runtime v6

Fecha: 2026-08-04  
Cliente: ArcheAge Kakao 8.0.3.12 r558734  
Estado estático: cerrado  
Estado de aceptación manual: pendiente

## Resultado

Sorcery v6 conserva el cierre ejecutable de v4 y las 222 localizaciones AA8
exactas de v5. La frontera que todavía se describía como “estructura candidata
10.x” quedó reducida: las 21 filas funcionales de los doodads de Wave Gods'
Whip y Magic Circle ancestral existen directamente en el resultado cacheado
`game11` de AA8.

El runtime activo es:

- `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v6.sqlite3`;
- SHA-256 `FD9B16F571628B869B1B0356ECFB5A432904063F94E3BB33392673471198B133`;
- `quick_check=ok`;
- `integrity_check=ok`.

El manifiesto reproducible es
`generated/sorcery-specialization-v6.manifest.json`, SHA-256
`6DB3328CFE5420226B4A726ED7875B9704CDCF63BC4E321BB558261E699FC495`.

## Nueva evidencia nativa

Fuente binaria:

- `E:\AAEmu-Research\output\compact-8.0-extracted\game11`;
- SHA-256 `E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031`.

El decodificador cacheado ya cubría doodad roots, groups, funcs, phase funcs y
clouts. V6 añadió dos límites AA8 que antes sólo tenían layout estático:

| Resultado | Inicio | Fin | Filas | SHA-256 de filas |
|---|---:|---:|---:|---|
| `doodad_func_finals` | `0x63D6590` | `0x63EE303` | 4.358 | `4E9096D34F09FDC8B3BB5B8AC2CCF7F023A5D98BF243E4B282F776F879E22B85` |
| `doodad_func_timers` | `0x63F3090` | `0x643B261` | 15.004 | `70F7B81648B79AEF2C59CCC05B2AF9DA8E0CCF306A7AFA7D2A352BC024D66A7E` |

La reconstrucción transversal ahora reconoce como funciones soportadas
`DoodadFuncClout`, `DoodadFuncTimer` y `DoodadFuncFinal`. Ya no aísla timers y
finals como fases desconocidas cuando una especialización alcanza esos tipos.

## Cierre promovido

Wave Gods' Whip:

- doodads AA8 `13406/13407`;
- grupos `38626…38630`;
- fases `49136,49137,49339,49340,49913`;
- timers `16372/16373`, ambos con delay exacto de `1000 ms`;
- finals `5304/5305/5320`, con `after=5000/1000/1000 ms`.

Magic Circle ancestral:

- doodads AA8 `14623/14666`;
- grupos `43090/43245`;
- fases `55165/55330`;
- clouts `4116/4121`;
- buffs `25646/25647`, projectiles `1126/1131` y AoE
  `16482/16501`, todos ya pertenecientes al cierre AA8.

La comparación de campo produjo:

- 21 filas nativas;
- 219 campos exactos AA8;
- 19 filas completamente exactas;
- 2 filas con cuatro campos literales resueltos;
- 7 columnas `comment` que son defaults vacíos del esquema del servidor.

Los cuatro campos no son propiedades inventadas: `game11` conserva sus IDs de
referencia global, y la fila estable 10.x resuelve el modelo/nombre literal.
Por ello su clasificación es
`aa8_native_with_bounded_string_reference_resolution`, no autoridad de balance
10.x.

## Raíces tombstone y localización

Las raíces visibles `10151` Freezing Earth y `10153` Insulating Lens siguen
siendo tombstones AA8: no existe su fila padre en el resultado completo de
`skills`, aunque tienen respectivamente 20 y 18 relaciones entrantes nativas.
V6 conserva el padre acotado y todos sus descendientes AA8.

V5 corrigió 222 textos exactos desde el compact AA8 (126 de skills y 96 de
buffs). Dos correcciones contractuales especialmente importantes son:

- Freezing Earth aplica Ice Shard/Snare; el texto AA8 no declara una tirada de
  probabilidad;
- Insulating Lens dura 40 s, absorbe daño, da inmunidad a Trip, explota y
  Snarea a 6 m, y aplica cooldown de 30 s cuando termina.

## Gate de aceptación

`validate_sorcery_runtime_v6.py` verifica:

1. el gate v5 completo: 2.272 filas AA8 exactas, 222 localizaciones y cero
   raíces bloqueadas;
2. las 21 filas contra el binario AA8 y contra el runtime;
3. los hashes/límites de los cinco resultados doodad involucrados;
4. que v6 sea idéntico a v5 en todas las tablas funcionales;
5. que sólo se añada la tabla de evidencia y cambien tres metadatos de
   autoridad.

Resultado: cero errores y cero warnings. El runtime y manifiesto resultaron
idénticos en dos construcciones consecutivas sobre el mismo destino.

Artefactos del gate:

- `generated/sorcery-runtime-acceptance-v6.json`, SHA-256
  `643905967116411B564C0A364505F6CD74BB82ED4A7546961A6FD3451C427539`;
- `generated/sorcery-runtime-acceptance-v6.csv`, SHA-256
  `F09CB02C556632923786A7A65F6A533F310A8A1BD0F3D6FC246BC1B8E50D3268`;
- 22 pruebas Sorcery aprobadas: 7 estructurales v4 y 15 de semántica/gates
  v4-v6.
- suite completa `AAEmu.Tests`: 410/410 aprobadas, cero omitidas y cero fallos
  (`DOTNET_ROLL_FORWARD=Major`, porque el host local no conserva .NET Core 3.1).

## Despliegue

`.env` apunta a v6 y sólo se recreó el contenedor Game. MySQL y Login no se
reiniciaron. Dentro del contenedor, `/app/Data/compact.sqlite3` tiene SHA-256
`fd9b16f571628b869b1b0356ecfb5a432904063f94e3bb33392673471198b133`.
Game abrió GameNetwork y StreamNetwork, terminó el arranque en
`00:01:49.0205188` y se registró correctamente en LoginServer.

La única frontera restante es conductual/visual. Deben ejecutarse las doce
activas con el protocolo `SORCERY_LIVE_ACCEPTANCE_PROTOCOL_V1.md`, incluyendo
repetición y relog. Un gate estático no puede certificar animación, FX, física
del cliente ni desaparición visual final.
