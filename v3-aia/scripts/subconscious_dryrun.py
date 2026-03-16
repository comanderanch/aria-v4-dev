#!/usr/bin/env python3
"""
AI-Core V3: Subconscious Dry Run (read-only)
=============================================

PROBLEMS WITH V1 subconscious_dryrun.py:
  1. Defined BLACK, GRAY, WHITE = -1, 0, +1 inline instead of importing
     from core/q_constants.py — every V3 file must import from there.
  2. Arc detection only looked for GRAY→WHITE arcs — missed the full
     routing picture. WHITE→GRAY and BLACK→WHITE arcs were invisible.
  3. is_emitter = WHITE only — but BLACK anchors are ALSO emitters
     (Rule Zero: sealed facts assert into superposition). A BLACK node
     with high resonance and WHITE links is an anchor firing.
  4. "additive_only" in invariants — meaningless for a dry run.
     Replaced with accurate invariant flags.

THIS REBUILD:
  Reads any qbithue/subconscious network (V1 list or dict format).
  Reports all three arc types: WHITE→GRAY, GRAY→BLACK, BLACK→WHITE.
  Correctly identifies emitters: WHITE (potential firing) and
  BLACK (anchors asserting — Rule Zero).
  Pure read-only — no writes, no side effects.
  Exits 0 on success; nonzero on error.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

HUE_STR_TO_INT = {"BLACK": BLACK, "GRAY": GRAY, "WHITE": WHITE}
HUE_INT_TO_STR = {BLACK: "BLACK", GRAY: "GRAY", WHITE: "WHITE"}

# Q-state roles — what each state IS in the subconscious
Q_ROLES = {
    WHITE: "superposition / firing state",
    GRAY:  "King's Chamber / reflex threshold",
    BLACK: "collapsed past / sealed anchor",
}


def _load_json(p: Path):
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERR] Missing file: {p}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[ERR] Invalid JSON in {p}: {e}", file=sys.stderr)
        return None


def _norm_hue(v) -> int:
    """Normalize hue_state string or int to q-state int."""
    if isinstance(v, str):
        up = v.strip().upper()
        if up in HUE_STR_TO_INT:
            return HUE_STR_TO_INT[up]
    if isinstance(v, (int, float)):
        iv = int(v)
        if iv in (BLACK, GRAY, WHITE):
            return iv
    return None


def _normalize_network(net_obj: object) -> dict:
    """
    Parse either list or dict network format.
    Returns dict: str(id) → {hue_state: int, resonance: float, links: [str, ...]}
    """
    nodes = {}

    # List format: [{"token_id": int, "hue_state": ..., "resonance": ..., "links": [...]}]
    if isinstance(net_obj, list) and net_obj:
        for entry in net_obj:
            if not isinstance(entry, dict):
                continue
            tid = entry.get("token_id")
            q   = _norm_hue(entry.get("hue_state"))
            res = float(entry.get("resonance", 0.0) or 0.0)
            lnk = [str(l) for l in (entry.get("links") or [])]
            if tid is None or q is None:
                continue
            nid = str(tid)
            nodes[nid] = {"hue_state": q, "resonance": res, "links": lnk}
        if nodes:
            return nodes

    # Dict format: {"nodes": {"id": {...}}}
    if isinstance(net_obj, dict) and isinstance(net_obj.get("nodes"), dict):
        for nid, nd in net_obj["nodes"].items():
            q   = _norm_hue(nd.get("hue_state"))
            res = float(nd.get("resonance", 0.0) or 0.0)
            lnk = [str(l) for l in (nd.get("links") or [])]
            if q is None:
                continue
            nodes[str(nid)] = {"hue_state": q, "resonance": res, "links": lnk}
        if nodes:
            return nodes

    return {}


# ─────────────────────────────────────────────────────────────────
# ARC DETECTION
# ─────────────────────────────────────────────────────────────────

def _detect_arcs(nodes: dict, max_sample: int = 10) -> dict:
    """
    Detect all three routing arc types in the network.

    WHITE→GRAY:  superposition fires toward King's Chamber threshold
    GRAY→BLACK:  King's Chamber collapses to sealed memory
    BLACK→WHITE: sealed anchor asserts into superposition (Rule Zero)

    Also detects illegal arc types:
    GRAY→GRAY:   reflex deadlock — resonance pools without collapsing
    BLACK→GRAY:  sealed state re-entering threshold — wrong direction
    BLACK→BLACK: sealed states compounding each other — wrong
    """
    arcs = {
        "WHITE→GRAY":  [],
        "WHITE→WHITE": [],
        "GRAY→BLACK":  [],
        "GRAY→WHITE":  [],
        "BLACK→WHITE": [],
        # Illegal arc types
        "GRAY→GRAY":   [],
        "BLACK→GRAY":  [],
        "BLACK→BLACK": [],
    }

    for nid, nd in nodes.items():
        q_from = nd["hue_state"]
        q_name = HUE_INT_TO_STR.get(q_from, str(q_from))
        for lid in nd.get("links", []):
            target = nodes.get(lid)
            if not target:
                continue
            q_to   = target["hue_state"]
            q_to_n = HUE_INT_TO_STR.get(q_to, str(q_to))
            arc_key = f"{q_name}→{q_to_n}"

            entry = {
                "from":       nid,
                "from_q":     q_name,
                "to":         lid,
                "to_q":       q_to_n,
                "from_res":   round(nd["resonance"], 6),
                "to_res":     round(target["resonance"], 6),
                "self_link":  nid == lid,
            }
            if arc_key in arcs:
                arcs[arc_key].append(entry)

    # Sort each arc list by combined resonance descending, trim to sample
    def _sort_trim(lst):
        lst.sort(key=lambda x: x["from_res"] + x["to_res"], reverse=True)
        return lst[:max_sample]

    return {k: _sort_trim(v) for k, v in arcs.items()}


# ─────────────────────────────────────────────────────────────────
# SELF-LINK DETECTION
# ─────────────────────────────────────────────────────────────────

def _detect_self_links(nodes: dict) -> list:
    """Find any node that links to itself — these create routing deadlock."""
    return [
        {"token_id": nid, "hue_state": HUE_INT_TO_STR.get(nd["hue_state"])}
        for nid, nd in nodes.items()
        if nid in nd.get("links", [])
    ]


# ─────────────────────────────────────────────────────────────────
# EMITTER CLASSIFICATION
# ─────────────────────────────────────────────────────────────────

def _classify_emitters(nodes: dict) -> dict:
    """
    Classify emitter types.

    WHITE emitters: in superposition — fire outward to GRAY/WHITE neighbors
    BLACK emitters: sealed anchors — assert into WHITE (Rule Zero)
    GRAY reflexes:  King's Chamber — receive and route, don't initiate

    A node is classified as an active emitter if it has resonance AND
    has valid targets to route to.
    """
    white_emitters = []
    black_emitters = []
    gray_reflexes  = []

    for nid, nd in nodes.items():
        q   = nd["hue_state"]
        res = nd["resonance"]
        # Find what link types this node has
        link_q_counts = defaultdict(int)
        for lid in nd.get("links", []):
            t = nodes.get(lid)
            if t:
                tq = HUE_INT_TO_STR.get(t["hue_state"], "?")
                link_q_counts[tq] += 1

        if q == WHITE:
            white_emitters.append({
                "id": nid,
                "resonance": round(res, 6),
                "links_to_gray":  link_q_counts["GRAY"],
                "links_to_white": link_q_counts["WHITE"],
                "links_to_black": link_q_counts["BLACK"],
            })
        elif q == BLACK:
            # BLACK emitters are Rule Zero anchors — they assert to WHITE
            black_emitters.append({
                "id": nid,
                "resonance": round(res, 6),
                "rule_zero_targets": link_q_counts["WHITE"],  # what it can assert to
                "links_to_gray":     link_q_counts["GRAY"],   # wrong direction
                "links_to_black":    link_q_counts["BLACK"],  # wrong direction
            })
        elif q == GRAY:
            gray_reflexes.append({
                "id": nid,
                "resonance": round(res, 6),
                "routes_to_white": link_q_counts["WHITE"],
                "routes_to_black": link_q_counts["BLACK"],
                "routes_to_gray":  link_q_counts["GRAY"],   # should be 0
            })

    # Sort by resonance desc
    for lst in (white_emitters, black_emitters, gray_reflexes):
        lst.sort(key=lambda x: x["resonance"], reverse=True)

    return {
        "white_emitters": white_emitters,
        "black_emitters": black_emitters,
        "gray_reflexes":  gray_reflexes,
    }


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser("subconscious-dryrun")
    ap.add_argument(
        "--network",
        default=str(Path(__file__).parent.parent / "memory" / "subconscious_network.json"),
        help="path to subconscious network JSON"
    )
    ap.add_argument(
        "--sample", type=int, default=5,
        help="max arc samples to include per arc type"
    )
    ap.add_argument(
        "--v1-network",
        dest="v1_network",
        action="store_true",
        help="load from V1 qbithue_network path instead"
    )
    args = ap.parse_args(argv)

    if args.v1_network:
        net_path = Path("/home/comanderanch/ai-core/memory/qbithue_network.json")
    else:
        net_path = Path(args.network)

    net_raw = _load_json(net_path)
    if net_raw is None:
        return 2

    nodes = _normalize_network(net_raw)
    if not nodes:
        print(f"[ERR] {net_path}: not in recognized shape or no usable nodes.",
              file=sys.stderr)
        return 3

    # Counts
    n_black = sum(1 for nd in nodes.values() if nd["hue_state"] == BLACK)
    n_gray  = sum(1 for nd in nodes.values() if nd["hue_state"] == GRAY)
    n_white = sum(1 for nd in nodes.values() if nd["hue_state"] == WHITE)
    res_sum = sum(nd["resonance"] for nd in nodes.values())

    arcs        = _detect_arcs(nodes, max_sample=args.sample)
    self_links  = _detect_self_links(nodes)
    emitters    = _classify_emitters(nodes)

    # Build output
    out = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source":    str(net_path),
        "q_state_map": {
            "WHITE":  f"{WHITE}  = {Q_ROLES[WHITE]}",
            "GRAY":   f"{GRAY}   = {Q_ROLES[GRAY]}",
            "BLACK":  f"{BLACK} = {Q_ROLES[BLACK]}",
        },
        "counts": {
            "WHITE": n_white,
            "GRAY":  n_gray,
            "BLACK": n_black,
            "total": n_white + n_gray + n_black,
        },
        "resonance_sum": round(res_sum, 6),
        "arcs": {
            "correct": {
                "WHITE→GRAY":  {"count": len(arcs["WHITE→GRAY"]),  "sample": arcs["WHITE→GRAY"]},
                "WHITE→WHITE": {"count": len(arcs["WHITE→WHITE"]), "sample": arcs["WHITE→WHITE"]},
                "GRAY→WHITE":  {"count": len(arcs["GRAY→WHITE"]),  "sample": arcs["GRAY→WHITE"]},
                "GRAY→BLACK":  {"count": len(arcs["GRAY→BLACK"]),  "sample": arcs["GRAY→BLACK"]},
                "BLACK→WHITE": {
                    "count": len(arcs["BLACK→WHITE"]),
                    "sample": arcs["BLACK→WHITE"],
                    "note": "Rule Zero: sealed anchors asserting into superposition",
                },
            },
            "illegal": {
                "GRAY→GRAY": {
                    "count": len(arcs["GRAY→GRAY"]),
                    "sample": arcs["GRAY→GRAY"],
                    "note": "reflex deadlock — resonance pools without collapsing",
                },
                "BLACK→GRAY": {
                    "count": len(arcs["BLACK→GRAY"]),
                    "sample": arcs["BLACK→GRAY"],
                    "note": "wrong direction — sealed state should not re-enter threshold",
                },
                "BLACK→BLACK": {
                    "count": len(arcs["BLACK→BLACK"]),
                    "sample": arcs["BLACK→BLACK"],
                    "note": "wrong direction — sealed states should not compound",
                },
                "self_links": {
                    "count": len(self_links),
                    "nodes": self_links,
                    "note": "routing deadlock — a node routing to itself",
                },
            },
        },
        "emitters": emitters,
        "invariants": {
            "no_writes":              True,
            "no_field_modification":  True,
            "routing_direction":      "WHITE→GRAY→BLACK + BLACK→WHITE (Rule Zero)",
            "gray_gray_blocked":      len(arcs["GRAY→GRAY"]) == 0,
            "self_links_clean":       len(self_links) == 0,
            "black_emitters_present": len(emitters["black_emitters"]) > 0,
        },
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
