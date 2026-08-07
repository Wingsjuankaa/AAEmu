# Checkpoint: native quest 4411 / Marian interaction v1

Date: 2026-08-02

## Result

Quest 4411 (`Tying Up Loose Ends`) now exposes the native AA8 interaction on the standing Marian NPC proxy. The proxy is materialized as doodad template 14125 with initial function group 41603, whose `DoodadFuncUse` invokes skill 41999 and world interaction 19 (`Marian's Farewell`).

No character quest state was edited, migrated, abandoned, or force-completed.

## Native authority

- Quest 4411 progress component: 41261.
- Progress act: 64231 / `QuestActObjInteraction`, detail 1115.
- Required object: doodad 14125, world interaction 19, alias 6600, count 1.
- Standing Marian NPC template: 10797, spawn 12796.
- Interactive client-doodad phase: function group 41603.
- Use function: 38602 -> `DoodadFuncUse` 10936 -> skill 41999.
- Skill effects restored from the AA8 decoded corpus:
  - skill effect 59299 -> effect 77957 -> `InteractionEffect` 7874 (`wi_id=19`).
  - skill effect 59325 -> effect 77994 -> `BubbleEffect` 6013.
- Report target after completion: NPC 11283 (Dalia).

Evidence dossiers:

- `E:\AAEmu-Research\output\aa8-client-forensics\dossiers\quest-4411.json`
- `E:\AAEmu-Research\output\aa8-client-forensics\dossiers\doodad-14125.json`
- `E:\AAEmu-Research\output\aa8-client-forensics\dossiers\skill-41999.json`

## Server changes

- Client-doodad NPC indexing now retains the selected function group, rather than only the doodad template.
- All Start/Normal `npctype://` phases are considered.
- Duplicate NPC mappings prefer a phase with `DoodadFuncUse`, then any phase with functions, then Normal, then the lowest group id.
- Synthetic client-doodad spawns carry the selected initial function group through `SpawnManager` and `DoodadSpawner`.
- `Doodad.GetFuncGroupId()` preserves an explicitly assigned nonzero phase.

For NPC template 10797 the deterministic selection is doodad 14125 / function group 41603.

## Runtime artifact

- Runtime: `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-quest4411-v1.sqlite3`
- SHA-256: `B3514EB99127BEACBC469A52789D7C99C3347CE43B2F2AB661984E644EE178C8`
- Manifest: `D:\Proyectos\AAemu\rama_8\reconstruccion_npcs_quests_8\generated\native-quest-4411-marian-v1-manifest.json`
- Manifest SHA-256: `9DD76E1A863A00BCED01AC792AD8DF19B47E1FCE161DFEAE45CD0783356A687E`
- Builder: `D:\Proyectos\AAemu\rama_8\reconstruccion_npcs_quests_8\build_native_quest_4411_runtime.py`
- Focused test: `D:\Proyectos\AAemu\rama_8\reconstruccion_npcs_quests_8\test_native_quest_4411.py`

The artifact was built twice deterministically with the same SHA-256. SQLite `quick_check` and `integrity_check` both returned `ok`.

## Validation

- Focused quest 4411 Python suite: 5/5 passed.
- Related client-doodad/quest Python suites: 22/22 passed.
- AAEmu .NET test suite under the official .NET Core 3.1 SDK container: 336/336 passed.
- Script compiler: 0 errors (8 pre-existing warnings).
- Runtime reward item closure verified for quest 4411.
- Report NPC 11283 exists in the deployed runtime.

Deployed service observations:

- Container `aaemu8-game-1`: running, restart count 0.
- Game ports 2239 and 2250 are published.
- Mounted `/app/Data/compact.sqlite3` SHA-256 matches `B3514E...178C8`.
- Server log: `Indexed npcTemplate=10797 -> doodadTemplate=14125, funcGroup=41603`.
- Server log: `Replaced NPC spawn 12796: npcTemplate=10797 -> doodadTemplate=14125, funcGroup=41603`.
- Server reached `Server started` and registered on LoginServer.

## Backup and rollback

- Backup directory: `D:\Proyectos\AAemu\backups\pre-native-quest4411-marian-v1-20260802-120242`
- Full MySQL dump SHA-256: `83B008495FDC71EE4B6CCF2F1B6B5475734D026080C77CF37863592271D4D0CF`
- Previous compact SHA-256: `E62DE...` (stored as `compact-before.sqlite3`).
- Quest 4411 state snapshot SHA-256: `DF40BB5BF9FD601718C1C12987A749049F92933E76DA8503A8B1668813867B6C`.
- Rollback image: `aaemu-game:pre-native-quest4411-marian-v1-20260802-120242`.
- Rollback image ID: `sha256:3f9a9c4724daeab4357566e5e405c76c9591ee7eebe49dc7826398111d446fcc`.

## Manual acceptance test

1. Reconnect the client after the game-container recreation.
2. Approach the standing Marian at spawn 12796 (not the corpse Marian).
3. Use the interaction prompt once.
4. Expect the farewell interaction/speech and objective `Marian's Farewell` to become 1/1.
5. Confirm the quest becomes Ready and points to Dalia (NPC 11283).
6. Stop before reporting to Dalia if a post-interaction server-log audit is desired.
