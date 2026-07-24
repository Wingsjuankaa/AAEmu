# Fase B11 — selección nativa de Lunagem AA8

Esta fase implementa el flujo común mostrado por Fireglow, Waveglow y las
otras familias base de Lunagem:

```text
clic derecho en Lunagem base
→ selector de efecto
→ confirmación
→ consumo del Lunagem base
→ creación del Lunagem final seleccionado
```

No corresponde al socketing de Lunascales. La fuente nativa
`selective_item.alb` confirma que el cliente abre el selector con
`SKILL_SELECTIVE_ITEM`, registra los índices mediante
`X2Bag:SetSelectiveItem` y confirma con `X2Bag:HandleSelectiveItems`.

## Autoridad confirmada

- La compact AA8 aporta el objeto fuente, su `use_skill_id`, UID y grado.
- `game11` aporta `effect=selective_item`, cantidad consumida, selección
  simple o múltiple y la lista de UIDs resultantes.
- `x2game.dll` confirma el paquete `0x1C4`:

```text
byte slotType
byte slot
uint32 tryCount
uint32 optionCount
uint32[optionCount] optionIndices
```

- `x2game.dll` confirma `ItemTaskType=150` para esta operación.
- Los índices de opción son uno-basados.
- Si el JSON no fija un grado, el resultado hereda el grado del reactivo; la
  definición del objeto final todavía puede imponer su `fixed_grade`.

Cada acción cuya lista contiene un UID no resoluble queda bloqueada completa.
No se emplean datos 3.0 ni resultados aproximados.

## Enlace nativo de tiers

La primera prueba funcional confirmó que `items.use_skill_id` no sirve como
enlace de la familia V2: alterna las listas y conecta el objeto base con
`2tier_*`. El enlace reproducible se deriva de tres datos AA8:

- alias `v2.socket_1tier_*` o `v2.socket_2tier_*`;
- color e icono del objeto fuente;
- `fixed_grade` 3 para base y 4 para Splendid.

Por ejemplo:

```text
Fireglow base 43476 -> v2.socket_1tier_red -> 43490..43499
Splendid base 43483 -> v2.socket_2tier_red -> 43500..43509
```

La regla se aplica también a brown, blue, yellow, green y pink. Tier 2 no se
obtiene al abrir una gema Tier 1: primero debe fabricarse el objeto Splendid
correspondiente mediante Handicrafts.

## Generación

```powershell
python .\extract_native_selective_items.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b10-socket-context-v1.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b11-selective-lunagem-v1.sqlite3 `
  --manifest ..\generated\native-selective-items-phase-b11-v1.json
```

El generador realiza dos builds, exige SHA-256 idéntico y ejecuta
`quick_check`, `integrity_check` y validación de referencias.
