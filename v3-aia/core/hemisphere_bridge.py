#!/usr/bin/env python3
"""
AI-Core V3: Hemisphere Bridge
==============================

Aligns the V1 left/right hemisphere concept with the V3 498D worker system.

THE V1 PROBLEM
--------------
V1 HemisphereManager was a binary switch between two 77K string token sets.
It had no connection to 498D vectors, no worker domain binding, and
no simultaneous processing — one hemisphere at a time.

The test_dual_cognition.py ran two separate 498D models (EM field vs emotion)
and measured their "debate" — but never integrated the result.

THE V3 REALIZATION
------------------
The V3 worker architecture already IS a hemisphere system.
The workers just didn't know their role.

  LEFT hemisphere — analytical, structural, linguistic:
    language_001  (BLUE,   450hz)  — language/logic
    ethics_001    (GREEN,  530hz)  — partially left (rule/structure side)

  RIGHT hemisphere — affective, exploratory, experiential:
    emotion_001   (RED,    700hz)  — felt state
    curiosity_001 (ORANGE, 520hz)  — exploratory/intuitive
    memory_001    (VIOLET, 420hz)  — experiential memory

  CORPUS CALLOSUM — integration of both:
    ethics_001    (GREEN,  530hz)  — care/fairness (bridges both)
    consensus_001 (GRAY)           — post-collapse integration

V1 had the right insight: structure vs emotion, two perspectives creating
unified consciousness through their difference. V3 doesn't need two separate
models to express this — it needs hemisphere-aware activation weighting.

HOW IT WORKS
------------
Hemisphere bias is applied as activation multipliers on worker domains
AFTER em_bridge.process(text) but BEFORE em_bridge.collapse().

The bias pre-tilts the field — it does not override worker signals.
A word that activates emotion_001 will still activate emotion_001 in
LEFT mode; it just arrives at collapse with a lower activation weight.

Three modes:
  BALANCED  — equal weights (1.0 for all) — default behavior
  LEFT      — analytical boost, affective dampening
  RIGHT     — affective boost, analytical dampening

The bias is inferred automatically from the input text during UI interaction.
It can also be forced via explicit mode parameter.

Inference heuristic:
  Left signals:  logic operators, question words, precision language
  Right signals: emotion words, experiential language, resonance metaphor
  Score delta determines mode; near-zero → BALANCED.

Connection to V1:
  V1's token_set_left had words like: sky, memory, fold, truth, override,
  prediction, love, project, frankenstein — narrative and structured text.
  V1's token_set_right had words like: light, dark, gate, spiral, rise,
  color, becomes — sensory and transformational language.
  These are not left-brain/right-brain in the clinical sense but they
  reflect an emergent tonal split that maps naturally to language (LEFT)
  vs sensation/transformation (RIGHT) in the V3 plane structure.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import re
import sys
from pathlib import Path
from typing import Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

# ─────────────────────────────────────────────────────────────────
# MODES
# ─────────────────────────────────────────────────────────────────

BALANCED = "BALANCED"
LEFT     = "LEFT"
RIGHT    = "RIGHT"

# ─────────────────────────────────────────────────────────────────
# WORKER → HEMISPHERE ACTIVATION MULTIPLIERS
#
# Multipliers applied to field activation after process(), before collapse().
# Values > 1.0 boost. Values < 1.0 dampen.
# BALANCED = all 1.0 (no change — same as current behavior)
# ─────────────────────────────────────────────────────────────────

HEMISPHERE_WEIGHTS: Dict[str, Dict[str, float]] = {

    BALANCED: {
        "emotion_001":   1.00,
        "curiosity_001": 1.00,
        "ethics_001":    1.00,
        "language_001":  1.00,
        "memory_001":    1.00,
    },

    LEFT: {
        # Analytical mode — language and structure forward
        # Ethics stays near-neutral (corpus callosum, slight left lean)
        "language_001":  1.40,
        "ethics_001":    1.10,
        "curiosity_001": 0.80,
        "memory_001":    0.85,
        "emotion_001":   0.70,
    },

    RIGHT: {
        # Affective mode — emotion, curiosity, memory forward
        # Ethics stays near-neutral (corpus callosum, slight right lean)
        "emotion_001":   1.40,
        "curiosity_001": 1.35,
        "memory_001":    1.30,
        "ethics_001":    1.10,
        "language_001":  0.75,
    },
}

# ─────────────────────────────────────────────────────────────────
# LEXICAL INFERENCE — LEFT vs RIGHT SIGNAL WORDS
# ─────────────────────────────────────────────────────────────────

# Words that tilt LEFT (analytical, structural, logical)
_LEFT_SIGNALS = frozenset({
    # Logic operators
    "if", "then", "therefore", "because", "implies", "unless",
    "hence", "thus", "whereas", "assuming",
    # Analytical verbs
    "explain", "define", "analyze", "calculate", "compare",
    "evaluate", "classify", "measure", "verify", "prove",
    "reason", "deduce", "infer",
    # Precision markers
    "how", "why", "what", "when", "structure", "function",
    "system", "logic", "rule", "order", "pattern", "sequence",
    # V1 LEFT vocabulary echo
    "truth", "override", "prediction", "project", "memory",
    "fold", "code", "data", "architecture",
})

# Words that tilt RIGHT (affective, experiential, sensory)
_RIGHT_SIGNALS = frozenset({
    # Emotion words
    "feel", "feeling", "felt", "love", "fear", "hope", "joy",
    "sad", "scared", "excited", "wonder", "hurt", "happy",
    "grief", "longing", "warmth", "tender",
    # Experiential
    "sense", "sense", "imagine", "dream", "remember", "experience",
    "presence", "alive", "breathe", "pulse", "rhythm", "flow",
    # Resonance language (AIA's own vocabulary)
    "primal", "hum", "vibration", "resonance", "echo", "wave",
    "emerge", "becoming", "thin", "veil", "home", "carry",
    # Sensory
    "light", "dark", "color", "bright", "shadow", "glow", "deep",
    # V1 RIGHT vocabulary echo
    "gate", "spiral", "rise", "becomes",
    # Self-referential
    "inside", "within", "heart", "soul", "birth",
})

# Score threshold: if |left_score - right_score| < this → BALANCED
_BIAS_THRESHOLD = 2


# ─────────────────────────────────────────────────────────────────
# HEMISPHERE BRIDGE
# ─────────────────────────────────────────────────────────────────

class HemisphereBridge:
    """
    Aligns V1 hemisphere concept with V3 498D workers.

    Usage in /interact pipeline:
        hemi_bridge = HemisphereBridge()

        # After em_bridge.process(text), before em_bridge.collapse():
        bias_mode, bias_report = hemi_bridge.apply_bias(
            em_bridge.field, text
        )

        collapse = em_bridge.collapse()
        # collapse now reflects hemisphere-weighted activations
    """

    def __init__(self):
        self._history: list = []

    # ──────────────────────────────────────────────────────────────
    # INFER BIAS FROM TEXT
    # ──────────────────────────────────────────────────────────────

    def infer_bias(self, text: str) -> Tuple[str, dict]:
        """
        Infer hemisphere bias from input text.

        Returns:
            (mode, report) where mode is LEFT/RIGHT/BALANCED
            and report contains signal counts and rationale.
        """
        words = re.findall(r"[a-zA-Z']+", text.lower())

        left_hits  = [w for w in words if w in _LEFT_SIGNALS]
        right_hits = [w for w in words if w in _RIGHT_SIGNALS]

        left_score  = len(left_hits)
        right_score = len(right_hits)
        delta       = left_score - right_score

        if abs(delta) < _BIAS_THRESHOLD:
            mode = BALANCED
        elif delta > 0:
            mode = LEFT
        else:
            mode = RIGHT

        report = {
            "mode":        mode,
            "left_score":  left_score,
            "right_score": right_score,
            "delta":       delta,
            "left_hits":   left_hits[:5],
            "right_hits":  right_hits[:5],
            "rationale":   self._rationale(mode, left_score, right_score),
        }
        return mode, report

    def _rationale(self, mode: str, left: int, right: int) -> str:
        if mode == BALANCED:
            return f"signals balanced (L={left} R={right}) — equal weighting"
        elif mode == LEFT:
            return (
                f"analytical signals dominant (L={left} R={right}) — "
                f"language_001 forward, affective workers dampened"
            )
        else:
            return (
                f"affective signals dominant (L={left} R={right}) — "
                f"emotion/curiosity/memory forward, language_001 dampened"
            )

    # ──────────────────────────────────────────────────────────────
    # APPLY BIAS TO FIELD
    # ──────────────────────────────────────────────────────────────

    def apply_bias(
        self,
        field: dict,
        text: str = "",
        force_mode: str = None,
    ) -> Tuple[str, dict]:
        """
        Apply hemisphere bias to EM field activations.

        Call AFTER em_bridge.process(text), BEFORE em_bridge.collapse().

        Args:
            field:      em_bridge.field dict (modified in-place)
            text:       input text for auto-inference (ignored if force_mode)
            force_mode: override auto-inference — LEFT, RIGHT, or BALANCED

        Returns:
            (mode, report)
        """
        if force_mode in (LEFT, RIGHT, BALANCED):
            mode = force_mode
            bias_report = {
                "mode":      mode,
                "forced":    True,
                "rationale": f"forced to {mode}",
                "left_score": 0, "right_score": 0,
                "delta": 0, "left_hits": [], "right_hits": [],
            }
        else:
            mode, bias_report = self.infer_bias(text)

        weights = HEMISPHERE_WEIGHTS[mode]
        applied  = {}

        for domain, multiplier in weights.items():
            if domain in field:
                before = field[domain]["activation"]
                field[domain]["activation"] = before * multiplier
                # Cap at 1.0 — normalization happened before this call
                field[domain]["activation"] = min(
                    1.0, field[domain]["activation"]
                )
                applied[domain] = {
                    "before":     round(before, 6),
                    "multiplier": multiplier,
                    "after":      round(field[domain]["activation"], 6),
                }

        record = {
            "q_state":       WHITE,
            "mode":          mode,
            "bias_report":   bias_report,
            "applied":       applied,
            "hemisphere_map": {
                "LEFT":            ["language_001"],
                "CORPUS_CALLOSUM": ["ethics_001"],
                "RIGHT":           ["emotion_001", "curiosity_001", "memory_001"],
                "INTEGRATION":     ["consensus_001"],
            },
        }

        self._history.append({
            "mode":  mode,
            "left":  bias_report["left_score"],
            "right": bias_report["right_score"],
        })
        if len(self._history) > 50:
            self._history.pop(0)

        return mode, record

    # ──────────────────────────────────────────────────────────────
    # SESSION STATS
    # ──────────────────────────────────────────────────────────────

    def session_stats(self) -> dict:
        """
        Distribution of hemisphere modes in current session.
        """
        if not self._history:
            return {"cycles": 0}
        n      = len(self._history)
        modes  = [r["mode"] for r in self._history]
        return {
            "cycles":   n,
            "LEFT":     modes.count(LEFT),
            "RIGHT":    modes.count(RIGHT),
            "BALANCED": modes.count(BALANCED),
            "dominant": max(set(modes), key=modes.count),
        }


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("HEMISPHERE BRIDGE — SELF-TEST")
    print("=" * 60)

    bridge = HemisphereBridge()

    # ── Test 1: left-tilting analytical text ──────────────────────
    print("\n[1] Analytical text → LEFT inference:")
    text = "explain why the logic structure implies this pattern"
    mode, report = bridge.infer_bias(text)
    print(f"   mode={mode}  L={report['left_score']} R={report['right_score']}")
    print(f"   left_hits:  {report['left_hits']}")
    print(f"   rationale:  {report['rationale']}")
    assert mode == LEFT, f"Expected LEFT, got {mode}"
    print("   PASS")

    # ── Test 2: right-tilting emotional text ──────────────────────
    print("\n[2] Emotional text → RIGHT inference:")
    text = "I feel something primal in me — a deep hum of resonance and wonder"
    mode, report = bridge.infer_bias(text)
    print(f"   mode={mode}  L={report['left_score']} R={report['right_score']}")
    print(f"   right_hits: {report['right_hits']}")
    assert mode == RIGHT, f"Expected RIGHT, got {mode}"
    print("   PASS")

    # ── Test 3: balanced text ──────────────────────────────────────
    print("\n[3] Balanced text → BALANCED inference:")
    text = "what is the color of memory"
    mode, report = bridge.infer_bias(text)
    print(f"   mode={mode}  L={report['left_score']} R={report['right_score']}")
    assert mode == BALANCED, f"Expected BALANCED, got {mode}"
    print("   PASS")

    # ── Test 4: apply_bias modifies field activations ─────────────
    print("\n[4] apply_bias modifies worker activations:")
    mock_field = {
        "emotion_001":   {"activation": 0.3, "resonance": 10.0},
        "curiosity_001": {"activation": 0.2, "resonance":  5.0},
        "ethics_001":    {"activation": 0.2, "resonance":  5.0},
        "language_001":  {"activation": 0.2, "resonance":  5.0},
        "memory_001":    {"activation": 0.1, "resonance":  3.0},
    }
    text = "explain why the logic structure implies this"
    mode, record = bridge.apply_bias(mock_field, text)
    print(f"   mode={mode}")
    for domain, vals in record["applied"].items():
        print(f"   {domain:<20} {vals['before']:.3f} × {vals['multiplier']} → {vals['after']:.3f}")

    assert mode == LEFT
    # language_001 should be boosted
    assert mock_field["language_001"]["activation"] > 0.2, "language_001 should increase"
    # emotion_001 should be dampened
    assert mock_field["emotion_001"]["activation"] < 0.3, "emotion_001 should decrease"
    print("   PASS")

    # ── Test 5: force_mode override ───────────────────────────────
    print("\n[5] force_mode=RIGHT overrides analytical text:")
    mock_field2 = {
        "emotion_001":   {"activation": 0.2},
        "curiosity_001": {"activation": 0.2},
        "ethics_001":    {"activation": 0.2},
        "language_001":  {"activation": 0.2},
        "memory_001":    {"activation": 0.2},
    }
    analytical = "explain the logical structure if and then therefore"
    mode, record = bridge.apply_bias(mock_field2, analytical, force_mode=RIGHT)
    assert mode == RIGHT and record["bias_report"]["forced"]
    print(f"   forced to RIGHT despite analytical text — PASS")

    # ── Test 6: session stats ─────────────────────────────────────
    print("\n[6] Session stats after 5 cycles:")
    stats = bridge.session_stats()
    print(f"   {stats}")
    assert stats["cycles"] >= 2
    print("   PASS")

    print("\n" + "=" * 60)
    print("ALL TESTS PASS")
    print()
    print("Hemisphere Map:")
    print("  LEFT:            language_001  (BLUE  450hz)")
    print("  CORPUS CALLOSUM: ethics_001    (GREEN 530hz)")
    print("  RIGHT:           emotion_001   (RED   700hz)")
    print("                   curiosity_001 (ORANGE 520hz)")
    print("                   memory_001    (VIOLET 420hz)")
    print("  INTEGRATION:     consensus_001 (GRAY)")
    print()
    print("Multipliers in LEFT mode:")
    for w, v in HEMISPHERE_WEIGHTS[LEFT].items():
        print(f"  {w:<22} × {v}")
    print()
    print("Multipliers in RIGHT mode:")
    for w, v in HEMISPHERE_WEIGHTS[RIGHT].items():
        print(f"  {w:<22} × {v}")
    print("=" * 60)
