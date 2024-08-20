#!/usr/bin/env bash

mysql -uroot -h 10.88.0.3 -p kidl -e 'select id,email,phone,code,token from kidl.members km where km.email = "child@tracker.net";'
