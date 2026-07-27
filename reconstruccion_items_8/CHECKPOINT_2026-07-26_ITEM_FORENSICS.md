# Checkpoint AA8 Item Forensics — 26 de julio de 2026

## Resultado

Se implementó `item_forensics` como CLI, base SQLite, auditor dimensional,
reporte estático y generador seguro por familia. El runtime activo fue leído
desde `COMPACT_DB`; no fue modificado ni desplegado.

Baseline reproducible Kakao r558734:

- 21.419 IDs positivos clasificados y una anomalía firmada conservada.
- 4.048 `catalog_only`, 16.223 `phase_a_candidate` y 1.148 `complete`
  entre los objetos positivos del cliente.
- 17.371 descriptores confirmados; 85 bloqueados, 1.813 faltantes y
  2.150 desconocidos.
- 63 layouts registrados: 51 resultados confirmados, 12 bloqueados por
  referencias de strings y 48 consultas todavía sin layout.
- 109 tablas SQL relacionadas con items, procedentes del catálogo global
  de SQL embebido.
- 277 tokens RTTI `Item*Desc` recuperados de los binarios `x2game`.
- `impl_id` aún sin asignación nativa: 4, 14, 26, 31, 32 y 35.

## Cobertura global de cliente

La búsqueda no se limitó a `game11`. La ejecución reutilizó:

- 44 manifests de búsquedas y extracciones ya realizadas;
- 507.873 entradas inventariadas;
- 377.295 rutas del índice completo de `game_pak`;
- 363 archivos externos al pak, incluidas 250 DLL;
- 1.112 Lua decompilados;
- 10.468 textos Lua/XML/config ya extraídos;
- los 12 streams cacheados y ambos `x2game.dll`.

Se registraron 95.251 coincidencias únicas entre objetos y superficies:
968 tienen contexto de item o path corroborativo y 94.283 son tokens
numéricos de baja confianza conservados como `unknown`. Ninguna confirma
gameplay hasta encontrar su consumer nativo.

## Determinismo e integridad

Dos ejecuciones completas consecutivas produjeron:

```text
SHA-256 9C7CFB0CC6FFBA36E7E9FCA1E99625D115A0DE62CCB815A8C0B6A6CA8F0BF31F
MATCH=True
PRAGMA quick_check=ok
PRAGMA integrity_check=ok
```

Salidas:

```text
E:\AAEmu-Research\output\aa8-item-forensics
```

## Candidatos de control

- `evolving_material-9c7cfb0cc6ff`: 70 objetos, 23 con datos nativos
  cerrados y 47 `catalog_only`; verificación correcta.
- `tool-9c7cfb0cc6ff`: 58 objetos, 38 candidatos no resueltos y
  20 `catalog_only`; verificación correcta y bloqueos conservados.

Ambos paquetes tienen seis archivos verificados, `deployable=false` y cero
filas de gameplay histórico 3.0.

## Integración AAEmu

Se añadió un catálogo opcional `aaemu_item_capability_coverage`. Cuando una
compact candidata lo contiene, `ItemManager` carga sus dimensiones y
`/item8 coverage` las muestra. Este catálogo no modifica
`ItemDefinitionCoverageService` ni el gate de creación.

Validación:

- 7/7 pruebas Python.
- prueba C# dirigida correcta.
- suite completa Docker SDK 3.1: 249/249 pruebas.

## Próximo cierre forense

La cola correcta no es una compact masiva. Deben cerrarse primero los 12
resultados con referencias internadas pendientes y los 48 layouts marcados
en `ghidra-layout-tasks.json`; después resolver el factory de los seis
`impl_id` opacos. Sólo entonces conviene promover familias completas con
protocolo, mutación atómica, persistencia y aceptación real del cliente.

## Actualización estructural v1.3

La fase pendiente descrita arriba quedó cerrada sin modificar ni desplegar el
runtime activo:

- 107 especificaciones cacheadas clasificadas.
- 90 resultados directos confirmados.
- 15 resultados resueltos mediante el consumer nativo de localización.
- `item_assets` resuelto mediante la caché global de strings calibrada.
- `items` confirmado para los 21.419 IDs positivos; la única referencia
  restante pertenece exclusivamente a la fila anómala de ID negativo.
- 4 loaders con layout confirmado y resultado nativo legítimamente ausente.
- Cero `layout_missing`, `decode_failed` o referencias de strings bloqueadas
  dentro del inventario positivo.

`item_assets` recuperó 317 referencias distintas de path que afectan 1.290
filas. La asignación ordinal queda encerrada entre dos calibraciones nativas:

```text
actor_models  first_reference=150174  FUN_39a2fdd0
item_procs    first_reference=193088
candidate_index_delta=395
value_digest=7354600C6414AFAD5B880FFD2A7C605B9ACBA24E66F1D2853E51FF5DF1010138
```

El índice completo de `game_pak` corrobora exactamente 312 de los 317 paths.
Los cinco restantes se conservan como paths nativos del stream con evidencia
negativa de archivo ausente; no se sustituyen ni corrigen por aproximación.

El resultado maestro `items` fue recuperado desde:

```text
loader=FUN_39a3c440
start=0x04D2B5DB
rows=21420
positive_rows=21419
```

La función nativa `FUN_39874940` confirmó el switch completo
`impl_id -> item_impl` para los valores 0..35. Las seis familias antes opacas
quedaron asignadas:

```text
4  -> bag
14 -> portal
26 -> music_sheet
31 -> location
32 -> rename_character
35 -> bless_uthstin
```

Los 29/29 objetos `bag` cierran contra `item_bags`; los 40/40
`bless_uthstin` cierran contra `item_bless_uthstins`. Las otras cuatro
familias son tipos sin tabla concreta adicional: su tipo queda confirmado,
pero su backend, protocolo, persistencia y aceptación continúan auditándose
por separado.

Evidencia Ghidra:

```text
ghidra-impl-string-consumers.txt
SHA-256 FD2D81270D45E0103D6E26D804179C800A6F6F0B51ECC596B47E06B9CDD7628C
```

Baseline reproducible actualizado:

```text
aa8-item-forensics.sqlite
SHA-256 A793FC81BEEB6E812A7C6EBF67185AC66BDD02DA273D0CE5EA0460F26DE314A0
MATCH=True
PRAGMA quick_check=ok
PRAGMA integrity_check=ok
ghidra-layout-tasks=0
unmapped_impl={}
```

Estado dimensional:

- 21.284 descriptores confirmados.
- 114 descriptores faltantes.
- 21 descriptores desconocidos.
- Cobertura agregada de runtime sin promoción automática:
  4.048 `catalog_only`, 16.223 `phase_a_candidate`, 1.148 `complete`.
- Tres regiones opacas globales conservadas: la fila negativa firmada, hits
  corroborativos todavía sin consumer y 26 filas `runtime_only`.

Validación v1.3:

- 16/16 pruebas Python.
- 250/250 pruebas C# en Docker SDK 3.1.
- Dos ejecuciones completas deterministas con el SHA-256 anterior.

El siguiente objetivo ya no es descifrar layouts de items. Es cerrar
capacidades por familia. La cola recomienda comenzar por una familia con datos
nativos completos, protocolo existente y operación no destructiva; `backpack`
ofrece el mayor alcance inmediato (850 objetos), sujeto a verificar que el
protocolo marcado como conocido tenga evidencia byte a byte y pruebas de
persistencia antes de promover cobertura.

## Actualización v1.4 — corroboración externa congelada

Se añadió una capa separada para ArcheRage Wiki. No modifica
`aa8-item-forensics.sqlite`, no alimenta builders y toda aserción queda marcada
`authority=false`, `provenance=wiki_archerage_visible`.

Comandos:

```text
python -B -m item_forensics scan-wiki --scope unresolved
python -B -m item_forensics scan-wiki --kind skills --from-audit
python -B -m item_forensics scan-wiki --kind crafts --from-audit
python -B -m item_forensics audit-wiki
```

El scanner usa los IDs nativos como semillas, es reanudable, escribe cada
respuesta atómicamente y respeta una sola secuencia de solicitudes. La política
observada y congelada fue:

```text
robots_sha256=B852C178F0304DEA0F325C5D0D0A2E8F98C423496E2B7435931C68A7C1F03E25
crawl_delay=1.0
```

Primer snapshot:

- 135/135 items con descriptor `missing` o `unknown`, cero ausentes;
- 17 skills alcanzadas;
- 69 crafts alcanzados;
- 12 doodads alcanzados;
- 1 buff alcanzado;
- total: 234 páginas, 233 `confirmed` y una `partial`;
- la página parcial es skill 45719: ID y tipo presentes, título vacío;
- `snapshot_digest=E11B5B2A90B1F528C89F05AADC6FC28AC87CBA857CE852E595EB998D9E960DE6`.

La clasificación visible de los 135 huecos fue:

```text
73  Consumables > Ship Component Design
26  Consumables > Design
26  Consumables > Dye
 6  Armor > Synthesis Materials
 3  Accessories
 1  Consumables > Explosive
```

Esto separa exactamente los estados nativos:

- `missing recipe`: 99 diseños;
- `unknown dyeing`: 21 tintes;
- `missing dyeing`: 5 tintes;
- `missing armor`: 6 materiales de síntesis;
- `missing accessory`: 3 accesorios;
- `missing slave_equipment`: 1 explosivo.

Resultados adicionales:

- cuatro nombres `<ref:N>` obtuvieron una etiqueta externa visible:
  30280, 30281, 30282 y 35945;
- seis diferencias exactas de nivel quedaron en conflicto: items
  47855..47860 usan nivel interno 0 y la wiki proyecta nivel 1;
- cuatro dependencias nativas no son expuestas por sus fichas:
  skill 10003 del item 35957 y buffs 3459/3480/3501 de los items
  45359..45361;
- 16/17 skills del primer cierre existen en la compact Kakao;
  la excepción es la skill custom 8000781;
- los crafts todavía se conservan como `unknown_native`: este inventario no
  aproxima un catálogo de crafts que aún no tiene loader nativo integrado.

La clausura visible produjo:

```text
native_match=2208
wiki_only=532
unknown_native=6417
```

`wiki_only` incluye 278 IDs de items y 46 skills ausentes del catálogo Kakao.
Esto prueba que la web es un superconjunto histórico/custom, útil para búsqueda
pero no una autoridad de versión.

Frontera reanudable actual:

```text
1466 crafts unknown_native
 960 skills native_match
  45 skills wiki_only
 341 items native_match
 278 items wiki_only
  68 maps unknown_native
```

Auditoría separada:

```text
aa8-wiki-corroboration.sqlite
SHA-256 9C23ABB70DC3E48553A09B94F3474B0185C18F4D3A022DAA44774C23A8FFF9EE
MATCH=True
PRAGMA quick_check=ok
PRAGMA integrity_check=ok
```

Validación v1.4:

- 19/19 pruebas Python;
- dos auditorías consecutivas idénticas;
- cero errores de rastreo pendientes;
- runtime, compact activa, Docker y persistencia sin cambios.

## Actualización v1.5 — clausura nativa de dependencias

Se integraron como catálogos consultables los resultados nativos de `buffs`,
`doodad_almighties`, `craft_materials`, `craft_products`, `item_recipes` y las
referencias `items.craft_id`. Sus SQL y layouts se validaron contra loaders de
`x2game.dll` en el proyecto Ghidra existente:

```text
craft_materials    FUN_39a3b900    36.137 filas / 11.270 crafts
craft_products     FUN_39a3bc30    11.787 filas / 11.782 crafts
doodad_almighties  FUN_39931d20    15.290 IDs
buffs              FUN_39a2ae70    27.303 IDs
crafts             FUN_39a818b0    loader confirmado / resultado ausente
```

El universo combinado contiene 11.940 craft IDs referenciados. No equivale a
11.940 crafts habilitados: el resultado de `crafts WHERE enable='t'` no está
asignado a ningún stream. La búsqueda exhaustiva de headers encontró dos
coincidencias estructurales en `game11` (12 y 4 filas), pero ambas fallan los
invariantes semánticos de ID, booleanos y dominios numéricos. Se conservan
como evidencia negativa y `crafts` permanece `native_result_absent`.

La clausura añadió 13.878 relaciones `craft_to_item` confirmadas y preservó
36.612 destinos item distintos ausentes del catálogo positivo. Estos últimos
no se descartan ni se generan: al no existir el resultado filtrado de
`crafts`, pueden proceder de recetas dormidas o eliminadas.

Los 135 descriptores pendientes no fueron promovidos:

```text
108 native_relation_confirmed_descriptor_unresolved
 27 consumer_unresolved

80 craft_material
 6 craft_product
27 skill_consumer
 3 buff_consumer
```

Distribución de huecos:

```text
99 recipe missing
21 dyeing unknown
 5 dyeing missing
 6 armor missing
 3 accessory missing
 1 slave_equipment missing
```

El baseline final usa explícitamente:

```text
compact:
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-nuian-green-arc-v5.sqlite3
SHA-256 11E4D8FD9D28DBA23E25934A5A27CCAD7E4CE4C7B15DF3EEE09C0797622D953B

aa8-item-forensics.sqlite:
SHA-256 DCD63B8AA86B32115EADFAF459DB0169A88F54447ADD57434CF255AF1AC47BE6

native-closure-audit.json:
SHA-256 4AB39EAEE3A401BB2B02C7F917436C20C9FAC6E74986862A8B085809661D21FE

native-closure-audit.csv:
SHA-256 34ED27C26832F4F93032A534BD4895A2F961668E570FE1569036EA4EFAD4BBEF

aa8-wiki-corroboration.sqlite:
SHA-256 E0A2742D0A009FEE12F940E7B18710AA698B389DF16998C754B7A0F42EEFCFBE
```

Validación v1.5:

- 21/21 pruebas Python;
- `compileall` correcto;
- 257/257 pruebas C# en Docker SDK 3.1;
- dos `run-all` consecutivos con SQLite idéntica;
- dos `audit-wiki` consecutivos idénticos;
- `PRAGMA quick_check=ok` e `integrity_check=ok`;
- 21.419/21.419 IDs positivos clasificados;
- 0 `impl_id` positivos sin familia;
- runtime v5 con el mismo hash antes y después;
- ningún despliegue ni modificación de la compact activa.

La siguiente frontera es recuperar o demostrar la inexistencia del resultado
filtrado de `crafts`, y después resolver los 27 objetos sin consumidor nativo
con búsquedas dirigidas en loaders, RTTI, xrefs, scripts y assets. La wiki se
mantiene como corroboración: actualmente 5.047 relaciones son `native_match`
y 4.042 son `wiki_only`; estas últimas no son autoridad para generar runtime.

## Actualización v1.6 — crafts, conversiones e inventario SQL exhaustivo

La supuesta ausencia del resultado nativo de `crafts` era falsa. El loader
`FUN_39a818b0` ejecuta primero `SELECT COUNT(*) FROM crafts` y después:

```sql
SELECT id, name, skill_id, skill_level, cast_delay, product_delay,
       consume_lp, require_lp, require_prof, require_prof_value,
       craft_group_id, category_id, sub_category_id, grade_id,
       show_upper_craft, use_only_actability_group_id, or_unit_reqs,
       actability_group_id, need_bind, auto_register, doodad_id,
       waive_default_fee, craft_pool_id, enable
FROM crafts
WHERE enable = 't'
```

El header de `game11` en `134099279` contiene el `COUNT(*)` total de 11.615.
El resultado filtrado empieza en `134099285`, contiene 9.369 crafts habilitados
y termina exactamente en `134777928`, donde comienza el resultado siguiente.
El layout quedó validado contra los loaders x64 `39a818b0` y x86 `39dc1ff0`.
La secuencia completa confirma también categorías, líneas, packs y smelting.

Se cerró la ruta nativa de los reactivos de conversión:

```text
item
→ item_conv_reagent
→ item_conv_rpack
→ item_conv
→ item_conv_ppack
→ item_conv_product
→ item_conv_set
```

Los IDs 31789–31808 forman tres grupos exactos que producen 40091, 40092 y
40093 dentro del set 3, `Magic Salvage`. La herramienta incorpora ahora los
catálogos `item_conv_epacks`, `item_conv_rpacks`, `item_conv_ppacks`,
`item_convs`, `item_conv_sets` y sus relaciones tipadas. No se infirieron
fórmulas, probabilidades ni comportamiento.

La búsqueda dejó de limitarse a `game11`. El inventario reproducible de las
consultas embebidas en `x2game.dll` contiene:

```text
977 SELECT únicos
908 llamadas únicas del loader maestro asociadas
1.086 referencias de función catalogadas por el barrido Ghidra completo
```

Además de DLL y streams, la evidencia continúa correlacionándose con scripts,
índices/extracciones de `game_pak`, RTTI, vtables, assets y consumidores. El
registro declarativo ya puede distinguir consultas distintas sobre la misma
tabla mediante SQL exacto.

El barrido binario y los xrefs recuperaron dos resultados previamente opacos:

```text
tags          offset 5.374.123   5.280 filas   layout 68 78
tagged_items  offset 21.952.540  28.910 filas  layout 68 68 68
```

Sus SQL y layouts coinciden en x86 y x64. Los siete objetos finales del grupo
investigado sí tienen metadata nativa:

```text
35945       tags 402 y 2539
47855–47860 tags 356, 1157 y 1528
```

Esto no demuestra su conducta. Los tags describen restricciones, interacción
y categoría de proficiencia, pero no reemplazan el descriptor, handler,
protocolo ni persistencia. Por ello esos objetos se clasifican como
`native_metadata_confirmed_consumer_unresolved`, no como completos.

Estado de clausura v1.6:

```text
21.419/21.419 IDs positivos clasificados
0 impl_id positivos sin familia
123 especificaciones declarativas
125 tablas SQL relacionadas con items

118 native_relation_confirmed_descriptor_unresolved
 13 native_metadata_confirmed_consumer_unresolved
  4 native_dependency_missing
```

Los cuatro bloqueos por dependencia son 35924→craft 7172, 35925→7173,
35944→7143 y 35947→7178. Esos crafts aparecen en relaciones auxiliares, pero
no en el resultado habilitado de `crafts`; se preservan como dormidos o
deshabilitados y no se generan.

Los 135 descriptores pendientes siguen distribuidos así:

```text
99 recipe missing
21 dyeing unknown
 5 dyeing missing
 6 armor missing
 3 accessory missing
 1 slave_equipment missing
```

Cobertura agregada de items positivos:

```text
 4.048 catalog_only
16.223 phase_a_candidate
 1.148 complete
```

Artefactos congelados:

```text
compact runtime v5:
SHA-256 11E4D8FD9D28DBA23E25934A5A27CCAD7E4CE4C7B15DF3EEE09C0797622D953B

aa8-item-forensics.sqlite:
SHA-256 97CCF92D36AB8DD64EF294753342EAF7AB75FDA3008E987993E0E96EA28E13AA

manifest.json:
SHA-256 6595A288B4DEA66979435F8E8C52194D38C1D473F7BF185391B88065D617AE74

native-closure-audit.json:
SHA-256 4F73F49DB36377802D38AE282E0152A4AFCB7824DDDB1E0B5C961B5D36FFB9D6

native-closure-audit.csv:
SHA-256 E8E111E42856AA3A908B5A85141D9CE40F4024FEB57FC42211CFD18F167CB89D

aa8-wiki-corroboration.sqlite:
SHA-256 45D0BA237B8E7F14A98FE1282BF84E941F7CDE5AB6BC7C56F5DC4631A8AC1FB5

wiki-audit.csv:
SHA-256 4F2207B755CDAF1A5327699A0B9107379B76649FDD675796F465B74056558C1D
```

Validación v1.6:

- 25/25 pruebas Python;
- `compileall` correcto;
- 257/257 pruebas C# en Docker SDK 3.1;
- dos `run-all` consecutivos con SQLite idéntica;
- dos `audit-wiki` consecutivos con SQLite idéntica;
- `PRAGMA quick_check=ok` e `integrity_check=ok`;
- runtime v5 con el mismo hash antes y después;
- ningún despliegue ni modificación de la compact activa.

La siguiente frontera recomendada es recuperar los resultados exactos de los
99 descriptores `item_recipes`, distinguiendo habilitados, deshabilitados y
tombstones; validar las exclusiones de `item_armors` para 47855–47860; cerrar
`item_smelting_probs` y las cuatro especificaciones que todavía reportan
`native_result_absent`; y después auditar backend, protocolo y persistencia
por familia. Llegar al 100 % exige cerrar esas capacidades, no solo encontrar
IDs, relaciones o metadata.
