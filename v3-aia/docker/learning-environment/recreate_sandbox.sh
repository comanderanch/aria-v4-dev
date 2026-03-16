#!/bin/bash
# Recreate AIA sandbox after destruction
# Run this anytime — logs preserved
# Fresh start in 60 seconds

echo "== Recreating AIA Sandbox =="
echo "Preserving logs..."

docker-compose -f docker-compose.learning.yml \
  stop aia-sandbox

docker-compose -f docker-compose.learning.yml \
  rm -f aia-sandbox

echo "Sandbox destroyed. Recreating..."

docker-compose -f docker-compose.learning.yml \
  up -d aia-sandbox

echo "== AIA Sandbox Ready =="
echo "Logs preserved in sandbox_logs volume"
echo "Connect: docker exec -it aia_sandbox bash"
