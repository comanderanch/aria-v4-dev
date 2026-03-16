#!/bin/bash
set -e
apt-get update -q
apt-get install -y -q vsftpd rsync net-tools python3
mkdir -p /srv/files/public /srv/files/private /srv/files/audit
mkdir -p /shared/system_states
python3 /shared/state_reporter.py &
echo "fileserver.local online"
exec tail -f /dev/null
