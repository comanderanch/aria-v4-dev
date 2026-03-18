#!/usr/bin/env python3
import sys, json, subprocess, hashlib
from pathlib import Path

BRIDGE_DIR = Path(__file__).parent
INDEX = BRIDGE_DIR / "index.json"

if not INDEX.exists():
    print("index.json not found")
    sys.exit(1)

arg = sys.argv[1] if len(sys.argv) > 1 else ""
index = json.loads(INDEX.read_text())

entry = next((e for e in index if e["pattern"] == arg or e["hash"] == arg), None)

if not entry:
    print(f"Unknown: {arg}")
    sys.exit(1)

cmd_file = BRIDGE_DIR / entry["file"]
content = cmd_file.read_text()
lines = content.split("\n")
in_cmd = False
cmds = []
for line in lines:
    if line.startswith("## Command"):
        in_cmd = True
        continue
    if in_cmd and line.strip():
        cmds.append(line)

print(f"[BRIDGE] {entry['pattern']} — {entry['description']}")
subprocess.run("\n".join(cmds), shell=True)
