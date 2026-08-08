-- Additional development/test supplies: livestock recovery and Auroria materials.

START TRANSACTION;

DELETE FROM `ics_menu` WHERE `shop_id` BETWEEN 9200001 AND 9200016;
DELETE FROM `ics_skus` WHERE `shop_id` BETWEEN 9200001 AND 9200016;
DELETE FROM `ics_shop_items` WHERE `shop_id` BETWEEN 9200001 AND 9200016;

REPLACE INTO `ics_shop_items`
  (`shop_id`, `display_item_id`, `name`, `limited_type`, `limited_stock_max`,
   `level_min`, `level_max`, `buy_restrict_type`, `buy_restrict_id`, `is_sale`,
   `is_hidden`, `sale_start`, `sale_end`, `shop_buttons`, `remaining`)
VALUES
  (9200001, 16220, 'DEV · Livestock Supplement x100',      2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200002, 18749, 'DEV · Flaming Log x100',               2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200003, 8000055, 'DEV · Thunderstruck Log x100',       2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200004, 17804, 'DEV · Auroria Stone x100',             2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200005, 16347, 'DEV · Sunlight Archeum Dust x100',     2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200006, 16350, 'DEV · Sunlight Archeum Shard x100',    2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200007, 16353, 'DEV · Sunlight Archeum Crystal x100',  2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200008, 16356, 'DEV · Sunlight Archeum Essence x100',  2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200009, 16348, 'DEV · Moonlight Archeum Dust x100',    2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200010, 16351, 'DEV · Moonlight Archeum Shard x100',   2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200011, 16354, 'DEV · Moonlight Archeum Crystal x100', 2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200012, 16357, 'DEV · Moonlight Archeum Essence x100', 2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200013, 16349, 'DEV · Starlight Archeum Dust x100',    2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200014, 16352, 'DEV · Starlight Archeum Shard x100',   2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200015, 16355, 'DEV · Starlight Archeum Crystal x100', 2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9200016, 16358, 'DEV · Starlight Archeum Essence x100', 2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1);

REPLACE INTO `ics_skus`
  (`sku`, `shop_id`, `position`, `item_id`, `item_count`, `select_type`,
   `is_default`, `event_type`, `event_end_date`, `currency`, `price`,
   `discount_price`, `bonus_item_id`, `bonus_item_count`)
VALUES
  (9200101, 9200001, 0, 16220, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200102, 9200002, 0, 18749, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200103, 9200003, 0, 8000055, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200104, 9200004, 0, 17804, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200105, 9200005, 0, 16347, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200106, 9200006, 0, 16350, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200107, 9200007, 0, 16353, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200108, 9200008, 0, 16356, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200109, 9200009, 0, 16348, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200110, 9200010, 0, 16351, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200111, 9200011, 0, 16354, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200112, 9200012, 0, 16357, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200113, 9200013, 0, 16349, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200114, 9200014, 0, 16352, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200115, 9200015, 0, 16355, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9200116, 9200016, 0, 16358, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0);

REPLACE INTO `ics_menu` (`id`, `main_tab`, `sub_tab`, `tab_pos`, `shop_id`)
VALUES
  (9200201, 5, 1, 13, 9200001),
  (9200202, 5, 1, 14, 9200002),
  (9200203, 5, 1, 15, 9200003),
  (9200204, 5, 1, 16, 9200004),
  (9200205, 5, 1, 17, 9200005),
  (9200206, 5, 1, 18, 9200006),
  (9200207, 5, 1, 19, 9200007),
  (9200208, 5, 1, 20, 9200008),
  (9200209, 5, 1, 21, 9200009),
  (9200210, 5, 1, 22, 9200010),
  (9200211, 5, 1, 23, 9200011),
  (9200212, 5, 1, 24, 9200012),
  (9200213, 5, 1, 25, 9200013),
  (9200214, 5, 1, 26, 9200014),
  (9200215, 5, 1, 27, 9200015),
  (9200216, 5, 1, 28, 9200016);

COMMIT;
