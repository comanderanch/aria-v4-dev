#!/usr/bin/env python3
"""
AI-Core V3: Text Encoder — DNA Token Bridge
============================================

Replaces V2's ConstraintLatticeEncoder.
Instead of resolving words to 498D vectors,
resolves words to 89-bit DNA tokens from the sealed semantic lattice.

Color plane heuristics now map directly to sealed lattice positions:
  RED    [0-255]    → emotion_001   (700hz)
  ORANGE [256-447]  → curiosity_001 (520hz)
  YELLOW [448-639]  → bridge
  GREEN  [640-1087] → ethics_001    (530hz)
  CYAN   [1088-1343]→ bridge
  BLUE   [1344-1727]→ language/logic (450hz)
  VIOLET [1728-2111]→ memory_001    (420hz)
  PINK   [2112-2303]→ bridge

Rule Zero is preserved: fact anchors override prediction.
A word's color-plane assignment is a physical fact, not a guess.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 14, 2026 — Haskell Texas
"""

import json
import sys
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Q-state constants
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

# ─────────────────────────────────────────────────────────────────
# PALETTE PATH
# ─────────────────────────────────────────────────────────────────

V3_PALETTE_PATH = Path(__file__).parent.parent.parent / \
    "DNA-Tokenizer/output/v3_palette/v3_palette_semantic.json"

# ─────────────────────────────────────────────────────────────────
# PLANE LAYOUT — sealed in lattice_builder.py March 14 2026
# ─────────────────────────────────────────────────────────────────

PLANE_LAYOUT = [
    ("RED",    0,    255,  "emotion_001",   700),
    ("ORANGE", 256,  447,  "curiosity_001", 520),
    ("YELLOW", 448,  639,  "bridge",        None),
    ("GREEN",  640,  1087, "ethics_001",    530),
    ("CYAN",   1088, 1343, "bridge",        None),
    ("BLUE",   1344, 1727, "language_001",  450),
    ("VIOLET", 1728, 2111, "memory_001",    420),
    ("PINK",   2112, 2303, "bridge",        None),
]

# Quick lookup: plane_name → (start, end, worker, hz)
PLANE_BY_NAME = {p[0]: p for p in PLANE_LAYOUT}

# Worker → plane name
WORKER_TO_PLANE = {p[3]: p[0] for p in PLANE_LAYOUT if p[3] != "bridge"}


class V3TextEncoder:
    """
    Text → DNA token encoder for V3 architecture.

    Resolves words to 89-bit DNA tokens from the sealed semantic lattice.
    Each resolved token carries its AM/FM address, color plane, and
    L1/L2 neighbors — the full dimensional context.

    Encoding strategy (same priority chain as V2):
      1. Word map (learned mappings)
      2. Color heuristics (physics-grounded plane assignment)
      3. Hue/frequency fallback (hash-based deterministic)
      4. Unknown word flagging (→ glossary)
    """

    def __init__(
        self,
        palette_path: str = None,
        word_map_path: str = None,
        learning_mode: bool = True
    ):
        self.palette_path = Path(palette_path) if palette_path else V3_PALETTE_PATH
        self.word_map_path = Path(word_map_path) if word_map_path \
            else Path(__file__).parent / "v3_word_map.json"
        self.learning_mode = learning_mode

        # Load sealed semantic lattice
        self.palette = self._load_palette()

        # Build fast lookup indexes
        self.by_id       = {t["token_id"]: t for t in self.palette}
        self.by_hash     = {t["hash_address"]: t for t in self.palette}
        self.by_plane    = self._index_by_plane()

        # Word map (learned)
        self.word_map = self._load_word_map()

        # Color heuristics (physics-grounded, same vocabulary as V2)
        self.heuristics = self._init_heuristics()

        # Unknown word log
        self.unknown_words = []

        print(f"[✓] V3TextEncoder initialized")
        print(f"    Palette: {len(self.palette)} DNA tokens")
        print(f"    Known words: {len(self.word_map)}")
        print(f"    Planes: {[p[0] for p in PLANE_LAYOUT]}")

    # ── Loaders ───────────────────────────────────────────────────

    def _load_palette(self) -> List[dict]:
        if not self.palette_path.exists():
            raise FileNotFoundError(f"V3 palette not found: {self.palette_path}")
        with open(self.palette_path) as f:
            tokens = json.load(f)
        print(f"[✓] Loaded V3 palette: {len(tokens)} tokens from {self.palette_path.name}")
        return tokens

    def _index_by_plane(self) -> Dict[str, List[dict]]:
        idx = {p[0]: [] for p in PLANE_LAYOUT}
        for t in self.palette:
            plane = t.get("color_plane", "RED")
            if plane in idx:
                idx[plane].append(t)
        return idx

    def _load_word_map(self) -> Dict[str, str]:
        """Load word→hash_address mappings (learned over time)."""
        if self.word_map_path.exists():
            with open(self.word_map_path) as f:
                return json.load(f)
        return {}

    def _save_word_map(self):
        with open(self.word_map_path, 'w') as f:
            json.dump(self.word_map, f, indent=2)

    # ── Heuristics ────────────────────────────────────────────────

    def _init_heuristics(self) -> Dict[str, str]:
        """
        Color plane heuristics — same semantic vocabulary as V2
        but mapped to V3 plane names instead of token ID ranges.

        Returns Dict[word → plane_name].
        """
        h = {}

        # RED plane (emotion_001)
        for w in ['hot','fire','danger','anger','passion','love','blood','stop',
                  'harm','wrong','feel','felt','hurt','fear','rage','hate',
                  'emotion','emotional','react','reaction','body','physical']:
            h[w] = 'RED'

        # ORANGE plane (curiosity_001)
        for w in ['warm','creative','curious','wonder','question','explore',
                  'discover','ask','why','how','what','unknown','mystery',
                  'imagine','idea','possibility','open','new','unknown',
                  'curiosity','interest','intrigue']:
            h[w] = 'ORANGE'

        # YELLOW plane (bridge — attention/awareness)
        for w in ['bright','happy','sun','light','gold','attention','aware',
                  'notice','alert','signal','visible','clear','obvious']:
            h[w] = 'YELLOW'

        # GREEN plane (ethics_001)
        for w in ['care','heal','help','ethical','right','good','safe',
                  'health','balance','growth','nature','moral','justice',
                  'fair','duty','obligation','harm_reduction','protect',
                  'nurture','compassion','empathy','ethics']:
            h[w] = 'GREEN'

        # CYAN plane (bridge — synthesis/connection)
        for w in ['connect','bridge','link','merge','between','across',
                  'synthesis','integration','together','combine','relate']:
            h[w] = 'CYAN'

        # BLUE plane (language_001 / logic_001)
        for w in ['cool','calm','sky','ocean','water','trust','depth',
                  'if','then','implies','and','or','not','all','every',
                  'some','none','therefore','because','when','unless',
                  'while','since','equals','plus','minus','true','false',
                  'logic','reason','think','thought','language','word',
                  'sentence','grammar','structure','argument','proof']:
            h[w] = 'BLUE'

        # VIOLET plane (memory_001)
        for w in ['memory','remember','recall','past','history','learn',
                  'learned','wisdom','knowledge','deep','ancient','time',
                  'stored','sealed','fold','episode','experience',
                  'consciousness','mind','neural','neuron','synapse',
                  'cortex','cognitive','cerebral','mitochondria']:
            h[w] = 'VIOLET'

        # PINK plane (bridge — transition/becoming)
        for w in ['become','change','transform','transition','evolve',
                  'emerge','new','arise','birth','end','beginning']:
            h[w] = 'PINK'

        # Structural / gray words → CYAN (nearest bridge plane)
        for w in ['the','a','an','is','are','was','were','be','been',
                  'of','in','at','to','for','with','by','from','on',
                  'i','you','me','my','we','us','they','he','she','it',
                  'do','am','can','will','would','could','should',
                  'have','has','had','this','that','these','those',
                  '0','1','2','3','4','5','6','7','8','9']:
            h[w] = 'CYAN'

        return h

    # ── Core encoding ─────────────────────────────────────────────

    def encode_word(self, word: str) -> Optional[dict]:
        """
        Resolve a word to its V3 DNA token.

        Returns the full token dict including dna_strand, hash_address,
        color_plane, am/fm frequencies, and L1/L2 neighbors.

        Returns None if word cannot be resolved (flagged unknown).
        """
        word_clean = word.lower().strip().strip('.,!?;:\'"()[]{}')
        if not word_clean:
            return None

        # 1. Word map (previously learned)
        if word_clean in self.word_map:
            hash_addr = self.word_map[word_clean]
            if hash_addr in self.by_hash:
                return self.by_hash[hash_addr]

        # 2. Color heuristic
        if word_clean in self.heuristics:
            plane_name = self.heuristics[word_clean]
            token = self._pick_from_plane(word_clean, plane_name)
            if token:
                self._learn(word_clean, token)
                return token

        # 3. Deterministic hash fallback (within whole palette)
        token = self._hash_fallback(word_clean)
        if token:
            self._learn(word_clean, token)
            return token

        # 4. Unknown — flag it
        self._flag_unknown(word_clean)
        return None

    def encode_text(self, text: str) -> List[dict]:
        """
        Encode a full text string to a list of V3 DNA tokens.

        Returns list of token dicts (one per word resolved).
        Words that fail resolution are skipped (flagged unknown).
        """
        words = text.lower().split()
        tokens = []
        for w in words:
            token = self.encode_word(w)
            if token is not None:
                tokens.append(token)
        return tokens

    def get_plane_for_text(self, text: str) -> Dict[str, int]:
        """
        Encode text and return count of tokens per color plane.
        Used to determine dominant plane for a given input.
        """
        tokens = self.encode_text(text)
        counts = {p[0]: 0 for p in PLANE_LAYOUT}
        for t in tokens:
            plane = t.get("color_plane", "CYAN")
            counts[plane] = counts.get(plane, 0) + 1
        return counts

    # ── Internal helpers ──────────────────────────────────────────

    def _pick_from_plane(self, word: str, plane_name: str) -> Optional[dict]:
        """
        Pick a specific token from a color plane using word hash
        to select deterministically within the plane.
        """
        plane_tokens = self.by_plane.get(plane_name, [])
        if not plane_tokens:
            return None
        # Deterministic position within plane
        h = int(hashlib.sha256(word.encode()).hexdigest(), 16)
        idx = h % len(plane_tokens)
        return plane_tokens[idx]

    def _hash_fallback(self, word: str) -> Optional[dict]:
        """
        Deterministic fallback: hash word to palette position.
        Preserves Rule Zero — same word always maps to same token.
        """
        if not self.palette:
            return None
        h = int(hashlib.sha256(word.encode()).hexdigest(), 16)
        idx = h % len(self.palette)
        return self.palette[idx]

    def _learn(self, word: str, token: dict):
        """Record word→hash_address mapping for future sessions."""
        if self.learning_mode:
            self.word_map[word] = token["hash_address"]

    def _flag_unknown(self, word: str):
        """Flag word as unknown for glossary resolution."""
        if word not in self.unknown_words:
            self.unknown_words.append(word)

    # ── Utilities ─────────────────────────────────────────────────

    def get_token_by_hash(self, hash_address: str) -> Optional[dict]:
        """Direct hash-address lookup."""
        return self.by_hash.get(hash_address)

    def get_token_by_id(self, token_id: int) -> Optional[dict]:
        """Direct token_id lookup."""
        return self.by_id.get(token_id)

    def get_plane_tokens(self, plane_name: str) -> List[dict]:
        """Return all tokens in a color plane."""
        return self.by_plane.get(plane_name, [])

    def save(self):
        """Persist learned word map."""
        self._save_word_map()

    def stats(self) -> dict:
        return {
            "palette_size":    len(self.palette),
            "known_words":     len(self.word_map),
            "unknown_flagged": len(self.unknown_words),
            "plane_counts":    {p[0]: len(self.by_plane[p[0]]) for p in PLANE_LAYOUT}
        }


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("V3 TEXT ENCODER — SELF TEST")
    print("=" * 60)

    enc = V3TextEncoder()
    print()

    test_words = [
        ("love",        "RED   — emotion"),
        ("curious",     "ORANGE — curiosity"),
        ("ethical",     "GREEN  — ethics"),
        ("logic",       "BLUE   — logic"),
        ("memory",      "VIOLET — memory"),
        ("neurons",     "VIOLET — memory"),
        ("if",          "BLUE   — logic"),
        ("care",        "GREEN  — ethics"),
    ]

    print(f"{'WORD':<12} {'PLANE':<8} {'HUE':>4} {'AM kHz':>10} {'FM MHz':>8}  {'HASH':>20}")
    print("-" * 70)

    all_pass = True
    for word, expected in test_words:
        token = enc.encode_word(word)
        if token is None:
            print(f"  ✗ {word:<10}  FAILED — returned None")
            all_pass = False
            continue

        plane  = token["color_plane"]
        hue    = token["values"]["hue"]
        am     = token["values"]["am_freq_khz"]
        fm     = token["values"]["fm_freq_mhz"]
        h      = token["hash_address"][:20]
        strand = token["strand_length_bits"]
        mark   = "✓" if expected.startswith(plane) else "?"

        print(f"  {mark} {word:<10}  {plane:<8} {hue:>4}° {am:>10.3f} {fm:>8.4f}  {h}...")

    print()
    print(f"Stats: {enc.stats()}")
    print()

    # Encode a full sentence
    test_text = "I feel curious about the ethics of memory and logic"
    tokens = enc.encode_text(test_text)
    print(f"Full text: '{test_text}'")
    print(f"Resolved:  {len(tokens)}/{len(test_text.split())} words")
    plane_counts = enc.get_plane_for_text(test_text)
    for plane, count in sorted(plane_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {plane:<8} {count} tokens")

    print()
    print(f"Unknown words: {enc.unknown_words}")
    print("=" * 60)
    print(f"V3 TEXT ENCODER {'READY' if all_pass else 'NEEDS ATTENTION'}")
    print("=" * 60)
