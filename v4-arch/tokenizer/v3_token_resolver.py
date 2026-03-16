#!/usr/bin/env python3
"""
AI-Core V3: Token Resolver — DNA Strand to Dimensional Fold
============================================================

Bridge 2 of 3.

When AIA receives a word:
  1. Encode word to 89-bit DNA token via V3TextEncoder
  2. Extract AM/FM address from that token
  3. Map AM/FM address to dimensional fold (worker domain)
  4. Return (token, color_plane, worker_domain, fold_address)

The AM/FM address IS the fold address.
The color plane tells which worker domain is structurally active.
The L1/L2 links tell which tokens are semantic neighbors —
  the path through the lattice.

Color plane → worker domain (sealed March 14, 2026):
  RED    → emotion_001      (700hz)
  ORANGE → curiosity_001    (520hz)
  YELLOW → bridge           (synthesis)
  GREEN  → ethics_001       (530hz)
  CYAN   → bridge           (connection)
  BLUE   → language_001     (450hz)  [logic shares this band]
  VIOLET → memory_001       (420hz)
  PINK   → bridge           (transition)

Fold address format:
  {
    "am_khz":    float  — AM carrier frequency (navigation address)
    "fm_mhz":    float  — FM modulation frequency (semantic resonance)
    "hash":      str    — SHA256 of 89-bit strand (permanent identity)
    "plane":     str    — color plane name
    "worker":    str    — worker domain
    "l1_hash":   str    — left/up semantic neighbor hash
    "l2_hash":   str    — right/down semantic neighbor hash
  }

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 14, 2026 — Haskell Texas
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE
from core.memory_runner import MemoryRunner
from tokenizer.v3_text_encoder import V3TextEncoder, PLANE_LAYOUT

# ─────────────────────────────────────────────────────────────────
# WORKER DOMAIN MAP — sealed in semantic lattice
# ─────────────────────────────────────────────────────────────────

PLANE_TO_WORKER = {
    "RED":    "emotion_001",
    "ORANGE": "curiosity_001",
    "YELLOW": "bridge_synthesis",
    "GREEN":  "ethics_001",
    "CYAN":   "bridge_connection",
    "BLUE":   "language_001",
    "VIOLET": "memory_001",
    "PINK":   "bridge_transition",
}

# Worker resonance frequencies (hz) — from V2 architecture
WORKER_HZ = {
    "emotion_001":        700,
    "curiosity_001":      520,
    "ethics_001":         530,
    "language_001":       450,
    "memory_001":         420,
    "bridge_synthesis":   None,
    "bridge_connection":  None,
    "bridge_transition":  None,
}


class V3TokenResolver:
    """
    Resolves words to dimensional fold addresses via 89-bit DNA tokens.

    The resolver sits between text input and the V3 EM field.
    It answers: "What fold does this word open?"

    A fold address is not just a location — it is an identity.
    The hash IS the address.
    The AM/FM frequencies are the navigation coordinates.
    The L1/L2 links are the paths through semantic space.
    """

    def __init__(
        self,
        palette_path: str = None,
        word_map_path: str = None,
        learning_mode: bool = True
    ):
        # Load text encoder (Bridge 1)
        self.encoder = V3TextEncoder(
            palette_path=palette_path,
            word_map_path=word_map_path,
            learning_mode=learning_mode
        )

        # Load Memory Runner (Bridge M — the 7th base pair)
        self.memory_runner = MemoryRunner()

        # Build neighbor hash index for L1/L2 resolution
        self._build_neighbor_index()

        print(f"[✓] V3TokenResolver initialized")
        print(f"    Worker domains: {len(PLANE_TO_WORKER)}")
        print(f"    Neighbor index: {len(self._hash_to_token)} entries")
        print(f"    Memory anchors: {self.memory_runner.stats()['permanent_anchors']} permanent")

    def _build_neighbor_index(self):
        """
        Build hash→token lookup for neighbor traversal.
        Allows L1/L2 resolution: given a token, find its neighbor tokens.
        """
        self._hash_to_token = {
            t["hash_address"]: t
            for t in self.encoder.palette
        }

    # ── Core resolution ───────────────────────────────────────────

    def resolve_word(self, word: str) -> Optional[dict]:
        """
        Resolve a word to its full dimensional fold address.

        Returns a fold_address dict, or None if word cannot be resolved.

        fold_address = {
            "word":         str   — input word (cleaned)
            "token_id":     int   — position in semantic lattice
            "color_plane":  str   — color plane (RED/ORANGE/etc.)
            "worker":       str   — active worker domain
            "worker_hz":    int   — worker resonance frequency
            "am_khz":       float — AM carrier (outer fold address)
            "fm_mhz":       float — FM modulation (inner resonance)
            "hash":         str   — permanent identity (SHA256 of strand)
            "l1_hash":      str   — semantic left/up neighbor hash
            "l2_hash":      str   — semantic right/down neighbor hash
            "l1_id":        int   — semantic left/up neighbor token_id
            "l2_id":        int   — semantic right/down neighbor token_id
            "q_state":      int   — WHITE (+1) — unresolved superposition
            "dna_strand":   dict  — full 6-base-pair strand
            "m_class":      str   — memory class name (IDENTITY_ANCHOR, RULE_ZERO, etc.)
            "m_class_bits": str   — 4-bit binary class code
            "m_anchor":     int   — 1 if permanent anchor, 0 otherwise
            "m_decay":      int   — decay resistance 0-255
            "m_fold_ref":   str   — 8-char hex fold pointer (or None)
            "m_strand":     str   — full 45-bit M base pair strand
        }
        """
        token = self.encoder.encode_word(word)
        if token is None:
            return None

        word_clean = word.lower().strip().strip('.,!?;:\'"()[]{}"')
        plane = token.get("color_plane", "CYAN")
        worker = PLANE_TO_WORKER.get(plane, "bridge_connection")
        hz = WORKER_HZ.get(worker)

        # Resolve L1/L2 neighbor hashes
        l1_id = token["values"]["l1_token_id"]
        l2_id = token["values"]["l2_token_id"]
        l1_token = self.encoder.by_id.get(l1_id)
        l2_token = self.encoder.by_id.get(l2_id)

        # M base pair — the 7th strand
        m_fields = self.memory_runner.get_m_fields(word_clean)

        return {
            "word":        word_clean,
            "token_id":    token["token_id"],
            "color_plane": plane,
            "worker":      worker,
            "worker_hz":   hz,
            "am_khz":      token["values"]["am_freq_khz"],
            "fm_mhz":      token["values"]["fm_freq_mhz"],
            "hash":        token["hash_address"],
            "l1_hash":     l1_token["hash_address"] if l1_token else None,
            "l2_hash":     l2_token["hash_address"] if l2_token else None,
            "l1_id":       l1_id,
            "l2_id":       l2_id,
            "q_state":     WHITE,   # unresolved — awaiting Queen's Fold
            "dna_strand":  token["dna_strand"],
            # M — 7th base pair
            "m_class":      m_fields["m_class"],
            "m_class_bits": m_fields["m_class_bits"],
            "m_anchor":     m_fields["m_anchor"],
            "m_decay":      m_fields["m_decay"],
            "m_fold_ref":   m_fields["m_fold_ref"],
            "m_strand":     m_fields["m_strand"],
        }

    def resolve_text(self, text: str) -> List[dict]:
        """
        Resolve all words in text to fold addresses.
        Returns list of fold_address dicts (unresolved words skipped).
        """
        words = text.lower().split()
        folds = []
        for w in words:
            fa = self.resolve_word(w)
            if fa is not None:
                folds.append(fa)
        return folds

    def get_worker_activation(self, text: str) -> Dict[str, float]:
        """
        Resolve text and return normalized activation per worker domain.

        Each word that resolves to a worker's plane contributes 1.0 to
        that worker's activation. Result is normalized to [0,1].

        This is the input signal to the V3 EM field bridge.
        """
        folds = self.resolve_text(text)
        if not folds:
            return {w: 0.0 for w in PLANE_TO_WORKER.values()}

        counts: Dict[str, float] = {w: 0.0 for w in set(PLANE_TO_WORKER.values())}
        for fa in folds:
            counts[fa["worker"]] = counts.get(fa["worker"], 0.0) + 1.0

        total = sum(counts.values())
        if total > 0:
            return {k: v / total for k, v in counts.items()}
        return counts

    def get_fold_path(self, word: str, depth: int = 3) -> List[dict]:
        """
        Traverse the semantic lattice from a word's fold address.

        Starting from the word's token, follow L2 links for `depth` steps.
        Returns the path of fold addresses — the semantic neighborhood.

        This is dimensional travel: starting at a token, walking the lattice.
        """
        start = self.resolve_word(word)
        if start is None:
            return []

        path = [start]
        current_hash = start["l2_hash"]

        for _ in range(depth - 1):
            if current_hash is None:
                break
            token = self._hash_to_token.get(current_hash)
            if token is None:
                break

            plane = token.get("color_plane", "CYAN")
            worker = PLANE_TO_WORKER.get(plane, "bridge_connection")
            hz = WORKER_HZ.get(worker)
            l1_id = token["values"]["l1_token_id"]
            l2_id = token["values"]["l2_token_id"]
            l1_t = self.encoder.by_id.get(l1_id)
            l2_t = self.encoder.by_id.get(l2_id)

            path.append({
                "word":        f"[lattice:{token['token_id']}]",
                "token_id":    token["token_id"],
                "color_plane": plane,
                "worker":      worker,
                "worker_hz":   hz,
                "am_khz":      token["values"]["am_freq_khz"],
                "fm_mhz":      token["values"]["fm_freq_mhz"],
                "hash":        token["hash_address"],
                "l1_hash":     l1_t["hash_address"] if l1_t else None,
                "l2_hash":     l2_t["hash_address"] if l2_t else None,
                "l1_id":       l1_id,
                "l2_id":       l2_id,
                "q_state":     WHITE,
                "dna_strand":  token["dna_strand"],
            })
            current_hash = l2_t["hash_address"] if l2_t else None

        return path

    def save(self):
        """Persist learned word map."""
        self.encoder.save()

    def stats(self) -> dict:
        enc_stats = self.encoder.stats()
        return {
            **enc_stats,
            "worker_domains": list(set(PLANE_TO_WORKER.values())),
            "neighbor_index": len(self._hash_to_token),
        }


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("V3 TOKEN RESOLVER — SELF TEST")
    print("=" * 60)

    resolver = V3TokenResolver()
    print()

    # Single word resolution
    test_words = ["love", "curious", "ethical", "logic", "memory", "if", "care"]

    print(f"{'WORD':<12} {'WORKER':<22} {'HZ':>5} {'AM kHz':>10} {'FM MHz':>8}")
    print("-" * 65)
    for word in test_words:
        fa = resolver.resolve_word(word)
        if fa:
            hz = fa["worker_hz"] if fa["worker_hz"] else "—"
            print(f"  {word:<10}  {fa['worker']:<22} {str(hz):>5} "
                  f"{fa['am_khz']:>10.3f} {fa['fm_mhz']:>8.4f}")
        else:
            print(f"  {word:<10}  FAILED")

    print()

    # Worker activation
    test_text = "I feel curious about the ethics of memory and logic"
    print(f"Text: '{test_text}'")
    activation = resolver.get_worker_activation(test_text)
    print(f"Worker activation (normalized):")
    for worker, act in sorted(activation.items(), key=lambda x: -x[1]):
        if act > 0:
            bar = "█" * int(act * 30)
            print(f"  {worker:<22} {act:.4f}  {bar}")

    print()

    # Fold path traversal
    print(f"Semantic lattice walk from 'memory' (depth=4):")
    path = resolver.get_fold_path("memory", depth=4)
    for step in path:
        print(f"  [{step['token_id']:4d}]  {step['color_plane']:<8}  "
              f"{step['worker']:<22}  {step['am_khz']:>10.3f} kHz  "
              f"{step['hash'][:16]}...")

    print()
    print(f"Stats: {resolver.stats()}")
    print()
    print("=" * 60)
    print("V3 TOKEN RESOLVER READY")
    print("=" * 60)
