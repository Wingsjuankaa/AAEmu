-- Replace the individual saplings with the actual Thunderstruck Tree test item.

START TRANSACTION;

DELETE FROM `ics_menu` WHERE `shop_id` BETWEEN 9200017 AND 9200024;
DELETE FROM `ics_skus` WHERE `shop_id` BETWEEN 9200017 AND 9200024;
DELETE FROM `ics_shop_items` WHERE `shop_id` BETWEEN 9200017 AND 9200024;

INSERT INTO `ics_shop_items`
  (`shop_id`, `display_item_id`, `name`, `limited_type`, `limited_stock_max`,
   `level_min`, `level_max`, `buy_restrict_type`, `buy_restrict_id`, `is_sale`,
   `is_hidden`, `sale_start`, `sale_end`, `shop_buttons`, `remaining`)
VALUES
  (9200017, 15709, 'DEV - Thunderstruck Tree', 2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1);

INSERT INTO `ics_skus`
  (`sku`, `shop_id`, `position`, `item_id`, `item_count`, `select_type`,
   `is_default`, `event_type`, `event_end_date`, `currency`, `price`,
   `discount_price`, `bonus_item_id`, `bonus_item_count`)
VALUES
  (9200117, 9200017, 0, 15709, 1, 0, 1, 0, NULL, 0, 0, 0, 0, 0);

INSERT INTO `ics_menu` (`id`, `main_tab`, `sub_tab`, `tab_pos`, `shop_id`)
VALUES
  (9200217, 5, 1, 29, 9200017);

COMMIT;
