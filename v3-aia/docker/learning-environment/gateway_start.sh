#!/bin/bash
set -e
apt-get update -q
apt-get install -y -q net-tools iputils-ping curl wget iptables python3
mkdir -p /shared/system_states
python3 /shared/state_reporter.py &
echo "gateway.local online"
exec tail -f /dev/null
