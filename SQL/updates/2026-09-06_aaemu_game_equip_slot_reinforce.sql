-- AA10 Ipnya progression belongs to character equipment slots, never to an item UID.
CREATE TABLE IF NOT EXISTS character_equip_slot_reinforces (
    owner INT UNSIGNED NOT NULL,
    slot TINYINT UNSIGNED NOT NULL,
    level TINYINT NOT NULL DEFAULT 1,
    experience INT NOT NULL DEFAULT 0,
    PRIMARY KEY (owner, slot),
    CHECK (level >= 1 AND experience >= 0)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS character_equip_slot_reinforce_effects (
    owner INT UNSIGNED NOT NULL,
    slot TINYINT UNSIGNED NOT NULL,
    level TINYINT NOT NULL,
    modifier INT UNSIGNED NOT NULL,
    PRIMARY KEY (owner, slot, level),
    CHECK (level >= 1 AND modifier > 0)
) ENGINE=InnoDB;
