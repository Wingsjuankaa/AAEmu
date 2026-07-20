FROM mysql:8.4

COPY ./SQL/aaemu_login.sql /aaemu-schema/aaemu_login.sql
COPY ./SQL/aaemu_game.sql /aaemu-schema/aaemu_game.sql
COPY ./SQL/examples/example-ics-default-en.sql /aaemu-schema/example-ics-default-en.sql
COPY ./SQL/updates /aaemu-schema/updates
COPY ./deploy/docker/mysql-init/10-aaemu-schema.sh /docker-entrypoint-initdb.d/10-aaemu-schema.sh
COPY ./deploy/docker/mysql-init/20-aaemu-custom-content.sh /docker-entrypoint-initdb.d/20-aaemu-custom-content.sh
