#!/bin/bash
set -e

mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" -e \
    "CREATE DATABASE IF NOT EXISTS aaemu_login CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE DATABASE IF NOT EXISTS aaemu_game CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" aaemu_login < /aaemu-schema/aaemu_login.sql
mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" aaemu_game < /aaemu-schema/aaemu_game.sql
mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" < /aaemu-schema/examples/example-server.sql
mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" < /aaemu-schema/examples/test-user.sql
