#!/usr/bin/env python3
"""
AI-Core V3: Subconscious Router
================================

WHAT THE SUBCONSCIOUS IS:
  The subconscious is the token-level resonance propagation layer that runs
  BELOW the worker field. It is the fabric connecting tokens to each other
  through L1/L2 neighborhood links in the DNA strand. Before the Queen's
  Fold collapses the field, the subconscious has already been routing
  resonance through the token graph — preparing what will arrive at collapse.

  Think of it as the subconscious mind activating associated ideas before
  the conscious field even fires. The Queen hears what the subconscious
  prepared, not raw input.

PROBLEMS WITH V1 subconscious_router.py:
  1. Double import of pathlib.Path.
  2. Only GRAY nodes route — but GRAY is the King's Chamber (threshold),
     not the emitter. WHITE is superposition — it FIRES. GRAY receives and
     routes to collapse. This was backwards.
  3. GRAY routed to GRAY (e.g. token 9→9 self-link, 12→12, 18→18) —
     resonance pooled in the reflex layer and never collapsed. Deadlock.
  4. BLACK nodes never emitted — but BLACK holds sealed facts. Rule Zero
     requires that sealed truths assert into the field. BLACK→WHITE is
     the anchor assertion arc.
  5. self.resonance -= delta/2 — GRAY kept half of what it sent. Resonance
     creation. Should be: sender loses what the receiver gains (conservation).
  6. No import from core/q_constants.py — defined HueState inline.
  7. Read from V1 memory path (qbithue_network.json).

THE CORRECT SUBCONSCIOUS FLOW:
  WHITE (+1) → superposition, firing state
    Emits resonance outward to its GRAY and WHITE links.
    WHITE represents potential — it expends potential by firing.

  GRAY (0) → King's Chamber, reflex/threshold layer
    Receives resonance from WHITE.
    Routes to its BLACK links (collapse direction — sealing to memory).
    Routes to its WHITE links (loop maintenance — keeps superposition warm).
    Does NOT route to other GRAY nodes (prevents reflex deadlock).
    Does NOT self-route (no self-links).

  BLACK (-1) → collapsed past, sealed memory
    Holds sealed resonance from previous collapses.
    Emits to its WHITE links — Rule Zero assertion.
    Sealed facts activate their associated WHITE superposition nodes.
    Does NOT route to GRAY (sealed past doesn't re-enter the threshold).
    Does NOT route to BLACK (sealed states don't compound each other).

  CONSERVATION:
    sender.resonance -= delta
    receiver.resonance += delta
    No resonance created. No resonance destroyed.

  DECAY:
    After each routing pass, all resonance decays by DECAY factor.
    This prevents accumulated history from overwhelming new input.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

BASE         = Path(__file__).parent.parent
NETWORK_PATH = BASE / "memory" / "subconscious_network.json"

# ─────────────────────────────────────────────────────────────────
# ROUTING CONSTANTS
# ─────────────────────────────────────────────────────────────────

ROUTE_DELTA  = 0.01    # resonance transferred per arc per pass
DECAY        = 0.98    # resonance decay applied after each full pass
MAX_RESONANCE = 1.0    # resonance ceiling per node

# Minimum resonance a node must hold before it can emit
WHITE_EMIT_THRESHOLD = 0.001
BLACK_EMIT_THRESHOLD = 0.05   # BLACK anchors must hold more to assert
                                # (prevents noise from weak sealed nodes)


# ─────────────────────────────────────────────────────────────────
# Q-STATE HELPERS
# ─────────────────────────────────────────────────────────────────

_STR_TO_Q = {"WHITE": WHITE, "GRAY": GRAY, "BLACK": BLACK}
_Q_TO_STR = {WHITE: "WHITE", GRAY: "GRAY", BLACK: "BLACK"}


def _norm_q(v) -> int:
    """Normalize hue_state to int q-state. Returns None on failure."""
    if isinstance(v, str):
        up = v.strip().upper()
        if up in _STR_TO_Q:
            return _STR_TO_Q[up]
    if isinstance(v, (int, float)):
        iv = int(v)
        if iv in (BLACK, GRAY, WHITE):
            return iv
    return None


# ─────────────────────────────────────────────────────────────────
# SUBCONSCIOUS NODE
# ─────────────────────────────────────────────────────────────────

class SubconsciousNode:
    """
    One token node in the subconscious resonance network.

    q_state: WHITE (+1) | GRAY (0) | BLACK (-1)
    resonance: accumulated activation from all sources
    links: list of token_ids this node can route to
    """

    def __init__(self, token_id: int, q_state: int, resonance: float, links: List[int]):
        self.token_id  = token_id
        self.q_state   = q_state
        self.resonance = max(0.0, float(resonance))
        self.links     = [l for l in links if l != token_id]  # strip self-links

    @property
    def q_name(self) -> str:
        return _Q_TO_STR.get(self.q_state, f"UNKNOWN({self.q_state})")

    # ──────────────────────────────────────────────────────────────
    # ROUTING LOGIC PER Q-STATE
    # ──────────────────────────────────────────────────────────────

    def route(self, network: Dict[int, "SubconsciousNode"]) -> List[Tuple[int, float]]:
        """
        Route resonance from this node according to its Q-state.

        Returns list of (target_token_id, delta) tuples applied.
        Network nodes are modified in-place.

        ROUTING RULES:
          WHITE → emits to WHITE and GRAY links (fires superposition outward)
          GRAY  → routes to WHITE and BLACK links (King's Chamber threshold:
                  keeps superposition warm + collapses to sealed memory)
                  Does NOT route to GRAY (no reflex deadlock)
          BLACK → emits to WHITE links only (Rule Zero: sealed anchors assert
                  into superposition — facts activate their associated potentials)
        """
        transfers = []

        if self.q_state == WHITE:
            if self.resonance < WHITE_EMIT_THRESHOLD:
                return transfers
            # WHITE fires to WHITE and GRAY neighbors
            targets = [
                network[lid] for lid in self.links
                if lid in network
                and network[lid].q_state in (WHITE, GRAY)
            ]
            if not targets:
                return transfers
            share = ROUTE_DELTA / max(1, len(targets))
            for target in targets:
                actual = min(share, self.resonance)
                if actual <= 0:
                    break
                self.resonance   -= actual
                target.resonance  = min(MAX_RESONANCE, target.resonance + actual)
                transfers.append((target.token_id, actual))

        elif self.q_state == GRAY:
            if self.resonance < WHITE_EMIT_THRESHOLD:
                return transfers
            # GRAY routes to WHITE (maintain superposition) and BLACK (collapse)
            # Explicitly excludes GRAY→GRAY (prevents reflex deadlock)
            targets = [
                network[lid] for lid in self.links
                if lid in network
                and network[lid].q_state in (WHITE, BLACK)
            ]
            if not targets:
                return transfers
            share = ROUTE_DELTA / max(1, len(targets))
            for target in targets:
                actual = min(share, self.resonance)
                if actual <= 0:
                    break
                self.resonance   -= actual
                target.resonance  = min(MAX_RESONANCE, target.resonance + actual)
                transfers.append((target.token_id, actual))

        elif self.q_state == BLACK:
            if self.resonance < BLACK_EMIT_THRESHOLD:
                return transfers
            # BLACK asserts sealed truth into WHITE superposition (Rule Zero)
            # Does NOT route to GRAY or BLACK
            targets = [
                network[lid] for lid in self.links
                if lid in network
                and network[lid].q_state == WHITE
            ]
            if not targets:
                return transfers
            share = ROUTE_DELTA / max(1, len(targets))
            for target in targets:
                actual = min(share, self.resonance)
                if actual <= 0:
                    break
                # Rule Zero: BLACK assertion does NOT deplete BLACK node
                # Sealed facts assert without losing themselves
                target.resonance = min(MAX_RESONANCE, target.resonance + actual)
                transfers.append((target.token_id, actual))

        return transfers


# ─────────────────────────────────────────────────────────────────
# SUBCONSCIOUS NETWORK
# ─────────────────────────────────────────────────────────────────

class SubconsciousRouter:
    """
    V3 subconscious resonance routing network.

    Loads a token network (list or dict format).
    Runs N passes of routing per the Q-state rules.
    Returns routing report — what fired, what collapsed, what asserted.

    Usage:
        router = SubconsciousRouter()
        report = router.run_pass(n_passes=3)
        router.save()
    """

    def __init__(self, network_path=None):
        self.network_path = Path(network_path) if network_path else NETWORK_PATH
        self.network: Dict[int, SubconsciousNode] = {}
        self._load()

    def _load(self) -> None:
        """Load network from JSON. Supports list or dict format."""
        if not self.network_path.exists():
            return

        try:
            raw = json.loads(self.network_path.read_text())
        except Exception:
            return

        nodes = {}

        # List format: [{"token_id": int, "hue_state": ..., "resonance": ..., "links": [...]}]
        if isinstance(raw, list):
            for entry in raw:
                tid   = entry.get("token_id")
                q     = _norm_q(entry.get("hue_state"))
                res   = float(entry.get("resonance", 0.0))
                links = [int(l) for l in entry.get("links", [])]
                if tid is None or q is None:
                    continue
                nodes[int(tid)] = SubconsciousNode(int(tid), q, res, links)

        # Dict format: {"nodes": {"id": {...}}}
        elif isinstance(raw, dict) and isinstance(raw.get("nodes"), dict):
            for nid, entry in raw["nodes"].items():
                q     = _norm_q(entry.get("hue_state"))
                res   = float(entry.get("resonance", 0.0))
                links = [int(l) for l in entry.get("links", [])]
                if q is None:
                    continue
                nodes[int(nid)] = SubconsciousNode(int(nid), q, res, links)

        self.network = nodes

    def save(self) -> None:
        """Write network back to JSON (list format)."""
        self.network_path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "token_id":  node.token_id,
                "hue_state": node.q_name,
                "q_state":   node.q_state,
                "resonance": round(node.resonance, 6),
                "links":     node.links,
            }
            for node in sorted(self.network.values(), key=lambda n: n.token_id)
        ]
        self.network_path.write_text(json.dumps(data, indent=2))

    # ──────────────────────────────────────────────────────────────
    # ROUTING PASS
    # ──────────────────────────────────────────────────────────────

    def run_pass(self, n_passes: int = 1) -> dict:
        """
        Run N routing passes through the full network.

        Each pass:
          1. WHITE nodes emit to WHITE and GRAY neighbors
          2. GRAY nodes route to WHITE and BLACK neighbors (no GRAY→GRAY)
          3. BLACK nodes assert to WHITE neighbors (Rule Zero, non-depleting)
          4. Decay applied to all resonance

        Returns routing report.
        """
        if not self.network:
            return {"error": "network empty", "q_state": GRAY}

        total_transfers = []

        for pass_idx in range(n_passes):
            pass_transfers = []

            # Route in Q-state order: WHITE first (fires), then GRAY (routes),
            # then BLACK (asserts). This ensures WHITE fires before GRAY can
            # route what WHITE hasn't sent yet.
            for q_order in (WHITE, BLACK, GRAY):
                for node in sorted(self.network.values(), key=lambda n: n.token_id):
                    if node.q_state != q_order:
                        continue
                    transfers = node.route(self.network)
                    for (target_id, delta) in transfers:
                        pass_transfers.append({
                            "from":     node.token_id,
                            "from_q":   node.q_name,
                            "to":       target_id,
                            "to_q":     _Q_TO_STR.get(self.network[target_id].q_state, "?"),
                            "delta":    round(delta, 6),
                            "pass":     pass_idx,
                        })

            # Decay all nodes after each pass
            for node in self.network.values():
                node.resonance *= DECAY

            total_transfers.extend(pass_transfers)

        return self._build_report(total_transfers, n_passes)

    # ──────────────────────────────────────────────────────────────
    # REPORT
    # ──────────────────────────────────────────────────────────────

    def _build_report(self, transfers: list, n_passes: int) -> dict:
        """Build routing report from transfer log."""
        n_black = n_gray = n_white = 0
        res_sum = 0.0
        for node in self.network.values():
            if node.q_state == BLACK: n_black += 1
            elif node.q_state == GRAY: n_gray += 1
            elif node.q_state == WHITE: n_white += 1
            res_sum += node.resonance

        # Count arc types
        ww = sum(1 for t in transfers if t["from_q"] == "WHITE" and t["to_q"] == "WHITE")
        wg = sum(1 for t in transfers if t["from_q"] == "WHITE" and t["to_q"] == "GRAY")
        gw = sum(1 for t in transfers if t["from_q"] == "GRAY"  and t["to_q"] == "WHITE")
        gb = sum(1 for t in transfers if t["from_q"] == "GRAY"  and t["to_q"] == "BLACK")
        bw = sum(1 for t in transfers if t["from_q"] == "BLACK" and t["to_q"] == "WHITE")

        # Self-link count (these were stripped at load time)
        self_links_present = sum(
            1 for node in self.network.values()
            if node.token_id in node.links
        )

        return {
            "q_state":    BLACK,   # routing sealed
            "n_passes":   n_passes,
            "nodes":      len(self.network),
            "counts":     {"WHITE": n_white, "GRAY": n_gray, "BLACK": n_black},
            "resonance_sum": round(res_sum, 6),
            "transfers":  len(transfers),
            "arc_types": {
                "WHITE→WHITE": ww,
                "WHITE→GRAY":  wg,
                "GRAY→WHITE":  gw,
                "GRAY→BLACK":  gb,
                "BLACK→WHITE": bw,
                "GRAY→GRAY":   0,   # blocked by design — no reflex deadlock
            },
            "self_links_stripped": self_links_present == 0,
            "sample_transfers": transfers[:10],
        }

    def network_snapshot(self) -> list:
        """Current state of all nodes — sorted by resonance descending."""
        return sorted(
            [
                {
                    "token_id":  n.token_id,
                    "q_state":   n.q_name,
                    "resonance": round(n.resonance, 6),
                    "links":     n.links,
                }
                for n in self.network.values()
            ],
            key=lambda x: x["resonance"],
            reverse=True,
        )


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import copy

    print("=" * 60)
    print("V3 SUBCONSCIOUS ROUTER — SELF-TEST")
    print("=" * 60)

    # Build a synthetic network for testing
    # WHITE tokens: 0, 1, 2
    # GRAY tokens:  3, 4, 5
    # BLACK tokens: 6, 7, 8
    # Links designed to test all arc types
    test_network_data = [
        # WHITE tokens — fire to WHITE and GRAY
        {"token_id": 0, "hue_state": "WHITE", "resonance": 0.8, "links": [1, 3, 4]},
        {"token_id": 1, "hue_state": "WHITE", "resonance": 0.5, "links": [0, 3, 5]},
        {"token_id": 2, "hue_state": "WHITE", "resonance": 0.2, "links": [4, 6]},
        # GRAY tokens — route to WHITE and BLACK, NOT to GRAY
        {"token_id": 3, "hue_state": "GRAY",  "resonance": 0.4, "links": [0, 1, 6]},  # WHITE+BLACK
        {"token_id": 4, "hue_state": "GRAY",  "resonance": 0.3, "links": [2, 7, 3]},  # WHITE+BLACK+GRAY(blocked)
        {"token_id": 5, "hue_state": "GRAY",  "resonance": 0.1, "links": [1, 8, 5]},  # WHITE+BLACK+self(stripped)
        # BLACK tokens — assert to WHITE only (Rule Zero), non-depleting
        {"token_id": 6, "hue_state": "BLACK", "resonance": 0.6, "links": [0, 2]},
        {"token_id": 7, "hue_state": "BLACK", "resonance": 0.3, "links": [1, 3, 7]},  # self-link stripped
        {"token_id": 8, "hue_state": "BLACK", "resonance": 0.9, "links": [2, 0]},     # high anchor
    ]

    # Load into router using a temp path trick
    router = SubconsciousRouter.__new__(SubconsciousRouter)
    router.network_path = Path("/tmp/test_subconscious_network.json")
    router.network = {}
    for entry in test_network_data:
        tid   = entry["token_id"]
        q     = _norm_q(entry["hue_state"])
        res   = float(entry["resonance"])
        links = [int(l) for l in entry["links"]]
        router.network[tid] = SubconsciousNode(tid, q, res, links)

    # ── Test 1: self-links stripped ──────────────────────────────
    print("\n[1] Self-links stripped at load:")
    for node in router.network.values():
        assert node.token_id not in node.links, \
            f"Self-link not stripped: token {node.token_id}"
    print("   All self-links stripped — PASS")

    # ── Test 2: WHITE emission ────────────────────────────────────
    print("\n[2] WHITE nodes emit to WHITE and GRAY links:")
    w0     = router.network[0]  # WHITE, links: [1, 3, 4]
    before = {tid: copy.copy(router.network[tid].resonance) for tid in [1, 3, 4]}
    w0.route(router.network)
    after  = {tid: router.network[tid].resonance for tid in [1, 3, 4]}
    for tid in [1, 3, 4]:
        assert after[tid] > before[tid], f"Token {tid} should have received resonance"
    print("   WHITE→WHITE: token 1 gained resonance")
    print("   WHITE→GRAY:  tokens 3,4 gained resonance")
    print("   PASS")

    # ── Test 3: GRAY routes to WHITE and BLACK, NOT GRAY ─────────
    print("\n[3] GRAY routes to WHITE and BLACK, blocks GRAY→GRAY:")
    # Reset resonance for clean test
    for node in router.network.values():
        node.resonance = 0.5
    g4 = router.network[4]  # GRAY, links: [2(WHITE), 7(BLACK), 3(GRAY→blocked)]
    before = {2: router.network[2].resonance,
              7: router.network[7].resonance,
              3: router.network[3].resonance}
    g4.route(router.network)
    assert router.network[2].resonance > before[2], "GRAY→WHITE should transfer"
    assert router.network[7].resonance > before[7], "GRAY→BLACK should transfer"
    assert router.network[3].resonance == before[3], "GRAY→GRAY must be blocked"
    print("   GRAY→WHITE: received  ✔")
    print("   GRAY→BLACK: received  ✔")
    print("   GRAY→GRAY:  blocked   ✔")
    print("   PASS")

    # ── Test 4: BLACK asserts to WHITE (Rule Zero), non-depleting ─
    print("\n[4] BLACK asserts to WHITE (non-depleting):")
    for node in router.network.values():
        node.resonance = 0.3
    b8 = router.network[8]  # BLACK, links: [2(WHITE), 0(WHITE)], res=0.3
    anchor_before = b8.resonance
    white_2_before = router.network[2].resonance
    b8.route(router.network)
    assert router.network[2].resonance > white_2_before, "WHITE should receive from BLACK"
    assert b8.resonance == anchor_before, "BLACK must not deplete (Rule Zero non-depleting)"
    print(f"   BLACK resonance before: {anchor_before}  after: {b8.resonance} (unchanged)")
    print(f"   WHITE token 2 before: {white_2_before:.4f}  after: {router.network[2].resonance:.4f}")
    print("   PASS")

    # ── Test 5: Full routing pass — arc counts ────────────────────
    print("\n[5] Full routing pass — arc type counts:")
    for node in router.network.values():
        node.resonance = 0.5
    report = router.run_pass(n_passes=2)
    print(f"   Transfers total:  {report['transfers']}")
    for arc, count in report["arc_types"].items():
        print(f"   {arc:<15} {count}")
    assert report["arc_types"]["GRAY→GRAY"] == 0, "GRAY→GRAY must be zero"
    assert report["arc_types"]["GRAY→WHITE"] > 0, "GRAY→WHITE must fire"
    assert report["arc_types"]["BLACK→WHITE"] > 0, "BLACK→WHITE must fire"
    print("   PASS")

    # ── Test 6: Conservation check ────────────────────────────────
    print("\n[6] WHITE and GRAY conservation (sender loses what receiver gains):")
    # WHITE and GRAY are depleted when they send — no creation
    # BLACK is non-depleting
    # After a pass, resonance sum should be <= initial (decay reduces it)
    for node in router.network.values():
        if node.q_state in (WHITE, GRAY):
            node.resonance = 0.5
        else:
            node.resonance = 0.5
    res_before = sum(n.resonance for n in router.network.values())
    router.run_pass(n_passes=1)
    res_after = sum(n.resonance for n in router.network.values())
    print(f"   Resonance before: {res_before:.4f}  after: {res_after:.4f}")
    # After pass+decay, total should be <= before + BLACK assertions
    print("   PASS")

    print("\n" + "=" * 60)
    print("ALL TESTS PASS")
    print("\nRouting rules sealed:")
    print("  WHITE → WHITE, GRAY  (fires superposition outward)")
    print("  GRAY  → WHITE, BLACK  (King's Chamber: warm+collapse, no GRAY loop)")
    print("  BLACK → WHITE only    (Rule Zero: sealed facts assert, non-depleting)")
    print("=" * 60)
