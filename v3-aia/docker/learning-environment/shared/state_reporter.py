"""
state_reporter.py
Runs inside each named container
Reports own state to shared volume
every 10 seconds
"""

import json
import time
import subprocess
import os
from pathlib import Path

CONTAINER_NAME = os.environ.get('SYSTEM_NAME', 'unknown')
STATE_DIR = Path("/shared/system_states")
STATE_DIR.mkdir(parents=True, exist_ok=True)

def get_state():
    def cmd(c):
        try:
            r = subprocess.run(
                c, shell=True,
                capture_output=True,
                text=True, timeout=3)
            return r.stdout.strip() or "—"
        except:
            return "—"

    return {
        "container":  CONTAINER_NAME,
        "processes":  cmd("ps aux --no-header | wc -l"),
        "uptime":     cmd("uptime -p"),
        "disk":       cmd("df -h / | tail -1 | awk '{print $5}'"),
        "users":      cmd("who | wc -l"),
        "network":    cmd(
            "netstat -tn 2>/dev/null | "
            "grep ESTABLISHED | wc -l || echo 0"),
        "timestamp":  time.time()
    }

while True:
    state = get_state()
    path = STATE_DIR / f"{CONTAINER_NAME}.json"
    with open(path, 'w') as f:
        json.dump(state, f)
    time.sleep(10)
