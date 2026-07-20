#!/bin/sh
set -eu

run_sql() {
    mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" aaemu_game < "$1"
}

run_sql /aaemu-schema/updates/2026-07-19_aaemu_game_ics_free_utilities.sql
run_sql /aaemu-schema/updates/2026-07-19_aaemu_game_ics_hereafter_stone_item.sql
run_sql /aaemu-schema/updates/2026-07-19_aaemu_game_ics_dev_catalog.sql
run_sql /aaemu-schema/updates/2026-07-19_aaemu_game_ics_dev_catalog_auroria.sql
run_sql /aaemu-schema/updates/2026-07-19_aaemu_game_ics_dev_thunderstruck_saplings.sql
run_sql /aaemu-schema/updates/2026-07-20_aaemu_game_ics_dev_thunderstruck_tree.sql
run_sql /aaemu-schema/updates/2026-07-20_aaemu_game_ics_dev_archeum_log.sql
run_sql /aaemu-schema/updates/2026-07-20_aaemu_game_ics_dev_livestock_combined_feed.sql
