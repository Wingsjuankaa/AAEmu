# Checkpoint: catálogo nativo de NPC, modelos y misiones AA8 v1

## Alcance

Este checkpoint abre el dominio `reconstruccion_npcs_quests_8` y fija la
primera frontera reproducible para Kakao 8.0.3.12 r558734:

`NPC -> model -> actor model`

`quest context -> component -> enabled act -> concrete act detail`

`quest component -> NPC / NPC spawner`

Todavía no es un cierre desplegable. El extractor no modifica el compact ni
los JSON de mundo.

## Autoridad y separación de procedencia

- `game11`: filas nativas cacheadas.
- `x2game.dll`: SQL, orden de columnas, tipos y consumidores cliente.
- `game_pak`: sólo evidencia de superficies de mundo/área cuando corresponde.
- compact runtime actual: comparación de cobertura, nunca fuente de filas AA8.
- compact 3.0 y `npc_spawns.json`: referencia histórica, prohibida como
  autoridad de gameplay AA8.

## Tablas nativas cerradas a nivel de fila

| Tabla | Filas AA8 | Rango cacheado |
|---|---:|---|
| `actor_models` | 1.598 | `0x3D6E2DD..0x3E5ECA6` |
| `models` | 2.907 | `0x3F1BECB..0x3F706F3` |
| `npcs` | 18.217 | `0x5A02E9D..0x5FD8D95` |
| `quest_acts` habilitados | 42.446 | `0x6DB2158..0x6E6D1D6` |
| `quest_components` | 32.191 | `0x745854B..0x7647870` |
| `quest_contexts` | 7.826 | `0x76635F8..0x77182D3` |

Cada rango se valida por `SQLITE_ROW`, layout nativo, cantidad esperada,
unicidad de `id`, byte final `SQLITE_DONE` y hash canónico de filas.

`x2game.dll` contiene además 97 consultas SQL nativas del dominio
`quest_act*`: la tabla polimórfica principal y 96 catálogos concretos. El
manifiesto conserva cada consulta y su offset de archivo. Los 85 tipos
efectivamente usados por los actos habilitados quedaron resueltos; 29 no
tienen todavía una clase homónima en el servidor. `QuestManager` sólo carga
64 de los 96 catálogos concretos, por lo que 32 loaders AA8 también deben
implementarse.

## Hallazgo frente al runtime

El runtime activo parte de datos históricos y queda por debajo del catálogo
nativo: 15.688 NPC, 2.127 modelos, 1.086 actor-modelos, 6.628 contextos y
24.408 componentes. Además, su tabla `npcs` expone menos columnas que el
loader AA8. El manifiesto generado calcula de nuevo estas diferencias sin
usar el runtime como procedencia.

## Strings cacheados

Sólo se resuelven bases demostradas por autorreferencias del mismo resultado:

- `actor_models`: primera referencia `150174`.
- `models`: primera referencia `154480`.
- `quest_acts`: primera referencia `320614`.

Las referencias a caché global o a resultados anteriores permanecen como
`<ref:N>` y se cuentan como bloqueo. No se rellenan con nombres de 3.0.

## Ubicaciones

`SpawnManager` consume actualmente
`AAEmu.Game/Data/Worlds/*/npc_spawns.json`. Esos archivos son legado de
servidor, no autoridad Kakao 8.0.

El contenedor cliente descifrado fue auditado de forma exhaustiva en sus cinco
streams no vacíos (`game0`, `game2`, `game6`, `game7`, `game11`). No existe
ninguna cadena contigua de filas que satisfaga los layouts exactos de
`npc_spawners` o `npc_spawner_npcs` demostrados por `x2game.dll`. Esto prueba
ausencia en la superficie cliente disponible; no prueba ausencia en la compact
privada del servidor Kakao.

La extracción XML completa de `game_pak` sólo mostró entidades de área de
misión y algunos marcadores `Spawn_*`; no contiene una relación completa
`npc_spawner_id -> world -> position -> rotation`. Por lo tanto, esos
marcadores no se convierten en spawns de servidor.

## Bloqueos para el primer despliegue

1. Localizar y decodificar `npc_spawners`.
2. Localizar y decodificar `npc_spawner_npcs`.
3. Reconstruir la fuente nativa de placements con mundo, coordenadas y giro.
4. Extraer todas las tablas concretas referidas por `quest_acts` habilitados.
5. Resolver las referencias de strings restantes con evidencia nativa.
6. Adaptar esquema y consumidores del servidor y recién entonces construir
   un compact runtime nuevo.

## Repetición

Desde la raíz del repositorio:

```powershell
python reconstruccion_npcs_quests_8\extract_native_npc_quest_catalog.py
```

El resultado esperado es
`reconstruccion_npcs_quests_8/generated/native-npc-quest-catalog-v1-manifest.json`.
Dos ejecuciones contra las mismas fuentes deben producir exactamente el mismo
archivo.

La regresión automatizada se ejecuta con:

```powershell
python -m unittest reconstruccion_npcs_quests_8\test_native_npc_quest_catalog.py -v
```

La auditoría exhaustiva de spawners (tarda aproximadamente un minuto) se
repite con:

```powershell
python reconstruccion_npcs_quests_8\audit_native_spawner_streams.py
```
