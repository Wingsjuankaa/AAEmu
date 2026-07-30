# Checkpoint Stage 90 V3 — cierre de enums nativos y `plot_event`

## Alcance

Esta iteración continuó exclusivamente el descifrado forense del cliente Kakao
8.0.3.12 r558734. No se modificó AAEmu, la compact activa, `.env`, MySQL,
Docker ni ninguna mecánica de juego.

Antes de construir se verificaron y eliminaron siete SQLite temporales
abandonadas del directorio forense:

- `.aa8-client-knowledge.utx2brv6.sqlite`
- `.stage-50-skills.e5q97i3o.sqlite`
- `.stage-50-skills.e5q97i3o.sqlite-journal`
- `.stage-50-skills.ubpuxlwy.sqlite`
- `.stage-50-skills.ubpuxlwy.sqlite-journal`
- `.stage-50-skills.uenqwgg8.sqlite`
- `.stage-50-skills.uenqwgg8.sqlite-journal`

Se liberaron 15.968.315.696 bytes. La eliminación fue permanente y la
auditoría final no encontró ninguna SQLite temporal oculta.

## Cierre de Stage 40

### `quest_detail`

`quest_detail` no es una tabla SQL ausente. Es un enum escalar inline consumido
por el cliente. Se recuperó el switch nativo completo con paridad x64/x86:

| ID | etiqueta nativa |
|---:|---|
| 1 | `normal` |
| 2 | `main` |
| 3 | `saga` |
| 4 | `tutorial` |
| 5 | `hidden` |
| 7 | `daily` |
| 8 | `livelihood` |
| 9 | `group` |
| 10 | `daily_hunt` |
| 11 | `daily_livelihood` |
| 12 | `daily_group` |
| 13 | `today` |
| 14 | `hero` |
| 15 | `weekly` |
| 16 | `expedition` |

El valor 6 cae en el default `invalid quest_detail` y no se materializó como
miembro válido. Los valores 11 y 12 se conservan como miembros nativos válidos
aunque el dataset actual no los referencia.

Evidencia:

- x64 `FUN_398764f0`
- x86 `FUN_398ece80`
- binding Lua `GetQuestDetail`
- callback x64 que lee `quest_context.detail_id`
- 7.826 relaciones `uses_quest_detail` confirmadas

### Dominios escalares inline

Los siguientes dominios tampoco tienen una consulta propietaria. Sus IDs,
layout, membresía y relaciones se confirmaron desde filas y loaders nativos:

| dominio | IDs | referencias | loader x64 |
|---|---:|---:|---|
| `quest_component_text_kind` | 4, 5, 6 | 13.531 | `FUN_399f2f00` |
| `chat_bubble_kind` | 1, 2, 3 | 25.939 | `FUN_399e1f80` |
| `npc_ai` | 1, 2, 3, 4, 6 | 32.191 | `FUN_399f3a80` |

Sus etiquetas humanas no se inventaron. Quedaron tres regiones opacas
`native_enum_semantic_labels_not_yet_recovered`, una por dominio. Esto separa:

- identidad, tipo y relaciones: `confirmed`
- semántica humana de cada valor: `opaque`

Resultado total de Stage 40:

- 26 miembros escalares confirmados
- 79.487 relaciones confirmadas hacia esos dominios
- cero gaps para los cuatro dominios
- tres regiones opacas semánticas explícitas

## Cierre de Stage 50

La consulta nativa completa:

```sql
SELECT ... FROM plot_events ORDER BY plot_id ASC, position ASC
```

produce 45.959 filas. Los siguientes 14 IDs están referenciados pero ausentes
de ese resultado no filtrado:

`4, 5, 6, 7, 8, 9, 10, 11, 15, 19, 20, 21, 22, 31`.

Se clasificaron como tombstones nativos. Todas sus referencias proceden de
`buff_triggers.event_id`:

- 14 entidades `plot_event` con `lifecycle=tombstone`
- 4.963 relaciones confirmadas
- cero gaps asociados

La construcción falla si cambia cualquier ID, frecuencia o fuente de esas
referencias.

## Impacto global

Comparación con V2:

| métrica | V2 | V3 | diferencia |
|---|---:|---:|---:|
| gaps fuente | 114.430 | 114.392 | -38 |
| regiones opacas | 89 | 92 | +3 |
| raíces causales | 513 | 499 | -14 |
| impactos | 460.946 | 460.835 | -111 |
| evidencias | 1.004 | 997 | -7 |
| cola de trabajo | 513 | 499 | -14 |

Los 38 IDs priorizados dejaron de ser gaps. Las tres opacidades nuevas son
deliberadas y representan únicamente etiquetas semánticas aún no demostradas.
No quedan raíces ni impactos para:

- `quest_detail`
- `quest_component_text_kind`
- `chat_bubble_kind`
- `npc_ai`
- `plot_event`

## Artefactos aceptados

- `stage-40-quests.sqlite`
  - SHA-256:
    `0338B3E40960A14FF71949F3840934B3C3394507D3AE0CA23DB6BD444C6C8DF6`
- `stage-50-skills.sqlite`
  - SHA-256:
    `AA75673AAD2141D1E7BC1D383147BEB909860D14E1DA1390A2BEBBBC58FB1FCB`
- `stage-90-coverage-closure.sqlite`
  - SHA-256:
    `5DAB842966AE9023988185AFA2C4DF2382C9BFF4624791B520D28B057CCF6D30`
- `aa8-client-knowledge.sqlite`
  - 6.904.795.136 bytes
  - SHA-256:
    `F11DBAE4073A70953D9C4FC94384E9C5FD76274F148A03CCB6FD7D1C4F3029EC`
- `manifest.json`
  - SHA-256:
    `2F4C416E6218C65FF9208478FF87D4EC74A5BE5F8490F4DA4CE8986AF7EAB7B1`

Evidencia Ghidra nueva:

- `ghidra-stage90-enum-consumers-x64.txt`
  - `C8CAA33F3E14564F2D0421DA65E7F1331D44964BE7BBDCD4523D80B13F147460`
- `ghidra-stage90-enum-consumers-x86.txt`
  - `8FE213FFC9091DA9AB3798F5785A6F5468CBC5D369E44EE5C5ECFDE12172D624`
- `ghidra-stage90-quest-bubble-callbacks-x64.txt`
  - `FDA7E39C95D4C5B2E98CD78B79216BA46448346F60F2B925B6C45C3CFED3F9BC`
- `ghidra-stage90-quest-component-struct-x64.txt`
  - `C710EE6B3461DDF74B1E80EF64664D8387A410DB8FBA09FEF7282515C807B339`

Reportes regenerados:

- `coverage-summary.csv`
  - `C539B7480D313E63246FF6E72B8716A9F940F129F097A859E8C2231D07A09B0F`
- `gaps-priority.csv`
  - `3177E598A62FACF1B5781C419FAE0027C8FBEC84D8FB1B3D2B9DCFDE25A8A407`
- `coverage-closure-work-queue.csv`
  - `86CB63817A438F334ADBB95342D9F3E53A9E873258E16F45EBEAA99399871E1F`
- `opaque-regions.json`
  - `F56A8F57BCCAF7C8FB1807D5A35013D9C36174F79513AE47036DD9BDC9CB7499`
- `viewer-coverage-closure.html`
  - `24A3800F078F6828C361C7078FB7F61C6E98C5D4CFF96002B39CFEBA50D155D6`

## Aceptación

- 17/17 pruebas Python aprobadas
- Stage 40 idéntica en dos builds
- Stage 50 idéntica en dos builds
- Stage 90 idéntica en dos builds
- consolidada idéntica en dos builds
- `PRAGMA quick_check = ok`
- `PRAGMA integrity_check = ok`
- cero huérfanos en propiedades, relaciones, cached results, wiki, blockers y
  work queue
- linaje completo de nueve stages
- cero SQLite temporales ocultas

## Siguiente frontera recomendada

Antes de perseguir ciegamente el ranking bruto, conviene reconciliar gaps
locales contra el estado final cross-stage. La cola aún presenta como faltantes
familias como `item`, `skill`, `icon` y `quest` que sí tienen entidades
confirmadas en otras stages. Normalizar esa reconciliación evitará invertir
tiempo en falsos gaps y reordenará el fan-out real.

Después de esa normalización, el siguiente lote concreto sugerido es:

1. `quest_name_kind`: 3 IDs, 1.673 referencias.
2. `quest_context_text_kind`: 5 IDs, 918 referencias.
3. `world_interaction`: 64 IDs, 7.679 referencias, si continúa faltante tras
   la reconciliación.
4. `npc_group` y `sphere`, separando primero dominios escalares de tablas
   propietarias reales.

`loot_pack` conserva evidencia `native_result_absent`; no debe encabezar una
nueva decodificación hasta aparecer otro stream, paquete auxiliar o captura
local no persistente que contenga sus filas.
