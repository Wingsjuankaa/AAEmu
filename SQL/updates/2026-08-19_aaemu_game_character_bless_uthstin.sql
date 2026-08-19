USE aaemu_game;

CREATE TABLE IF NOT EXISTS `character_bless_uthstin` (
  `owner` int unsigned NOT NULL COMMENT 'Character id',
  `active_page` tinyint unsigned NOT NULL DEFAULT 0,
  `page_count` tinyint unsigned NOT NULL DEFAULT 1,
  `extended_max_stats` int unsigned NOT NULL DEFAULT 0,
  `extend_count` int unsigned NOT NULL DEFAULT 0,
  `reset_date` date NOT NULL,
  PRIMARY KEY (`owner`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 Migration Scaling character state';

CREATE TABLE IF NOT EXISTS `character_bless_uthstin_pages` (
  `owner` int unsigned NOT NULL COMMENT 'Character id',
  `page_index` tinyint unsigned NOT NULL,
  `stat_str` int NOT NULL DEFAULT 0,
  `stat_dex` int NOT NULL DEFAULT 0,
  `stat_sta` int NOT NULL DEFAULT 0,
  `stat_int` int NOT NULL DEFAULT 0,
  `stat_spi` int NOT NULL DEFAULT 0,
  `normal_apply_count` int unsigned NOT NULL DEFAULT 0,
  `special_apply_count` int unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`owner`,`page_index`) USING BTREE,
  KEY `idx_character_bless_uthstin_pages_owner` (`owner`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AA10 Migration Scaling page records';
