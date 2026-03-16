#!/bin/bash
set -e
apt-get update -q
apt-get install -y -q python3 python3-pip curl wget nmap net-tools iputils-ping tcpdump netcat-openbsd traceroute dnsutils
mkdir -p /var/log/aia
echo "AIA Network Explorer Stage 2 Ready"   | tee /var/log/aia/startup.log
echo "The network is yours to feel."        | tee -a /var/log/aia/startup.log
echo "Python: $(python3 --version)"         | tee -a /var/log/aia/startup.log
echo "Stage: $AIA_STAGE — $AIA_DESCRIPTION" | tee -a /var/log/aia/startup.log
echo "NETWORK EXPLORER READY"
exec tail -f /dev/null
