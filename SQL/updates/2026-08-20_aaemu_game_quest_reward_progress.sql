CREATE TABLE IF NOT EXISTS `character_quest_reward_progress` (
  `character_id` int unsigned NOT NULL,
  `leadership_point` int unsigned NOT NULL DEFAULT 0,
  `daily_leadership_point` int unsigned NOT NULL DEFAULT 0,
  `daily_reset_date` date NOT NULL,
  PRIMARY KEY (`character_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 quest leadership state';

CREATE TABLE IF NOT EXISTS `expedition_quest_progress` (
  `expedition_id` int unsigned NOT NULL,
  `exp` bigint unsigned NOT NULL DEFAULT 0,
  `daily_exp` int unsigned NOT NULL DEFAULT 0,
  `daily_reset_date` date NOT NULL,
  PRIMARY KEY (`expedition_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 expedition experience granted by quests';

CREATE TABLE IF NOT EXISTS `quest_reward_ledger` (
  `attempt_id` binary(16) NOT NULL,
  `act_id` int unsigned NOT NULL,
  `character_id` int unsigned NOT NULL,
  `quest_template_id` int unsigned NOT NULL,
  `detail_type` varchar(64) NOT NULL,
  `detail_id` int unsigned NOT NULL,
  `status` tinyint unsigned NOT NULL DEFAULT 0 COMMENT '0=pending, 1=completed',
  `created_at` datetime NOT NULL,
  `completed_at` datetime NULL,
  PRIMARY KEY (`attempt_id`, `act_id`),
  KEY `idx_quest_reward_ledger_character` (`character_id`, `quest_template_id`),
  CONSTRAINT `chk_quest_reward_ledger_status` CHECK (`status` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Idempotent AA10 quest reward acts; pending rows require reconciliation';

CREATE TABLE IF NOT EXISTS `family_progress` (
  `family_id` int unsigned NOT NULL,
  `level` int unsigned NOT NULL DEFAULT 1,
  `exp` int unsigned NOT NULL DEFAULT 0,
  `name` varchar(128) NOT NULL DEFAULT '',
  `type` int NOT NULL DEFAULT 0,
  `inc_member_count` int unsigned NOT NULL DEFAULT 0,
  `change_name_time` bigint NOT NULL DEFAULT 0,
  PRIMARY KEY (`family_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 family progression and UI state';

CREATE TABLE IF NOT EXISTS `resident_service_points` (
  `character_id` int unsigned NOT NULL,
  `zone_group_id` smallint unsigned NOT NULL,
  `service_point` int unsigned NOT NULL DEFAULT 0,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`character_id`, `zone_group_id`),
  KEY `idx_resident_service_points_zone` (`zone_group_id`, `service_point`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 per-character resident service points';

CREATE TABLE IF NOT EXISTS `resident_zone_balances` (
  `zone_group_id` smallint unsigned NOT NULL,
  `normal_charge` bigint unsigned NOT NULL DEFAULT 0,
  `hunting_charge` bigint unsigned NOT NULL DEFAULT 0,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`zone_group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 resident normal and hunting charge balances';
