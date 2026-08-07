# Reconstrucción nativa de NPC y quests AA8

Este directorio es la autoridad durable del dominio NPC/quests para el cliente
ArcheAge Kakao `8.0.3.12 r558734`.

## Por dónde empezar

Para reconstruir o diagnosticar cualquier quest nueva, leer primero:

```text
QUEST_RECONSTRUCTION_PLAYBOOK_V1.md
```

Ese documento contiene:

- la base global que debe funcionar antes de revisar quests individuales;
- el cierre mínimo de datos requerido por cada quest;
- un árbol de diagnóstico según el síntoma visible;
- las pruebas automáticas y manuales obligatorias;
- una plantilla para registrar cada reconstrucción.

## Checkpoints principales

```text
CHECKPOINT_NATIVE_NPC_QUEST_CATALOG_V1.md
  Identidad y relaciones nativas NPC/quest.

CHECKPOINT_NATIVE_NPC_QUEST_CATALOG_V2.md
  Spawners y ubicaciones recuperadas desde game_pak.

NPC_MODEL_RECONSTRUCTION_PATTERN_V1.md
  Patrón probado para reconstruir modelos completos, usando Lucius como caso.

CHECKPOINT_NATIVE_QUEST_330_V8_DEEP_CLIENT_PROBE.md
  Caso de referencia de extremo a extremo y causa raíz de los marcadores
  ausentes: faltaba SCFilterPacket 0x138.

CHECKPOINT_NATIVE_NUIAN_GREEN_ARC_V1.md
  Primera reparación transversal: siete quests verdes Nuian y el patrón
  ReportDoodad/client_doodad que representa NPCs lógicos como Marian.

CHECKPOINT_NATIVE_CLIENT_DOODAD_PROXY_V2.md
  Consumidor genérico de client_doodad npctype:// y corrección forense de
  quest 2256: Bloodhand Corpse es el Object 14073 respaldado por
  npctype://10646, no un ReportNpc.

CHECKPOINT_NATIVE_QUEST_2255_ITEM_CLOSURE_V1.md
  Cierre del objeto 16280 entregado al aceptar 2255, protección contra
  definiciones rechazadas y procedimiento para diagnosticar SupplyItem.

CHECKPOINT_NATIVE_QUEST_2532_REWARD_DIALOG_V1.md
  Protocolo AA8 de entrega por ReportDoodad, diálogo/reward frame 0x0AD,
  selección 1-based, preflight de recompensas y caso completo de quest 2532.

CHECKPOINT_NATIVE_NPC_VISUAL_CATALOG_V1.md
  Reconstrucción transversal de modelos, total customs, rostro, cabello,
  ropa, armas, descriptores y assets de los NPC ya presentes en runtime.

CHECKPOINT_NATIVE_QUEST_REPAIR_STACK_V1.md
  Primer stack observado: quest 2259 y carta 16259, feedback de cofres
  selectivos, idempotencia de loot de quest, reentrada de casteo y
  SkillObject AA8 tipo 28.

CHECKPOINT_NATIVE_QUEST_SUPPLY_CLOSURE_V2.md
  Segunda instancia confirmada del patrón SupplyItem: quest 2260 e ítem
  16260. Formaliza una promoción transversal explícita para objetos genéricos
  sin dependencias y conserva fail-closed todo caso todavía no demostrado.

CHECKPOINT_NATIVE_NUIA_STORY_CHAPTER6_V1.md
  Reconstrucción transversal de las 55 quests raciales Nuia de capítulos 0–6:
  grafo nativo completo, 61 items habilitados, siete client-doodads proxy y
  primitivas compartidas de sphere, cinema y talk.

CHECKPOINT_NATIVE_QUEST_3993_MULTI_PROGRESS_V1.md
  Reconciliación de quests no selectivas con múltiples componentes Progress y
  reparación al cargar el estado persistido de Runebearer.

CHECKPOINT_NATIVE_QUEST_3993_MULTI_PROGRESS_V2.md
  Separa el componente persistido de los filtros de refresco de
  SCQuestContextUpdated y reenvía todos los Progress tras relogin.

QUEST_FAILURE_BACKLOG_V1.md
  Registro acumulativo de fallos observados, evidencia, familias
  transversales, estado de reparación y criterios de retest.
```

## Nuia Story V2

`CHECKPOINT_NATIVE_NUIA_STORY_V2.md` documenta el compilador acumulativo y el
inventario de las 294 quests Nuia hasta 10682. El bloque A (capítulos 7–11)
está desplegable; la frontera posterior permanece fail-closed con blockers
exactos.

## Regla de autoridad

No completar huecos con gameplay de AA 3.0. Usar, en orden:

```text
compact AA8 descifrado
game11 nativo
x2game.dll
protocolo local observado
game_pak
wiki de la versión sólo como corroboración visible
develop sólo como referencia de implementación
```
