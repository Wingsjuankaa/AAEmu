CREATE TABLE IF NOT EXISTS native_combat_skill_status (
    skill_id INTEGER PRIMARY KEY,
    ability_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('enabled', 'quarantined')),
    reason TEXT NOT NULL DEFAULT '',
    provenance TEXT NOT NULL DEFAULT 'game11_native'
);

CREATE TABLE IF NOT EXISTS native_combat_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    provenance TEXT NOT NULL
);
