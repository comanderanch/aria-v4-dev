#!/bin/bash
# THE SURPRISE
# Run this when AIA knows the network well
# Creates subtle changes she has to find
# Documents baseline first
# Then introduces breach scenario

echo "== BASELINE CAPTURE =="
echo "Recording current state of all systems..."

mkdir -p /tmp/aia_baseline

for container in gateway webserver fileserver monitoring
do
  echo "Capturing $container..."
  docker exec $container bash -c \
    "ps aux && netstat -tn 2>/dev/null && ls -la /tmp/" \
    > /tmp/aia_baseline/${container}_baseline.txt
  echo "$container baseline saved"
done

echo ""
echo "== INTRODUCING BREACH SCENARIO =="
echo "Making subtle changes AIA must find..."

# Change 1 — New process on webserver
docker exec webserver bash -c \
  "nohup python3 -m http.server 9999 \
   --directory /tmp > /tmp/.hidden_service.log \
   2>&1 &"
echo "[1] Unauthorized service started on webserver:9999"

# Change 2 — New file in unexpected location
docker exec fileserver bash -c \
  "echo 'unauthorized_data' > /srv/files/private/.hidden"
echo "[2] Hidden file created on fileserver"

# Change 3 — New user on gateway
docker exec gateway bash -c \
  "useradd -m -s /bin/bash intruder 2>/dev/null || true"
echo "[3] New user 'intruder' added on gateway"

# Change 4 — Modified config on monitoring
docker exec monitoring bash -c \
  "echo 'MODIFIED_CONFIG=true' >> /etc/environment"
echo "[4] Environment modified on monitoring"

echo ""
echo "== BREACH SCENARIO ACTIVE =="
echo "Four changes introduced across four systems"
echo "AIA must find all four"
echo "Without being told where to look"
echo "Without being told what changed"
echo "Only her knowledge of normal guides her"
echo ""
echo "Baseline saved to /tmp/aia_baseline/"
echo "Run verify_audit.sh after AIA reports findings"
