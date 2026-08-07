# Checkpoint: AA8 doodad visibility and deferred phase-cycle guard v1

Date: 2026-08-02

Authority: ArcheAge Kakao 8.0.3.12 r558734, observed local protocol,
the decoded AA8 rows for doodad 2231 and groups 4257/4271/4272, and the
current AAEmu doodad visibility implementation used only as corroborating
backend reference.

## Incident

After completing quest 4411 at Dalia, Dannia disconnected reproducibly about
24-36 seconds after spawning near three target doodads. Removing reward item
24087 from equipment did not change the failure, which excluded the item as
the primary cause.

Diagnostic packet metadata identified the repeating objects:

- objIds 27814, 27818 and 27819;
- doodad template 2231;
- phase cycle 4257 -> 4271/4272 -> 4257;
- twelve `SCDoodadPhaseChangedPacket` notifications per three-second burst.

The client stopped sending packets at the first burst while the server
continued running normally. There was no fatal exception or container restart.

## Proven cause

`Region.AddToCharacters` treated doodads twice: it called
`AddVisibleObject` for each one and later sent the authoritative batched
`SCDoodadsCreatedPacket` list. The same visibility path also reset the doodad
to its starting group and executed its phase functions again for every
character entry.

Template 2231 has a native ratio-selection group at 4257 and three-second
clout return phases. The deferred return lost its traversal history because
`Doodad.DoPhaseFuncs` cleared `ListGroupId` before the delayed callback. The
return therefore re-entered 4257 as a new chain instead of terminating the
cycle.

## Correction

- Visibility skips per-object doodad handling and relies exclusively on the
  existing batched creation packets.
- Visibility no longer mutates shared doodad phase or executes phase effects.
- Phase traversal history remains alive across deferred phase functions; a
  return to an already visited phase clears and terminates the chain.
- `TryTrackPhaseTraversal` centralizes that cycle guard and has direct
  regression coverage.
- Temporary packet metadata remains available in
  `SCDoodadPhaseChangedPacket.Verbose` for the controlled acceptance pass.

## Validation

- Targeted .NET 3.1 tests: 50/50 passed.
- Complete .NET 3.1 suite: 350/350 passed.
- Deployed image:
  `sha256:6cc2f781b0df0e26c0eea5650323f619e3c81da7629840ea7dba895727d35cf8`.
- Rollback image: `aaemu-game:rollback-doodad-phase-trace-20260802`.
- Mounted compact:
  `compact-8.0-runtime-native-quest4411-v2.sqlite3`, SHA-256
  `B3514EB99127BEACBC469A52789D7C99C3347CE43B2F2AB661984E644EE178C8`.
- Game and Stream started and registered on LoginServer; restart count zero.
- Controlled relog remained connected beyond the former failure window.
- Acceptance trace contained 17 normal `SCDoodadsCreatedPacket` batches,
  zero individual duplicate creation packets, and zero phase-change packets
  for template 2231.

Quest 4411 remains completed (no active quest row; completed chunk 68 retains
bit 59). Reward item instance 16777287 remains intact in Inventory slot 31.

## Runtime note

During deployment, `.env` was externally changed to a different compact.
It was not edited by this work. The active game container was recreated with
an explicit process-scoped `COMPACT_DB` override to the quest4411-v2 runtime.
Future recreations must select the intended compact explicitly or reconcile
the external `.env` change first.
