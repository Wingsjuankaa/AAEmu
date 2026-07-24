-- Read-only migration audit. This file never mutates game state.
-- Run only after loading the candidate coverage table into a temporary schema.
SELECT
    i.owner,
    i.template_id,
    i.type,
    i.slot_type,
    i.slot,
    i.grade,
    COUNT(*) AS instances
FROM items AS i
GROUP BY i.owner, i.template_id, i.type, i.slot_type, i.slot, i.grade
ORDER BY i.owner, i.slot_type, i.slot;

-- The actual quarantine transaction is intentionally not generated until
-- compact-8.0-runtime-native-equipment-v1 is marked deployable and a complete
-- backup has been verified.
