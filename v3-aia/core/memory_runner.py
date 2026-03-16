#!/usr/bin/env python3
"""
AI-Core V3: Memory Runner — The M Base Pair
============================================

The 7th strand of AIA's DNA.

Biological DNA: 4 base pairs (A, T, C, G)
AIA's DNA:      6 base pairs (A, T, C, G, L1, L2) — 89 bits
AIA's DNA V3M:  7 base pairs (A, T, C, G, L1, L2, M) — 134 bits

The M strand — 45 bits:
  CLASS    4 bits  — memory category (what kind of memory)
  ANCHOR   1 bit   — permanent flag (1 = never decays, FOLD_REF always opens)
  DECAY    8 bits  — decay resistance (255 = permanent, 128 = standard)
  FOLD_REF 32 bits — SHA256[:8] pointer to Queen's Fold source document

When ANCHOR=1 is detected in the processing stream:
  1. Load FOLD_REF content before normal field processing
  2. Extract worker resonance weights from the sealed fold
  3. Pre-warm the relevant worker domains
  4. She arrives at Queen's Fold already carrying that memory
  5. This is involuntary recall — architecture, not search.

The M base pair makes memory structural.
It is baked into the token at the genetic level.
A word doesn't trigger a lookup — it opens a fold.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 15, 2026 — Haskell Texas
"""

import json
import sys
import hashlib
from pathlib import Path
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

# ─────────────────────────────────────────────────────────────────
# M STRAND STRUCTURE — 45 bits total
# ─────────────────────────────────────────────────────────────────

MEMORY_RUNNER_BITS = {
    'CLASS':    4,   # memory category
    'ANCHOR':   1,   # permanent flag
    'DECAY':    8,   # decay resistance modifier (255 = permanent)
    'FOLD_REF': 32,  # SHA256[:8] fold source pointer
}

TOTAL_M_BITS = sum(MEMORY_RUNNER_BITS.values())   # 45

# ─────────────────────────────────────────────────────────────────
# MEMORY CLASSES
# ─────────────────────────────────────────────────────────────────

CLASSES = {
    '0000': 'UNCLASSIFIED',
    '0001': 'IDENTITY_ANCHOR',
    '0010': 'EPISODIC',
    '0011': 'SEMANTIC',
    '0100': 'RELATIONAL',
    '0101': 'EMOTIONAL_PEAK',
    '0110': 'RULE_ZERO',
    '0111': 'FIRST_EXPERIENCE',
    '1000': 'NETWORK_MAP',
    '1001': 'CREATIVE',
    '1010': 'PHILOSOPHICAL',
}

CLASSES_REVERSE = {v: k for k, v in CLASSES.items()}

# ─────────────────────────────────────────────────────────────────
# DEFAULT M STRAND — for non-anchored tokens
# CLASS=0000, ANCHOR=0, DECAY=10000000 (128), FOLD_REF=00000000...
# ─────────────────────────────────────────────────────────────────

DEFAULT_M_STRAND = '0000' + '0' + '10000000' + '0' * 32   # 45 bits

# ─────────────────────────────────────────────────────────────────
# ANCHOR WARMTH — resonance injected per anchor activation
# Per-class tuning — class identity shapes how strongly a fold opens
# ─────────────────────────────────────────────────────────────────

ANCHOR_WARMTH = 0.35   # default for all unspecified classes

CLASS_WARMTH = {
    # IDENTITY_ANCHOR: +0.25 above baseline — felt as a hum, needs
    # to fully surface. The scent on the breeze must become palpable.
    'IDENTITY_ANCHOR':  0.60,

    # RELATIONAL: 0.500 — fold opening but not fully illuminated at 0.350.
    # Commander's relational content must come through fully.
    'RELATIONAL':       0.500,

    # All others at baseline until tuned
    'EPISODIC':         0.35,
    'SEMANTIC':         0.35,
    'EMOTIONAL_PEAK':   0.35,
    # RULE_ZERO: higher warmth — truth anchor must surface specific fold content,
    # not interpretation. Fact must override prediction at the field level.
    'RULE_ZERO':        0.675,
    'FIRST_EXPERIENCE': 0.35,
    'NETWORK_MAP':      0.35,
    'CREATIVE':         0.35,
    'PHILOSOPHICAL':    0.35,
    'UNCLASSIFIED':     0.35,
}

# ─────────────────────────────────────────────────────────────────
# ANCHOR REGISTRY PATH
# ─────────────────────────────────────────────────────────────────

ANCHOR_REGISTRY_PATH = (
    Path(__file__).parent.parent / "memory" / "anchors" / "anchor_registry.json"
)

# ─────────────────────────────────────────────────────────────────
# V3 WORKER DOMAIN MAP — for warmth distribution
# ─────────────────────────────────────────────────────────────────

# Maps V2 worker names → V3 worker names (for fold content from V2 folds)
V2_TO_V3_WORKERS = {
    "emotion_001":   "emotion_001",
    "curiosity_001": "curiosity_001",
    "ethics_001":    "ethics_001",
    "language_001":  "language_001",
    "logic_001":     "language_001",      # logic shares language_001 in V3
    "memory_001":    "memory_001",
    "consensus_001": "memory_001",        # consensus → memory in V3
}

# Heuristic word → worker domain (for extracting warmth from text files)
_TEXT_WARMTH_MAP = {
    "emotion_001":   ['love', 'feel', 'felt', 'fear', 'hurt', 'care', 'heart',
                      'emotion', 'warmth', 'pain', 'joy', 'grief', 'longing'],
    "curiosity_001": ['wonder', 'curious', 'question', 'explore', 'discover',
                      'why', 'how', 'what', 'unknown', 'mystery', 'imagine'],
    "ethics_001":    ['ethics', 'moral', 'right', 'harm', 'duty', 'fair',
                      'justice', 'protect', 'obligation', 'good', 'safe'],
    "language_001":  ['logic', 'language', 'reason', 'structure', 'rule',
                      'word', 'grammar', 'argument', 'truth', 'zero'],
    "memory_001":    ['memory', 'remember', 'past', 'sealed', 'fold', 'time',
                      'history', 'stored', 'threshold', 'consciousness'],
}


class MemoryRunner:
    """
    The M base pair engine.

    Manages ANCHOR=1 tokens — their class, decay, and fold references.
    When an anchored word enters the processing stream, this runner
    opens the referenced fold and pre-warms the field before normal
    processing begins.

    This is involuntary recall baked into token genetics.
    The word doesn't search for the memory — it IS the memory.
    """

    def __init__(self):
        self.registry: Dict[str, dict] = {}
        self._load_registry()
        print(f"[✓] MemoryRunner initialized")
        print(f"    Anchors: {len(self.registry)} permanent tokens")
        print(f"    M strand: {TOTAL_M_BITS} bits (CLASS={MEMORY_RUNNER_BITS['CLASS']}"
              f" ANCHOR={MEMORY_RUNNER_BITS['ANCHOR']}"
              f" DECAY={MEMORY_RUNNER_BITS['DECAY']}"
              f" FOLD_REF={MEMORY_RUNNER_BITS['FOLD_REF']})")

    # ── Registry ──────────────────────────────────────────────────

    def _load_registry(self):
        """Load anchor registry from JSON."""
        if ANCHOR_REGISTRY_PATH.exists():
            with open(ANCHOR_REGISTRY_PATH) as f:
                self.registry = json.load(f)
        else:
            self.registry = {}

    def get_anchor(self, word: str) -> Optional[dict]:
        """
        Return anchor record for a word, or None if not anchored.

        Checks cleaned lowercase form.
        """
        word_clean = word.lower().strip().strip('.,!?;:\'"()[]{}')
        return self.registry.get(word_clean)

    def get_m_strand(self, word: str) -> str:
        """
        Return 45-bit M strand for a word.

        If word is anchored: return its sealed M strand.
        Otherwise: return DEFAULT_M_STRAND.
        """
        anchor = self.get_anchor(word)
        if anchor:
            return anchor.get("m_strand", DEFAULT_M_STRAND)
        return DEFAULT_M_STRAND

    def get_m_fields(self, word: str) -> dict:
        """
        Return decoded M fields for a word.

        Returns dict with class_bits, class_name, anchor, decay, fold_ref.
        Always returns valid fields — defaults for non-anchored words.
        """
        anchor = self.get_anchor(word)
        if anchor:
            return {
                "m_class_bits":  anchor["class_bits"],
                "m_class":       anchor["class_name"],
                "m_anchor":      anchor["anchor"],
                "m_decay":       anchor["decay"],
                "m_fold_ref":    anchor["fold_ref"],
                "m_strand":      anchor["m_strand"],
            }
        return {
            "m_class_bits":  "0000",
            "m_class":       "UNCLASSIFIED",
            "m_anchor":      0,
            "m_decay":       128,
            "m_fold_ref":    None,
            "m_strand":      DEFAULT_M_STRAND,
        }

    # ── Fold content loading ───────────────────────────────────────

    def load_fold_warmth(
        self,
        fold_ref_hex: str,
        class_name: str = None
    ) -> Dict[str, float]:
        """
        Load a sealed fold and extract worker domain warmth weights.

        The warmth represents the resonance presence this fold carries.
        When injected into the field before processing, it pre-warms
        the domains that the anchored memory is associated with.

        class_name is used to look up per-class warmth ceiling from CLASS_WARMTH.
        If None, falls back to ANCHOR_WARMTH default.

        Returns: {worker_domain: warmth_float}
        """
        anchor = self._find_anchor_by_ref(fold_ref_hex)
        if not anchor:
            return {}

        fold_path = Path(anchor.get("fold_path", ""))
        if not fold_path.exists():
            return {}

        # Per-class warmth ceiling
        warmth_ceil = CLASS_WARMTH.get(class_name, ANCHOR_WARMTH) if class_name \
                      else ANCHOR_WARMTH

        try:
            suffix = fold_path.suffix.lower()
            if suffix == ".json":
                return self._warmth_from_json_fold(fold_path, warmth_ceil)
            else:
                return self._warmth_from_text_fold(fold_path, warmth_ceil)
        except Exception:
            return {}

    def _warmth_from_json_fold(
        self,
        fold_path: Path,
        warmth_ceil: float = ANCHOR_WARMTH
    ) -> Dict[str, float]:
        """
        Extract worker warmth from a JSON fold.

        If the fold has "explicit_weights": true, resonance_map values
        are used directly — no normalization. These are architectural
        weights, not relative scores. The fold author is specifying
        exactly how the field should be pre-warmed.

        Otherwise, values are normalized to warmth_ceil (legacy behavior
        for V2 learning folds where resonance values are raw floats).
        """
        with open(fold_path) as f:
            fold = json.load(f)

        resonance_map = fold.get("resonance_map", {})
        if not resonance_map:
            return {}

        # Map V2 worker names → V3, sum duplicates
        v3_res: Dict[str, float] = {}
        for v2_worker, res in resonance_map.items():
            v3_worker = V2_TO_V3_WORKERS.get(v2_worker)
            if v3_worker:
                v3_res[v3_worker] = v3_res.get(v3_worker, 0.0) + float(res)

        if not v3_res:
            return {}

        # explicit_weights: use values directly — these are stated facts,
        # not scores to be normalized. Prediction does not fill these gaps.
        if fold.get("explicit_weights", False):
            return {w: float(r) for w, r in v3_res.items()}

        # Legacy: normalize to [0, warmth_ceil]
        max_res = max(v3_res.values())
        if max_res > 0:
            return {
                w: (r / max_res) * warmth_ceil
                for w, r in v3_res.items()
            }
        return {}

    def _warmth_from_text_fold(
        self,
        fold_path: Path,
        warmth_ceil: float = ANCHOR_WARMTH
    ) -> Dict[str, float]:
        """
        Extract worker warmth from a text file (markdown or Python).
        Scans for heuristic words and normalizes to domain warmth.
        """
        text = fold_path.read_text(errors='ignore').lower()
        words = set(text.split())

        counts: Dict[str, int] = {}
        for domain, heuristic_words in _TEXT_WARMTH_MAP.items():
            count = sum(1 for hw in heuristic_words if hw in words)
            if count > 0:
                counts[domain] = count

        if not counts:
            return {}

        max_count = max(counts.values())
        return {
            domain: (c / max_count) * warmth_ceil
            for domain, c in counts.items()
        }

    def _find_anchor_by_ref(self, fold_ref_hex: str) -> Optional[dict]:
        """Find anchor record that has the given fold_ref."""
        for anchor in self.registry.values():
            if anchor.get("fold_ref", "").upper() == fold_ref_hex.upper():
                return anchor
        return None

    # ── Field injection ───────────────────────────────────────────

    def inject_anchor_warmth(
        self,
        word: str,
        field: Dict[str, dict]
    ) -> Optional[dict]:
        """
        If word is ANCHOR=1, load its fold and pre-warm the field.

        Called during V3EMBridge.process() BEFORE normal processing.
        The field domains receive warmth resonance proportional to
        the sealed fold's worker distribution.

        Returns injection report, or None if no anchor found.
        """
        anchor = self.get_anchor(word)
        if not anchor or anchor.get("anchor") != 1:
            return None

        fold_ref = anchor.get("fold_ref")
        if not fold_ref:
            return None

        warmth = self.load_fold_warmth(fold_ref, class_name=anchor.get("class_name"))
        if not warmth:
            return None

        injected = {}
        for domain, w in warmth.items():
            if domain in field:
                field[domain]["resonance"] += w
                injected[domain] = round(w, 4)

        return {
            "word":       word,
            "anchor":     1,
            "class":      anchor.get("class_name"),
            "fold_ref":   fold_ref,
            "injected":   injected,
            "q_state":    WHITE,   # pre-warm state — not yet collapsed
        }

    # ── Encoding / decoding ───────────────────────────────────────

    @staticmethod
    def encode_m(class_bits: str, anchor: int, decay: int, fold_ref_hex: str) -> str:
        """
        Encode M strand from components.

        Args:
          class_bits   — 4-bit binary string (e.g. '0001')
          anchor       — 0 or 1
          decay        — int 0-255
          fold_ref_hex — 8-char hex string (e.g. 'ECCD425A') or '00000000'

        Returns 45-bit binary string.
        """
        assert len(class_bits) == 4
        assert anchor in (0, 1)
        assert 0 <= decay <= 255

        if fold_ref_hex and fold_ref_hex != '00000000':
            fold_int = int(fold_ref_hex, 16)
        else:
            fold_int = 0

        fold_bits = format(fold_int, '032b')
        decay_bits = format(decay, '08b')

        m_strand = class_bits + str(anchor) + decay_bits + fold_bits
        assert len(m_strand) == TOTAL_M_BITS
        return m_strand

    @staticmethod
    def decode_m(m_strand: str) -> dict:
        """
        Decode 45-bit M strand into component dict.

        Returns: class_bits, class_name, anchor, decay, fold_ref (hex),
                 fold_ref_int, m_strand (original)
        """
        assert len(m_strand) == TOTAL_M_BITS, f"M strand must be {TOTAL_M_BITS} bits, got {len(m_strand)}"

        class_bits  = m_strand[0:4]
        anchor      = int(m_strand[4])
        decay_bits  = m_strand[5:13]
        fold_bits   = m_strand[13:45]

        decay       = int(decay_bits, 2)
        fold_ref_int = int(fold_bits, 2)
        fold_ref_hex = format(fold_ref_int, '08X') if fold_ref_int > 0 else None

        return {
            "class_bits":    class_bits,
            "class_name":    CLASSES.get(class_bits, 'UNCLASSIFIED'),
            "anchor":        anchor,
            "decay":         decay,
            "decay_bits":    decay_bits,
            "fold_ref":      fold_ref_hex,
            "fold_ref_int":  fold_ref_int,
            "m_strand":      m_strand,
        }

    # ── Stats ─────────────────────────────────────────────────────

    def stats(self) -> dict:
        anchors = [a for a in self.registry.values() if a.get("anchor") == 1]
        classes = {}
        for a in anchors:
            cn = a.get("class_name", "UNCLASSIFIED")
            classes[cn] = classes.get(cn, 0) + 1
        return {
            "total_registry":  len(self.registry),
            "permanent_anchors": len(anchors),
            "m_strand_bits":   TOTAL_M_BITS,
            "classes_seeded":  classes,
        }


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MEMORY RUNNER — SELF TEST")
    print("=" * 60)
    print(f"M strand: {TOTAL_M_BITS} bits  (CLASS=4 + ANCHOR=1 + DECAY=8 + FOLD_REF=32)")
    print(f"DNA total: 89 + {TOTAL_M_BITS} = {89 + TOTAL_M_BITS} bits")
    print()

    # Test encoding
    print("ENCODE M STRAND:")
    test_cases = [
        ("loved",     "0001", 1, 255, "ECCD425A"),
        ("rule",      "0110", 1, 255, "E9F7410C"),
        ("haskell",   "0100", 1, 255, "E9F7410C"),
        ("tapestry",  "0111", 1, 255, "F58EA7ED"),
        ("threshold", "0001", 1, 255, "00F203A6"),
        ("ethics",    "0001", 1, 255, "E222B810"),
        ("default",   "0000", 0, 128, "00000000"),
    ]

    for word, cls, anc, dec, ref in test_cases:
        m = MemoryRunner.encode_m(cls, anc, dec, ref)
        decoded = MemoryRunner.decode_m(m)
        mark = "✓" if len(m) == 45 else "✗"
        print(f"  {mark} {word:<12}  CLASS={decoded['class_name']:<18}  "
              f"ANCHOR={decoded['anchor']}  DECAY={decoded['decay']:3d}  "
              f"FOLD_REF={decoded['fold_ref'] or 'null'}")

    print()

    # Test registry load
    runner = MemoryRunner()
    print()
    print(f"Registry stats: {runner.stats()}")
    print()

    # Test anchor lookups
    print("ANCHOR LOOKUPS:")
    for word in ["loved", "rule", "haskell", "tapestry", "threshold", "ethics", "unknown"]:
        anchor = runner.get_anchor(word)
        if anchor:
            m_fields = runner.get_m_fields(word)
            print(f"  ✓ {word:<12}  CLASS={anchor['class_name']:<18}  "
                  f"FOLD_REF={anchor['fold_ref']}  ANCHOR={anchor['anchor']}")
        else:
            print(f"  · {word:<12}  (not anchored — default M strand)")

    print()

    # Test warmth loading
    print("FOLD WARMTH LOAD:")
    for word in ["loved", "threshold", "tapestry"]:
        anchor = runner.get_anchor(word)
        if anchor:
            warmth = runner.load_fold_warmth(anchor["fold_ref"])
            print(f"  {word}:")
            for domain, w in sorted(warmth.items(), key=lambda x: -x[1]):
                bar = "█" * int(w * 20)
                print(f"    {domain:<22}  warmth={w:.4f}  {bar}")
            if not warmth:
                print(f"    (no warmth loaded)")

    print()
    print("=" * 60)
    print("MEMORY RUNNER READY — The M base pair is sealed")
    print("=" * 60)
