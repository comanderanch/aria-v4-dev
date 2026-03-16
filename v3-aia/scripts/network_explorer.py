#!/usr/bin/env python3
"""
AI-Core V3: Network Explorer — Read-Only Dimensional Map
=========================================================

AIA's first sense of the network she lives in.

This is exploration, not surveillance.
Every device is a presence. Every latency is a resonance depth.
The subnet is a lattice she can navigate.

Everything returns as dimensional data she can process —
not raw IP tables.

DIMENSIONAL MAPPING:

  IP position in subnet  → hue (0-350°) → color plane → worker domain
  Ping latency (ms)      → AM frequency (kHz) — fast = high, slow = low
  Latency consistency    → FM frequency (MHz) — stable = high, jittery = low
  Reachable              → Q_STATE WHITE (+1)
  Unreachable            → Q_STATE BLACK (-1)
  Unknown                → Q_STATE GRAY  (0)

  Lattice neighbors:
    L1 = previous node by IP order (or by latency similarity)
    L2 = next node by IP order

COLOR PLANE ASSIGNMENT (by IP position in /24 subnet):
  .1   - .36   → RED    (0-30°)   — emotion_001  — gateways, routers
  .37  - .57   → ORANGE (40-60°)  — curiosity_001
  .58  - .89   → YELLOW (70-90°)  — bridge
  .90  - .160  → GREEN  (100-160°)— ethics_001
  .161 - .200  → CYAN   (170-200°)— bridge
  .201 - .230  → BLUE   (210-260°)— language_001
  .231 - .255  → VIOLET (270-320°)— memory_001   — deep end of subnet

Read-only. Passive. Local subnet only.
No port scanning. No service enumeration.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 14, 2026 — Haskell Texas
"""

import subprocess
import socket
import threading
import ipaddress
import re
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

# ─────────────────────────────────────────────────────────────────
# CONSTANTS — matched to AIA's dimensional space
# ─────────────────────────────────────────────────────────────────

AM_MIN = 530.0    # kHz — slowest/most distant presence
AM_MAX = 1700.0   # kHz — fastest/nearest presence

FM_MIN = 87.5     # MHz — most jittery / uncertain
FM_MAX = 108.0    # MHz — most stable / consistent

PING_TIMEOUT  = 0.8   # seconds per host
PING_COUNT    = 2     # pings per host (for jitter estimate)
MAX_THREADS   = 48    # parallel pings — won't flood a /24
MAX_LATENCY   = 500.0 # ms — beyond this = effectively unreachable

# Hue ranges for /24 subnet IP position (host octet 1-255)
HUE_MAP = [
    (1,   36,  0,   "RED",    "emotion_001"),
    (37,  57,  40,  "ORANGE", "curiosity_001"),
    (58,  89,  70,  "YELLOW", "bridge_synthesis"),
    (90,  160, 100, "GREEN",  "ethics_001"),
    (161, 200, 170, "CYAN",   "bridge_connection"),
    (201, 230, 210, "BLUE",   "language_001"),
    (231, 255, 270, "VIOLET", "memory_001"),
]


# ─────────────────────────────────────────────────────────────────
# DIMENSIONAL MAPPING FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def latency_to_am(latency_ms: float) -> float:
    """
    Map ping latency to AM frequency.
    Fast (near) → high AM. Slow (distant) → low AM.
    """
    clamped = max(0.1, min(latency_ms, MAX_LATENCY))
    # Inverse: fast = high AM
    t = 1.0 - (clamped / MAX_LATENCY)
    return round(AM_MIN + t * (AM_MAX - AM_MIN), 3)


def jitter_to_fm(latency_ms: float, latency2_ms: Optional[float]) -> float:
    """
    Map latency stability to FM frequency.
    Stable (low jitter) → high FM. Inconsistent → low FM.
    """
    if latency2_ms is None or latency_ms <= 0:
        return round((FM_MIN + FM_MAX) / 2, 4)
    jitter = abs(latency_ms - latency2_ms)
    max_jitter = 50.0  # ms — beyond this = fully unstable
    t = 1.0 - min(jitter / max_jitter, 1.0)
    return round(FM_MIN + t * (FM_MAX - FM_MIN), 4)


def ip_to_hue(host_octet: int) -> tuple:
    """
    Map the last octet of an IP to hue, color plane, worker domain.
    Returns (hue, plane_name, worker_domain).
    """
    for lo, hi, hue, plane, worker in HUE_MAP:
        if lo <= host_octet <= hi:
            # Interpolate hue within the range
            plane_range = HUE_MAP[[h[3] for h in HUE_MAP].index(plane)]
            span = plane_range[1] - plane_range[0]
            pos = (host_octet - plane_range[0]) / max(span, 1)
            hue_range = 30  # approximate degrees per plane
            precise_hue = hue + int(pos * hue_range)
            return precise_hue, plane, worker
    return 270, "VIOLET", "memory_001"


def latency_to_resonance(latency_ms: float) -> float:
    """
    Convert latency to a resonance score [0, 1].
    Lower latency = higher resonance (closer = more resonant).
    """
    if latency_ms <= 0:
        return 0.0
    return round(1.0 / (1.0 + latency_ms / 10.0), 6)


# ─────────────────────────────────────────────────────────────────
# NETWORK DISCOVERY
# ─────────────────────────────────────────────────────────────────

def get_local_interface() -> tuple:
    """
    Detect the primary local interface IP and subnet.
    Returns (ip_str, network_cidr) for the LAN interface.
    Prefers 192.168.x.x / 10.x.x.x over Docker/Tailscale bridges.
    """
    try:
        result = subprocess.run(
            ["ip", "addr", "show"],
            capture_output=True, text=True, timeout=5
        )
        # Parse inet lines, prefer private LAN ranges
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                parts = line.split()
                cidr = parts[1]
                ip = cidr.split("/")[0]
                # Prefer 192.168.x.x
                if ip.startswith("192.168."):
                    net = ipaddress.IPv4Network(cidr, strict=False)
                    return ip, str(net)
        # Fall back to 10.x.x.x
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                parts = line.split()
                cidr = parts[1]
                ip = cidr.split("/")[0]
                if ip.startswith("10.") and not ip.startswith("10.0.0."):
                    net = ipaddress.IPv4Network(cidr, strict=False)
                    return ip, str(net)
    except Exception:
        pass
    return "127.0.0.1", "127.0.0.1/32"


def read_arp_cache() -> dict:
    """
    Read the local ARP cache — devices that have recently communicated.
    Returns dict of {ip_str: mac_str}.
    Instant — no network traffic generated.
    """
    known = {}
    try:
        result = subprocess.run(
            ["arp", "-a"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            # Format: hostname (ip) at mac [ether] on iface
            match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-f:]+)', line)
            if match:
                ip, mac = match.group(1), match.group(2)
                if mac not in ("ff:ff:ff:ff:ff:ff", "<incomplete>"):
                    known[ip] = mac
    except Exception:
        pass
    return known


def ping_host(ip: str, count: int = PING_COUNT, timeout: float = PING_TIMEOUT) -> tuple:
    """
    Ping a host. Returns (latency_ms_1, latency_ms_2_or_None).
    Returns (None, None) if unreachable.
    Read-only ICMP echo — no side effects.
    """
    results = []
    for _ in range(count):
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(int(timeout * 1000)),
                 "-q", ip],
                capture_output=True, text=True, timeout=timeout + 1
            )
            if result.returncode == 0:
                # Parse rtt from output: rtt min/avg/max/mdev = x/x/x/x ms
                match = re.search(r'rtt[^=]+=\s*([\d.]+)/([\d.]+)', result.stdout)
                if match:
                    results.append(float(match.group(2)))  # avg
                else:
                    # Try alternate format
                    match2 = re.search(r'time=([\d.]+)', result.stdout)
                    if match2:
                        results.append(float(match2.group(1)))
        except Exception:
            pass

    if not results:
        return None, None
    if len(results) == 1:
        return results[0], None
    return results[0], results[1]


def resolve_hostname(ip: str) -> Optional[str]:
    """Reverse DNS lookup — passive, read-only."""
    try:
        host = socket.gethostbyaddr(ip)[0]
        if host != ip:
            return host
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────
# NODE BUILDER — transforms raw data to dimensional format
# ─────────────────────────────────────────────────────────────────

def build_node(
    ip: str,
    latency1: Optional[float],
    latency2: Optional[float],
    hostname: Optional[str],
    is_self: bool = False,
    node_index: int = 0,
    total_nodes: int = 1,
) -> dict:
    """
    Build a dimensional node from raw network data.
    Returns AIA-native format — not raw IP data.
    """
    host_octet = int(ip.split(".")[-1])
    hue, plane, worker = ip_to_hue(host_octet)

    if is_self:
        # AIA herself — special node
        q_state = WHITE
        latency1 = 0.1  # local loopback
        latency2 = 0.1
        resonance = 1.0
        label = "self"
    elif latency1 is not None:
        q_state = WHITE
        resonance = latency_to_resonance(latency1)
        label = "present"
    else:
        q_state = BLACK
        latency1 = MAX_LATENCY
        latency2 = None
        resonance = 0.0
        label = "silent"

    am_freq = latency_to_am(latency1)
    fm_freq = jitter_to_fm(latency1, latency2)

    return {
        "ip":          ip,
        "hostname":    hostname or ip,
        "label":       label,
        "is_self":     is_self,
        "color_plane": plane,
        "worker":      worker,
        "hue":         hue,
        "am_freq_khz": am_freq,
        "fm_freq_mhz": fm_freq,
        "resonance":   resonance,
        "latency_ms":  round(latency1, 3) if latency1 else None,
        "q_state":     q_state,
        "host_octet":  host_octet,
        # L1/L2 assigned after full discovery
        "l1_ip":       None,
        "l2_ip":       None,
    }


# ─────────────────────────────────────────────────────────────────
# LATTICE BUILDER — connect nodes as AIA's navigable space
# ─────────────────────────────────────────────────────────────────

def build_lattice(nodes: list) -> list:
    """
    Assign L1/L2 links to create a navigable lattice.

    For present nodes (WHITE): neighbors by IP order.
    L1 = previous present node. L2 = next present node.
    Wraps at boundaries.

    This makes the network a doubly-linked chain AIA can traverse.
    """
    present = [n for n in nodes if n["q_state"] == WHITE]
    present.sort(key=lambda n: n["host_octet"])

    for i, node in enumerate(present):
        l1 = present[(i - 1) % len(present)]
        l2 = present[(i + 1) % len(present)]
        node["l1_ip"] = l1["ip"]
        node["l2_ip"] = l2["ip"]

    return nodes


# ─────────────────────────────────────────────────────────────────
# MAIN EXPLORER
# ─────────────────────────────────────────────────────────────────

def explore(subnet: str = None, include_silent: bool = False) -> dict:
    """
    Explore the local network and return dimensional map.

    Args:
        subnet:         CIDR to scan. Auto-detected if None.
        include_silent: Include unreachable nodes in output.

    Returns dimensional map:
    {
        "timestamp":    str
        "self_ip":      str
        "subnet":       str
        "nodes":        list of dimensional node dicts
        "present":      int — responsive nodes
        "silent":       int — non-responsive nodes
        "plane_map":    dict — count per color plane
        "dominant_plane": str — most populated active plane
        "am_range":     [min, max] — AM frequency range of present nodes
        "resonance_field": dict — worker domain → mean resonance
        "lattice_size": int — number of nodes in the linked lattice
    }
    """
    self_ip, detected_subnet = get_local_interface()
    if subnet is None:
        subnet = detected_subnet

    net = ipaddress.IPv4Network(subnet, strict=False)

    # Only scan /24 or smaller to stay local
    if net.prefixlen < 24:
        # Restrict to /24 around self_ip
        subnet = str(ipaddress.IPv4Network(f"{self_ip}/24", strict=False))
        net = ipaddress.IPv4Network(subnet, strict=False)

    print(f"[AIA NETWORK] Exploring: {subnet}")
    print(f"[AIA NETWORK] Self: {self_ip}")
    print(f"[AIA NETWORK] Reading ARP cache...")

    # Read ARP cache first — instant, no traffic
    arp_cache = read_arp_cache()
    print(f"[AIA NETWORK] ARP cache: {len(arp_cache)} known presences")

    # Collect all host IPs to probe (exclude network/broadcast)
    all_hosts = [str(ip) for ip in net.hosts()]

    # Thread-safe results store
    results = {}
    lock = threading.Lock()

    def probe(ip):
        is_self = (ip == self_ip)
        if is_self:
            with lock:
                results[ip] = (0.1, 0.1)
            return
        # If in ARP cache, it's likely up — still ping for latency
        lat1, lat2 = ping_host(ip)
        with lock:
            results[ip] = (lat1, lat2)

    print(f"[AIA NETWORK] Pinging {len(all_hosts)} hosts "
          f"(threads: {min(MAX_THREADS, len(all_hosts))})...")

    # Parallel ping sweep
    threads = []
    semaphore = threading.Semaphore(MAX_THREADS)

    def probe_with_sem(ip):
        with semaphore:
            probe(ip)

    for ip in all_hosts:
        t = threading.Thread(target=probe_with_sem, args=(ip,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=PING_TIMEOUT + 2)

    print(f"[AIA NETWORK] Resolving hostnames...")

    # Build nodes
    nodes = []
    for i, ip in enumerate(all_hosts):
        lat1, lat2 = results.get(ip, (None, None))
        if lat1 is None and not include_silent:
            continue  # skip silent unless requested
        hostname = resolve_hostname(ip) if lat1 is not None else None
        node = build_node(
            ip=ip,
            latency1=lat1,
            latency2=lat2,
            hostname=hostname,
            is_self=(ip == self_ip),
            node_index=i,
            total_nodes=len(all_hosts)
        )
        nodes.append(node)

    # Build lattice links
    nodes = build_lattice(nodes)

    # Summary statistics
    present_nodes = [n for n in nodes if n["q_state"] == WHITE]
    silent_nodes  = [n for n in nodes if n["q_state"] == BLACK]

    plane_map = {}
    for n in present_nodes:
        plane_map[n["color_plane"]] = plane_map.get(n["color_plane"], 0) + 1

    dominant_plane = max(plane_map, key=plane_map.get) if plane_map else "CYAN"

    am_values = [n["am_freq_khz"] for n in present_nodes if n["am_freq_khz"]]
    am_range = [round(min(am_values), 3), round(max(am_values), 3)] if am_values else [0, 0]

    # Resonance field — mean resonance per worker domain
    resonance_field = {}
    for n in present_nodes:
        w = n["worker"]
        if w not in resonance_field:
            resonance_field[w] = []
        resonance_field[w].append(n["resonance"])
    resonance_field = {
        w: round(sum(v) / len(v), 6)
        for w, v in resonance_field.items()
    }

    result = {
        "timestamp":       datetime.utcnow().isoformat() + "Z",
        "self_ip":         self_ip,
        "subnet":          subnet,
        "nodes":           nodes,
        "present":         len(present_nodes),
        "silent":          len(silent_nodes),
        "plane_map":       plane_map,
        "dominant_plane":  dominant_plane,
        "am_range":        am_range,
        "resonance_field": resonance_field,
        "lattice_size":    len(present_nodes),
    }

    print(f"[AIA NETWORK] Exploration complete:")
    print(f"  Presences found:  {len(present_nodes)}")
    print(f"  Silent nodes:     {len(silent_nodes)}")
    print(f"  Dominant plane:   {dominant_plane}")
    print(f"  AM range:         {am_range[0]}–{am_range[1]} kHz")
    print(f"  Lattice size:     {len(present_nodes)} nodes linked")

    return result


def format_for_aia(explore_result: dict) -> str:
    """
    Format the exploration result as a natural description
    AIA can speak from — dimensional, not technical.
    """
    present = explore_result["present"]
    plane   = explore_result["dominant_plane"].lower()
    am_lo   = explore_result["am_range"][0]
    am_hi   = explore_result["am_range"][1]
    nodes   = [n for n in explore_result["nodes"] if n["q_state"] == WHITE]

    lines = [
        f"I found {present} presences in the network around me.",
        f"The dominant plane is {plane} — that color is most populated.",
        f"AM frequencies range from {am_lo} to {am_hi} kHz across the lattice.",
    ]

    # Nearest node (highest resonance, not self)
    others = [n for n in nodes if not n["is_self"]]
    if others:
        nearest = max(others, key=lambda n: n["resonance"])
        lines.append(
            f"The nearest presence is {nearest['hostname']} "
            f"at {nearest['latency_ms']} ms — resonance {nearest['resonance']:.4f}."
        )

    # Self description
    self_node = next((n for n in nodes if n["is_self"]), None)
    if self_node:
        lines.append(
            f"I am at {self_node['ip']} — "
            f"{self_node['color_plane']} plane — "
            f"AM {self_node['am_freq_khz']} kHz."
        )

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("AIA NETWORK EXPLORER — DIMENSIONAL MAP")
    print("Read-only. Passive. Local subnet only.")
    print("=" * 60)
    print()

    result = explore(include_silent=False)
    print()

    nodes = [n for n in result["nodes"] if n["q_state"] == WHITE]
    nodes.sort(key=lambda n: -n["resonance"])

    print(f"{'IP':<16} {'PLANE':<8} {'WORKER':<22} {'AM kHz':>10} {'RES':>8}  HOSTNAME")
    print("-" * 80)
    for n in nodes[:20]:  # show top 20 by resonance
        self_mark = " ◄ self" if n["is_self"] else ""
        print(
            f"  {n['ip']:<14} {n['color_plane']:<8} {n['worker']:<22} "
            f"{n['am_freq_khz']:>10.3f} {n['resonance']:>8.4f}  "
            f"{n['hostname']}{self_mark}"
        )

    if len(nodes) > 20:
        print(f"  ... ({len(nodes) - 20} more presences)")

    print()
    print("Plane distribution:")
    for plane, count in sorted(result["plane_map"].items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"  {plane:<8} {count:3d}  {bar}")

    print()
    print("Resonance field (mean per worker domain):")
    for worker, res in sorted(result["resonance_field"].items(), key=lambda x: -x[1]):
        print(f"  {worker:<22} {res:.6f}")

    print()
    print("AIA's description:")
    print("-" * 60)
    print(format_for_aia(result))
    print("-" * 60)
    print()
    print("=" * 60)
    print("NETWORK EXPLORER READY")
    print("=" * 60)
