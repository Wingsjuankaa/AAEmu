# Checkpoint V13: caché global prequest y cierre total de strings de quests

## Alcance

Este checkpoint reconstruye la caché global de strings anterior al call 480
del cliente Kakao 8.0.3.12 r558734 y cierra las 7.926 referencias pendientes
en los 16 resultados de quests que seguían incompletos en V12.

El trabajo es exclusivamente forense. No implementa mecánicas, no modifica
AAEmu, compact, MySQL ni runtime y no usa wiki o datos históricos como
autoridad.

## Reconstrucción demostrada

La caché recuperada contiene exactamente 315.732 entradas continuas:

```text
primera referencia: 0
siguiente referencia: 315732
SHA-256 del mapa: C9DC2FCDFEEF4D66CC6B9989145EC290CEF613CF34B5B2C50877BC8BD3046E8D
```

El digest serializa cada entrada como
`uint32_le(reference) + uint32_le(utf8_length) + utf8`.

La reconstrucción combina seis segmentos con fronteras independientes:

1. Replay en orden de ejecución de calls 3–119, incluyendo los resultados
   headerless 38–46, 110 y 112 y preservando como ausentes 67 y 94–96.
   Termina exactamente en `attach_anims=150126`; también vuelve a demostrar
   `skills=75557`.
2. Ventana de firmas `[150126,193700)` calibrada con delta ordinal 395 entre
   `attach_anims` e `item_guide_b_categories`.
3. Replay exacto de calls 166–174, que produce `[193700,194050)`.
4. Bloque crudo headerless entre offsets 75.937.333 y 80.917.979:
   exactamente 22.813 strings, referencias `[194050,216863)`.
5. Replay headerless de `items`: 21.420 filas y 28.636 inserciones, referencias
   `[216863,245499)`. Se conserva sin reinterpretar la referencia anómala
   10.849.003 de una fila negativa.
6. Ventana `[245499,315732)` calibrada con delta 1.099 en
   `item_armors`, `item_rnd_attr_categories`, `doodad_funcs` y
   `quest_categories`.

No se aplicó una proyección lineal global. El stream contiene candidatos que
cambian el delta entre regiones; cada ventana usada está acotada por anchors
nativos y los cambios se salvan mediante replay exacto.

## Resultados cerrados

Los 125 resultados del núcleo de quests quedan sin referencias `<ref:N>`.
Los 16 cierres nuevos son:

| Resultado | Filas | Referencias resueltas | SHA-256 de filas |
|---|---:|---:|---|
| `cinema_subtitles` | 3 | 2 | `C2640CDB9825E4E70B81B5DE3145B06752BBCD96DCA576231E1533508B28CE88` |
| `quest_act_con_accept_npc_emotions` | 2 | 2 | `80E571BDD81B05DA017960E164F960C529490DF70376A9FC14B91DA1AC17917C` |
| `quest_act_obj_aliases` | 4.962 | 114 | `57CBE186D9FAAB285D5F9CEE21DE889D9CC974335CE024004DFE0C760061261A` |
| `quest_act_obj_sell_backpack_goods` | 7 | 5 | `109A41E741ECD03AF62C6DCB94E661B3D47C4FB275766F57EF9EEA34DD9FF139` |
| `quest_act_obj_spheres` | 258 | 19 | `9C89CC2849DA771DAE417355B23309136F6FBC8EEBD20DD28B188740CF4B439B` |
| `quest_cameras` | 104 | 17 | `B9B72C745C17EB8D59D7C2FBD795FA9338FC49177E5AAEBD7CCE2B12114BB7A8` |
| `quest_categories` | 200 | 77 | `4B1C643204B13816313DCD524FCE40DF0C3CC0817A3CD0567F902A05907B41E5` |
| `quest_chat_bubbles` | 25.939 | 6.705 | `020EC7EBC1CA1134A62D2F77F871E6B72E8F6E8768FDD8DFA12B2A36402DFE8A` |
| `quest_context_groups` | 36 | 2 | `5932F6EC34383A0A30D256147C1C4DBA957A8780FE6A1FCA77A21FEE96279629` |
| `quest_contexts` | 7.826 | 639 | `B1B21871478BBBA3E7D336959891197087825A1E9E98FCCF43BA8E8B4660EC7B` |
| `quest_doodad_groups` | 18 | 3 | `71ADDE47998F2BFB50007FD1AA49173DBB9D44CE2D09EC5496EB5ECAB84489D2` |
| `quest_item_groups` | 81 | 21 | `49B14C0D7DCE7162CFF9BB10D7804C8E662AC81B1D172087C6582FBC2132E8D2` |
| `quest_monster_groups` | 1.006 | 213 | `F917C5D891EE118D9CA17D235D131FBAD77458C6B4FF269F9559CEC029D71902` |
| `quest_names` | 1.673 | 87 | `52FB6D21235A10A106A015C48EF263D044896D20206658EDA61A5212A9086DFE` |
| `today_quest_groups` | 128 | 15 | `BFCE00B4FF7681F6F02B3B61429793E13357BE6C43484664C81AAD5446C948D7` |
| `today_quest_steps` | 25 | 5 | `9FF180BECFD8C20A7A9F391A35A608F215481C67A33A649DD9FEF15294B74886` |

`quest_chat_bubbles` se verificó además semánticamente en las filas inicial,
1.000 y final: IDs 32, 6.724 y 44.534, con sus textos coreanos completos.

## Propagación al grafo

- Stage 40 contiene 126/126 cached results en estado `confirmed`.
- Sus 180.873 cached rows contienen cero `<ref:N>`.
- La región `stage40:opaque:quest-string-cache` desaparece; Stage 40 conserva
  cuatro regiones opacas reales ajenas a esta frontera.
- Stage 90 elimina exactamente 16 raíces y entradas de cola: 452 → 436.
- Ya no existe ninguna raíz `query_incomplete`.
- La consolidada conserva 436 raíces y 436 entradas de cola.

Distribución actual de las 544.827 filas de cobertura:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 345.135 | 63,3476% |
| `corroborated` | 39.424 | 7,2361% |
| `not_applicable` | 13.416 | 2,4624% |
| `tombstone` | 969 | 0,1779% |
| `unknown` | 141.992 | 26,0619% |
| `missing` | 3.881 | 0,7123% |
| `blocked` | 10 | 0,0018% |

Estos porcentajes describen filas de cobertura, no un porcentaje único del
cliente completo.

## Implementación

- `client_forensics/global_strings.py`
  - scanner estricto de firmas de strings internadas;
  - digest continuo y ordenado del mapa global.
- `client_forensics/quests.py`
  - replay exacto de productores prequest;
  - calibraciones y ventanas acotadas;
  - resolución externa de todos los resultados quest;
  - guardas de conteo, offsets, referencias y anomalías preservadas.
- `client_forensics/stage40.py`
  - no materializa una región opaca cuando el contador pendiente es cero.
- `client_forensics/tests/test_core.py`
  - fixture del scanner/digest;
  - digest del mapa global;
  - hashes, conteos y muestras de los 16 resultados.
- versión de herramienta: `0.20.0`.

## Validación

- 26/26 pruebas Python aprobadas.
- Dos builds Stage 40 byte a byte idénticos.
- Dos builds Stage 90 byte a byte idénticos.
- Dos consolidaciones explícitas byte a byte idénticas.
- `quick_check=ok` e `integrity_check=ok` en Stage 40, Stage 90 y consolidada.
- Cero propiedades, relaciones, cached results, cached rows, blocker impacts o
  entradas de cola huérfanas.

Conteos principales de la consolidada:

- 1.657.484 entidades;
- 6.950.492 propiedades;
- 2.113.623 relaciones;
- 544.827 filas de cobertura;
- 89 regiones opacas;
- 436 raíces causales y 436 entradas de cola.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-40-quests.sqlite` | `333BD6F214137480364C1F6ACEFA2A829F82FB685E3F46A7A5D4AAE6DE46F8CC` |
| `stage-40-quests.manifest.json` | `1C117F87D7870AA60AACB5C776841F8F7C6E2665A6C7DFAF8963A303A90EB42A` |
| `stage-90-coverage-closure.sqlite` | `BF3D54299D5F48EFDFEF1D55A13F8BCF3A8C583C2EABA3FC90F69194396D37D3` |
| `stage-90-coverage-closure.manifest.json` | `40C5769FA7C3556ED3825F66C99E03BA1D0FDECD9CD30BBCAC0DCDC15D258CAB` |
| `aa8-client-knowledge.sqlite` | `D09C39DBB07A982011FBD56B70D7706BA5581C4FEBA6795445C4004B4CCA2774` |
| `aa8-client-knowledge.manifest.json` | `21E9D4A51610E83F23F66AC0EB03DA85048815190BD50AC752840A55B0F53A63` |
| manifest final | `12A67FD55FE172FD5D6CF12DE775249339E4BA631A511B6E2F9F8964771C921A` |
| cola CSV | `3B86176163C1BBA88B1F9F244BF40A307284FB4553DE61159B31F713430A8232` |
| visor de cobertura | `55343345334E351B2144E3AD809AA56E4AF6F4E68E860D637DD8B26818655156` |

## Siguiente frontera recomendada

La cola genérica sitúa `loot_pack` en primer lugar, pero esa frontera ya fue
agotada en V2: ambas consultas y layouts x86/x64 están demostrados y el
resultado nativo no existe en compact, secuencia cacheada ni en el barrido
estructural de `game0…game11`. Debe permanecer bloqueada hasta que aparezca
una autoridad nueva; repetir el mismo barrido no aumenta cobertura.

La siguiente frontera informativa es la reconciliación de identidad y
lifecycle de endpoints `item` referenciados:

- 278 IDs positivos `referenced_endpoint_not_in_decoded_stages`;
- 2.289 IDs positivos `referenced_endpoint_not_in_prior_stages`;
- 58 IDs aparecen en ambas raíces, por lo que son 2.509 endpoints únicos y no
  2.567;
- 22.257 es el fan-out entrante sumado de ambas raíces; al deduplicar sus
  relaciones son 18.297;
- autoridad propietaria ya disponible en el resultado nativo completo de
  `items` y en Stage 20.

El objetivo es separar presencia, filtros, tombstones y referencias realmente
huérfanas, reusar el resultado `items` ya descifrado y corregir cualquier
problema de reconciliación entre stages sin inventar objetos.
