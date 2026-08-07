# Checkpoint: quest 4411 Marian re-entry guard v2

Date: 2026-08-02

Authority: ArcheAge Kakao 8.0.3.12 r558734, observed client protocol,
decoded AA8 compact graph, native dossiers for skill 41999 and doodad 14125,
and the Stage 15 native corpus.

## Incident

Dannia sent one `CSStartSkillPacket` for skill 41999 at
`2026-08-02 16:39:57 UTC`. The server then recursively scheduled the same
skill through this chain:

`41999 -> InteractionEffect(use) -> Doodad.Use -> DoodadFuncUse -> 41999`

The client sent no repeated start request. The server executed 360,367 copies
of the skill before containment. The game and stream connections closed at
`16:40:37 UTC`; there was no fatal exception and the container did not
restart. The server-side interaction flood caused the disconnect.

The concurrent quest updates also granted the reward boundary once before an
explicit report to Dalia: 40,000 copper and item instances 16777466-16777468.
Quest 4411 persisted as Ready with objective 2 and invalid step 9.

## Native interpretation

- The AA8 client starts skill 41999 itself.
- Skill 41999 owns InteractionEffect 7874 (`wi_id=19`, use).
- Doodad 14125 phase group 41603 owns DoodadFuncUse 10936 and points to the
  same skill 41999.
- The observed packet trace is therefore the behavior authority: the server
  must not re-schedule the identical trigger skill when its InteractionEffect
  reaches that function.
- Quest 4411's native Ready component is 19170 and reports to NPC 11283
  (Dalia). Reward component 19171 is not valid before that report.

## Runtime changes

- `DoodadFuncUse` suppresses only an identical non-zero skill re-schedule;
  different configured skills retain the existing server scheduling path.
- `Quest.OnInteraction` serializes objective mutation and the Progress-to-Ready
  transition per quest instance.
- Persisted Ready quests beyond the Ready boundary normalize to the first
  native Ready component during character load.
- Regression coverage was added for the scheduling decision and persisted
  boundary normalization.

The immutable v2 runtime was rebuilt twice from the same pinned AA8 sources.
Both outputs are byte-identical:

`B3514EB99127BEACBC469A52789D7C99C3347CE43B2F2AB661984E644EE178C8`

This matches v1 because the incident correction is generic server behavior;
no AA8 static row required mutation.

## Character repair

Pre-repair backup:

`D:\Proyectos\AAemu\backups\pre-native-quest4411-reentry-v2-20260802-130317\mysql-all.sql`

SHA-256:

`48BBFBA1D1261783D33E08C621B01D546D89A57CE982782A067997F9F49A7CAC`

The transaction required every incident value to match before writing. It:

- moved item instances 16777466-16777468 to `quarantined_items` with runtime
  provenance instead of deleting evidence;
- removed exactly 40,000 copper from Dannia;
- preserved experience at 7,784,000;
- left no completed-quest row for 4411;
- restored quest 4411 to Ready, objective 1, step 6, component 19170.

Post-repair quest payload:

`010000000000000000000000000000000000000000000000000000000000000000000000000000000602E24A00002C3700000000000000000000`

## Validation and deployment

- Focused .NET 3.1 Docker tests: 45/45 passed.
- Complete .NET 3.1 Docker suite: 341/341 passed.
- Quest runtime and repair-stack Python tests: 11/11 passed.
- SQLite `quick_check` and `integrity_check`: `ok`.
- Script compilation on deployed server: 0 errors, 8 pre-existing warnings.
- Deployed game image:
  `sha256:04c91032850ea47c895b80e1bc8604a26e17676b6ce3efca714e585c68c26180`.
- Rollback image:
  `aaemu-game:rollback-quest4411-reentry-v2-20260802`.
- Mounted compact SHA-256 matches the v2 runtime.
- Game ports 2239/2250 are listening, registration on LoginServer succeeded,
  and restart count is zero.

One pre-existing asynchronous doodad timer emitted a non-fatal
`Collection was modified` exception after startup. It is outside the Marian
interaction chain, did not restart the service, and is not evidence of a
41999 recurrence.

## Manual acceptance boundary

1. Log in with Dannia.
2. Confirm 4411 is Ready and points to Dalia.
3. Do not interact with Marian again and do not report to Dalia yet.
4. Stop and inspect logs plus persisted quest state before the final report
   interaction is authorized.
