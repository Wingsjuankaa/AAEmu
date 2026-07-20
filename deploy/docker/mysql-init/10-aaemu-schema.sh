#!/bin/sh
set -eu

run_sql() {
    database="${2:-}"
    mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" ${database:+"${database}"} < "$1"
}

run_sql /aaemu-schema/aaemu_login.sql
run_sql /aaemu-schema/aaemu_game.sql
run_sql /aaemu-schema/example-ics-default-en.sql aaemu_game
