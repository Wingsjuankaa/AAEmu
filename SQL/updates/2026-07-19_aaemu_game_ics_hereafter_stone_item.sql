-- Correct the Hereafter Stone marketplace entries for client 1.2.
-- Item 11123 displays a potion; 4052 is the actual Hereafter Stone.

START TRANSACTION;

UPDATE `ics_shop_items`
SET `display_item_id` = 4052
WHERE `shop_id` IN (9000004, 9000005, 9000006);

UPDATE `ics_skus`
SET `item_id` = 4052
WHERE `sku` IN (9000104, 9000105, 9000106);

COMMIT;
