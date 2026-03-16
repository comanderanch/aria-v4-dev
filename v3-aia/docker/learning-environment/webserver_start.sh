#!/bin/bash
set -e
apt-get update -q
apt-get install -y -q apache2 curl wget net-tools python3
echo '<h1>webserver.local</h1>' > /var/www/html/index.html
apache2ctl start
mkdir -p /shared/system_states
python3 /shared/state_reporter.py &
echo "webserver.local online"
exec tail -f /dev/null
