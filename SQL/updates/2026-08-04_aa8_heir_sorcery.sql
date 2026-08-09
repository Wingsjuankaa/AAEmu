ALTER TABLE `characters`
  ADD COLUMN `heir_level` tinyint(3) UNSIGNED NOT NULL DEFAULT 0 AFTER `level`,
  ADD COLUMN `heir_exp` bigint(20) NOT NULL DEFAULT 0 AFTER `heir_level`;

CREATE TABLE IF NOT EXISTS `character_skill_active_types` (
  `owner` int(10) UNSIGNED NOT NULL,
  `heir_skill_type` int(10) UNSIGNED NOT NULL,
  `skill_type` int(10) UNSIGNED NOT NULL,
  `active_type` tinyint(3) UNSIGNED NOT NULL,
  PRIMARY KEY (`owner`,`heir_skill_type`,`skill_type`) USING BTREE
) ENGINE=InnoDB CHARACTER SET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE IF NOT EXISTS `heir_skill_activations` (
  `owner` int(10) UNSIGNED NOT NULL,
  `heir_skill_id` int(10) UNSIGNED NOT NULL,
  `successor_skill_id` int(10) UNSIGNED NOT NULL,
  PRIMARY KEY (`owner`,`heir_skill_id`) USING BTREE,
  UNIQUE KEY `uq_heir_successor` (`owner`,`successor_skill_id`) USING BTREE
) ENGINE=InnoDB CHARACTER SET=utf8 COLLATE=utf8_general_ci;
