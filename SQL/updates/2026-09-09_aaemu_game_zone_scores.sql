-- Additive storage for the native persistent zone_score_kinds; currently Garden kind 3.
CREATE TABLE IF NOT EXISTS `character_zone_scores` (
  `owner` int unsigned NOT NULL,
  `kind` int unsigned NOT NULL,
  `score` int unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`owner`, `kind`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
