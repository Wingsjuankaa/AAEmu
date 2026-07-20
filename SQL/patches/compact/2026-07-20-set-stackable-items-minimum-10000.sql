-- Raise every stackable item to a minimum stack size of 10,000.
--
-- Items with max_stack_size = 1 remain non-stackable. Values already above
-- 10,000 (for example currencies using INT_MAX) are intentionally preserved.
-- Apply this patch to both the server and client compact.sqlite3 files so
-- inventory validation and client-side stack operations use the same limit.

BEGIN TRANSACTION;

UPDATE items
SET max_stack_size = 10000
WHERE max_stack_size > 1
  AND max_stack_size < 10000;

COMMIT;
