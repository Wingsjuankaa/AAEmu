USE aaemu_game;

-- AA10 Account Attendance is account-scoped and advances by one cumulative campaign day per
-- UTC calendar day. The two uniqueness constraints independently prevent duplicate campaign
-- indices and two claims on the same UTC date, including requests from concurrent characters.
CREATE TABLE IF NOT EXISTS `account_attendance_claims` (
  `account_id` int unsigned NOT NULL,
  `campaign_year` smallint unsigned NOT NULL,
  `campaign_month` tinyint unsigned NOT NULL,
  `day_count` tinyint unsigned NOT NULL,
  `claim_day` date NOT NULL,
  `claimed_at` datetime NOT NULL,
  `is_archelife` tinyint(1) NOT NULL DEFAULT 0,
  `claimed_by` int unsigned NOT NULL,
  PRIMARY KEY (`account_id`, `campaign_year`, `campaign_month`, `day_count`),
  UNIQUE KEY `uq_account_attendance_claim_day` (`account_id`, `claim_day`),
  KEY `idx_account_attendance_claimed_by` (`claimed_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
