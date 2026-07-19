-- Free utility items for local AAEmu testing (client 1.2 r208022).
-- Price 0 uses the Credits currency but does not deduct any credits.
-- The cart is enabled. The 1.2 client does not reliably select SKU variants,
-- so each quantity is a separate catalog entry.
-- Each listing is limited per character to keep the test catalog controlled.

START TRANSACTION;

DELETE FROM `ics_menu` WHERE `shop_id` BETWEEN 9000001 AND 9000015;
DELETE FROM `ics_skus` WHERE `shop_id` BETWEEN 9000001 AND 9000015;
DELETE FROM `ics_shop_items` WHERE `shop_id` BETWEEN 9000001 AND 9000015;

REPLACE INTO `ics_shop_items`
  (`shop_id`, `display_item_id`, `name`, `limited_type`, `limited_stock_max`,
   `level_min`, `level_max`, `buy_restrict_type`, `buy_restrict_id`, `is_sale`,
   `is_hidden`, `sale_start`, `sale_end`, `shop_buttons`, `remaining`)
VALUES
  (9000001, 8000025, 'Expansion Scroll x1 (Free)',    2, 20, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000002, 8000025, 'Expansion Scroll x5 (Free)',    2, 20, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000003, 8000025, 'Expansion Scroll x10 (Free)',   2, 20, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000004,   11123, 'Hereafter Stone x10 (Free)',    2, 200, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000005,   11123, 'Hereafter Stone x50 (Free)',    2, 200, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000006,   11123, 'Hereafter Stone x100 (Free)',   2, 200, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000007,   31145, 'Labor Recharger x1 (Free)',     2, 10, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000008,   31145, 'Labor Recharger x3 (Free)',     2, 10, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000009,   31145, 'Labor Recharger x5 (Free)',     2, 10, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000010,   19043, 'Nui''s Nova x10 (Free)',        2, 100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000011,   19043, 'Nui''s Nova x50 (Free)',        2, 100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000012,   19043, 'Nui''s Nova x100 (Free)',       2, 100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000013,   31775, 'Mossy Pool x10 (Free)',         2, 100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000014,   31775, 'Mossy Pool x50 (Free)',         2, 100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9000015,   31775, 'Mossy Pool x100 (Free)',        2, 100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1);

REPLACE INTO `ics_skus`
  (`sku`, `shop_id`, `position`, `item_id`, `item_count`, `select_type`,
   `is_default`, `event_type`, `event_end_date`, `currency`, `price`,
   `discount_price`, `bonus_item_id`, `bonus_item_count`)
VALUES
  (9000101, 9000001, 0, 8000025,   1, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000102, 9000002, 0, 8000025,   5, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000103, 9000003, 0, 8000025,  10, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000104, 9000004, 0,   11123,  10, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000105, 9000005, 0,   11123,  50, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000106, 9000006, 0,   11123, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000107, 9000007, 0,   31145,   1, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000108, 9000008, 0,   31145,   3, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000109, 9000009, 0,   31145,   5, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000110, 9000010, 0,   19043,  10, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000111, 9000011, 0,   19043,  50, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000112, 9000012, 0,   19043, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000113, 9000013, 0,   31775,  10, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000114, 9000014, 0,   31775,  50, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9000115, 9000015, 0,   31775, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0);

REPLACE INTO `ics_menu` (`id`, `main_tab`, `sub_tab`, `tab_pos`, `shop_id`)
VALUES
  (9000201, 2, 1,  1, 9000001),
  (9000202, 2, 1,  2, 9000002),
  (9000203, 2, 1,  3, 9000003),
  (9000204, 2, 1,  4, 9000004),
  (9000205, 2, 1,  5, 9000005),
  (9000206, 2, 1,  6, 9000006),
  (9000207, 2, 1,  7, 9000007),
  (9000208, 2, 1,  8, 9000008),
  (9000209, 2, 1,  9, 9000009),
  (9000210, 2, 1, 10, 9000010),
  (9000211, 2, 1, 11, 9000011),
  (9000212, 2, 1, 12, 9000012),
  (9000213, 2, 1, 13, 9000013),
  (9000214, 2, 1, 14, 9000014),
  (9000215, 2, 1, 15, 9000015);

COMMIT;
