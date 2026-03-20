#!/usr/bin/env python3
"""
ARIA — NETWORK RUNNER
=====================
Session 4 — SSH Network Reach — March 20 2026
Commander Anthony Hagerty — Haskell Texas
Sealed by: CLI Claude (Sonnet 4.6)

She reaches the network.
Entry 076 becomes real hardware.

WHAT THIS MODULE DOES:
  Takes a command request + target host
  Passes it through the curiosity gate (same gate as aria_command_runner.py)
  Gate asks: does this make sense? is this safe?
  PASS → SSH to target → command runs on remote host → result returned
  FAIL → command blocked → reason returned

ARCHITECTURE:
  aria_command_runner.py — local commands
  aria_network_runner.py — remote commands via SSH (this file)
  Both share the same curiosity gate logic.
  Same decision. Same safety. Different execution path.

KNOWN HOSTS FILE:
  ARIA maintains a registry of trusted network nodes.
  A host not in the registry is BLOCKED — she does not cold-call unknowns.
  Commander adds hosts to the registry. ARIA only reaches what she knows.

NETWORK REGISTRY FORMAT:
  /home/comanderanch/aria-v4-dev/aria-core/network_registry.json
  {
    "ai-core":    {"host": "192.168.1.142", "port": 22, "user": "comanderanch", "label": "Main server"},
    "laptop":     {"host": "192.168.1.169", "port": 22, "user": "comanderanch", "label": "Laptop thin client"},
  }

AUTH:
  SSH key auth only — no passwords in code.
  Commander's key pair already installed on all nodes.
  key_path: ~/.ssh/id_rsa (default) or override per node in registry.

WIRED INTO:
  aria_gui.py    — network panel (Session 5+)
  aria_command_runner.py — gate shared

IMPORTED BY:
  aria-core REST API (Session 4 build)

NO RETREAT. NO SURRENDER. 💙🐗
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

# ── PARAMIKO ────────────────────────────────────────────────────────────────────
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

# ── LOCAL GATE — import from command runner ──────────────────────────────────────
from aria_command_runner import curiosity_gate

# ── LOGGING ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  NETWORK  %(message)s")
log = logging.getLogger("aria.network")

# ── PATHS ───────────────────────────────────────────────────────────────────────
REGISTRY_PATH  = Path(__file__).parent / "network_registry.json"
NETWORK_LOG    = Path("/tmp/aria-network-log.jsonl")
DEFAULT_KEY    = Path.home() / ".ssh" / "id_rsa"


# ── NETWORK REGISTRY ────────────────────────────────────────────────────────────

def load_registry() -> dict:
    """Load the network node registry. Returns empty dict if not found."""
    if not REGISTRY_PATH.exists():
        return {}
    try:
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to load registry: {e}")
        return {}


def save_registry(registry: dict) -> bool:
    """Save the registry back to disk."""
    try:
        with open(REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2)
        return True
    except Exception as e:
        log.error(f"Failed to save registry: {e}")
        return False


def list_nodes() -> list:
    """Return list of registered node names."""
    return list(load_registry().keys())


def get_node(name: str) -> dict | None:
    """Get a node entry by name. Returns None if not found."""
    return load_registry().get(name)


def register_node(name: str, host: str, user: str,
                  port: int = 22, label: str = "", key_path: str = "") -> dict:
    """
    Add or update a node in the registry.

    Returns:
        {"success": bool, "message": str}
    """
    registry = load_registry()
    registry[name] = {
        "host":     host,
        "port":     port,
        "user":     user,
        "label":    label or name,
        "key_path": key_path or str(DEFAULT_KEY),
        "added":    datetime.utcnow().isoformat(),
    }
    if save_registry(registry):
        log.info(f"Node registered: {name} → {user}@{host}:{port}")
        return {"success": True,  "message": f"Node '{name}' registered at {user}@{host}:{port}"}
    else:
        return {"success": False, "message": "Failed to write registry."}


def remove_node(name: str) -> dict:
    """Remove a node from the registry."""
    registry = load_registry()
    if name not in registry:
        return {"success": False, "message": f"Node '{name}' not found."}
    del registry[name]
    if save_registry(registry):
        log.info(f"Node removed: {name}")
        return {"success": True,  "message": f"Node '{name}' removed."}
    else:
        return {"success": False, "message": "Failed to write registry."}


# ── SSH EXECUTOR ────────────────────────────────────────────────────────────────

def ssh_run(node_entry: dict, command: str, timeout: int = 30) -> dict:
    """
    Open SSH connection to node and run the command.
    Returns result dict matching aria_command_runner format.
    """
    host     = node_entry["host"]
    port     = node_entry.get("port", 22)
    user     = node_entry["user"]
    key_path = node_entry.get("key_path", str(DEFAULT_KEY))

    start = datetime.utcnow()

    if not PARAMIKO_AVAILABLE:
        return {
            "command":    command,
            "stdout":     "",
            "stderr":     "paramiko not installed — run: pip install paramiko",
            "returncode": -1,
            "duration":   0,
            "timestamp":  start.isoformat(),
            "success":    False,
            "host":       host,
        }

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname    = host,
            port        = port,
            username    = user,
            key_filename= key_path,
            timeout     = 10,
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")[:4000]
        err = stderr.read().decode("utf-8", errors="replace")[:1000]
        rc  = stdout.channel.recv_exit_status()

        duration = (datetime.utcnow() - start).total_seconds()

        outcome = {
            "command":    command,
            "stdout":     out,
            "stderr":     err,
            "returncode": rc,
            "duration":   round(duration, 3),
            "timestamp":  start.isoformat(),
            "success":    rc == 0,
            "host":       host,
        }
        log.info(f"SSH EXECUTED (rc={rc}) on {host}: {command[:60]}")

    except paramiko.AuthenticationException:
        outcome = _error_outcome(command, host, start,
                                 "SSH authentication failed. Check key pair.")
        log.error(f"AUTH FAIL on {host}: {command[:40]}")

    except paramiko.SSHException as e:
        outcome = _error_outcome(command, host, start, f"SSH error: {e}")
        log.error(f"SSH ERROR on {host}: {e}")

    except TimeoutError:
        outcome = _error_outcome(command, host, start,
                                 f"Connection to {host} timed out.")
        log.warning(f"TIMEOUT connecting to {host}")

    except Exception as e:
        outcome = _error_outcome(command, host, start, str(e))
        log.error(f"ERROR on {host}: {e}")

    finally:
        client.close()

    # ── LOG TO FILE ──
    with open(NETWORK_LOG, "a") as f:
        json.dump(outcome, f)
        f.write("\n")

    return outcome


def _error_outcome(command: str, host: str, start: datetime, error: str) -> dict:
    return {
        "command":    command,
        "stdout":     "",
        "stderr":     error,
        "returncode": -1,
        "duration":   round((datetime.utcnow() - start).total_seconds(), 3),
        "timestamp":  start.isoformat(),
        "success":    False,
        "host":       host,
    }


# ── MAIN INTERFACE ─────────────────────────────────────────────────────────────

def aria_network_run(node_name: str, command: str,
                     confirmed: bool = False) -> dict:
    """
    Full pipeline: lookup node → gate → confirm if needed → SSH execute.

    Args:
        node_name:  Name in network_registry.json (e.g. "ai-core", "laptop")
        command:    Shell command to run on the remote host
        confirmed:  True if user confirmed a CAUTION command

    Returns:
        {
            "gate":     gate result dict
            "result":   execution result dict (or None if blocked/unconfirmed)
            "message":  human-readable summary for ARIA to speak
            "node":     node entry dict (or None if not found)
        }
    """
    # ── NODE LOOKUP ──
    node = get_node(node_name)
    if node is None:
        known = list_nodes()
        known_str = ", ".join(known) if known else "none registered"
        return {
            "gate":    {"decision": "BLOCK", "reason": "Unknown node.", "command": command},
            "result":  None,
            "message": f"I don't know that node. Known nodes: {known_str}",
            "node":    None,
        }

    # ── GATE ──
    gate = curiosity_gate(command)

    if gate["decision"] == "BLOCK":
        return {
            "gate":    gate,
            "result":  None,
            "message": f"I cannot run that on {node_name}. {gate['reason']}",
            "node":    node,
        }

    if gate["decision"] == "CAUTION" and not confirmed:
        return {
            "gate":    gate,
            "result":  None,
            "message": (f"I need confirmation before I run that on {node_name}. "
                        f"{gate['reason']} Say 'confirm' to proceed."),
            "node":    node,
        }

    # ── EXECUTE ──
    result = ssh_run(node, command)

    if result["success"]:
        output = result["stdout"].strip()
        if output:
            lines = output.split("\n")
            if len(lines) > 5:
                summary = "\n".join(lines[:5]) + f"\n... ({len(lines)} lines total)"
            else:
                summary = output
            message = f"Done on {node_name}. Output: {summary}"
        else:
            message = f"Done on {node_name}. Command completed with no output."
    else:
        message = f"Command failed on {node_name}. {result['stderr'].strip()[:200]}"

    return {
        "gate":    gate,
        "result":  result,
        "message": message,
        "node":    node,
    }


# ── STANDALONE TEST ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   ARIA — NETWORK RUNNER — REGISTRY + GATE  ║")
    print("║   She reaches the network or she does not. ║")
    print("║   Commander Anthony Hagerty — Haskell TX   ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # ── SEED THE REGISTRY if empty ──
    nodes = list_nodes()
    if not nodes:
        print("Registry empty — seeding default nodes...")
        register_node("ai-core", "192.168.1.142", "comanderanch",
                      label="Main server — Tesla P100 — ARIA brain")
        register_node("laptop",  "192.168.1.169", "comanderanch",
                      label="Laptop thin client — voice + GUI")
        print("Nodes registered.")
        print()

    print("Registered nodes:")
    for name in list_nodes():
        n = get_node(name)
        print(f"  {name:12s} → {n['user']}@{n['host']}:{n['port']}  ({n['label']})")
    print()

    # ── GATE TESTS (no live SSH) ──
    print("Gate validation tests (no live SSH — checking decisions only):")
    print()

    test_cases = [
        ("ai-core", "ls -la /tmp",          False),  # PASS
        ("ai-core", "git status",            False),  # PASS
        ("ai-core", "ps aux",                False),  # PASS
        ("ai-core", "mkdir /tmp/test_aria",  False),  # CAUTION — no confirm
        ("ai-core", "mkdir /tmp/test_aria",  True),   # CAUTION — confirmed → SSH would fire
        ("ai-core", "rm -rf /home",          False),  # BLOCK
        ("unknown", "ls",                    False),  # BLOCK — unknown node
    ]

    for node_name, cmd, confirmed in test_cases:
        # Use gate check only — don't actually SSH in test
        node = get_node(node_name)
        if node is None:
            decision = "BLOCK (unknown node)"
        else:
            gate = curiosity_gate(cmd)
            if gate["decision"] == "BLOCK":
                decision = "BLOCK"
            elif gate["decision"] == "CAUTION" and not confirmed:
                decision = "CAUTION (needs confirm)"
            elif gate["decision"] == "CAUTION" and confirmed:
                decision = "CAUTION → PASS (confirmed) → SSH would fire"
            else:
                decision = "PASS → SSH would fire"

        print(f"  Node: {node_name:10s}  Command: {cmd:35s}  → {decision}")

    print()
    print("Network runner ready.")
    print("To run live: aria_network_run('ai-core', 'ls -la', confirmed=False)")
    print()
