USE aaemu_game;

CREATE TABLE IF NOT EXISTS `character_gacha_records` (
  `owner` int unsigned NOT NULL COMMENT 'Character id',
  `gacha_loot_pack_id` int unsigned NOT NULL,
  `total_count` int unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`owner`,`gacha_loot_pack_id`) USING BTREE,
  KEY `idx_character_gacha_records_owner` (`owner`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 Loot Gacha base counters';

CREATE TABLE IF NOT EXISTS `character_gacha_advanced_records` (
  `owner` int unsigned NOT NULL COMMENT 'Character id',
  `gacha_advanced_loot_pack_id` int unsigned NOT NULL,
  `last_round` int unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`owner`,`gacha_advanced_loot_pack_id`) USING BTREE,
  KEY `idx_character_gacha_advanced_records_owner` (`owner`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 Loot Gacha pity checkpoints';
