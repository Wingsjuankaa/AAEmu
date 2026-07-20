-- Development/test catalog for the fixed client-side Custom Marketplace tab.
-- All offers cost 0 Credits and are limited per character.

START TRANSACTION;

DELETE FROM `ics_menu` WHERE `shop_id` BETWEEN 9100001 AND 9100012;
DELETE FROM `ics_skus` WHERE `shop_id` BETWEEN 9100001 AND 9100012;
DELETE FROM `ics_shop_items` WHERE `shop_id` BETWEEN 9100001 AND 9100012;

REPLACE INTO `ics_shop_items`
  (`shop_id`, `display_item_id`, `name`, `limited_type`, `limited_stock_max`,
   `level_min`, `level_max`, `buy_restrict_type`, `buy_restrict_id`, `is_sale`,
   `is_hidden`, `sale_start`, `sale_end`, `shop_buttons`, `remaining`)
VALUES
  (9100001, 23633, 'DEV · Gilda Star x100',             2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100002, 31891, 'DEV · Tax Certificate x100',        2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100003, 31892, 'DEV · Bound Tax Certificate x100',  2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100004, 26548, 'DEV · Eco-Friendly Fuel x100',      2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100005, 14520, 'DEV · Charcoal x100',               2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100006, 32103, 'DEV · Charcoal Stabilizer x100',    2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100007,  4052, 'DEV · Hereafter Stone x100',        2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100008, 31145, 'DEV · Labor Recharger x5',          2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100009, 16225, 'DEV · Dairy Calf',                  2,  100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100010, 21331, 'DEV · Yata Calf',                   2,  100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100011, 19942, 'DEV · Goat Kid',                    2,  100, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1),
  (9100012, 14840, 'DEV · Yata Calf Food x100',         2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1);

REPLACE INTO `ics_skus`
  (`sku`, `shop_id`, `position`, `item_id`, `item_count`, `select_type`,
   `is_default`, `event_type`, `event_end_date`, `currency`, `price`,
   `discount_price`, `bonus_item_id`, `bonus_item_count`)
VALUES
  (9100101, 9100001, 0, 23633, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100102, 9100002, 0, 31891, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100103, 9100003, 0, 31892, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100104, 9100004, 0, 26548, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100105, 9100005, 0, 14520, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100106, 9100006, 0, 32103, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100107, 9100007, 0,  4052, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100108, 9100008, 0, 31145,   5, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100109, 9100009, 0, 16225,   1, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100110, 9100010, 0, 21331,   1, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100111, 9100011, 0, 19942,   1, 0, 1, 0, NULL, 0, 0, 0, 0, 0),
  (9100112, 9100012, 0, 14840, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0);

-- Main tab 5 is the client-defined Custom tab; its label cannot be changed server-side.
REPLACE INTO `ics_menu` (`id`, `main_tab`, `sub_tab`, `tab_pos`, `shop_id`)
VALUES
  (9100201, 5, 1,  1, 9100001),
  (9100202, 5, 1,  2, 9100002),
  (9100203, 5, 1,  3, 9100003),
  (9100204, 5, 1,  4, 9100004),
  (9100205, 5, 1,  5, 9100005),
  (9100206, 5, 1,  6, 9100006),
  (9100207, 5, 1,  7, 9100007),
  (9100208, 5, 1,  8, 9100008),
  (9100209, 5, 1,  9, 9100009),
  (9100210, 5, 1, 10, 9100010),
  (9100211, 5, 1, 11, 9100011),
  (9100212, 5, 1, 12, 9100012);

COMMIT;
