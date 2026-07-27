# Checkpoint: capas nativas de spawners NPC del `game_pak` AA8 v2

## Corrección del checkpoint v1

La extracción global realizada durante la reconstrucción de creación de
personajes sí contenía una superficie que el escaneo temático anterior no
había clasificado: 45 archivos raíz `.lyr`. Trece de ellos contienen objetos
`NpcPointSpawner` o `NpcAreaSpawner`.

Por lo tanto, queda reemplazada esta conclusión de v1:

> `game_pak` no contiene una relación de placement NPC utilizable.

La conclusión correcta y más estrecha es:

> `game_pak` contiene placements nativos parciales y estructurados de NPC,
> pero todavía no demuestra el catálogo completo de spawners activos ni el
> mundo/revisión activa de cada capa raíz.

## Evidencia recuperada

El inventario exhaustivo y reproducible encontró:

| Evidencia | Cantidad |
|---|---:|
| Archivos `.lyr` revisados | 45 |
| Archivos con spawners NPC | 13 |
| Filas de spawner | 157 |
| `spawnerId` únicos | 126 |
| `NpcPointSpawner` | 149 |
| `NpcAreaSpawner` | 8 |
| IDs NPC únicos en point-spawners | 42 |
| IDs NPC cerrados contra `game11.npcs` | 42 |
| Modelos nativos distintos enlazados | 19 |
| Placements con `Pos="0,0,0"` | 5 |

Cada `NpcPointSpawner` conserva:

- `spawnerId`;
- ID NPC primario incluido en `NPC_Spawner_Type`;
- posición y cuaternión de rotación;
- punto y ángulo de spawn;
- rutas `AIPath`, cuando existen;
- identificador interno `spawnerType`.

Cada `NpcAreaSpawner` conserva además los puntos, triángulos, ponderaciones de
área y `roamingArea`. Sus IDs primarios `23563` y `23566` no son IDs de
`npcs`; se mantienen como tipos/grupos todavía no resueltos.

Los 42 IDs primarios de `NpcPointSpawner` existen en el catálogo nativo
`game11.npcs`. Sus 19 `model_id` existen en `models`; 18 cierran hasta
`ActorModel` y uno (`buddha_statue`) es un `PrefabModel`.

## Límites de autoridad

Los `.lyr` son artefactos nativos del cliente Kakao 8.0.3.12, no filas
históricas 3.0. Sin embargo, varios son capas de eventos fechadas o revisiones
duplicadas. Diecisiete `spawnerId` aparecen más de una vez; quince conservan
la misma firma y dos tienen variantes entre revisiones.

Antes de desplegarlos faltan:

1. demostrar el `world_id` y zona de cada capa raíz;
2. decidir qué revisión de capa estaba activa para r558734;
3. resolver cinco placements con origen `0,0,0`;
4. cerrar los ocho area-spawners contra sus tipos/grupos;
5. reconciliar `spawnerId` con `npc_spawners` y `npc_spawner_npcs`;
6. verificar el consumidor servidor y las reglas temporales de eventos.

## Misiones

Este hallazgo no agrega filas de misiones. Ningún objeto `.lyr` contiene
atributos `questId` o `questContextId`. El Lua de cliente confirma el flujo
de interacción mediante `X2Quest` y `npcId`, pero obtiene los contextos desde
el estado/datos del juego; no incorpora el catálogo ni las asignaciones de
misión dentro de las capas.

Las 7.826 `quest_contexts`, 32.191 `quest_components` y 42.446 `quest_acts`
habilitados recuperados en v1 siguen siendo la autoridad nativa disponible
para misiones.

## Repetición

Desde la raíz del repositorio:

```powershell
python reconstruccion_npcs_quests_8\extract_gamepak_npc_spawner_layers.py
python -m unittest reconstruccion_npcs_quests_8\test_gamepak_npc_spawner_layers.py -v
```

El resultado es:

`reconstruccion_npcs_quests_8/generated/gamepak-native-npc-spawner-layers-v1-manifest.json`
