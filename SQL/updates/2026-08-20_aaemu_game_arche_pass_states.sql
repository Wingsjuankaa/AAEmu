CREATE TABLE IF NOT EXISTS `character_arche_passes` (
  `character_id` int unsigned NOT NULL,
  `arche_pass_id` int NOT NULL,
  `point` bigint unsigned NOT NULL DEFAULT 0,
  `status` tinyint unsigned NOT NULL,
  `premium` tinyint(1) NOT NULL DEFAULT 0,
  `last_reward_tier` int unsigned NOT NULL DEFAULT 0,
  `last_premium_reward_tier` int unsigned NOT NULL DEFAULT 0,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`character_id`, `arche_pass_id`),
  KEY `idx_character_arche_pass_status` (`character_id`, `status`),
  CONSTRAINT `chk_character_arche_pass_status` CHECK (`status` IN (1, 2, 3, 4, 5))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 character ArchePass ownership, progression and claim frontiers';
