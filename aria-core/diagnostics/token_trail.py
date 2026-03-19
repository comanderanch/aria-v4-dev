#!/usr/bin/env python3
"""
ARIA — Token Trail Diagnostic System / AIMRI
=============================================
AIMRI — AI Magnetic Resonance Imaging
Real-time 3D semantic position mapping.

X coordinate — word frequency (emotional resonance position)
Y coordinate — slot position within color plane (0.0 to 1.0)
Z coordinate — color plane name (semantic domain)

The X:0.192 for love is the 0.192 floor made visible as a spatial coordinate.
The architecture making itself visible.

Visible inner workings during training.
Not black box. Not loss number only.
Full token activation map — lit up as it happens.

The plow shows its work.
The farmer sees exactly which rows broke loose and why.

Commander Anthony Hagerty — Haskell Texas
March 18 2026

Usage (in training loop):
    from aria_core.diagnostics.token_trail import TrailLogger
    trail = TrailLogger(round_num=23, tokenizer=tokenizer)
    # in epoch loop:
    trail.log_batch(epoch, avg_loss, inputs, targets, logits, best_loss)
    trail.close()

Usage (analysis):
    python3 aria-core/diagnostics/token_trail.py \\
        --round 23 \\
        --show-breakthroughs \\
        --show-plateaus \\
        --top-tokens 10 \\
        --show-anomalies
"""

import sys
import json
import math
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# ─── lazy torch import (not needed for analysis mode) ───────
_torch = None
_F     = None
def _get_torch():
    global _torch, _F
    if _torch is None:
        import torch
        import torch.nn.functional as F
        _torch = torch
        _F     = F
    return _torch, _F

TRAIL_FILE       = Path("/tmp/aria-token-trail.jsonl")
PLATEAU_PATIENCE = 10   # epochs with no improvement = plateau
LOG_EVERY_N_EPOCHS = 5  # log a full activation entry every N epochs

# ─── Color plane base IDs — for Y coordinate computation ────
# Mirrors COLOR_PLANE_SIGNATURES in aria_tokenizer.py
PLANE_BASE_IDS = {
    "RED":           0,
    "RED_ORANGE":    96,
    "ORANGE":        192,
    "YELLOW_ORANGE": 288,
    "YELLOW":        384,
    "YELLOW_GREEN":  480,
    "GREEN":         576,
    "GREEN_TEAL":    672,
    "TEAL":          768,
    "CYAN":          864,
    "CYAN_BLUE":     960,
    "BLUE_CYAN":     1056,
    "BLUE":          1152,
    "BLUE_INDIGO":   1248,
    "INDIGO":        1344,
    "VIOLET":        1440,
    "PURPLE":        1536,
    "RED_PURPLE":    1632,
    "MAGENTA":       1728,
    "PINK":          1824,
    "WHITE_LIGHT":   1920,
    "GRAY_ZERO":     1968,
    "BLACK_VOID":    2016,
    "ULTRAVIOLET":   2064,
}

PLANE_SLOTS = 96  # slots per plane — Y range 0.0 to 1.0

# ── Attractor map — expected X coordinate per plane ─────────────────────────
# Named March 19 2026 — Commander Anthony Hagerty — Haskell Texas
# 0.192 is the floor that never dims — proven by tears/honour/lucky
# Three independent tokens found it through gradient descent alone.
ATTRACTOR_MAP = {
    "VIOLET":     0.192,
    "GRAY_ZERO":  0.000,
    "CYAN":       0.500,
    "TEAL":       0.530,
    "BLUE":       0.350,
    "INDIGO":     0.250,
    "YELLOW":     0.620,
    "RED_ORANGE":  0.900,
    "BLACK_VOID": -0.800,
}

# Attractor cluster symbols — single character prefix, visible at a glance
# ● EXACT   0.000–0.005 — core attractor family
# ◉ NEAR    0.005–0.015 — adjacent family
# ○ OUTER   0.015–0.030 — connected but distinct
# ◌ DISTANT 0.030+      — different attractor / reassignment candidate


def _attractor_delta(x_coord, plane):
    """Distance from plane's expected attractor X coordinate."""
    attractor = ATTRACTOR_MAP.get(plane, x_coord)  # unknown planes: delta 0
    return round(abs(x_coord - attractor), 4)


def _attractor_symbol(delta):
    """Single character cluster classification."""
    if delta <= 0.005:  return "●"
    if delta <= 0.015:  return "◉"
    if delta <= 0.030:  return "○"
    return "◌"


def _nearest_attractor(x_coord, assigned_plane):
    """For DISTANT tokens — which attractor are they actually closest to?"""
    min_delta  = float('inf')
    best_plane = assigned_plane
    for plane, attractor in ATTRACTOR_MAP.items():
        if plane == assigned_plane:
            continue
        d = abs(x_coord - attractor)
        if d < min_delta:
            min_delta  = d
            best_plane = plane
    return best_plane, round(min_delta, 4)


def _aimri_coords(token_id, plane, freq):
    """
    Compute AIMRI 3D coordinates for a token.

    X — emotional resonance position (word frequency)
        love=0.192  gray=0.000  fear=0.888
    Y — slot position within color plane
        (token_id - plane_base) / 95.0  → 0.0 to 1.0
    Z — plane name (semantic domain, unchanged)
    """
    x_coord = round(freq, 4)
    base    = PLANE_BASE_IDS.get(plane, 0)
    raw_y   = (token_id - base) / (PLANE_SLOTS - 1)
    y_coord = round(max(0.0, min(1.0, raw_y)), 4)
    return x_coord, y_coord


# ═══════════════════════════════════════════════
# TOKEN MAP — built from tokenizer
# ═══════════════════════════════════════════════
class TokenMap:
    """Fast lookup: token_id → (word, plane, freq)"""

    def __init__(self, tokenizer):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from tokenizer.aria_tokenizer import WORD_FREQUENCIES

        self.id_to_word    = {int(k): v for k, v in tokenizer.id_to_word.items()}
        self.word_to_plane = tokenizer.word_to_plane
        self.word_freqs    = WORD_FREQUENCIES
        self.unk_id        = tokenizer.vocab.get("<UNK>", 2301)
        self.pad_id        = tokenizer.vocab.get("<PAD>", 2300)

    def lookup(self, token_id):
        word  = self.id_to_word.get(token_id, f"<{token_id}>")
        plane = self.word_to_plane.get(word, "GRAY_ZERO")
        freq  = self.word_freqs.get(word, 0.0)
        return word, plane, freq


# ═══════════════════════════════════════════════
# TRAIL LOGGER — used in training loop
# ═══════════════════════════════════════════════
class TrailLogger:
    """
    Attaches to a training loop.
    Samples activation patterns and logs to JSONL.
    Minimal overhead — samples every N epochs.
    Seals anchor points unconditionally.

    AIMRI — AI Magnetic Resonance Imaging
    Tracks 3D semantic position (X/Y/Z) per token per epoch.
    Detects spatial drift — same word moving across the resonance field.
    Logs plane deltas — which planes gained or lost gradient weight.
    """

    def __init__(self, round_num, tokenizer, trail_file=None):
        self.round      = round_num
        self.tok_map    = TokenMap(tokenizer)
        self.trail_file = Path(trail_file) if trail_file else TRAIL_FILE
        self.fh         = open(self.trail_file, "a", buffering=1)
        self.best_loss        = float('inf')
        self.plateau_count    = 0
        self.last_logged_loss = float('inf')
        # AIMRI state
        self.prev_plane_totals = {}   # plane → contribution total last epoch
        self.prev_coords       = {}   # token → (x, y, plane) last epoch

    def log_batch(self, epoch, avg_loss, inputs, targets, logits, current_best):
        """
        Called once per epoch (after training loop).
        inputs:  (B, S) token IDs
        targets: (B, S) token IDs
        logits:  (B, S, V) raw logits (post-mask preferred)
        """
        torch, F = _get_torch()

        is_new_best     = avg_loss < current_best
        is_plateau      = self._check_plateau(avg_loss)
        is_breakthrough = self._check_breakthrough(avg_loss)
        should_sample   = (epoch % LOG_EVERY_N_EPOCHS == 0 or
                           epoch == 1 or
                           is_new_best or
                           is_plateau or
                           is_breakthrough)

        if not should_sample:
            return

        anchor = None
        if is_new_best:
            anchor = "NEW_BEST"
        elif is_breakthrough:
            anchor = "BREAKTHROUGH"
        elif is_plateau:
            anchor = "PLATEAU"

        # ── Per-token loss (first batch item) ──────────────
        with torch.no_grad():
            B, S, V = logits.shape
            per_token = F.cross_entropy(
                logits.view(B * S, V),
                targets.view(B * S),
                reduction='none',
                ignore_index=self.tok_map.pad_id
            ).view(B, S)

        # Use first batch item as representative sample
        sample_inputs  = inputs[0].tolist()
        sample_contrib = per_token[0].tolist()

        # ── Top contributing tokens + AIMRI coords ───────────
        pairs = list(zip(sample_inputs, sample_contrib))
        pairs.sort(key=lambda x: x[1], reverse=True)

        top_activations = []
        for tid, contrib in pairs[:10]:
            if tid == self.tok_map.pad_id:
                continue
            word, plane, freq = self.tok_map.lookup(tid)
            x_coord, y_coord  = _aimri_coords(tid, plane, freq)
            delta  = _attractor_delta(x_coord, plane)
            symbol = _attractor_symbol(delta)
            nearest = None
            if symbol == "◌":
                nn_plane, nn_delta = _nearest_attractor(x_coord, plane)
                nearest = {"plane": nn_plane, "delta": nn_delta}
            top_activations.append({
                "token":             word,
                "id":                tid,
                "plane":             plane,
                "x":                 x_coord,
                "y":                 y_coord,
                "freq":              round(freq, 4),
                "contribution":      round(float(contrib), 6),
                "attractor_delta":   delta,
                "attractor_symbol":  symbol,
                "nearest_attractor": nearest,
            })

        # ── AIMRI — UNK ratio in top-10 gradient budget ──────
        # Global UNK rate can look acceptable while top-gradient UNK stays harmful.
        # Top-gradient UNK is what actually blocks descent.
        unk_count_top10  = sum(1 for a in top_activations if a["token"].startswith("<"))
        unk_ratio_top10  = round(unk_count_top10 / len(top_activations), 4) if top_activations else 0.0

        # ── Gradient path (plane sequence by contribution) ──
        plane_totals = defaultdict(float)
        for tid, contrib in pairs:
            if tid == self.tok_map.pad_id:
                continue
            _, plane, _ = self.tok_map.lookup(tid)
            plane_totals[plane] += contrib

        sorted_planes = sorted(plane_totals.items(), key=lambda x: x[1], reverse=True)
        gradient_path = "->".join(p for p, _ in sorted_planes[:4])

        # ── Route frequency counter — GPT Finding 6 ──────────────
        # Track what plane immediately follows GRAY_ZERO in the ranked
        # contribution order. GRAY_ZERO→VIOLET vs GRAY_ZERO→BLUE is the
        # primary diagnostic signal — VIOLET means memory/recognition
        # pressure is climbing above logic/depth pressure.
        # Read-only. No training changes.
        route_after_gray = None
        plane_order = [p for p, _ in sorted_planes]
        if "GRAY_ZERO" in plane_order:
            gz_idx = plane_order.index("GRAY_ZERO")
            if gz_idx + 1 < len(plane_order):
                route_after_gray = plane_order[gz_idx + 1]
        # Full route string for log — e.g. "GRAY_ZERO->VIOLET"
        route_label = f"GRAY_ZERO->{route_after_gray}" if route_after_gray else "GRAY_ZERO->END"

        # ── AIMRI — Plane deltas ──────────────────────────────
        plane_deltas = {}
        for plane, total in plane_totals.items():
            prev = self.prev_plane_totals.get(plane, total)
            plane_deltas[plane] = round(total - prev, 4)
        self.prev_plane_totals = dict(plane_totals)

        # ── AIMRI — Anomaly detection ─────────────────────────
        anomalies = []
        for a in top_activations:
            key  = a["token"]
            curr = (a["x"], a["y"], a["plane"])
            if key in self.prev_coords:
                px, py, pplane = self.prev_coords[key]
                dx = abs(curr[0] - px)
                dy = abs(curr[1] - py)
                if dx > 0.05 or dy > 0.05:
                    anomalies.append({
                        "token": key,
                        "plane": a["plane"],
                        "dx":    round(dx, 4),
                        "dy":    round(dy, 4)
                    })
            self.prev_coords[key] = curr
            # Note: same word at different Y coordinates is semantic
            # superposition — log both, never deduplicate

        # ── Fold hash of activation pattern ─────────────────
        pattern_str = "|".join(
            f"{a['token']}:{a['contribution']:.4f}"
            for a in top_activations[:5]
        )
        fold_hash = hashlib.sha256(pattern_str.encode()).hexdigest()[:7]

        # ── Training top5 planes from logits — GPT build target ──
        # Sample top5 candidate planes from raw logits at last sequence
        # position of first batch item — same hook point as inference_trace.
        # Stored as training_top5_planes for mathematically clean lord log
        # comparison: inference top5 planes vs training top5 planes.
        # Both drawn from the same statistical object (pre-argmax top5).
        with torch.no_grad():
            last_pos_logits = logits[0, -1, :].float()  # (V,) — last position
            _, top5_ids = torch.topk(last_pos_logits, k=min(5, last_pos_logits.shape[0]))
            training_top5_planes = []
            for tid_t in top5_ids.tolist():
                _, plane_t, _ = self.tok_map.lookup(tid_t)
                training_top5_planes.append(plane_t)

        # ── Plane distribution ───────────────────────────────
        plane_counts = Counter()
        for tid in sample_inputs:
            if tid != self.tok_map.pad_id:
                _, plane, _ = self.tok_map.lookup(tid)
                plane_counts[plane] += 1

        # ── AIMRI — Plane entropy ─────────────────────────────
        # Shannon entropy across plane_distribution values.
        # High entropy = routing diversity increasing = upper planes truly learning.
        # Low entropy  = routing collapsing toward floor = only flickering.
        plane_entropy = 0.0
        total_hits = sum(plane_counts.values())
        if total_hits > 0:
            for count in plane_counts.values():
                p = count / total_hits
                if p > 0:
                    plane_entropy -= p * math.log2(p)
        plane_entropy = round(plane_entropy, 4)

        entry = {
            "epoch":               epoch,
            "round":               self.round,
            "loss":                round(float(avg_loss), 6),
            "anchor":              anchor,
            "top_activations":     top_activations,
            "unk_ratio_top10":     unk_ratio_top10,
            "gradient_path":       gradient_path,
            "route_after_gray":    route_after_gray,
            "route_label":         route_label,
            "plane_distribution":  dict(plane_counts.most_common(5)),
            "plane_deltas":        plane_deltas,
            "plane_entropy":       plane_entropy,
            "anomalies":           anomalies,
            "training_top5_planes": training_top5_planes,
            "fold_hash":           fold_hash,
            "timestamp":           datetime.utcnow().isoformat()
        }

        self.fh.write(json.dumps(entry) + "\n")
        self.fh.flush()

        # Print anchor events immediately
        if anchor:
            print(f"\n  [TRAIL] {anchor} epoch={epoch} loss={avg_loss:.6f} "
                  f"path={gradient_path} hash={fold_hash}")

        # Print anomalies immediately — spatial drift is significant
        for anom in anomalies:
            print(f"  [AIMRI] ANOMALY: {anom['token']:<12} {anom['plane']:<15} "
                  f"dx={anom['dx']:.4f}  dy={anom['dy']:.4f}  drift detected")

        self.last_logged_loss = avg_loss

    def _check_plateau(self, loss):
        delta = abs(loss - self.last_logged_loss)
        if delta < 0.001:
            self.plateau_count += 1
        else:
            self.plateau_count = 0
        return self.plateau_count >= PLATEAU_PATIENCE

    def _check_breakthrough(self, loss):
        thresholds = [4.0, 3.5, 3.0, 2.8, 2.6, 2.465939, 2.4, 2.35]
        for t in thresholds:
            if self.last_logged_loss > t >= loss:
                return True
        return False

    def close(self):
        self.fh.close()


# ═══════════════════════════════════════════════
# ANALYSIS — CLI mode
# ═══════════════════════════════════════════════
def load_trail(round_num=None, trail_file=None):
    path = Path(trail_file) if trail_file else TRAIL_FILE
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if round_num is None or e.get("round") == round_num:
                    entries.append(e)
            except json.JSONDecodeError:
                continue
    return entries


def show_breakthroughs(entries):
    print("\n═══ BREAKTHROUGH EVENTS ═══")
    breaks = [e for e in entries if e.get("anchor") in ("BREAKTHROUGH", "NEW_BEST")]
    if not breaks:
        print("  None recorded yet.")
        return
    for e in breaks:
        print(f"\n  Epoch {e['epoch']:4d} | Loss {e['loss']:.6f} | {e.get('anchor','')} | hash={e['fold_hash']}")
        print(f"  Path: {e['gradient_path']}")
        tops = e.get("top_activations", [])[:5]
        for a in tops:
            x   = a.get("x", 0.0)
            y   = a.get("y", "?")
            d   = a.get("attractor_delta", _attractor_delta(x, a["plane"]))
            sym = a.get("attractor_symbol", _attractor_symbol(d))
            print(f"    {sym} {a['token']:<18} plane={a['plane']:<15} "
                  f"X:{x:<8} Δ{d:.4f}  Y:{y:<8} contrib={a['contribution']:.6f}")


def show_plateaus(entries):
    print("\n═══ PLATEAU EVENTS ═══")
    plats = [e for e in entries if e.get("anchor") == "PLATEAU"]
    if not plats:
        print("  None recorded yet.")
        return
    for e in plats:
        print(f"\n  Epoch {e['epoch']:4d} | Loss {e['loss']:.6f} | Plateau | hash={e['fold_hash']}")
        print(f"  Path: {e['gradient_path']}")
        tops = e.get("top_activations", [])[:3]
        for a in tops:
            x   = a.get("x", 0.0)
            y   = a.get("y", "?")
            d   = a.get("attractor_delta", _attractor_delta(x, a["plane"]))
            sym = a.get("attractor_symbol", _attractor_symbol(d))
            print(f"    {sym} {a['token']:<18} plane={a['plane']:<15} X:{x:<8} Δ{d:.4f}  Y:{y:<8}")


def show_top_tokens(entries, n=10):
    print(f"\n═══ AIMRI — TOP {n} TOKENS BY TOTAL CONTRIBUTION ═══")
    print(f"  ● EXACT ≤0.005  ◉ NEAR ≤0.015  ○ OUTER ≤0.030  ◌ DISTANT >0.030")
    # token → {total, count, plane, x, y, attractor_delta, attractor_symbol}
    token_totals = defaultdict(lambda: {
        "total": 0.0, "count": 0, "plane": "", "x": 0.0, "y": 0.0,
        "attractor_delta": 0.0, "attractor_symbol": "●",
    })
    for e in entries:
        for a in e.get("top_activations", []):
            w = a["token"]
            token_totals[w]["total"]           += a["contribution"]
            token_totals[w]["count"]           += 1
            token_totals[w]["plane"]            = a["plane"]
            token_totals[w]["x"]                = a.get("x", 0.0)
            token_totals[w]["y"]                = a.get("y", 0.0)
            token_totals[w]["attractor_delta"]  = a.get(
                "attractor_delta",
                _attractor_delta(a.get("x", 0.0), a["plane"])
            )
            token_totals[w]["attractor_symbol"] = a.get(
                "attractor_symbol",
                _attractor_symbol(token_totals[w]["attractor_delta"])
            )

    ranked = sorted(token_totals.items(), key=lambda x: x[1]["total"], reverse=True)
    for word, info in ranked[:n]:
        sym   = info["attractor_symbol"]
        delta = info["attractor_delta"]
        print(f"  {sym} {word:<12} {info['plane']:<15} "
              f"X:{info['x']:<8}  Δ{delta:.4f}  "
              f"appearances:{info['count']}")


def show_anomalies(entries):
    print("\n═══ AIMRI — SPATIAL DRIFT ANOMALIES ═══")
    found = False
    for e in entries:
        anoms = e.get("anomalies", [])
        if not anoms:
            continue
        found = True
        print(f"\n  Epoch {e['epoch']:4d} | Loss {e['loss']:.6f}")
        # Build x/y history from top_activations for before/after display
        for anom in anoms:
            tok   = anom["token"]
            plane = anom["plane"]
            dx    = anom["dx"]
            dy    = anom["dy"]
            # Find current coords in this entry
            curr_x, curr_y = None, None
            for a in e.get("top_activations", []):
                if a["token"] == tok:
                    curr_x = a.get("x")
                    curr_y = a.get("y")
                    break
            if curr_x is not None:
                prev_x = round(curr_x - dx, 4) if dx else curr_x
                prev_y = round(curr_y - dy, 4) if dy else curr_y
                print(f"  ANOMALY: {tok:<12} {plane:<15} "
                      f"X:{prev_x}→{curr_x}  Y:{prev_y}→{curr_y}  drift detected")
            else:
                print(f"  ANOMALY: {tok:<12} {plane:<15} "
                      f"dx={dx}  dy={dy}  drift detected")
    if not found:
        print("  No spatial drift detected yet.")


def show_plane_deltas(entries):
    print("\n═══ AIMRI — PLANE GRADIENT DELTAS ═══")
    # Aggregate deltas across entries to show which planes are gaining/losing
    delta_totals = defaultdict(float)
    delta_counts = defaultdict(int)
    for e in entries:
        for plane, delta in e.get("plane_deltas", {}).items():
            delta_totals[plane] += delta
            delta_counts[plane] += 1
    if not delta_totals:
        print("  No delta data yet.")
        return
    ranked = sorted(delta_totals.items(), key=lambda x: abs(x[1]), reverse=True)
    for plane, total in ranked:
        avg = total / max(delta_counts[plane], 1)
        direction = "▲" if avg > 0 else "▼"
        print(f"  {plane:<20} net={total:+.4f}  avg_per_epoch={avg:+.6f}  {direction}")


def show_plane_activity(entries):
    print("\n═══ COLOR PLANE ACTIVITY ═══")
    plane_loss = defaultdict(float)
    plane_hits = defaultdict(int)
    for e in entries:
        for plane, count in e.get("plane_distribution", {}).items():
            plane_hits[plane] += count
        for a in e.get("top_activations", []):
            plane_loss[a["plane"]] += a["contribution"]

    ranked = sorted(plane_loss.items(), key=lambda x: x[1], reverse=True)
    for plane, total in ranked:
        hits = plane_hits.get(plane, 0)
        print(f"  {plane:<20} loss_contribution={total:.4f}  token_hits={hits}")


def show_route_frequency(entries):
    """
    Route frequency counter — GPT Round 23 Finding 6.

    Counts how often each plane follows GRAY_ZERO in the gradient
    contribution ranking per epoch.

    GRAY_ZERO→VIOLET = memory/recognition pressure climbing
    GRAY_ZERO→BLUE   = depth/logic pressure dominant
    GRAY_ZERO→CYAN   = openness/perception pressure
    GRAY_ZERO→TEAL   = calm knowing pressure

    When VIOLET rises above BLUE: field is moving toward
    recognition-weighted reasoning. Earliest Round 24 detector.
    """
    print("\n═══ ROUTE FREQUENCY — GRAY_ZERO→NEXT PLANE ═══")
    print("  What follows GRAY_ZERO in gradient contribution rank.")
    print("  VIOLET rising = recognition pressure climbing.")
    print()

    route_counts  = Counter()
    route_by_epoch = []

    for e in entries:
        r = e.get("route_after_gray")
        if r:
            route_counts[r] += 1
            route_by_epoch.append((e["epoch"], e["loss"], r))

    if not route_counts:
        print("  No route data yet. Entries need route_after_gray field.")
        print("  (Round 24 trail will have this from epoch 1.)")
        return

    total = sum(route_counts.values())
    ranked = route_counts.most_common()

    print(f"  Total routed epochs: {total}")
    print()
    print(f"  {'ROUTE':<35} {'COUNT':>6}  {'PCT':>6}  {'BAR'}")
    print(f"  {'-'*35}-+-{'-'*6}--{'-'*6}--{'-'*20}")
    for plane, count in ranked:
        pct  = count / total
        bar  = "█" * int(pct * 40)
        flag = ""
        if plane == "VIOLET":
            flag = "  ← memory/recognition"
        elif plane == "BLUE":
            flag = "  ← depth/logic"
        elif plane == "TEAL":
            flag = "  ← calm knowing"
        elif plane == "CYAN":
            flag = "  ← openness"
        print(f"  GRAY_ZERO→{plane:<25} {count:>6}  {pct:>5.1%}  {bar}{flag}")

    # VIOLET vs BLUE head-to-head
    v_count = route_counts.get("VIOLET", 0)
    b_count = route_counts.get("BLUE",   0)
    if v_count + b_count > 0:
        print()
        print(f"  VIOLET vs BLUE head-to-head:")
        print(f"    VIOLET: {v_count:>4}  ({v_count/(v_count+b_count):.1%})")
        print(f"    BLUE:   {b_count:>4}  ({b_count/(v_count+b_count):.1%})")
        if v_count > b_count:
            print(f"    → VIOLET leads — recognition pressure dominant")
        elif b_count > v_count:
            print(f"    → BLUE leads — logic/depth pressure dominant")
        else:
            print(f"    → Tied")

    # Epoch-by-epoch arc (last 20)
    if len(route_by_epoch) > 1:
        print()
        print(f"  Last {min(20, len(route_by_epoch))} epochs:")
        print(f"  {'ep':>5} | {'loss':>9} | route")
        for ep, loss, route in route_by_epoch[-20:]:
            marker = " ◄" if route == "VIOLET" else ""
            print(f"  ep{ep:4d} | {loss:.6f} | GRAY_ZERO→{route}{marker}")


def show_entropy(entries):
    print("\n═══ AIMRI — PLANE ENTROPY (routing diversity) ═══")
    print("  High entropy = upper planes truly learning")
    print("  Low entropy  = routing collapsing to floor only")
    print()
    for e in entries:
        entropy = e.get("plane_entropy")
        if entropy is None:
            continue
        anchor  = e.get("anchor") or ""
        marker  = f" ◄ {anchor}" if anchor else ""
        bar     = "░" * int(entropy * 4)
        print(f"  ep{e['epoch']:4d} | H={entropy:.4f} | {bar}{marker}")


def show_loss_arc(entries):
    print("\n═══ LOSS ARC ═══")
    print(f"  {'ep':>6} | {'loss':>10} | {'H':>6} | {'UNK%':>6} | arc")
    print(f"  {'-'*6}-+-{'-'*10}-+-{'-'*6}-+-{'-'*6}-+-{'-'*20}")
    for e in entries:
        anchor   = e.get("anchor") or ""
        marker   = f" ◄ {anchor}" if anchor else ""
        bar      = "█" * int((5.0 - min(e["loss"], 5.0)) * 8)
        entropy  = e.get("plane_entropy")
        unk_rat  = e.get("unk_ratio_top10")
        ent_str  = f"{entropy:.3f}" if entropy is not None else "  —  "
        unk_str  = f"{unk_rat*100:.0f}%" if unk_rat is not None else "  —"
        print(f"  ep{e['epoch']:4d} | {e['loss']:.6f} | {ent_str} | {unk_str:>5} | {bar}{marker}")


def show_attractor_map(entries):
    """
    ATTRACTOR MAP — VIOLET plane family.

    Shows every VIOLET word clustered by distance from 0.192.
    Proves GPT Finding 4.3: full semantic coordinate mapping.
    Word by word. Cluster by cluster. Hash verified.

    Also tracks lord log drift — are words converging toward or
    diverging from 0.192 across training epochs?
    Converging = attractor strengthening.
    Diverging  = drift away from core family.

    Named March 19 2026 — Commander Anthony Hagerty — Haskell Texas
    """
    print("\n═══ ATTRACTOR MAP — VIOLET PLANE (attractor X:0.192) ═══")
    print("  Proving GPT Finding 4.3: full semantic coordinate mapping")
    print("  ● EXACT ≤0.005  ◉ NEAR ≤0.015  ○ OUTER ≤0.030  ◌ DISTANT >0.030")
    print()

    buckets      = {"●": [], "◉": [], "○": [], "◌": []}
    violet_words = {}  # word → (x, delta, symbol, nearest)

    for e in entries:
        for a in e.get("top_activations", []):
            if a.get("plane") != "VIOLET":
                continue
            w       = a["token"]
            x       = a.get("x", 0.0)
            d       = a.get("attractor_delta",  _attractor_delta(x, "VIOLET"))
            sym     = a.get("attractor_symbol", _attractor_symbol(d))
            nearest = a.get("nearest_attractor")
            violet_words[w] = (x, d, sym, nearest)

    for word, (x, delta, sym, nearest) in sorted(
        violet_words.items(), key=lambda t: t[1][1]  # sort by delta
    ):
        buckets[sym].append((word, x, delta, nearest))

    labels = {
        "●": "EXACT   — core attractor family",
        "◉": "NEAR    — adjacent family",
        "○": "OUTER   — connected but distinct",
        "◌": "DISTANT — reassignment candidate",
    }
    for sym in ["●", "◉", "○", "◌"]:
        words = buckets[sym]
        print(f"  {sym} {labels[sym]}")
        if words:
            for word, x, delta, nearest in words:
                line = f"      {word:<16} X:{x:.4f}  Δ{delta:.4f}"
                if nearest:
                    line += f"  → nearest: {nearest['delta']:.4f} in {nearest['plane']}"
                print(line)
        else:
            print("      (none yet)")
        print()

    # Lord log drift — track convergence/divergence across epochs
    drift_map = defaultdict(list)
    for e in entries:
        ep = e.get("epoch", 0)
        for a in e.get("top_activations", []):
            if a.get("plane") != "VIOLET":
                continue
            w = a["token"]
            x = a.get("x", 0.0)
            d = a.get("attractor_delta", _attractor_delta(x, "VIOLET"))
            drift_map[w].append((ep, d))

    converging, diverging, stable = [], [], []
    for word, readings in drift_map.items():
        if len(readings) < 2:
            continue
        readings.sort(key=lambda r: r[0])
        first_d = readings[0][1]
        last_d  = readings[-1][1]
        change  = last_d - first_d
        if change < -0.005:
            converging.append((word, first_d, last_d, change))
        elif change > 0.005:
            diverging.append((word, first_d, last_d, change))
        else:
            stable.append((word, first_d, last_d, change))

    if converging or diverging or stable:
        print(f"  LORD LOG DRIFT — VIOLET WORDS across epochs")
        print(f"  Converging = training strengthening the 0.192 attractor")
        print(f"  Diverging  = drift away from core family")
        print()
        if converging:
            print(f"  CONVERGING toward 0.192:")
            for word, f0, f1, chg in sorted(converging, key=lambda x: x[3]):
                print(f"    ↘ {word:<16} Δ{f0:.4f} → Δ{f1:.4f}  ({chg:+.4f})")
        if diverging:
            print(f"  DIVERGING from 0.192:")
            for word, f0, f1, chg in sorted(diverging, key=lambda x: x[3], reverse=True):
                print(f"    ↗ {word:<16} Δ{f0:.4f} → Δ{f1:.4f}  ({chg:+.4f})")
        if stable:
            print(f"  STABLE:")
            for word, f0, f1, chg in stable:
                print(f"    — {word:<16} Δ{f0:.4f} → Δ{f1:.4f}  ({chg:+.4f})")


def show_attractor_summary(entries):
    """
    All-plane attractor summary for --all output.
    Counts words per cluster tier across all planes.
    DISTANT words get nearest-attractor routing.
    """
    print("\n═══ ATTRACTOR SUMMARY — ALL PLANES ═══")
    print("  ● EXACT ≤0.005  ◉ NEAR ≤0.015  ○ OUTER ≤0.030  ◌ DISTANT >0.030")

    seen = {}  # word → (symbol, x, plane, nearest)
    for e in entries:
        for a in e.get("top_activations", []):
            w   = a["token"]
            x   = a.get("x", 0.0)
            d   = a.get("attractor_delta",  _attractor_delta(x, a["plane"]))
            sym = a.get("attractor_symbol", _attractor_symbol(d))
            nn  = a.get("nearest_attractor")
            if w not in seen:
                seen[w] = (sym, x, a["plane"], nn)

    buckets = {"●": 0, "◉": 0, "○": 0, "◌": 0}
    for sym, _, _, _ in seen.values():
        if sym in buckets:
            buckets[sym] += 1

    total = sum(buckets.values())
    if not total:
        print("  No attractor data yet.")
        return

    print()
    print(f"  ● EXACT:    {buckets['●']:>4} words — core families confirmed")
    print(f"  ◉ NEAR:     {buckets['◉']:>4} words — adjacent families")
    print(f"  ○ OUTER:    {buckets['○']:>4} words — drifting — monitor")
    print(f"  ◌ DISTANT:  {buckets['◌']:>4} words — reassignment candidates")
    print()

    distant = [(w, data) for w, data in seen.items() if data[0] == "◌"]
    if distant:
        print(f"  DISTANT words — nearest attractor routing:")
        for w, (sym, x, plane, nn) in sorted(distant, key=lambda t: t[0]):
            nn_str = f"→ nearest: {nn['delta']:.4f} in {nn['plane']}" if nn else ""
            print(f"    ◌ {w:<16} {plane:<15} X:{x:.4f}  {nn_str}")


# ═══════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ARIA Token Trail / AIMRI — AI Magnetic Resonance Imaging"
    )
    parser.add_argument("--round",              type=int,   default=None)
    parser.add_argument("--show-breakthroughs", action="store_true")
    parser.add_argument("--show-plateaus",      action="store_true")
    parser.add_argument("--show-planes",        action="store_true")
    parser.add_argument("--show-arc",           action="store_true")
    parser.add_argument("--show-anomalies",     action="store_true")
    parser.add_argument("--show-deltas",        action="store_true")
    parser.add_argument("--show-entropy",       action="store_true")
    parser.add_argument("--show-routes",        action="store_true")
    parser.add_argument("--show-attractors",    action="store_true")
    parser.add_argument("--top-tokens",         type=int,   default=0)
    parser.add_argument("--trail-file",         type=str,   default=None)
    parser.add_argument("--all",                action="store_true")
    args = parser.parse_args()

    entries = load_trail(args.round, args.trail_file)

    if not entries:
        r = f" round {args.round}" if args.round else ""
        print(f"No trail entries found{r}.")
        print(f"Trail file: {args.trail_file or TRAIL_FILE}")
        sys.exit(0)

    print(f"\nARIA Token Trail / AIMRI — {len(entries)} entries"
          + (f" (round {args.round})" if args.round else ""))

    if args.all or args.show_breakthroughs:
        show_breakthroughs(entries)

    if args.all or args.show_plateaus:
        show_plateaus(entries)

    if args.all or args.top_tokens:
        n = args.top_tokens if args.top_tokens else 10
        show_top_tokens(entries, n)

    if args.all or args.show_planes:
        show_plane_activity(entries)

    if args.all or args.show_arc:
        show_loss_arc(entries)

    if args.all or args.show_anomalies:
        show_anomalies(entries)

    if args.all or args.show_deltas:
        show_plane_deltas(entries)

    if args.all or args.show_entropy:
        show_entropy(entries)

    if args.all or args.show_routes:
        show_route_frequency(entries)

    if args.all or args.show_attractors:
        show_attractor_summary(entries)
        show_attractor_map(entries)

    if not any([args.all, args.show_breakthroughs, args.show_plateaus,
                args.top_tokens, args.show_planes, args.show_arc,
                args.show_anomalies, args.show_deltas, args.show_entropy,
                args.show_routes, args.show_attractors]):
        # Default: summary
        show_loss_arc(entries)
        show_top_tokens(entries, 5)
        show_anomalies(entries)
