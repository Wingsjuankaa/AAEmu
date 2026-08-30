# AA10 — Inventario y plan de prueba de progresión Erenor

## Propósito y alcance

Este checkpoint reúne los objetos, recetas, grados y rutas necesarios para probar la progresión Erenor en ArcheAge Returns `10.0.2.13 r575` con AAEmu `rama_10`.

El documento distingue cuatro problemas que no deben confundirse:

1. **Catálogo de fabricación:** la receta base existe y puede ser ejecutable.
2. **Folio:** el producto puede no ser localizable aunque la receta exista.
3. **Enciclopedia/Item Guide:** el objeto puede no tener una entrada visible.
4. **Progresión:** síntesis y despertar pueden fallar por lógica o relaciones incompletas aunque el objeto sea visible.

La reconstrucción v1 quedó aplicada el `2026-08-30` al compact suelto, al compact del runtime y al `game_pak` efectivo. No se duplicó ninguna de las 42 recetas: se repararon las superficies nativas de Folio/enciclopedia, los topes de síntesis y la semántica de temper de los scrolls. No se entregaron objetos a un personaje; los gates visuales y jugables siguen requiriendo prueba manual.

## Baseline de evidencia

- Rama: `rama_10`
- HEAD analizado: `2ecce32fd709b59c534c19d5dde2de02694a1186`
- Fuente autoritativa: `E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3`
- SHA-256 autoritativo: `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`
- Compact del cliente: `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game\db\compact.sqlite3`
- SHA-256 antes/después: `F12818D3B0E765C4F761C9587FD84E99DF7E7E64DC51C22647191F9A284B1F75` → `F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B`
- Compact del runtime: `E:\AAEmu\rama_10\server\AAEmu\.server_files\AAEmu.Game\Data\compact.sqlite3`
- SHA-256 antes/después: `1BA34AE534DB13B7E7268D2F723BE69B39FB2EE83E3F6D747FE0AFC69F4E642D` → `85024F044F2A0B119776012EE516F90FDD9DB28B4E5581403D40526B1B7D8C65`
- Compact empaquetado antes/después: `74703B9B221028240AB5FBD58AE52E49BDF22D2B5F6C56CDF94412E10EAB89D2` → `FFEE421EAFA5617FF844D9DEE12F33ABD24CCCC0DC035C2E029E72ED073646E5`
- `game_pak` antes/después: `2F751B81B007155A1B891327CE02965DDC46225DCC4032A220CCB17B4D38ABD3` → `8CD6A13F0B7DB62BBC908A43CE191B8DFE351D8C3A42773974C21F17ADDBEFF4`; tamaño preservado: `68.963.258.880` bytes
- Política de crafteo: `AAEmu.Game/Data/aa10-crafting-wave5-policy.json`
- SHA-256 de la política: `193BD16E9B9AAEAD102BA2188A3A53D4FBB6D0F0FDDFDA122A018F4F95190569`
- Nombre interno de Erenor en los datos coreanos: `ipnir` / `이프니르`

## Diagnóstico del catálogo

La evidencia no indica que falten las recetas base Erenor. Los cuatro snapshots consultados —autoritativo, compact suelto del cliente, compact verificado del paquete más reciente y compact del runtime— coinciden en esta cobertura:

| Relación | Cobertura Erenor base |
|---|---:|
| `crafts` habilitadas | 42/42 |
| `craft_products` | 42/42 |
| `craft_materials` | 210, cinco por receta |
| `craft_pack_crafts`, pack `206` | 42/42 |
| Política Wave 5 | 42 `executable_wave5`, sin blocker |
| Consumidor nativo | `doodad_craft_pack` |
| Workbench requerido | doodad `9351` |
| Grado del producto base | `4` (Arcane) |
| `item_recipes` | **0/42** |
| `craft_line_components` | **0/42** |
| `item_guide_elems` para el equipo base antes/después | **0/42 → 42/42** |

Además, los 42 productos y títulos de receta tienen localización inglesa no vacía en el compact efectivo. Por ello, un resultado vacío al buscar `Erenor Cuirass` no se explica por una receta deshabilitada ni por falta de nombre inglés.

### Interpretación

- La fabricación y la búsqueda de Folio consumen grafos relacionados, pero no idénticos.
- `item_recipes` enlaza objetos de diseño/receta, no el producto terminado. Su ausencia para los 42 equipos Erenor es nativa y se preservó.
- El filtro nativo de Folio (`X2Craft:GetListBySearching`) excluía 39 categorías D Erenor y tres categorías C de accesorios porque tenían `use_only_doodad='t'`. La reparación cambia exclusivamente esas 42 categorías a `f`.
- `craft_line_components` no participa en esta familia base. Su ausencia es nativa y se preservó.
- La enciclopedia estaba realmente incompleta: guías `619`, `873`, `922` y `994` contenían `0`, `0`, `1` y `1` piezas. Se reconstruyeron a `42`, `42`, `42` y `39`, derivando la membresía de los mappings nativos `23`, `275` y `311`.
- Los padres `item_guides.show='f'` se preservaron: la visibilidad efectiva depende de su integración nativa y no exige forzarlos globalmente a `t`.
- La captura donde se observa `Erenor Cap` no demuestra que falten las otras recetas en `crafts`: el árbol está organizado por ranura y en la captura la sección `Chest` aparece colapsada. El fallo reproducible y concluyente es la búsqueda vacía del Folio.

## Las 42 recetas base

Todas producen una unidad a grado `4`, requieren doodad `9351`, pertenecen al pack `206` y están habilitadas.

### Armadura de placa

| Craft | Producto | Nombre |
|---:|---:|---|
| 9918 | 43003 | Erenor Helm |
| 9919 | 43004 | Erenor Cuirass |
| 9920 | 43005 | Erenor Greaves |
| 9921 | 43006 | Erenor Gauntlets |
| 9922 | 43007 | Erenor Sabatons |
| 9923 | 43008 | Erenor Vambraces |
| 9924 | 43009 | Erenor Tassets |

### Armadura de cuero

| Craft | Producto | Nombre |
|---:|---:|---|
| 9925 | 43010 | Erenor Cap |
| 9926 | 43011 | Erenor Jerkin |
| 9927 | 43012 | Erenor Breeches |
| 9928 | 43013 | Erenor Fists |
| 9929 | 43014 | Erenor Boots |
| 9930 | 43015 | Erenor Guards |
| 9931 | 43016 | Erenor Belt |

### Armadura de tela

| Craft | Producto | Nombre |
|---:|---:|---|
| 9932 | 43017 | Erenor Hood |
| 9933 | 43018 | Erenor Shirt |
| 9934 | 43019 | Erenor Pants |
| 9935 | 43020 | Erenor Gloves |
| 9936 | 43021 | Erenor Shoes |
| 9937 | 43022 | Erenor Sleeves |
| 9938 | 43023 | Erenor Sash |

### Armas e instrumentos

| Craft | Producto | Nombre |
|---:|---:|---|
| 9939 | 43031 | Erenor Dagger |
| 9940 | 43032 | Erenor Sword |
| 9941 | 43033 | Erenor Greatsword |
| 9942 | 43034 | Erenor Katana |
| 9943 | 43035 | Erenor Nodachi |
| 9944 | 43036 | Erenor Axe |
| 9945 | 43037 | Erenor Greataxe |
| 9946 | 43038 | Erenor Club |
| 9947 | 43039 | Erenor Greatclub |
| 9948 | 43040 | Erenor Shortspear |
| 9949 | 43041 | Erenor Longspear |
| 9950 | 43042 | Erenor Scepter |
| 9951 | 43043 | Erenor Staff |
| 9952 | 43044 | Erenor Bow |
| 9953 | 43045 | Erenor Shield |
| 9954 | 43046 | Erenor Lute |
| 9955 | 43047 | Erenor Flute |
| 11934 | 50833 | Erenor Rifle |

### Accesorios

| Craft | Producto | Nombre |
|---:|---:|---|
| 9956 | 43081 | Erenor Necklace |
| 9957 | 43082 | Erenor Earring |
| 9958 | 43083 | Erenor Ring |

## Matriz completa de tiers del equipo

Los grados fuente exigidos por las relaciones de despertar son:

- T1 Erenor → T2 Radiant: grado `10` (Legendary), mapping group `23`.
- T2 Radiant → T3 Brilliant: grado `11` (Mythic), mapping group `275`.
- T3 Brilliant → T4 Refined: grado `12` (Eternal), mapping group `311`.

| Línea | T1 Erenor | T2 Radiant | T3 Brilliant | T4 Refined |
|---|---:|---:|---:|---:|
| Plate Helm | 43003 | 46994 | 48561 | 53059 |
| Plate Cuirass | 43004 | 46995 | 48562 | 53060 |
| Plate Greaves | 43005 | 46996 | 48563 | 53061 |
| Plate Gauntlets | 43006 | 46997 | 48564 | 53062 |
| Plate Sabatons | 43007 | 46998 | 48565 | 53063 |
| Plate Vambraces | 43008 | 46999 | 48566 | 53064 |
| Plate Tassets | 43009 | 47000 | 48567 | 53065 |
| Leather Cap | 43010 | 47001 | 48568 | 53066 |
| Leather Jerkin | 43011 | 47002 | 48569 | 53067 |
| Leather Breeches | 43012 | 47003 | 48570 | 53068 |
| Leather Fists | 43013 | 47004 | 48571 | 53069 |
| Leather Boots | 43014 | 47031 | 48598 | 53070 |
| Leather Guards | 43015 | 47005 | 48572 | 53071 |
| Leather Belt | 43016 | 47006 | 48573 | 53072 |
| Cloth Hood | 43017 | 47007 | 48574 | 53073 |
| Cloth Shirt | 43018 | 47008 | 48575 | 53074 |
| Cloth Pants | 43019 | 47009 | 48576 | 53075 |
| Cloth Gloves | 43020 | 47010 | 48577 | 53076 |
| Cloth Shoes | 43021 | 47011 | 48578 | 53077 |
| Cloth Sleeves | 43022 | 47012 | 48579 | 53079 |
| Cloth Sash | 43023 | 47013 | 48580 | 53080 |
| Dagger | 43031 | 47014 | 48581 | 53081 |
| Sword | 43032 | 47015 | 48582 | 53083 |
| Greatsword | 43033 | 47016 | 48583 | 53084 |
| Katana | 43034 | 47017 | 48584 | 53085 |
| Nodachi | 43035 | 47018 | 48585 | 53086 |
| Axe | 43036 | 47019 | 48586 | 53087 |
| Greataxe | 43037 | 47020 | 48587 | 53088 |
| Club | 43038 | 47021 | 48588 | 53089 |
| Greatclub | 43039 | 47022 | 48589 | 53090 |
| Shortspear | 43040 | 47023 | 48590 | 53091 |
| Longspear | 43041 | 47024 | 48591 | 53092 |
| Scepter | 43042 | 47025 | 48592 | 53093 |
| Staff | 43043 | 47026 | 48593 | 53094 |
| Bow | 43044 | 47027 | 48594 | 53095 |
| Shield | 43045 | 47028 | 50398 | 53096 |
| Lute | 43046 | 47029 | 48596 | 53097 |
| Flute | 43047 | 47030 | 48597 | 53098 |
| Rifle | 50833 | 50834 | 50835 | 53370 |
| Necklace | 43081 | 48539 | 54147 | **54150, sin mapping** |
| Earring | 43082 | 48540 | 54148 | **54151, sin mapping** |
| Ring | 43083 | 48538 | 54146 | **54149, sin mapping** |

Los tres objetos Refined de accesorios existen en `items`, pero el grupo `311` no contiene relaciones desde `54147`, `54148` ni `54146`. Por ello se registran como **catalogados pero no alcanzables por la ruta estática de despertar**.

## Infusiones Erenor

### Plantillas actuales preferidas

Estas trece plantillas tienen implementación explícita de material de evolución (`impl_id=33` / `item_evolving_materials`) o una categoría de síntesis directamente utilizable por AAEmu.

| Item ID | Nombre efectivo | Uso/XP estático |
|---:|---|---|
| 48829 | Clear Erenor Infusion | 188 XP en grado 0; escala hasta 395 en grado 12 |
| 48830 | Vivid Erenor Infusion | 383 XP en grado 0; escala hasta 804 en grado 12 |
| 48831 | Lucid Erenor Infusion | 1.243 XP en grado 0; escala hasta 2.610 en grado 12 |
| 48832 | Radiant Erenor Infusion | 1.545 XP en grado 0; escala hasta 3.245 en grado 12 |
| 48833 | Resplendent Erenor Infusion | 1.800 XP en grado 0; escala hasta 3.780 en grado 12 |
| 48836 | Erenor Infusion | 100 XP en todo grado no Poor |
| 48840 | Net Cafe Mythic Erenor Infusion | 600 XP únicamente en grado 11; nombre efectivo `X` |
| 48843 | Net Cafe Eternal Erenor Infusion | 1.150 XP únicamente en grado 12; nombre efectivo `X` |
| 48849 | Erenor Weapon Infusion | 2.000 XP en grados 4–12; 0 XP en grados 0–3 |
| 48850 | Erenor Armor Infusion | 2.000 XP en grados 4–12; 0 XP en grados 0–3 |
| 48851 | Erenor Accessory Infusion | 2.000 XP en grados 4–12; 0 XP en grados 0–3 |
| 48853 | Mythic Erenor Infusion | 600 XP únicamente en grado 11 |
| 54329 | Ancestral Erenor Infusion | 10.000 XP únicamente en grado 12 |

**Advertencia de prueba:** entregar `48849`, `48850` o `48851` sin `-Grade` puede crear una infusión básica que aporta `0 XP`. Para el smoke test deben entregarse a grado `4` o superior. `54329` debe entregarse a grado `12`.

### Recetas de infusión por grado

Las 27 recetas siguientes están habilitadas y materializan la misma plantilla con un grado explícito:

| Familia | Crafts | Grados producidos |
|---|---|---|
| 48849, Weapon | 11170–11178 | 4 Arcane, 5 Heroic, 6 Unique, 7 Celestial, 8 Divine, 9 Epic, 10 Legendary, 11 Mythic, 12 Eternal |
| 48850, Armor | 11179–11187 | 4–12, mismo orden |
| 48851, Accessory | 11188–11196 | 4–12, mismo orden |

### Plantillas legacy/alternativas

Se conservan para regresión y comparación, pero no deben mezclarse con el kit canónico sin una razón concreta:

| Item ID | Nombre efectivo | Equivalente actual aproximado |
|---:|---|---:|
| 46009 | Clear Erenor Infusion | 48829 |
| 46012 | Vivid Erenor Infusion | 48830 |
| 46013 | Lucid Erenor Infusion | 48831 |
| 46014 | Radiant Erenor Infusion | 48832 |
| 46015 | Resplendent Erenor Infusion | 48833 |
| 46429 | Erenor Infusion | 48836 |
| 47444 | Net Cafe Mythic Erenor Infusion | 48840 |
| 47447 | Net Cafe Eternal Erenor Infusion | 48843 |
| 48140 | Erenor Weapon Infusion | 48849 |
| 48141 | Erenor Armor Infusion | 48850 |
| 48142 | Erenor Accessory Infusion | 48851 |
| 48488 | Mythic Erenor Infusion | 48853 |
| 48492 | Mythic Erenor Infusion | 48853 |

## Scrolls de despertar y utilitarios

### Equipo principal

| Item ID | Nombre | Skill | Mapping | Fuente requerida | Resultado | Probabilidad |
|---:|---|---:|---:|---|---|---:|
| 47032 | Erenor Awakening Scroll | 40743 | 23 | T1 grado 10 | T2 Radiant | 25% + 5% por fallo |
| 47050 | Holy Erenor Awakening Scroll | 40750 | 23 | T1 grado 10 | T2 Radiant | 25% + 5% por fallo |
| 49173 | Radiant Erenor Awakening Scroll | 44397 | 275 | T2 grado 11 | T3 Brilliant | 25% + 5% por fallo |
| 49174 | Blessed Erenor Awakening Scroll | 44421 | 275 | T2 grado 11 | T3 Brilliant | 25% + 5% por fallo |
| 53793 | Brilliant Erenor Awakening Scroll | 50200 | 311 | T3 grado 12 | T4 Refined | 25% + 5% por fallo |
| 53794 | Refined Erenor Awakening Scroll | 50201 | 311 | T3 grado 12 | T4 Refined | 25% + 5% por fallo |

Los scrolls normales `47032`, `49173` y `53793` codifican `value2=20`, `value3=0`, `value4=2`: en un despertar exitoso conservan un piso de temper `+20` y pueden perder aleatoriamente entre 0 y 2 puntos por encima de él. Sus variantes Holy/Blessed/Refined tienen los tres valores en cero y conservan el temper. `ItemChangeMapping` y `ItemAwakeningCalculator` ya consumen esta semántica y restauran el valor anterior si falla el cobro de materiales.

### Capas

| Item ID | Nombre | Mapping | Fuente | Destino | Probabilidad |
|---:|---|---:|---|---|---:|
| 49206 | Erenor Cloak Awakening Scroll | 277 | Erenor Cloak grado 11 | Radiant Erenor Cloak | 25% |
| 52913 | Radiant Erenor Cloak Awakening Scroll | 305 | Radiant Erenor Cloak grado 11 | Brilliant Erenor Cloak | 25% |

Lineajes canónicos de capa:

| Variante | T1 principal | T2 Radiant | T3 Brilliant |
|---|---:|---:|---:|
| Windsong | 49200 | 48634 | 52657 |
| Twintail | 49209 | 48635 | 52658 |
| Bastion | 49207 | 48636 | 52659 |
| Arrowflash | 49210 | 48637 | 52660 |
| Hatchetblade | 49208 | 48638 | 52661 |

El grupo `277` también acepta las variantes antiguas `43115–43124`, incluidas las Flaming, y las normaliza a uno de los cinco resultados Radiant.

### Materiales de síntesis para capas

Las capas pertenecen al grupo de objetivo `7` y no aceptan las infusiones Erenor de arma, armadura o accesorio. El runtime permite materiales de los grupos `7`, `8`, `9` y `10`: otras capas de síntesis, los materiales de Auroria y el material administrativo.

| Item ID | Nombre | Grado del material | XP efectivo | Uso |
|---:|---|---|---:|---|
| 48819 | Auroran Synthesis Shard | Basic `0` | 50 | Material retail de Auroria |
| 48819 | Auroran Synthesis Shard | Grand `2` / Rare `3` / Arcane `4` / Heroic `5` | 75 / 112 / 168 / 252 | Material retail de Auroria |
| 48819 | Auroran Synthesis Shard | Unique `6` a Mythic `11` | 378 | Rango recomendado para prueba |
| 48820 | Auroran Synthesis Stone | Mismos grados que `48819` | Mismos valores | Material retail de Auroria |
| 48823 | Purified Administrator's Stone Pack | Divine `8` fijo | 851 | Material GM, no ruta retail normal |

`48819` y `48820` aportan `0 XP` en Crude `1` y Eternal `12`; no deben entregarse en esos grados. Las tres plantillas tienen `max_stack_size=1`.

Ruta exacta de `49210 Erenor Arrowflash Cloak`:

1. T1 Arcane `4` → Mythic `11`: 109.747 XP; scroll `49206`.
2. El despertar produce `48637 Radiant Erenor Arrowflash Cloak` alrededor de Heroic `5`, conservando cualquier remanente; subir a Mythic `11`: 224.224 XP menos el remanente.
3. El scroll `52913` produce `52660 Brilliant Erenor Arrowflash Cloak` alrededor de Unique `6`; subir a Eternal `12`: 691.162 XP menos el remanente.

Usando exclusivamente `48819/48820` a 378 XP desde barras vacías y conservando el sobrante entre etapas, la referencia es 291, 593 y 1.828 unidades respectivamente. Deben entregarse por lotes debido al stack máximo de uno.

### Conversión y reroll

| Item ID | Nombre | Función |
|---:|---|---|
| 54038 | Bound Erenor Weapon Type Conversion Scroll | Grupo 314, conversión de arma; 208 mappings, 100% |
| 54039 | Bound Erenor Armor Type Conversion Scroll | Grupo 315, conversión de armadura; 168 mappings, 100% |
| 50552 | Lucent Serendipity Stone | Selección/reroll de efecto de síntesis |
| 50635 | Bound Lucent Serendipity Stone | Variante ligada del mismo reroll |

### Excluidos del kit normal

| Item ID | Motivo |
|---:|---|
| 43179 | `Erenor Lucky Scroll`; objeto antiguo/deprecado ligado a devolución, no a la ruta actual |
| 48946 | `[test] Erenor Awakening Scroll`; plantilla de prueba interna |
| 47718 y 48236–48355 | Materiales/scrolls por pieza para la ruta legacy Ayanad → Erenor; útiles para una prueba de adquisición histórica, no para el smoke T1 → T4 |

## Categorías aceptadas por la síntesis

| Objetivo Erenor | Grupo del objetivo | Grupos de material aceptados |
|---|---:|---|
| Weapon | 21 | 21, 22, 23, 24, 25, 28 |
| Armor | 22 | 21, 22, 23, 24, 26, 28 |
| Accessory | 23 | 21, 22, 23, 24, 27, 28 |
| Cloak | 7 | 7, 8, 9, 10 |

Las categorías Erenor principales están distribuidas así:

- T1: `49–62`.
- T2: `594–605` y accesorios `681–683`.
- T3: `712–725`, con categoría de shield adicional `732`.
- T4: `811–825`.

## Kit mínimo de prueba

Se recomienda comenzar con un arma, una pieza de armadura y un accesorio para cubrir los tres grupos de síntesis, y después ejecutar una matriz completa por ranura.

### Entrega segura por API de administración

El script valida que el personaje esté online, detiene el lote ante el primer error y admite `-WhatIf`.

```powershell
$erenorCharacter = 'NOMBRE_PERSONAJE'
$giveItems = "$env:USERPROFILE\.codex\skills\aaemu10-native-reconstruction\scripts\give-test-items.ps1"

# Primero revisar sin mutar.
& $giveItems -Character $erenorCharacter `
  -ItemId @(43043, 43004, 43081, 47032, 47050, 49173, 49174, 53793, 53794, 50552) `
  -Count 1 -WhatIf

# Equipo y scrolls.
& $giveItems -Character $erenorCharacter `
  -ItemId @(43043, 43004, 43081, 47032, 47050, 49173, 49174, 53793, 53794, 50552) `
  -Count 1

# Infusiones universales para acelerar el ascenso; requieren grado 12.
& $giveItems -Character $erenorCharacter -ItemId @(54329) -Count 20 -Grade 12

# Infusiones tipadas; nunca entregarlas a grado básico.
& $giveItems -Character $erenorCharacter -ItemId @(48849, 48850, 48851) -Count 20 -Grade 4
```

No se debe aplicar `-Grade 12` al lote que contiene equipo base y scrolls: el parámetro se aplica por igual a todos los IDs del lote y alteraría el estado inicial de la prueba.

### Orden de prueba

1. Confirmar que `Erenor Staff` (`43043`), `Erenor Cuirass` (`43004`) y `Erenor Necklace` (`43081`) llegan a grado 4.
2. Abrir síntesis y confirmar que cada objetivo acepta solamente los grupos de material previstos.
3. Probar una infusión tipada en grado 4 y verificar que añade 2.000 XP.
4. Probar la misma plantilla en grado 0 en un entorno descartable y verificar la evidencia negativa: 0 XP.
5. Ascender T1 hasta grado 10 y despertar con `47032`; repetir con `47050` para comparar temper.
6. Ascender T2 hasta grado 11 y despertar con `49173`; repetir con `49174`.
7. Ascender T3 hasta grado 12 y despertar con `53793`; repetir con `53794`.
8. Repetir los pasos en arma, armadura y accesorio.
9. Verificar que Necklace/Earring/Ring fallan de T3 a T4 por ausencia de mapping; este fallo es actualmente esperado.
10. Probar una capa T1 a grado 11 con `49206` y luego su T2 a grado 11 con `52913`.

## Gates de aceptación

### Fabricación base

- [ ] Las 42 recetas aparecen en las categorías correctas del workbench.
- [ ] Cada receta presenta cinco materiales y produce el item esperado a grado 4.
- [ ] Craftear `9918`, `9919`, `9925`, `9926`, `9932`, `9933`, `9951`, `9956` y `11934` cubre cabeza, pecho, los tres tipos de armadura, arma, accesorio y rifle.
- [ ] El servidor descuenta materiales, labor y moneda una sola vez.

### Folio y enciclopedia

- [ ] Buscar `Erenor Cuirass` devuelve el producto `43004` y la receta `9919`.
- [ ] Buscar al menos una pieza de cada una de las 42 líneas devuelve resultado.
- [ ] La enciclopedia muestra T1, T2, T3 y T4 según las relaciones válidas.
- [ ] Infusiones y scrolls aparecen bajo una guía cuyo padre está visible.
- [ ] No se muestran plantillas `[test]`, de Net Cafe ocultas ni objetos deprecados como ruta normal.

### Síntesis y despertar

- [ ] `48849/48850/48851` a grados 4–12 aportan 2.000 XP.
- [ ] La progresión puede superar grado 7 y alcanzar 10, 11 y 12.
- [ ] Los grupos 23, 275 y 311 transforman cada fuente en el destino de la matriz.
- [ ] La bonificación acumulada tras fallo aumenta conforme a 500/10.000.
- [ ] La variante normal y la variante especial de cada scroll conservan la semántica de temper correspondiente.
- [ ] Los tres accesorios tienen una política explícita para T3 → T4: mapping nativo reconstruido o bloqueo documentado.

## Estado de las reparaciones y frontera pendiente

### 1. Topes de síntesis reparados

Se corrigieron 78 categorías activas con los topes exigidos por sus rutas nativas: T1 a grado `10`, T2 y Radiant Cloak a `11`, T3/Refined y Brilliant Cloak a `12`. Se omitieron deliberadamente categorías sin uso `597`, `810`, `815` y los accesorios T4 inalcanzables `823–825`.

### 2. Accesorios T3 → T4 sin mapping

Existen `54149`, `54150` y `54151`, pero el grupo `311` no enlaza los accesorios Brilliant con ellos. No debe inventarse la correspondencia únicamente por semejanza nominal sin contrastarla con cliente comparativo, `x2game.dll` o corpus nativo.

### 3. Diferencia normal/especial reparada

El handler consume ahora `value2/value3/value4` tras un despertar exitoso. Los scrolls normales aplican piso y rango de pérdida; las variantes especiales conservan el temper. La lógica está cubierta por pruebas unitarias dedicadas.

### 4. Catálogo reconstruido

- Folio: 39 categorías D del equipo y tres categorías C de accesorios quedaron buscables sin alterar las 42 recetas existentes.
- Enciclopedia de equipo: T1/T2/T3/T4 quedaron con `42/42/42/39` entradas.
- Se retiró de la guía T3 el shield obsoleto `48595` y se registró el shield efectivo `50398`.
- Se agregaron seis relaciones faltantes para infusiones/scrolls: `48836`, `48853`, `54329`, `52913`, `53793` y `53794`.
- `item_recipes`, `craft_line_components`, IDs de recipes y flags globales de padres se conservaron como en el cliente nativo.

## Reconstrucción aplicada

1. `Scripts/PatchAa10ErenorCatalog.py` deriva y valida el catálogo desde los crafts y mappings nativos; funciona en dry-run, apply, JSON e idempotencia, y falla cerrado ante estados parciales.
2. `Scripts/ApplyAa10ErenorCatalogGamePakPatch.ps1` aplica el compact con hashes de transición exactos, backup, rollback, preservación de tamaño, `PRAGMA quick_check`, reextracción y probes binarios ajenos al parche.
3. El `game_pak`, el compact suelto y el runtime quedaron sincronizados; únicamente el servicio Game fue reconstruido y recreado.
4. La frontera deliberadamente abierta sigue siendo T3 → T4 de accesorios: los destinos existen, pero r575 no aporta mappings en el grupo `311`.
5. Folio, enciclopedia y workbench deben validarse por separado dentro del cliente; la validación estática no sustituye esos gates visuales.

## Consultas mínimas de auditoría

```sql
-- Las 42 recetas base deben existir una sola vez y estar habilitadas.
SELECT c.id, c.enable, p.item_id, p.item_grade_id, c.req_doodad_id
FROM crafts c
JOIN craft_products p ON p.craft_id = c.id
WHERE c.id BETWEEN 9918 AND 9958 OR c.id = 11934
ORDER BY c.id;

-- Debe devolver 39 categorías D visibles.
SELECT COUNT(DISTINCT c.craft_d_category_id) AS categorias_d_visibles
FROM crafts c
JOIN craft_d_categories d ON d.id = c.craft_d_category_id
WHERE (c.id BETWEEN 9918 AND 9958 OR c.id = 11934)
  AND d.use_only_doodad = 'f';

-- Debe devolver 3 categorías C de accesorios visibles.
SELECT COUNT(*) AS categorias_c_accesorio_visibles
FROM craft_c_categories
WHERE id IN (236, 237, 238)
  AND use_only_doodad = 'f';

-- La enciclopedia debe contener 42/42/42/39 piezas por tier.
SELECT item_guide_id, COUNT(*) AS piezas
FROM item_guide_elems
WHERE item_guide_id IN (619, 873, 922, 994)
GROUP BY item_guide_id
ORDER BY item_guide_id;

-- Conteo de mappings por tier.
SELECT mapping_group_id, COUNT(*) AS mappings,
       COUNT(DISTINCT source_item_id) AS sources,
       COUNT(DISTINCT target_item_id) AS targets
FROM item_change_mappings
WHERE mapping_group_id IN (23, 275, 311, 277, 305, 314, 315)
GROUP BY mapping_group_id
ORDER BY mapping_group_id;

-- Debe exponer la ausencia T3 -> T4 de accesorios.
SELECT *
FROM item_change_mappings
WHERE mapping_group_id = 311
  AND source_item_id IN (54146, 54147, 54148);
```

## Criterio de cierre

La reconstrucción estática, el empaquetado y el despliegue están cerrados. La aceptación retail queda cerrada cuando:

- las 42 recetas existentes son visibles y fabricables sin duplicados;
- Folio y enciclopedia muestran el catálogo correcto;
- arma, armadura, accesorio y capa completan su ruta de síntesis/despertar según datos nativos;
- las diferencias de scroll normal/especial están implementadas;
- la ruta T3 → T4 de accesorios permanece bloqueada de forma explícita hasta obtener evidencia nativa suficiente, o se resuelve con esa evidencia;
- las pruebas se repiten contra el `compact.sqlite3` realmente empaquetado y el runtime realmente desplegado.
