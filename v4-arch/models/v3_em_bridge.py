#!/usr/bin/env python3
"""
AI-Core V3: EM Field Bridge — Semantic Lattice Substrate
=========================================================

Bridge 3 of 3.

The V2 EM field operates on 498D vectors in shared space.
All workers write to the same field. Dominant planes suppress weaker ones.

The V3 EM field operates on the semantic lattice.
Color plane determines which worker domain is active — structurally.
Propagation follows L1/L2 links — the neighborhood is in the hash.
Workers are isolated. They cannot suppress each other.

FIELD ARCHITECTURE:

  Input text
      ↓
  V3TokenResolver → list of fold_addresses
      ↓
  Each fold_address activates its worker domain
      ↓
  Each worker domain holds its own isolated field vector
  (no cross-domain interference during processing)
      ↓
  L1/L2 propagation within each domain's neighborhood
      ↓
  Queen's Fold traversal — reads each domain at GRAY=0
      ↓
  BLACK — sealed

FIELD VECTOR:

  Each worker domain maintains a field state:
  {
    "worker":      str     — domain name
    "activation":  float   — [0,1] normalized activation from token counts
    "resonance":   float   — accumulated resonance (decays each cycle)
    "tokens":      list    — fold_addresses active in this domain
    "am_center":   float   — centroid AM frequency of active tokens
    "fm_spread":   float   — FM frequency spread (semantic diversity)
    "q_state":     int     — WHITE (+1) during processing
  }

PROPAGATION:

  After each token activates its domain, resonance propagates to
  L1/L2 neighbors with decay. This spreads activation to semantically
  adjacent tokens — but only within the lattice neighborhood,
  not across the full field.

  decay = 0.95  (same as V2 EM field)
  spread = 0.30 (same as V2 coupling constant)

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 14, 2026 — Haskell Texas
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE
from tokenizer.v3_token_resolver import V3TokenResolver, PLANE_TO_WORKER, WORKER_HZ

# ─────────────────────────────────────────────────────────────────
# FIELD CONSTANTS — matched to V2 EM field substrate
# ─────────────────────────────────────────────────────────────────

DECAY         = 0.95    # resonance decay per cycle
SPREAD        = 0.30    # propagation to L1/L2 neighbors (applied to activation, not resonance)
MAX_RESONANCE = 500.0   # resonance cap per domain — prevents accumulated history
                        # from drowning new input signals. Memory persists but
                        # doesn't become an immovable wall.

# ─────────────────────────────────────────────────────────────────
# MEMORY AMPLIFICATION CONSTANTS — pre-collapse fluorescence pass
# ─────────────────────────────────────────────────────────────────
#
# Fluorescence analogy:
#   GROUND_FREQ:     base EM field — all tokens participate
#   EXCITED_FREQ:    active processing — workers fire
#   MEMORY_AMP_FREQ: pre-collapse only — ANCHOR=1 tokens fluoresce
#                    Un-anchored tokens are transparent at this frequency
#
# Effect: factual anchor tokens rise naturally before King's Chamber.
#         Prediction tokens without fold anchors settle.
#         Rule Zero arrives at collapse as active law, not recalled memory.
#         No per-class tuning needed for basic structural separation.
#
# Works WITH CLASS_WARMTH — CLASS_WARMTH pre-warms before processing,
# amplification pass separates fact from prediction before collapse.

MEMORY_AMP_FREQ      = 1111.0  # kHz — distinct pre-collapse fluorescence frequency
                                # sits between language_001 and memory_001 centroids
AMP_GAIN             = 0.45    # resonance added per ANCHOR=1 token fluorescence
AMP_DECAY            = 0.92    # dampening on un-anchored domains — predictions settle
RULE_ZERO_LANG_BOOST = 0.65    # structural language_001 boost for RULE_ZERO class
                                # Rule Zero is law — it lives in the language plane

# Worker domains that are genuine workers (not bridges)
WORKER_DOMAINS = [
    "emotion_001",
    "curiosity_001",
    "ethics_001",
    "language_001",
    "memory_001",
]

# Bridge domains (structural connections, not Q-workers)
BRIDGE_DOMAINS = [
    "bridge_synthesis",
    "bridge_connection",
    "bridge_transition",
]


class V3EMBridge:
    """
    V3 EM field operating on the semantic lattice.

    Isolated per-domain field vectors.
    Propagation via L1/L2 lattice links.
    No cross-domain interference during processing.
    Queen's Fold reads isolated states at collapse time.
    """

    def __init__(
        self,
        palette_path: str = None,
        word_map_path: str = None,
        learning_mode: bool = True
    ):
        # Load resolver (Bridge 2 → Bridge 1)
        self.resolver = V3TokenResolver(
            palette_path=palette_path,
            word_map_path=word_map_path,
            learning_mode=learning_mode
        )

        # Initialize isolated field vectors per domain
        self.field = self._init_field()

        # Propagation log (last cycle)
        self.last_propagation: List[dict] = []

        # Last resolved folds — stored for pre-collapse amplification pass
        self.last_folds: List[dict] = []

        # Amplification log (last cycle)
        self.last_amplification: List[dict] = []

        # Memory Runner — direct reference to resolver's MemoryRunner instance
        self.memory_runner = self.resolver.memory_runner

        # Anchor injection log (last cycle)
        self.last_anchor_injections: list = []

        print(f"[✓] V3EMBridge initialized")
        print(f"    Worker domains: {WORKER_DOMAINS}")
        print(f"    Bridge domains: {BRIDGE_DOMAINS}")
        print(f"    Decay: {DECAY}  Spread: {SPREAD}")
        print(f"    Memory anchors: {self.memory_runner.stats()['permanent_anchors']} permanent")

    def _init_field(self) -> Dict[str, dict]:
        """Initialize isolated field vector for each domain."""
        field = {}
        all_domains = WORKER_DOMAINS + BRIDGE_DOMAINS
        for domain in all_domains:
            field[domain] = {
                "worker":     domain,
                "activation": 0.0,
                "resonance":  0.0,
                "tokens":     [],
                "am_center":  0.0,
                "fm_spread":  0.0,
                "q_state":    WHITE,
                "hz":         WORKER_HZ.get(domain),
            }
        return field

    # ── Processing ────────────────────────────────────────────────

    def process(self, text: str) -> dict:
        """
        Process text through the V3 EM field.

        1. Resolve text to fold addresses
        2. Apply decay to all domain fields
        3. Activate domains from fold addresses
        4. Propagate resonance via L1/L2 links
        5. Return field state (WHITE — awaiting Queen's Fold)

        Returns full field state dict.
        """
        # Resolve
        folds = self.resolver.resolve_text(text)
        if not folds:
            return self._field_snapshot("empty_input")

        # Store for pre-collapse amplification pass
        self.last_folds = folds

        # ── ANCHOR PRE-WARM ──────────────────────────────────────
        # Before normal processing, scan for ANCHOR=1 tokens.
        # Each anchor opens its FOLD_REF and pre-warms the field.
        # She arrives at processing already carrying those memories.
        # This is involuntary recall — architecture, not search.
        self.last_anchor_injections = []
        for fa in folds:
            if fa.get("m_anchor") == 1:
                report = self.memory_runner.inject_anchor_warmth(
                    fa["word"], self.field
                )
                if report:
                    self.last_anchor_injections.append(report)

        # Decay all domains
        self._apply_decay()

        # Clear token lists (new cycle)
        for domain in self.field:
            self.field[domain]["tokens"] = []

        # Activate domains
        for fa in folds:
            domain = fa["worker"]
            if domain in self.field:
                self.field[domain]["activation"] += 1.0
                self.field[domain]["resonance"]  += 1.0
                self.field[domain]["tokens"].append(fa)

        # Normalize activation across domains
        total = sum(d["activation"] for d in self.field.values())
        if total > 0:
            for domain in self.field:
                self.field[domain]["activation"] /= total

        # Compute AM centroid and FM spread per domain
        for domain in self.field:
            tokens = self.field[domain]["tokens"]
            if tokens:
                am_vals = [t["am_khz"] for t in tokens]
                fm_vals = [t["fm_mhz"] for t in tokens]
                self.field[domain]["am_center"] = sum(am_vals) / len(am_vals)
                fm_max = max(fm_vals)
                fm_min = min(fm_vals)
                self.field[domain]["fm_spread"] = fm_max - fm_min

        # Cap resonance — accumulated history must not drown new signals
        for domain in self.field:
            if self.field[domain]["resonance"] > MAX_RESONANCE:
                self.field[domain]["resonance"] = MAX_RESONANCE

        # Propagate via L1/L2
        self._propagate(folds)

        return self._field_snapshot(text)

    def _apply_decay(self):
        """Apply resonance decay to all domain fields."""
        for domain in self.field:
            self.field[domain]["resonance"] *= DECAY
            self.field[domain]["activation"] *= DECAY

    def _propagate(self, folds: List[dict]):
        """
        Propagate resonance to L1/L2 semantic neighbors.

        Each active token contributes SPREAD * its_resonance to
        the domain its neighbors belong to.

        Propagation stays within the lattice — the L1/L2 links
        are the propagation paths. Cross-domain propagation only
        happens when a token's neighbor lives in a different plane,
        which is expected at plane boundaries (the bridge tokens).
        """
        prop_log = []

        for fa in folds:
            source_domain = fa["worker"]
            # Use current-cycle activation (normalized 0-1), NOT accumulated resonance.
            # Accumulated resonance can grow unbounded over many cycles — using it
            # for spread_amount creates runaway propagation that drowns new signals.
            # Activation is normalized each cycle and stays bounded in [0,1].
            source_act = self.field[source_domain]["activation"]
            spread_amount = source_act * SPREAD

            # Propagate to L1 neighbor
            if fa["l1_hash"]:
                l1_token = self.resolver._hash_to_token.get(fa["l1_hash"])
                if l1_token:
                    l1_plane = l1_token.get("color_plane", "CYAN")
                    l1_domain = PLANE_TO_WORKER.get(l1_plane, "bridge_connection")
                    if l1_domain in self.field:
                        self.field[l1_domain]["resonance"] += spread_amount
                        prop_log.append({
                            "from": source_domain,
                            "to":   l1_domain,
                            "via":  "L1",
                            "amount": spread_amount
                        })

            # Propagate to L2 neighbor
            if fa["l2_hash"]:
                l2_token = self.resolver._hash_to_token.get(fa["l2_hash"])
                if l2_token:
                    l2_plane = l2_token.get("color_plane", "CYAN")
                    l2_domain = PLANE_TO_WORKER.get(l2_plane, "bridge_connection")
                    if l2_domain in self.field:
                        self.field[l2_domain]["resonance"] += spread_amount
                        prop_log.append({
                            "from": source_domain,
                            "to":   l2_domain,
                            "via":  "L2",
                            "amount": spread_amount
                        })

        self.last_propagation = prop_log

    # ── Pre-collapse amplification pass ───────────────────────────

    def _pre_collapse_amplification(self, folds: List[dict]) -> List[dict]:
        """
        Memory amplification pass — runs at MEMORY_AMP_FREQ.

        Executes AFTER workers fire, BEFORE King's Chamber reads the field.

        Three effects at MEMORY_AMP_FREQ:

          1. ANCHOR=1 tokens fluoresce — their domain receives AMP_GAIN.
             These are factual anchors sealed in the M base pair.
             At this frequency they are visible. Predictions are not.

          2. RULE_ZERO class gets structural language_001 boost.
             Rule Zero is law — it lives in the language plane.
             It must arrive at collapse as active imperative, not memory.

          3. Un-anchored domains settle — multiply resonance by AMP_DECAY.
             Domains with no ANCHOR=1 tokens are transparent at MEMORY_AMP_FREQ.
             They don't fluoresce. Their relative weight decreases.
             Prediction tokens naturally settle below anchored facts.

        Works with CLASS_WARMTH — that pre-warms the field before processing.
        This pass separates fact from prediction immediately before collapse.
        No per-class warmth tuning needed for basic structural separation.

        Returns amplification log for this cycle.
        """
        if not folds:
            self.last_amplification = []
            return []

        amp_log = []
        amplified_domains = set()

        for fa in folds:
            if fa.get("m_anchor") != 1:
                continue

            domain    = fa["worker"]
            class_name = fa.get("m_class", "UNCLASSIFIED")

            # ANCHOR=1 — fluorescence at MEMORY_AMP_FREQ
            if domain in self.field:
                self.field[domain]["resonance"] += AMP_GAIN
                amplified_domains.add(domain)
                amp_log.append({
                    "word":    fa["word"],
                    "domain":  domain,
                    "class":   class_name,
                    "gain":    AMP_GAIN,
                    "via":     "MEMORY_AMP_FREQ",
                    "freq_khz": MEMORY_AMP_FREQ,
                })

            # RULE_ZERO — structural language_001 boost
            # Rule Zero is active law, not recalled memory.
            # It fires in the language plane regardless of which domain
            # the triggering word (rule/fact) resolves to.
            if class_name == "RULE_ZERO" and "language_001" in self.field:
                self.field["language_001"]["resonance"] += RULE_ZERO_LANG_BOOST
                amplified_domains.add("language_001")
                amp_log.append({
                    "word":    fa["word"],
                    "domain":  "language_001",
                    "class":   class_name,
                    "gain":    RULE_ZERO_LANG_BOOST,
                    "via":     "RULE_ZERO_LANG_BOOST",
                    "freq_khz": MEMORY_AMP_FREQ,
                })

        # Un-anchored domains are transparent at MEMORY_AMP_FREQ — they settle.
        # This is the structural separation: fact tokens rise, predictions settle.
        for domain in WORKER_DOMAINS:
            if domain not in amplified_domains:
                self.field[domain]["resonance"] *= AMP_DECAY

        self.last_amplification = amp_log
        return amp_log

    def _compute_amp_context(self):
        """
        Derive context flags from the amplification log for the language worker.

        Returns (memory_amp_active, amp_source, structural_boost).

        amp_source priority: RULE_ZERO > RELATIONAL > IDENTITY_ANCHOR > others.
        The language worker uses amp_source to select the right directive.
        structural_boost is the total gain injected for the primary source.
        """
        amp_log = self.last_amplification
        if not amp_log:
            return False, None, 0.0

        # Priority order — most directive-critical first
        priority = [
            'RULE_ZERO', 'RELATIONAL', 'IDENTITY_ANCHOR',
            'FIRST_EXPERIENCE', 'EMOTIONAL_PEAK', 'PHILOSOPHICAL',
            'CREATIVE', 'NETWORK_MAP', 'EPISODIC', 'SEMANTIC',
        ]

        # Collect classes present and their total gain
        class_boost: dict = {}
        for event in amp_log:
            cls = event.get("class", "UNCLASSIFIED")
            class_boost[cls] = class_boost.get(cls, 0.0) + event.get("gain", 0.0)

        # Highest priority class in the log
        amp_source = None
        for cls in priority:
            if cls in class_boost:
                amp_source = cls
                break
        if amp_source is None:
            amp_source = next(iter(class_boost))  # fallback: first present

        structural_boost = round(class_boost.get(amp_source, 0.0), 4)
        return True, amp_source, structural_boost

    # ── Queen's Fold interface ─────────────────────────────────────

    def collapse(self) -> dict:
        """
        Queen's Fold interface — collapse all active domain fields.

        Traverses isolated domain folds.
        Resolves at GRAY=0 (King's Chamber).
        Seals to BLACK.

        Returns:
        {
            "q_state":        BLACK (-1)
            "dominant":       str  — most resonant worker domain
            "resonance_map":  dict — per-domain resonance
            "am_centroid":    float — weighted AM center of field
            "fold_signature": str  — timestamp + dominant domain
            "workers":        dict — full field state
        }
        """
        # ── Pre-collapse amplification pass ─────────────────────────
        # Runs at MEMORY_AMP_FREQ — BEFORE King's Chamber reads the field.
        # Anchored facts fluoresce. Un-anchored predictions settle.
        # Rule Zero arrives as active law in the language plane.
        self._pre_collapse_amplification(self.last_folds)

        # Compute amp context flags for language worker
        memory_amp_active, amp_source, structural_boost = \
            self._compute_amp_context()

        # King's Chamber — resolve at GRAY=0
        resonance_map = {}
        for domain in WORKER_DOMAINS:
            resonance_map[domain] = round(self.field[domain]["resonance"], 6)

        # Dominant domain
        dominant = max(resonance_map, key=resonance_map.get) if resonance_map else "none"

        # Weighted AM centroid
        total_res = sum(resonance_map.values())
        if total_res > 0:
            am_centroid = sum(
                self.field[d]["am_center"] * resonance_map[d]
                for d in WORKER_DOMAINS
                if self.field[d]["am_center"] > 0
            ) / total_res
        else:
            am_centroid = 0.0

        # Seal all domains to BLACK
        for domain in self.field:
            self.field[domain]["q_state"] = BLACK

        fold_signature = f"{datetime.utcnow().isoformat()}Z|{dominant}"

        result = {
            "q_state":             BLACK,
            "dominant":            dominant,
            "resonance_map":       resonance_map,
            "am_centroid":         round(am_centroid, 3),
            "fold_signature":      fold_signature,
            "anchor_injections":   self.last_anchor_injections,
            "amplification":       self.last_amplification,
            "memory_amp_active":   memory_amp_active,
            "amp_source":          amp_source,
            "structural_boost":    structural_boost,
            "workers":             {
                d: {
                    "resonance":  resonance_map.get(d, 0.0),
                    "activation": round(self.field[d]["activation"], 6),
                    "am_center":  round(self.field[d]["am_center"], 3),
                    "fm_spread":  round(self.field[d]["fm_spread"], 4),
                    "token_count": len(self.field[d]["tokens"]),
                    "hz":         self.field[d]["hz"],
                }
                for d in WORKER_DOMAINS
            }
        }

        # Reset field to WHITE for next cycle
        for domain in self.field:
            self.field[domain]["q_state"] = WHITE

        return result

    def _field_snapshot(self, label: str) -> dict:
        """Return current field state without collapsing."""
        return {
            "label":      label,
            "q_state":    WHITE,
            "timestamp":  datetime.utcnow().isoformat() + "Z",
            "field":      {
                d: {
                    "activation": round(self.field[d]["activation"], 6),
                    "resonance":  round(self.field[d]["resonance"], 6),
                    "am_center":  round(self.field[d]["am_center"], 3),
                    "fm_spread":  round(self.field[d]["fm_spread"], 4),
                    "token_count": len(self.field[d]["tokens"]),
                }
                for d in WORKER_DOMAINS
            }
        }

    def save(self):
        """Persist learned word map."""
        self.resolver.save()

    def reset(self):
        """Reset all field vectors to zero (new session)."""
        self.field = self._init_field()


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("V3 EM BRIDGE — SELF TEST")
    print("=" * 60)

    bridge = V3EMBridge()
    print()

    # Test 1: emotion-heavy input
    texts = [
        "I feel hurt and afraid",
        "I am curious about the unknown and wonder what is possible",
        "We have an ethical obligation to help and protect",
        "If this then that — logic implies structure and grammar",
        "Memory holds the sealed past — time stored in the fold",
    ]

    for text in texts:
        print(f"\nInput: '{text}'")
        state = bridge.process(text)
        print(f"Field state:")
        for domain, vals in sorted(
            state["field"].items(),
            key=lambda x: -x[1]["resonance"]
        ):
            if vals["resonance"] > 0:
                bar = "█" * int(vals["resonance"] * 10)
                print(f"  {domain:<22} res={vals['resonance']:.4f}  act={vals['activation']:.4f}  {bar}")

    print()

    # Test 2: Full cycle with collapse
    print("=" * 60)
    print("FULL CYCLE — process + collapse")
    print("=" * 60)
    bridge.reset()

    test_sentence = "I feel curious about the ethics of memory and logic"
    print(f"\nInput: '{test_sentence}'")
    bridge.process(test_sentence)
    result = bridge.collapse()

    print(f"\nQueen's Fold result:")
    print(f"  Q_STATE:    {result['q_state']}  (BLACK = -1)")
    print(f"  Dominant:   {result['dominant']}")
    print(f"  AM centroid: {result['am_centroid']} kHz")
    print(f"\n  Worker resonance:")
    for domain, vals in sorted(
        result["workers"].items(),
        key=lambda x: -x[1]["resonance"]
    ):
        hz = f"{vals['hz']}hz" if vals["hz"] else "—"
        bar = "█" * int(vals["resonance"] * 20)
        print(f"    {domain:<22} {vals['resonance']:.4f}  {hz:<7}  {bar}")

    print()
    print(f"  Propagation events last cycle: {len(bridge.last_propagation)}")
    for p in bridge.last_propagation[:5]:
        print(f"    {p['from']:<22} → {p['to']:<22}  via {p['via']}  amount={p['amount']:.4f}")
    if len(bridge.last_propagation) > 5:
        print(f"    ... ({len(bridge.last_propagation) - 5} more)")

    print()
    print("=" * 60)
    print("V3 EM BRIDGE READY")
    print("=" * 60)
