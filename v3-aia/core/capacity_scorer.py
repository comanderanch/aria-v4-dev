#!/usr/bin/env python3
"""
AI-Core V3: Capacity Scorer
============================

Dimensional capacity scoring between the 82D foundation
and the 498D top-layer workers.

Problem this solves:
  CognitiveEntropy re-balances when weight variance > threshold.
  But it does not know WHICH DIMENSIONS are being exercised.
  A worker can fire with high activation and still leave large
  regions of the 498D vector space completely dark.

  This scorer reads the EM field activation per worker and maps
  it through the dimensional layer structure:

    base_82   (dims   0–81)  — fluorescent physics — the foundation
    grid_250  (dims  82–331) — GridBloc spatial reasoning
    quantum_166 (dims 332–497) — Quadrademini superposition

  Each worker has a dimensional affinity to these layers based on
  its color physics (physical waves → base, abstract structure →
  grid/quantum).

Three scores per cycle:

  WORKER_LOAD
    Per-worker load fraction:
    activation × (palette_span / 2304)
    How much of the palette is this worker actively covering.

  DIM_LOAD
    Per-layer dimensional pressure:
    Sum of worker loads weighted by layer affinity.
    Shows which dimensional layer is being exercised.

  FOUNDATION_CONGRUENCE
    base_82 load fraction of total dim load.
    Low congruence = abstract layers firing without foundation.
    The 82D base must not be starved while grid/quantum run hot.

One output: entropy_modifier
  Returned to CognitiveEntropy — adjusts entropy_threshold.
  - HHI high (one worker dominates) → tighten threshold
  - DIM coverage unbalanced → tighten threshold
  - Foundation underloaded → flag_congruence_break = True
  - Well distributed, congruent → relax threshold slightly

Connection to 82D foundation (minimal_llm.py):
  The 82D MinimalLLM was trained on color token vectors.
  It operates entirely in base_82 space.
  If capacity_scorer shows base_82 < CONGRUENCE_FLOOR,
  the foundation is not load-bearing — the upper layers
  are operating without grounding.
  This is the structural equivalent of Rule Zero:
  The fact (physics, color, frequency) must underpin the prediction.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

# ─────────────────────────────────────────────────────────────────
# PALETTE SPANS — from PLANE_LAYOUT in v3_text_encoder.py (sealed)
# (start, end_inclusive, span)
# ─────────────────────────────────────────────────────────────────

PALETTE_SIZE = 2304

WORKER_PALETTE = {
    "emotion_001":   (0,    255,  256),
    "curiosity_001": (256,  447,  192),
    "ethics_001":    (640,  1087, 448),
    "language_001":  (1344, 1727, 384),
    "memory_001":    (1728, 2111, 384),
}

# Bridge/consensus domains — not primary workers
# Included so field snapshots with these keys don't cause errors
BRIDGE_DOMAINS = [
    "bridge_synthesis",
    "bridge_connection",
    "bridge_transition",
]

# ─────────────────────────────────────────────────────────────────
# DIMENSIONAL LAYERS — from MinimalLLM498D docstring (sealed)
# 82D fluorescent + 250D GridBloc + 166D Quadrademini = 498D
# ─────────────────────────────────────────────────────────────────

DIM_LAYERS = {
    "base_82":      (0,   81,  82),
    "grid_250":     (82,  331, 250),
    "quantum_166":  (332, 497, 166),
}

TOTAL_498D = 498

# ─────────────────────────────────────────────────────────────────
# WORKER → DIMENSIONAL AFFINITY
# Each worker primarily exercises different dimensional layers.
# Based on the physics of their color plane:
#   Red/Orange = physical wave phenomena  → heavy base_82
#   Green      = relational/structural    → base + grid
#   Blue       = language/logic/abstract  → grid + quantum
#   Violet     = memory/temporal          → quantum dominant
#
# Affinities sum to 1.0 per worker.
# ─────────────────────────────────────────────────────────────────

WORKER_DIM_AFFINITY = {
    # worker: {base_82, grid_250, quantum_166}
    "emotion_001":   {"base_82": 0.70, "grid_250": 0.20, "quantum_166": 0.10},
    "curiosity_001": {"base_82": 0.50, "grid_250": 0.40, "quantum_166": 0.10},
    "ethics_001":    {"base_82": 0.30, "grid_250": 0.50, "quantum_166": 0.20},
    "language_001":  {"base_82": 0.10, "grid_250": 0.50, "quantum_166": 0.40},
    "memory_001":    {"base_82": 0.10, "grid_250": 0.40, "quantum_166": 0.50},
}

# ─────────────────────────────────────────────────────────────────
# THRESHOLDS
# ─────────────────────────────────────────────────────────────────

HHI_CONCENTRATED   = 0.60   # HHI above this → one worker dominates
HHI_BALANCED       = 0.25   # HHI below this → well distributed
CONGRUENCE_FLOOR   = 0.15   # base_82 load below this → foundation underloaded
DIM_SKEW_MAX       = 0.65   # any single dim layer above this fraction → imbalanced

# Entropy threshold modifier bounds
MOD_MIN = -0.05
MOD_MAX = +0.03


class CapacityScorer:
    """
    Dimensional capacity scorer.

    Reads EM field state → produces capacity scores → entropy modifier.

    Usage:
        scorer  = CapacityScorer()
        entropy = CognitiveEntropy()

        field_state = em_bridge.process(text)
        report      = scorer.score(field_state["domains"])

        # Apply modifier
        entropy.entropy_threshold = scorer.apply_modifier(
            entropy.entropy_threshold, report
        )
    """

    def __init__(self):
        self._history: list = []   # last N reports

    # ──────────────────────────────────────────────────────────────
    # MAIN ENTRY
    # ──────────────────────────────────────────────────────────────

    def score(self, field_domains: dict) -> dict:
        """
        Score dimensional capacity from live EM field state.

        Args:
            field_domains: dict keyed by worker name, each with
                           at minimum {"activation": float}
                           (the dict returned by V3EMBridge._field_snapshot)

        Returns:
            Full capacity report dict.
        """
        # ── 1. Worker load ────────────────────────────────────────
        worker_load = self._compute_worker_load(field_domains)

        # ── 2. Dimensional load ───────────────────────────────────
        dim_load = self._compute_dim_load(worker_load)

        # ── 3. HHI concentration ─────────────────────────────────
        hhi = self._compute_hhi(worker_load)

        # ── 4. Foundation congruence ─────────────────────────────
        congruence = self._compute_congruence(dim_load)

        # ── 5. Flags ─────────────────────────────────────────────
        flags = self._compute_flags(hhi, dim_load, congruence)

        # ── 6. Entropy modifier ───────────────────────────────────
        modifier = self._compute_modifier(hhi, dim_load, congruence)

        report = {
            "q_state":       WHITE,
            "worker_load":   worker_load,
            "dim_load":      dim_load,
            "hhi":           round(hhi, 4),
            "congruence":    round(congruence, 4),
            "entropy_modifier": round(modifier, 4),
            "flags":         flags,
            "diagnosis":     self._diagnose(hhi, congruence, dim_load, flags),
        }

        self._history.append(report)
        if len(self._history) > 20:
            self._history.pop(0)

        return report

    # ──────────────────────────────────────────────────────────────
    # WORKER LOAD
    # ──────────────────────────────────────────────────────────────

    def _compute_worker_load(self, field_domains: dict) -> dict:
        """
        Per-worker load fraction.
        load = activation × (palette_span / PALETTE_SIZE)

        Workers not in field get load 0.0.
        """
        load = {}
        for worker, (_, _, span) in WORKER_PALETTE.items():
            activation = 0.0
            if worker in field_domains:
                activation = float(
                    field_domains[worker].get("activation", 0.0)
                )
            load[worker] = round(
                activation * (span / PALETTE_SIZE), 6
            )
        return load

    # ──────────────────────────────────────────────────────────────
    # DIMENSIONAL LOAD
    # ──────────────────────────────────────────────────────────────

    def _compute_dim_load(self, worker_load: dict) -> dict:
        """
        Per-layer dimensional pressure.
        dim_load[layer] = sum(worker_load[w] × affinity[w][layer])
        """
        dim = {layer: 0.0 for layer in DIM_LAYERS}
        for worker, load in worker_load.items():
            affinity = WORKER_DIM_AFFINITY.get(worker, {})
            for layer in DIM_LAYERS:
                dim[layer] += load * affinity.get(layer, 0.0)

        total = sum(dim.values())
        if total > 0:
            return {
                layer: round(val / total, 4)
                for layer, val in dim.items()
            }
        return {layer: 0.0 for layer in DIM_LAYERS}

    # ──────────────────────────────────────────────────────────────
    # HHI — Herfindahl-Hirschman Index
    # ──────────────────────────────────────────────────────────────

    def _compute_hhi(self, worker_load: dict) -> float:
        """
        Concentration index across workers.
        HHI = sum(load_i^2) normalized to [0, 1].

        HHI → 0: perfectly distributed
        HHI → 1: one worker has all load
        """
        values = list(worker_load.values())
        total  = sum(values)
        if total <= 0:
            return 0.0

        shares = [v / total for v in values]
        n      = len(shares)
        raw    = sum(s ** 2 for s in shares)
        # Normalize: min HHI = 1/N (perfect distribution)
        normalized = (raw - 1 / n) / (1 - 1 / n + 1e-10)
        return max(0.0, min(1.0, normalized))

    # ──────────────────────────────────────────────────────────────
    # FOUNDATION CONGRUENCE
    # ──────────────────────────────────────────────────────────────

    def _compute_congruence(self, dim_load: dict) -> float:
        """
        Fraction of dimensional load in the base_82 layer.
        Low congruence = abstract layers firing without foundation support.
        """
        return dim_load.get("base_82", 0.0)

    # ──────────────────────────────────────────────────────────────
    # FLAGS
    # ──────────────────────────────────────────────────────────────

    def _compute_flags(
        self,
        hhi: float,
        dim_load: dict,
        congruence: float
    ) -> dict:
        """
        Boolean diagnostic flags.
        """
        dominant_layer = max(dim_load, key=dim_load.get) \
                         if dim_load else None
        dominant_val   = dim_load.get(dominant_layer, 0.0) \
                         if dominant_layer else 0.0

        return {
            "hhi_concentrated":        hhi > HHI_CONCENTRATED,
            "hhi_balanced":            hhi < HHI_BALANCED,
            "foundation_underloaded":  congruence < CONGRUENCE_FLOOR,
            "dim_layer_skewed":        dominant_val > DIM_SKEW_MAX,
            "dominant_layer":          dominant_layer,
        }

    # ──────────────────────────────────────────────────────────────
    # ENTROPY MODIFIER
    # ──────────────────────────────────────────────────────────────

    def _compute_modifier(
        self,
        hhi: float,
        dim_load: dict,
        congruence: float
    ) -> float:
        """
        Entropy threshold modifier.

        Returns value in [MOD_MIN, MOD_MAX]:
          Negative → tighten threshold (more aggressive re-balance)
          Positive → relax threshold (distribution is healthy)

        Logic:
          1. HHI contribution: high concentration tightens
          2. Dim skew contribution: heavy layer imbalance tightens
          3. Congruence penalty: low base_82 tightens
          4. Balance bonus: well-distributed slightly relaxes
        """
        modifier = 0.0

        # HHI component
        if hhi > HHI_CONCENTRATED:
            modifier -= 0.03                   # heavily concentrated
        elif hhi < HHI_BALANCED:
            modifier += 0.02                   # well distributed
        else:
            # Linear interpolation in middle range
            t = (hhi - HHI_BALANCED) / (HHI_CONCENTRATED - HHI_BALANCED)
            modifier -= 0.03 * t

        # Dimensional skew component
        if dim_load:
            max_load = max(dim_load.values())
            if max_load > DIM_SKEW_MAX:
                skew = (max_load - DIM_SKEW_MAX) / (1.0 - DIM_SKEW_MAX + 1e-10)
                modifier -= 0.02 * skew

        # Foundation congruence penalty
        if congruence < CONGRUENCE_FLOOR:
            deficit = CONGRUENCE_FLOOR - congruence
            modifier -= 0.02 * (deficit / CONGRUENCE_FLOOR)

        return float(np.clip(modifier, MOD_MIN, MOD_MAX))

    # ──────────────────────────────────────────────────────────────
    # APPLY MODIFIER TO ENTROPY ENGINE
    # ──────────────────────────────────────────────────────────────

    def apply_modifier(
        self,
        current_threshold: float,
        report: dict,
        base_threshold: float = 0.15,
        clamp_min: float = 0.08,
        clamp_max: float = 0.22,
    ) -> float:
        """
        Apply the entropy modifier to the entropy engine's threshold.

        The modifier is applied as a delta from base_threshold.
        Clamped to [clamp_min, clamp_max] for safety.

        Args:
            current_threshold: CognitiveEntropy.entropy_threshold
            report: capacity score report (from .score())
            base_threshold: the factory default (0.15)
            clamp_min: minimum threshold floor
            clamp_max: maximum threshold ceiling

        Returns:
            New entropy_threshold value.
        """
        modifier    = report.get("entropy_modifier", 0.0)
        new_val     = base_threshold + modifier
        new_val     = float(np.clip(new_val, clamp_min, clamp_max))
        return round(new_val, 4)

    # ──────────────────────────────────────────────────────────────
    # DIAGNOSIS STRING
    # ──────────────────────────────────────────────────────────────

    def _diagnose(
        self,
        hhi: float,
        congruence: float,
        dim_load: dict,
        flags: dict
    ) -> str:
        """
        Human-readable one-line diagnosis.
        """
        parts = []

        if flags["hhi_concentrated"]:
            parts.append("worker load concentrated — one domain dominant")
        elif flags["hhi_balanced"]:
            parts.append("worker load well distributed")
        else:
            parts.append("worker load moderately spread")

        if flags["foundation_underloaded"]:
            parts.append(
                f"FOUNDATION UNDERLOADED — base_82={congruence:.2f} "
                f"(floor={CONGRUENCE_FLOOR}) — abstract layers unsupported"
            )
        else:
            parts.append(f"foundation congruent ({congruence:.2f})")

        if flags["dim_layer_skewed"] and flags.get("dominant_layer"):
            parts.append(
                f"dim skewed → {flags['dominant_layer']} "
                f"({dim_load.get(flags['dominant_layer'], 0):.2f})"
            )

        return " | ".join(parts)

    # ──────────────────────────────────────────────────────────────
    # HISTORY / TRENDING
    # ──────────────────────────────────────────────────────────────

    def trend(self) -> dict:
        """
        Rolling trend over last N cycles.
        Returns average HHI, congruence, modifier.
        """
        if not self._history:
            return {}
        n       = len(self._history)
        avg_hhi = sum(r["hhi"]             for r in self._history) / n
        avg_con = sum(r["congruence"]      for r in self._history) / n
        avg_mod = sum(r["entropy_modifier"] for r in self._history) / n
        return {
            "cycles":           n,
            "avg_hhi":          round(avg_hhi, 4),
            "avg_congruence":   round(avg_con, 4),
            "avg_modifier":     round(avg_mod, 4),
        }


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 64)
    print("CAPACITY SCORER — SELF-TEST")
    print("=" * 64)

    scorer = CapacityScorer()

    # ── Test 1: single dominant worker ────────────────────────────
    print("\n[1] Single dominant worker (emotion only):")
    field = {
        "emotion_001":   {"activation": 1.0},
        "curiosity_001": {"activation": 0.0},
        "ethics_001":    {"activation": 0.0},
        "language_001":  {"activation": 0.0},
        "memory_001":    {"activation": 0.0},
    }
    r = scorer.score(field)
    print(f"   HHI={r['hhi']}  congruence={r['congruence']}"
          f"  modifier={r['entropy_modifier']}")
    print(f"   worker_load: {r['worker_load']}")
    print(f"   dim_load:    {r['dim_load']}")
    print(f"   flags:       {r['flags']}")
    print(f"   diagnosis:   {r['diagnosis']}")
    assert r["flags"]["hhi_concentrated"], "Expected concentrated"
    assert r["flags"]["hhi_balanced"] == False
    assert r["entropy_modifier"] <= 0, "Concentrated should tighten"
    print("   PASS")

    # ── Test 2: balanced field ─────────────────────────────────────
    print("\n[2] Balanced field (all workers equal):")
    field = {w: {"activation": 0.2} for w in WORKER_PALETTE}
    r = scorer.score(field)
    print(f"   HHI={r['hhi']}  congruence={r['congruence']}"
          f"  modifier={r['entropy_modifier']}")
    print(f"   dim_load: {r['dim_load']}")
    print(f"   diagnosis: {r['diagnosis']}")
    assert r["flags"]["hhi_balanced"], "Expected balanced"
    assert r["entropy_modifier"] >= 0, "Balanced should relax"
    print("   PASS")

    # ── Test 3: abstract-heavy, foundation starved ─────────────────
    print("\n[3] Abstract heavy — language + memory dominant:")
    field = {
        "emotion_001":   {"activation": 0.02},
        "curiosity_001": {"activation": 0.02},
        "ethics_001":    {"activation": 0.06},
        "language_001":  {"activation": 0.50},
        "memory_001":    {"activation": 0.50},
    }
    r = scorer.score(field)
    print(f"   HHI={r['hhi']}  congruence={r['congruence']}"
          f"  modifier={r['entropy_modifier']}")
    print(f"   dim_load: {r['dim_load']}")
    print(f"   flags: {r['flags']}")
    print(f"   diagnosis: {r['diagnosis']}")
    assert r["flags"]["foundation_underloaded"], \
        f"Expected foundation underloaded, got congruence={r['congruence']}"
    print("   PASS")

    # ── Test 4: apply_modifier to entropy threshold ────────────────
    print("\n[4] apply_modifier — concentrated → tighten threshold:")
    field = {"emotion_001": {"activation": 1.0},
             **{w: {"activation": 0.0} for w in WORKER_PALETTE if w != "emotion_001"}}
    r     = scorer.score(field)
    new_t = scorer.apply_modifier(0.15, r)
    print(f"   base=0.15  modifier={r['entropy_modifier']}  new={new_t}")
    assert new_t < 0.15, "Should be tighter"
    print("   PASS")

    # ── Test 5: trend after several cycles ────────────────────────
    print("\n[5] Trend over 5 cycles:")
    for _ in range(4):
        scorer.score({w: {"activation": 0.2} for w in WORKER_PALETTE})
    t = scorer.trend()
    print(f"   {t}")
    assert t["cycles"] >= 5
    print("   PASS")

    print("\n" + "=" * 64)
    print("ALL TESTS PASS")
    print(f"Base threshold range: {0.15+MOD_MIN:.3f} to {0.15+MOD_MAX:.3f}")
    print(f"  Concentrated workers  → threshold ~{0.15+MOD_MIN:.3f}")
    print(f"  Balanced distribution → threshold ~{0.15+MOD_MAX:.3f}")
    print(f"  Foundation floor:      congruence ≥ {CONGRUENCE_FLOOR}")
    print("=" * 64)
