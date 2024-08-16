#!/usr/bin/env bash

echo  "Restore dump"
mariadb -u${MARIADB_ROOT_USER} -p${MARIADB_ROOT_PASSWORD} kidl < docker-entrypoint-initdb.d/dump.sql
#echo  "Apply migration"
#[ -f docker-entrypoint-initdb.d/migration.sql ] && mariadb -u${MARIADB_ROOT_USER} -p${MARIADB_ROOT_PASSWORD} < docker-entrypoint-initdb.d/migration.sql
