#!/usr/bin/env bash

mysqldump -u root -p -h 10.88.0.3 kidl > dump.sql
mysqldump -d -u root -p -h 10.88.0.3 kidl > schema.sql
