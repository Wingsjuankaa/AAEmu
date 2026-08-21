USE aaemu_game;

-- Live AA10 competition/conquest scores are global world state. Keeping the timer and every
-- scoreboard row together makes restart recovery deterministic and preserves winner-only resets.
CREATE TABLE IF NOT EXISTS `faction_competition_states` (
  `kind` tinyint unsigned NOT NULL COMMENT '0=faction competition, 1=conquest war',
  `source_id` int unsigned NOT NULL,
  `zone_group_id` smallint unsigned NOT NULL,
  `faction_id` int NOT NULL,
  `points` int unsigned NOT NULL DEFAULT 0,
  `active` tinyint(1) NOT NULL DEFAULT 0,
  `started_at` datetime NULL,
  `ends_at` datetime NULL,
  PRIMARY KEY (`kind`, `source_id`, `faction_id`),
  KEY `idx_faction_competition_zone` (`zone_group_id`, `active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
