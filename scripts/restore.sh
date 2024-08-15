#!/usr/bin/env bash

mariadb -u${MARIADB_ROOT_USER} -p${MARIADB_ROOT_PASSWORD} < docker-entrypoint-initdb.d/dump.sql
