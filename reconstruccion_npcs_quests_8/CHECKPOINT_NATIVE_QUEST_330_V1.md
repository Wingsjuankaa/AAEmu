# Checkpoint: quest 330 nativa AA8 v1

## Resultado

La quest `330` quedó reconstruida como piloto desplegable contra la autoridad
Kakao `8.0.3.12 r558734`.

El runtime activo es:

`D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-quest330-v1.sqlite3`

SHA-256:

`67F473B82FB243473E54940FDC8893671FE0AEE20BCF15C5373C76CC51941007`

## Flujo cerrado

| Etapa | Evidencia AA8 |
|---|---|
| Aceptación | NPC `3597` → act `9874` → detail `1250` |
| Contexto | quest `330`, categoría `3`, capítulo `1`, índice `1`, raza `1`, zona `125` |
| Progreso | No existe componente objetivo intermedio |
| Entrega | NPC `11541` → act `2438` → detail `329` |
| EXP | `210` mediante detail `3922` |
| Moneda | `33` copper mediante `quest_supplies` nativo de nivel 1 |
| Siguiente quest | NPC `11541` → quest `2531` → detail de aceptación `2097` |

La recompensa genérica de nivel 1 también contiene `420 EXP`, pero no se
aplica porque la quest tiene un act explícito de `210 EXP`.

## Items de recompensa

Recompensas fijas:

- item `23633` x1;
- item `51185` x1;
- item `18791` x5.

Recompensa seleccionable:

- item `47868` x2; o
- item `47869` x1.

El item `23633` no existía en el runtime anterior. Su fila completa se extrajo
del resultado nativo `items` de `game11`; los otros cuatro items ya cerraban
contra el runtime AA8.

## NPC y modelos

Los NPC ya existentes en el runtime coinciden con los campos nativos necesarios:

- `3597`, Lucius, modelo `10`;
- `11541`, Parish, modelo `10`;
- modelo `10` → `ActorModel` `1`;
- `ActorModel` `1` →
  `objects/Characters/nuian/male/nude/nu_m.cdf`.

Las ubicaciones usadas por el piloto son las que ya hacían visibles a ambos
NPC en el servidor:

- spawn `7682`, NPC `3597`, zona servidor `5`;
- spawn `8238`, NPC `11541`, zona servidor `5`;
- distancia aproximada: `143.057` metros.

Estas dos ubicaciones se clasifican como
`server_derived_accepted_for_pilot`. No se presentan como coordenadas nativas
recuperadas del cliente.

## Corrección del servidor

`Quest.GetCustomSupplies` borraba una recompensa personalizada ya encontrada
cuando recorría un act posterior de otro tipo. En la quest 330 esto convertía
los `210 EXP` explícitos en cero y luego aplicaba los `420 EXP` genéricos,
además de haber ejecutado el act de EXP.

Ahora el método retorna inmediatamente el valor del act solicitado. Para la
quest 330 el resultado esperado es exactamente `210 EXP` y `33 copper`.

## Reproducción

Desde la raíz del repositorio:

```powershell
python reconstruccion_npcs_quests_8\extract_native_quest_330.py
python reconstruccion_npcs_quests_8\build_native_quest_330_runtime.py
python -m unittest reconstruccion_npcs_quests_8.test_native_quest_330 -v
```

Regresión completa del dominio:

```powershell
python -m unittest `
  reconstruccion_npcs_quests_8.test_native_npc_quest_catalog `
  reconstruccion_npcs_quests_8.test_gamepak_npc_spawner_layers `
  reconstruccion_npcs_quests_8.test_native_quest_330 -v
```

Los tests C# deben ejecutarse con .NET Core 3.1. En esta estación se validaron
dentro del SDK oficial `mcr.microsoft.com/dotnet/sdk:3.1.409-focal`: `227/227`
tests aprobados.

## Prueba dentro del juego

Usar un personaje Nuian nuevo o uno que no tenga completada la quest `330`.
Mantener al menos seis espacios libres de inventario.

1. Hablar con NPC `3597` y aceptar la quest `330`.
2. Confirmar que la quest no solicita un objetivo intermedio.
3. Ir al NPC `11541` y abrir la entrega.
4. Probar una de las dos selecciones de recompensa.
5. Confirmar:
   - quest `330` completada;
   - incremento de `210 EXP`;
   - incremento de `33 copper`;
   - items fijos `23633` x1, `51185` x1 y `18791` x5;
   - sólo la opción elegida: `47868` x2 o `47869` x1.
6. Volver a interactuar con NPC `11541` y confirmar que ofrece la quest `2531`.

La única evidencia todavía pendiente después de esta prueba es la observación
en vivo del cliente/servidor: UI de aceptación, selección, entrega, inventario,
EXP, copper y aparición de la quest siguiente.
