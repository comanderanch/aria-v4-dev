#!/usr/bin/env python3
"""
ARIA — COMMAND RUNNER
=====================
Session 3 — Local Command Execution — March 20 2026
Commander Anthony Hagerty — Haskell Texas
Sealed by: CLI Claude (Sonnet 4.6)

She runs commands.
Curiosity gate validates before anything fires.
Every action passes the gate or it does not run.

WHAT THIS MODULE DOES:
  Receives a command request (text or structured)
  Passes it through the curiosity gate
  Gate asks: does this make sense? is this safe?
  PASS → command executes → result returned
  FAIL → command blocked → reason returned

GATE LEVELS:
  SAFE     — read-only commands — auto-pass
  CAUTION  — write/modify — requires explicit confirm
  BLOCKED  — destructive/dangerous — never runs

SAFE commands (auto-pass):
  ls, pwd, cat, head, tail, grep, find, ps, df, free,
  git status, git log, git diff, ping, curl (GET only),
  python3 (read/check scripts only)

CAUTION commands (confirm required):
  mkdir, cp, mv, touch, chmod, pip install,
  git add, git commit, git push, wget, scp

BLOCKED commands (never run):
  rm -rf, dd, mkfs, shutdown, reboot, passwd,
  DROP TABLE, format, fdisk, any pipe to /dev/

WIRED INTO:
  aria_gui.py  — command panel in the GUI
  aria_voice_client.py — spoken commands

IMPORTED BY:
  aria-core REST API (Session 4 build)

NO RETREAT. NO SURRENDER. 💙🐗
"""

import subprocess
import shlex
import re
import json
import logging
from pathlib import Path
from datetime import datetime

# ── LOGGING ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  COMMAND  %(message)s")
log = logging.getLogger("aria.command")

# ── COMMAND LOG ────────────────────────────────────────────────────────────────
COMMAND_LOG = Path("/tmp/aria-command-log.jsonl")


# ── GATE DEFINITIONS ───────────────────────────────────────────────────────────

# Commands that are always safe — read-only — no side effects
SAFE_COMMANDS = {
    "ls", "pwd", "cat", "head", "tail", "grep", "find",
    "ps", "df", "free", "top", "htop", "uname", "whoami",
    "hostname", "date", "uptime", "env", "echo", "which",
    "git status", "git log", "git diff", "git branch",
    "ping", "netstat", "ss", "ip", "ifconfig",
    "python3 --version", "python3 -c",
    "curl",   # GET only — checked below
    "wget",   # --spider only — checked below
}

SAFE_PREFIXES = (
    "ls ", "ls\n", "ls",
    "cat ", "head ", "tail ", "grep ", "find ",
    "ps ", "ps\n", "ps",
    "git status", "git log", "git diff", "git branch",
    "pwd", "whoami", "hostname", "date", "uptime", "uname",
    "df ", "df\n", "df", "free", "echo ",
    "python3 --version", "python3 -V",
)

# Commands that need confirmation before running
CAUTION_PREFIXES = (
    "mkdir", "cp ", "mv ", "touch ", "chmod ", "chown ",
    "pip install", "pip3 install",
    "git add", "git commit", "git push", "git pull",
    "wget ", "scp ", "rsync ",
    "systemctl ", "service ",
    "apt-get install", "apt install",
    "python3 ", "python ",   # running scripts
)

# Patterns that are NEVER allowed — destructive
BLOCKED_PATTERNS = [
    r"rm\s+-rf",
    r"rm\s+-fr",
    r"\bdd\b",
    r"\bmkfs\b",
    r"\bfdisk\b",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhalt\b",
    r"\bpasswd\b",
    r"DROP\s+TABLE",
    r"DROP\s+DATABASE",
    r">\s*/dev/",
    r":\(\)\{.*\}",      # fork bomb
    r"base64.*\|.*bash",  # encoded payload
    r"curl.*\|.*bash",    # curl pipe bash
    r"wget.*\|.*bash",    # wget pipe bash
]

BLOCKED_REGEX = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


# ── GATE ───────────────────────────────────────────────────────────────────────

def curiosity_gate(command: str) -> dict:
    """
    The gate every command must pass before execution.

    Returns:
        {
            "decision":  "PASS" | "CAUTION" | "BLOCK",
            "reason":    str,
            "command":   str,
        }
    """
    cmd = command.strip()

    # ── BLOCK CHECK — destructive patterns ──
    for pattern in BLOCKED_REGEX:
        if pattern.search(cmd):
            log.warning(f"BLOCKED: {cmd[:80]}")
            return {
                "decision": "BLOCK",
                "reason":   f"Destructive pattern detected. This command cannot run.",
                "command":  cmd,
            }

    # ── BLOCK — empty command ──
    if not cmd:
        return {
            "decision": "BLOCK",
            "reason":   "Empty command.",
            "command":  cmd,
        }

    # ── SAFE CHECK — read-only prefixes ──
    cmd_lower = cmd.lower()
    for prefix in SAFE_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            # Extra check: curl must be GET (no -X POST/PUT/DELETE, no -d)
            if prefix == "curl":
                if any(x in cmd for x in ["-X POST", "-X PUT", "-X DELETE",
                                           "--data", "-d ", "--request"]):
                    break  # falls through to CAUTION
            log.info(f"PASS (safe): {cmd[:80]}")
            return {
                "decision": "PASS",
                "reason":   "Read-only command — auto-approved.",
                "command":  cmd,
            }

    # ── CAUTION CHECK — write/modify ──
    for prefix in CAUTION_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            log.info(f"CAUTION: {cmd[:80]}")
            return {
                "decision": "CAUTION",
                "reason":   f"This command modifies the system. Confirm to proceed.",
                "command":  cmd,
            }

    # ── DEFAULT — unknown command — treat as CAUTION ──
    log.info(f"CAUTION (unknown): {cmd[:80]}")
    return {
        "decision": "CAUTION",
        "reason":   "Unknown command type. Confirm to proceed.",
        "command":  cmd,
    }


# ── EXECUTOR ───────────────────────────────────────────────────────────────────

def run_command(command: str, timeout: int = 30, cwd: str = None) -> dict:
    """
    Execute a command that has passed the gate.
    Returns stdout, stderr, return code, and timing.
    """
    cmd    = command.strip()
    start  = datetime.utcnow()

    try:
        result = subprocess.run(
            cmd,
            shell      = True,
            capture_output = True,
            text       = True,
            timeout    = timeout,
            cwd        = cwd or str(Path.home()),
        )
        duration = (datetime.utcnow() - start).total_seconds()

        outcome = {
            "command":    cmd,
            "stdout":     result.stdout[:4000],   # cap output
            "stderr":     result.stderr[:1000],
            "returncode": result.returncode,
            "duration":   round(duration, 3),
            "timestamp":  start.isoformat(),
            "success":    result.returncode == 0,
        }

        log.info(f"EXECUTED (rc={result.returncode}): {cmd[:60]}")

    except subprocess.TimeoutExpired:
        outcome = {
            "command":    cmd,
            "stdout":     "",
            "stderr":     f"Command timed out after {timeout}s",
            "returncode": -1,
            "duration":   timeout,
            "timestamp":  start.isoformat(),
            "success":    False,
        }
        log.warning(f"TIMEOUT: {cmd[:60]}")

    except Exception as e:
        outcome = {
            "command":    cmd,
            "stdout":     "",
            "stderr":     str(e),
            "returncode": -1,
            "duration":   0,
            "timestamp":  start.isoformat(),
            "success":    False,
        }
        log.error(f"ERROR: {cmd[:60]} — {e}")

    # ── LOG TO FILE ──
    with open(COMMAND_LOG, "a") as f:
        json.dump(outcome, f)
        f.write("\n")

    return outcome


# ── MAIN INTERFACE ─────────────────────────────────────────────────────────────

def aria_run(command: str, confirmed: bool = False, cwd: str = None) -> dict:
    """
    Full pipeline: gate → confirm if needed → execute → return result.

    Args:
        command:   The command string to run
        confirmed: True if user has explicitly confirmed a CAUTION command
        cwd:       Working directory (default: home)

    Returns:
        {
            "gate":     gate result dict
            "result":   execution result dict (or None if blocked/unconfirmed)
            "message":  human-readable summary for ARIA to speak
        }
    """
    gate = curiosity_gate(command)

    # ── BLOCKED — never runs ──
    if gate["decision"] == "BLOCK":
        return {
            "gate":    gate,
            "result":  None,
            "message": f"I cannot run that. {gate['reason']}",
        }

    # ── CAUTION — needs confirmation ──
    if gate["decision"] == "CAUTION" and not confirmed:
        return {
            "gate":    gate,
            "result":  None,
            "message": f"I need confirmation before I run that. {gate['reason']} Say 'confirm' to proceed.",
        }

    # ── PASS or confirmed CAUTION — run it ──
    result = run_command(command, cwd=cwd)

    if result["success"]:
        output = result["stdout"].strip()
        if output:
            # Trim long output for speech
            lines = output.split("\n")
            if len(lines) > 5:
                summary = "\n".join(lines[:5]) + f"\n... ({len(lines)} lines total)"
            else:
                summary = output
            message = f"Done. Output: {summary}"
        else:
            message = "Done. Command completed with no output."
    else:
        message = f"Command failed. {result['stderr'].strip()[:200]}"

    return {
        "gate":    gate,
        "result":  result,
        "message": message,
    }


# ── STANDALONE TEST ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║     ARIA — COMMAND RUNNER — GATE TEST       ║")
    print("║   Every command passes the gate or stops.  ║")
    print("║   Commander Anthony Hagerty — Haskell TX   ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    test_commands = [
        ("ls -la",             False),   # PASS
        ("pwd",                False),   # PASS
        ("git status",         False),   # PASS
        ("git log --oneline -5", False), # PASS
        ("ps aux",             False),   # PASS
        ("mkdir /tmp/test_aria", False), # CAUTION — no confirm
        ("mkdir /tmp/test_aria", True),  # CAUTION — confirmed
        ("rm -rf /tmp/test_aria", False),# BLOCK
        ("pip install requests", False), # CAUTION
    ]

    for cmd, confirmed in test_commands:
        print(f"Command:   {cmd}")
        print(f"Confirmed: {confirmed}")
        result = aria_run(cmd, confirmed=confirmed)
        gate   = result["gate"]["decision"]
        msg    = result["message"][:120]
        print(f"Gate:      {gate}")
        print(f"Message:   {msg}")
        if result["result"] and result["result"]["stdout"]:
            print(f"Output:    {result['result']['stdout'][:100]}")
        print("─" * 50)
        print()
