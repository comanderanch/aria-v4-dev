## Description
Docker status — containers, images, system info

## Command
docker ps -a 2>/dev/null || echo "Docker not running"
echo "---"
docker images 2>/dev/null | head -10
