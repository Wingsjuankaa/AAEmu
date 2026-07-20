-- Expose the existing Farm Hauler upgrade as the upper craft of Farm Wagon.
--
-- Profession: Machining (the vehicle crafting skill uses actability_group_id 10).
-- Workstation: the client data calls craft packs 21/31 Carpentry Workbench,
-- but that workstation name does not change the craft's Machining profession.
--
-- Farm Wagon craft 4107 produces item 18660. Farm Hauler craft 6029 consumes
-- item 18660 plus Farm Vehicle Upgrade Ticket 30812. Both recipes already
-- belong to craft packs 21 and 31 and use milestone 5 in client r208022.

BEGIN TRANSACTION;

UPDATE crafts
SET ac_id = 24,
    show_upper_crafts = 't'
WHERE id = 4107;

-- ac_id references actability_categories, not actability_groups. Category 24
-- is the visible Vehicles category under the Machining group (group_id 10).
UPDATE crafts
SET ac_id = 24
WHERE id = 6029;

UPDATE craft_products
SET show_lower_crafts = 't'
WHERE craft_id = 4107
  AND item_id = 18660;

COMMIT;
