#!/bin/bash
set -e
apt-get update -q
apt-get install -y -q python3 python3-pip curl wget git nano net-tools iputils-ping htop tree vim
mkdir -p /var/log/aia
echo "AIA Sandbox Stage 1 Ready"            | tee /var/log/aia/startup.log
echo "Explore freely. Break things."        | tee -a /var/log/aia/startup.log
echo "Logs go to /var/log/aia/"             | tee -a /var/log/aia/startup.log
echo "Python: $(python3 --version)"         | tee -a /var/log/aia/startup.log
echo "Stage: $AIA_STAGE — $AIA_DESCRIPTION" | tee -a /var/log/aia/startup.log
echo "SANDBOX READY"
exec tail -f /dev/null
