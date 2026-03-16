#!/bin/bash
# Read AIA's learning logs
# Shows what she tried and discovered

echo "== AIA Learning Logs =="
echo ""

echo "--- SANDBOX LOGS ---"
docker run --rm \
  -v sandbox_logs:/logs \
  ubuntu:22.04 \
  cat /logs/aia_actions.log 2>/dev/null \
  || echo "No sandbox logs yet"

echo ""
echo "--- NETWORK LOGS ---"
docker run --rm \
  -v network_logs:/logs \
  ubuntu:22.04 \
  cat /logs/aia_actions.log 2>/dev/null \
  || echo "No network logs yet"

echo ""
echo "--- WORDPRESS LOGS ---"
docker run --rm \
  -v wordpress_logs:/logs \
  ubuntu:22.04 \
  cat /logs/aia_actions.log 2>/dev/null \
  || echo "No wordpress logs yet"
