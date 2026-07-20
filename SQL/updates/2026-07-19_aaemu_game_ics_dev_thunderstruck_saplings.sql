-- The Thunderstruck Tree is a rare doodad state, not an inventory item.
-- These plantings are the test inputs that can produce it.

START TRANSACTION;

DELETE FROM `ics_menu` WHERE `shop_id` BETWEEN 9200017 AND 9200024;
DELETE FROM `ics_skus` WHERE `shop_id` BETWEEN 9200017 AND 9200024;
DELETE FROM `ics_shop_items` WHERE `shop_id` BETWEEN 9200017 AND 9200024;

REPLACE INTO `ics_shop_items`
  (`shop_id`, `display_item_id`, `name`, `limited_type`, `limited_stock_max`,
   `level_min`, `level_max`, `buy_restrict_type`, `buy_restrict_id`, `is_sale`,
   `is_hidden`, `sale_start`, `sale_end`, `shop_buttons`, `remaining`)
VALUES
  (9200017, 13728, 'DEV - Rubber Tree Sapling x100',  2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200018, 14905, 'DEV - Beech Tree Sapling x100',   2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200019, 14896, 'DEV - Ebony Tree Sapling x100',   2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200020, 14906, 'DEV - Cherry Tree Sapling x100',  2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200021, 14902, 'DEV - Cedar Tree Sapling x100',   2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200022, 14898, 'DEV - Pine Tree Sapling x100',    2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200023, 16332, 'DEV - Ginkgo Tree Sapling x100',  2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200024, 4866,  'DEV - Poplar Tree Sapling x100',  2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1);

REPLACE INTO `ics_skus`
  (`sku`, `shop_id`, `position`, `item_id`, `item_count`, `select_type`,
   `is_default`, `event_type`, `event_end_date`, `currency`, `price`,
   `discount_price`, `bonus_item_id`, `bonus_item_count`)
VALUES
  (9200117, 9200017, 0, 13728, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200118, 9200018, 0, 14905, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200119, 9200019, 0, 14896, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200120, 9200020, 0, 14906, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200121, 9200021, 0, 14902, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200122, 9200022, 0, 14898, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200123, 9200023, 0, 16332, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200124, 9200024, 0, 4866,  100, 0, 1, 0, NULL, 0, 0, 0, 0, 0);

REPLACE INTO `ics_menu` (`id`, `main_tab`, `sub_tab`, `tab_pos`, `shop_id`)
VALUES
  (9200217, 5, 1, 29, 9200017),
  (9200218, 5, 1, 30, 9200018),
  (9200219, 5, 1, 31, 9200019),
  (9200220, 5, 1, 32, 9200020),
  (9200221, 5, 1, 33, 9200021),
  (9200222, 5, 1, 34, 9200022),
  (9200223, 5, 1, 35, 9200023),
  (9200224, 5, 1, 36, 9200024);

COMMIT;
