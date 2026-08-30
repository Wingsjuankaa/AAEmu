-- ArcheAge Returns 10.0.2.13 r575 housing owner-domain migration.
--
-- x2game-dev!FUN_3971c0c0 treats owner ids below 1000 as native
-- special/fallback ids. Move every historical low character id to old_id +
-- 1000 and update all persistent character references atomically. A second
-- execution produces an empty map, making the migration idempotent.

START TRANSACTION;

CREATE TEMPORARY TABLE `aa10_character_id_map` (
  `old_id` int unsigned NOT NULL,
  `new_id` int unsigned NOT NULL,
  PRIMARY KEY (`old_id`),
  UNIQUE KEY `uq_aa10_character_new_id` (`new_id`)
) ENGINE=MEMORY;

INSERT INTO `aa10_character_id_map` (`old_id`, `new_id`)
SELECT `id`, `id` + 1000
FROM `characters`
WHERE `id` > 0 AND `id` < 1000;

-- Abort through a primary-key violation if a target is already occupied by a
-- character or slave. CharacterIdManager audits the same shared id domain.
CREATE TEMPORARY TABLE `aa10_character_id_guard` (
  `id` int unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MEMORY;

INSERT INTO `aa10_character_id_guard` (`id`)
SELECT `id` FROM `characters`
UNION
SELECT `id` FROM `slaves`;

INSERT INTO `aa10_character_id_guard` (`id`)
SELECT `new_id` FROM `aa10_character_id_map`;

UPDATE `abilities` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `actabilities` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `appellations` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `audit_char_sus` t JOIN `aa10_character_id_map` m ON t.`sus_character` = m.`old_id` SET t.`sus_character` = m.`new_id`;
UPDATE `audit_ics_sales` t JOIN `aa10_character_id_map` m ON t.`buyer_char` = m.`old_id` SET t.`buyer_char` = m.`new_id`;
UPDATE `audit_ics_sales` t JOIN `aa10_character_id_map` m ON t.`target_char` = m.`old_id` SET t.`target_char` = m.`new_id`;
UPDATE `auction_house` t JOIN `aa10_character_id_map` m ON t.`client_id` = m.`old_id` SET t.`client_id` = m.`new_id`;
UPDATE `auction_house` t JOIN `aa10_character_id_map` m ON t.`bidder_id` = m.`old_id` SET t.`bidder_id` = m.`new_id`;
UPDATE `blocked` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `blocked` t JOIN `aa10_character_id_map` m ON t.`blocked_id` = m.`old_id` SET t.`blocked_id` = m.`new_id`;
UPDATE `character_active_buffs` t JOIN `aa10_character_id_map` m ON t.`character_id` = m.`old_id` SET t.`character_id` = m.`new_id`;
UPDATE `character_arche_passes` t JOIN `aa10_character_id_map` m ON t.`character_id` = m.`old_id` SET t.`character_id` = m.`new_id`;
UPDATE `character_bless_uthstin` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `character_bless_uthstin_pages` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `character_favorite_crafts` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `character_merchant_purchases` t JOIN `aa10_character_id_map` m ON t.`character_id` = m.`old_id` SET t.`character_id` = m.`new_id`;
UPDATE `character_quest_reward_progress` t JOIN `aa10_character_id_map` m ON t.`character_id` = m.`old_id` SET t.`character_id` = m.`new_id`;
UPDATE `character_skill_active_types` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `completed_quests` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `crime` t JOIN `aa10_character_id_map` m ON t.`criminal` = m.`old_id` SET t.`criminal` = m.`new_id`;
UPDATE `crime` t JOIN `aa10_character_id_map` m ON t.`victim` = m.`old_id` SET t.`victim` = m.`new_id`;
UPDATE `crime` t JOIN `aa10_character_id_map` m ON t.`reporter` = m.`old_id` SET t.`reporter` = m.`new_id`;
UPDATE `doodads` t JOIN `aa10_character_id_map` m ON t.`owner_id` = m.`old_id` SET t.`owner_id` = m.`new_id` WHERE t.`owner_type` = 254;
UPDATE `expedition_members` t JOIN `aa10_character_id_map` m ON t.`character_id` = m.`old_id` SET t.`character_id` = m.`new_id`;
UPDATE `expeditions` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `family_members` t JOIN `aa10_character_id_map` m ON t.`character_id` = m.`old_id` SET t.`character_id` = m.`new_id`;
UPDATE `friends` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `friends` t JOIN `aa10_character_id_map` m ON t.`friend_id` = m.`old_id` SET t.`friend_id` = m.`new_id`;
UPDATE `heir_skill_activations` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `housings` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `housings` t JOIN `aa10_character_id_map` m ON t.`co_owner` = m.`old_id` SET t.`co_owner` = m.`new_id` WHERE t.`permission` = 0;
UPDATE `housings` t JOIN `aa10_character_id_map` m ON t.`sell_to` = m.`old_id` SET t.`sell_to` = m.`new_id`;
UPDATE `item_containers` t JOIN `aa10_character_id_map` m ON t.`owner_id` = m.`old_id` SET t.`owner_id` = m.`new_id`;
UPDATE `items` t JOIN `aa10_character_id_map` m ON t.`made_unit_id` = m.`old_id` SET t.`made_unit_id` = m.`new_id`;
UPDATE `items` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `mails` t JOIN `aa10_character_id_map` m ON t.`sender_id` = m.`old_id` SET t.`sender_id` = m.`new_id`;
UPDATE `mails` t JOIN `aa10_character_id_map` m ON t.`receiver_id` = m.`old_id` SET t.`receiver_id` = m.`new_id`;
UPDATE `mates` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `music` t JOIN `aa10_character_id_map` m ON t.`author` = m.`old_id` SET t.`author` = m.`new_id`;
UPDATE `options` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `portal_book_coords` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `portal_visited_district` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `quest_reward_ledger` t JOIN `aa10_character_id_map` m ON t.`character_id` = m.`old_id` SET t.`character_id` = m.`new_id`;
UPDATE `quests` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `resident_service_points` t JOIN `aa10_character_id_map` m ON t.`character_id` = m.`old_id` SET t.`character_id` = m.`new_id`;
UPDATE `skills` t JOIN `aa10_character_id_map` m ON t.`owner` = m.`old_id` SET t.`owner` = m.`new_id`;
UPDATE `slaves` t JOIN `aa10_character_id_map` m ON t.`owner_id` = m.`old_id` SET t.`owner_id` = m.`new_id` WHERE t.`owner_type` = 0;
UPDATE `slaves` t JOIN `aa10_character_id_map` m ON t.`summoner` = m.`old_id` SET t.`summoner` = m.`new_id`;
UPDATE `uccs` t JOIN `aa10_character_id_map` m ON t.`uploader_id` = m.`old_id` SET t.`uploader_id` = m.`new_id`;

-- Update the primary identity last. Any preceding conflict rolls back together.
UPDATE `characters` t JOIN `aa10_character_id_map` m ON t.`id` = m.`old_id` SET t.`id` = m.`new_id`;

COMMIT;

DROP TEMPORARY TABLE `aa10_character_id_guard`;
DROP TEMPORARY TABLE `aa10_character_id_map`;
