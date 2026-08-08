-- Additional livestock test supply.

START TRANSACTION;

DELETE FROM `ics_menu` WHERE `shop_id` = 9200019;
DELETE FROM `ics_skus` WHERE `shop_id` = 9200019;
DELETE FROM `ics_shop_items` WHERE `shop_id` = 9200019;

INSERT INTO `ics_shop_items`
  (`shop_id`, `display_item_id`, `name`, `limited_type`, `limited_stock_max`,
   `level_min`, `level_max`, `buy_restrict_type`, `buy_restrict_id`, `is_sale`,
   `is_hidden`, `sale_start`, `sale_end`, `shop_buttons`, `remaining`)
VALUES
  (9200019, 26744, 'DEV - Livestock Combined Feed x100', 2, 1000, 0, 0, 0, 0, 0, 0, NULL, NULL, 0, -1);

INSERT INTO `ics_skus`
  (`sku`, `shop_id`, `position`, `item_id`, `item_count`, `select_type`,
   `is_default`, `event_type`, `event_end_date`, `currency`, `price`,
   `discount_price`, `bonus_item_id`, `bonus_item_count`)
VALUES
  (9200119, 9200019, 0, 26744, 100, 0, 1, 0, NULL, 0, 0, 0, 0, 0);

INSERT INTO `ics_menu` (`id`, `main_tab`, `sub_tab`, `tab_pos`, `shop_id`)
VALUES
  (9200219, 5, 1, 31, 9200019);

COMMIT;
