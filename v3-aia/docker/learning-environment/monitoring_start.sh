#!/bin/bash
set -e
apt-get update -q
apt-get install -y -q python3 python3-pip net-tools curl nmap tcpdump
pip3 install -q flask
mkdir -p /shared/system_states
python3 /shared/state_reporter.py &
echo "monitoring.local online"
exec tail -f /dev/null
