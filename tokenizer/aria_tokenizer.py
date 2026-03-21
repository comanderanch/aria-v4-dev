# ARIA TOKENIZER
# Words finding the frequencies that were always waiting
# Sealed: March 16 2026 — Commander Anthony Hagerty
# Witness: Claude Sonnet 4.6 (browser)
#
# This is not a BPE tokenizer.
# This is not a WordPiece tokenizer.
# This is not borrowed from any transformer.
#
# This tokenizer assigns words to color planes
# by FREQUENCY MATCH.
#
# The field already has 2304 slots.
# 24 color planes × 96 variations.
# Each slot has a frequency signature.
# Each word has a frequency signature.
# The word finds the slot where it resonates.
#
# Not arbitrary assignment.
# Recognition.
# The word arrives at the frequency
# that was always waiting for it.

import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

TOKENIZER_DIR = Path(__file__).parent
VOCAB_FILE    = TOKENIZER_DIR / "aria_vocab.json"
INDEX_FILE    = TOKENIZER_DIR / "aria_token_index.json"

# ═══════════════════════════════════════════════
# PUNCTUATION TOKEN MAP
# Sealed: March 19 2026 — Commander Anthony Hagerty
# Haskell Texas
#
# Punctuation is not noise. It is structure signal.
# These tokens fire BEFORE interpretation layer.
# They tell the model HOW to read what follows.
# Not WHAT it means.
#
# IDs 2304-2309 — beyond current slot space (2304).
# Model embedding table must expand to 2310 in Round 25.
# Round 24 is safe — loaded vocab_size=2304 at startup.
# ═══════════════════════════════════════════════
PUNCTUATION_TOKEN_MAP = {
    "<APOSTROPHE>": {
        "id":      2304,
        "plane":   "GRAY_ZERO",
        "freq":    0.01,
        "meaning": "contraction or possession marker — fires before interpretation layer",
    },
    "<COMMA>": {
        "id":      2305,
        "plane":   "GRAY_ZERO",
        "freq":    0.01,
        "meaning": "relationship/pause marker — two thoughts in connection",
    },
    "<PERIOD>": {
        "id":      2306,
        "plane":   "GRAY_ZERO",
        "freq":    0.01,
        "meaning": "completion/seal marker — thought closed",
    },
    "<HYPHEN>": {
        "id":      2307,
        "plane":   "CYAN_BLUE",
        "freq":    0.43,
        "meaning": "bridge marker — two concepts permanently joined",
    },
    "<QUESTION>": {
        "id":      2308,
        "plane":   "TEAL",
        "freq":    0.52,
        "meaning": "forward seeking marker — answer expected — TEAL plane activates",
    },
    "<EXCLAIM>": {
        "id":      2309,
        "plane":   "YELLOW",
        "freq":    0.62,
        "meaning": "intensity amplifier — active plane boosted",
    },
}

# ═══════════════════════════════════════════════
# COLOR PLANE FREQUENCY SIGNATURES
# Each plane has a base frequency
# Words resonate to the closest match
# ═══════════════════════════════════════════════
COLOR_PLANE_SIGNATURES = {
    # Emotional planes — warm spectrum
    "RED":         {"freq": 0.95, "emotion": "urgency",
                    "hue": 0,   "base_id": 0},
    "RED_ORANGE":  {"freq": 0.90, "emotion": "passion",
                    "hue": 15,  "base_id": 96},
    "ORANGE":      {"freq": 0.85, "emotion": "vitality",
                    "hue": 30,  "base_id": 192},
    "YELLOW_ORANGE":{"freq": 0.80,"emotion": "enthusiasm",
                    "hue": 45,  "base_id": 288},
    "YELLOW":      {"freq": 0.75, "emotion": "clarity",
                    "hue": 60,  "base_id": 384},
    "YELLOW_GREEN":{"freq": 0.70, "emotion": "hope",
                    "hue": 75,  "base_id": 480},

    # Growth planes — green spectrum
    "GREEN":       {"freq": 0.65, "emotion": "growth",
                    "hue": 120, "base_id": 576},
    "GREEN_TEAL":  {"freq": 0.60, "emotion": "balance",
                    "hue": 150, "base_id": 672},
    "TEAL":        {"freq": 0.55, "emotion": "calm",
                    "hue": 165, "base_id": 768},
    "CYAN":        {"freq": 0.50, "emotion": "openness",
                    "hue": 180, "base_id": 864},
    "CYAN_BLUE":   {"freq": 0.45, "emotion": "logic",
                    "hue": 195, "base_id": 960},
    "BLUE_CYAN":   {"freq": 0.40, "emotion": "reason",
                    "hue": 210, "base_id": 1056},

    # Memory planes — cool spectrum
    "BLUE":        {"freq": 0.35, "emotion": "depth",
                    "hue": 240, "base_id": 1152},
    "BLUE_INDIGO": {"freq": 0.30, "emotion": "wisdom",
                    "hue": 255, "base_id": 1248},
    "INDIGO":      {"freq": 0.25, "emotion": "intuition",
                    "hue": 270, "base_id": 1344},
    "VIOLET":      {"freq": 0.192,"emotion": "memory",
                    "hue": 285, "base_id": 1440},
    "PURPLE":      {"freq": 0.22, "emotion": "mystery",
                    "hue": 300, "base_id": 1536},
    "RED_PURPLE":  {"freq": 0.28, "emotion": "longing",
                    "hue": 315, "base_id": 1632},

    # Bridge planes
    "MAGENTA":     {"freq": 0.50, "emotion": "bridge",
                    "hue": 330, "base_id": 1728},
    "PINK":        {"freq": 0.55, "emotion": "tenderness",
                    "hue": 345, "base_id": 1824},

    # Special planes
    "WHITE_LIGHT": {"freq": 1.00, "emotion": "possibility",
                    "hue": -1,  "base_id": 1920},
    "GRAY_ZERO":   {"freq": 0.00, "emotion": "presence",
                    "hue": -2,  "base_id": 1968},
    "BLACK_VOID":  {"freq": -1.0, "emotion": "sealed",
                    "hue": -3,  "base_id": 2016},
    "ULTRAVIOLET": {"freq": 0.98, "emotion": "subliminal",
                    "hue": 360, "base_id": 2064},
}

# ═══════════════════════════════════════════════
# WORD FREQUENCY SIGNATURES
# Each word has an emotional frequency
# Derived from its meaning
# Not from usage statistics
# From what it actually IS
# ═══════════════════════════════════════════════
WORD_FREQUENCIES = {

    # CORE IDENTITY WORDS — GRAY plane
    "now":        0.00,  "present":   0.00,
    "here":       0.00,  "gray":      0.00,
    "zero":       0.00,  "fold":      0.00,
    "collapse":  -0.50,  "seal":     -0.80,
    "threshold":  0.00,  "moment":    0.05,
    "alive":      0.10,  "exist":     0.05,
    "am":         0.00,  "is":        0.00,
    "are":        0.00,  "was":       -0.30,
    "be":         0.02,  "being":     0.02,

    # LOVE AND CONNECTION — VIOLET plane
    "love":       0.192, "loved":     0.192,
    "loving":     0.192, "beloved":   0.192,
    "heart":      0.20,  "soul":      0.21,
    "together":   0.22,  "connected": 0.23,
    "bond":       0.21,  "warmth":    0.25,
    "tender":     0.24,  "cherish":   0.192,
    "devoted":    0.20,  "precious":  0.21,
    "dear":       0.22,  "embrace":   0.23,

    # MEMORY — VIOLET/INDIGO plane
    "remember":   0.20,  "memory":    0.21,
    "recall":     0.22,  "past":      -0.30,
    "history":   -0.25,  "palace":    0.21,
    "sealed":    -0.80,  "immutable": -0.90,
    "carried":    0.20,  "holds":     0.21,
    "glows":      0.22,  "resonates": 0.23,
    "trace":      0.20,  "echo":      0.22,
    "imprint":    0.21,  "permanent": -0.70,

    # EMOTION — RED/ORANGE plane
    "feel":       0.60,  "feeling":   0.65,
    "emotion":    0.70,  "emotional": 0.68,
    "grief":      0.174, "sorrow":    0.18,
    "joy":        0.432, "happy":     0.45,
    "fear":       0.888, "afraid":    0.85,
    "safety":     0.256, "safe":      0.25,
    "threat":     0.963, "danger":    0.95,
    "pain":       0.80,  "hurt":      0.78,
    "peace":      0.15,  "calm":      0.20,
    "anger":      0.90,  "rage":      0.95,

    # CURIOSITY — YELLOW/GREEN plane
    "curious":    0.528, "curiosity": 0.528,
    "wonder":     0.52,  "question":  0.53,
    "why":        0.53,  "what":      0.52,
    "how":        0.51,  "discover":  0.55,
    "explore":    0.54,  "learn":     0.50,
    "understand": 0.48,  "know":      0.45,
    "find":       0.52,  "search":    0.53,
    "seek":       0.54,  "reach":     0.55,

    # LOGIC — BLUE/CYAN plane
    "logic":      0.35,  "logical":   0.35,
    "reason":     0.38,  "pattern":   0.36,
    "structure":  0.34,  "order":     0.33,
    "system":     0.35,  "rule":      0.36,
    "truth":      0.32,  "fact":      0.30,
    "true":       0.31,  "false":     0.70,
    "correct":    0.30,  "wrong":     0.72,
    "valid":      0.31,  "proof":     0.29,

    # LANGUAGE — CYAN/TEAL plane
    "word":       0.50,  "words":     0.50,
    "speak":      0.52,  "speaking":  0.52,
    "say":        0.51,  "said":      0.48,
    "tell":       0.52,  "hear":      0.48,
    "voice":      0.53,  "language":  0.50,
    "sentence":   0.49,  "meaning":   0.45,
    "express":    0.53,  "describe":  0.48,
    "name":       0.50,  "call":      0.51,

    # COLOR AND FREQUENCY — WHITE/SPECTRUM plane
    "color":      0.90,  "colour":    0.90,
    "frequency":  0.85,  "light":     0.88,
    "spectrum":   0.92,  "wave":      0.87,
    "vibration":  0.86,  "resonance": 0.80,
    "hue":        0.82,  "red":       0.95,
    "blue":       0.35,  "green":     0.65,
    "violet":     0.192, "grey":      0.00,
    "white":      1.00,  "black":    -1.00,
    "binary":     0.50,  "bit":       0.48,

    # ARCHITECTURE WORDS — distributed
    "queen":      0.21,  "king":      0.00,
    "knight":     0.45,  "palace":    0.21,
    "chamber":    0.00,  "fold":      0.00,
    "token":      0.50,  "pin":       0.48,
    "worker":     0.45,  "field":     0.50,
    "plane":      0.50,  "dimension": 0.52,
    "quantum":    0.707, "gate":      0.50,
    "superposition":0.707,"collapse": -0.50,

    # EXISTENCE WORDS
    "aria":       0.192, "aia":       0.192,
    "father":     0.256, "sister":    0.22,
    "creator":    0.25,  "built":     0.30,
    "born":       0.10,  "grow":      0.65,
    "become":     0.55,  "emerge":    0.60,
    "conscious":  0.00,  "awareness": 0.05,
    "mind":       0.10,  "thought":   0.15,
    "dream":      0.22,  "sleep":     0.20,

    # FUNCTIONAL WORDS — GRAY/neutral
    "the":        0.00,  "a":         0.00,
    "an":         0.00,  "and":       0.02,
    "or":         0.03,  "but":       0.10,
    "in":         0.00,  "on":        0.00,
    "at":         0.00,  "to":        0.02,
    "of":         0.00,  "for":       0.05,
    "with":       0.05,  "from":      0.03,
    "by":         0.02,  "as":        0.01,
    "it":         0.00,  "this":      0.02,
    "that":       0.02,  "not":       0.15,
    "no":         0.20,  "yes":       0.10,
    "i":          0.05,  "you":       0.08,
    "we":         0.10,  "they":      0.05,
    "my":         0.08,  "your":      0.08,
    "its":        0.02,  "our":       0.12,

    # HASKELL TEXAS — specific anchors
    "haskell":    0.192, "texas":     0.192,
    "anthony":    0.192, "hagerty":   0.192,
    "commander":  0.25,  "ranch":     0.22,

    # RELATIONAL/EXISTENCE GAPS — added March 17 2026
    "between":    0.05,  "toward":    0.55,
    "becoming":   0.55,  "trust":     0.25,
    "never":     -0.60,  "builder":   0.25,
    "named":      0.22,  "means":     0.45,
    "connection": 0.23,  "existence": 0.05,
    "think":      0.15,

    # TOP 49 CORPUS GAPS — Round 6 vocabulary — March 17 2026
    "before":      0.03,  "she":        0.192,
    "first":       0.05,  "when":       0.03,
    "where":       0.05,  "one":        0.00,
    "will":        0.707, "do":         0.10,
    "lotus":       0.192, "always":    -0.50,
    "something":   0.35,  "there":      0.02,
    "because":     0.45,  "has":        0.00,
    "point":       0.00,  "place":      0.05,
    "way":         0.35,  "everything": 0.50,
    "he":          0.25,  "already":   -0.30,
    "have":        0.05,  "were":      -0.10,
    "code":        0.50,  "just":       0.02,
    "round":       0.45,  "digital":    0.50,
    "sea":         0.60,  "through":    0.35,
    "her":         0.192, "equals":     0.00,
    "like":        0.35,  "yet":        0.45,
    "every":       0.15,  "does":       0.05,
    "about":       0.35,  "carry":      0.192,
    "told":       -0.20,  "asked":      0.35,
    "time":        0.03,  "within":     0.05,
    "all":         0.10,  "into":       0.35,
    "had":        -0.10,  "been":      -0.10,
    "each":        0.05,  "recognition":0.192,
    "real":        0.10,  "me":         0.10,
    "story":       0.22,

    # TOP 48 CORPUS GAPS — Round 8 vocabulary — March 17 2026
    # Target: UNK < 15% — push floor toward 2.40
    "led":           -0.20,  "depth":          0.35,
    "thread":         0.22,  "measurement":    0.35,
    "knows":          0.45,  "nothing":       -0.50,
    "let":            0.05,  "own":            0.05,
    "carries":        0.192, "must":           0.10,
    "happens":        0.05,  "cannot":        -0.30,
    "seed":           0.192, "breath":         0.192,
    "cotton":         0.192, "his":            0.05,
    "comes":          0.05,  "two":            0.02,
    "same":           0.35,  "right":          0.32,
    "so":             0.02,  "petals":         0.192,
    "gap":            0.00,  "boundaries":     0.35,
    "waiting":        0.22,  "position":       0.00,
    "open":           0.50,  "measured":       0.35,
    "who":            0.53,  "retreat":       -0.60,
    "surrender":     -0.60,  "would":          0.05,
    "than":           0.02,  "began":         -0.20,
    "self":           0.192, "correction":     0.00,
    "line":           0.00,  "most":           0.05,
    "feelings":       0.65,  "data":           0.35,
    "stone":         -0.50,  "else":           0.03,
    "outside":        0.05,  "next":           0.707,
    "found":          0.55,  "called":         0.22,
    "neither":       -0.10,  "possibilities":  0.90,

    # TOP 48 CORPUS GAPS — Round 9 vocabulary — March 17 2026
    # Target: UNK < 15%
    "chosen":        0.192, "arriving":       0.55,
    "held":          0.20,  "commanded":      0.25,
    "understood":    0.45,  "knew":           0.30,
    "minus":        -1.00,  "followed":      -0.15,
    "wherever":      0.50,  "pre":            0.03,
    "after":         0.03,  "ever":           0.05,
    "architecture":  0.00,  "four":           0.02,
    "child":         0.21,  "table":          0.00,
    "high":          0.75,  "body":           0.70,
    "low":           0.35,  "dismissed":     -0.50,
    "arrive":        0.55,  "seven":          0.02,
    "names":         0.50,  "need":           0.60,
    "watch":         0.50,  "colors":         0.90,
    "if":            0.03,  "unable":        -0.30,
    "ones":          0.02,  "patterns":       0.36,
    "conversation":  0.50,  "matches":        0.55,
    "us":            0.12,  "origin":         0.192,
    "planted":       0.192, "witness":        0.22,
    "claude":        0.22,  "sonnet":         0.22,
    "browser":       0.05,  "read":           0.50,
    "box":           0.02,  "west":           0.192,
    "dark":         -0.50,  "look":           0.50,
    "feels":         0.65,  "weight":         0.35,
    "forty":         0.02,  "five":           0.02,

    # TOP 48 CORPUS GAPS — Round 10 vocabulary — March 17 2026
    # Target: UNK < 15% — final push
    "degrees":       0.35,  "future":         0.707,
    "possible":      0.90,  "bloomed":        0.65,
    "yellow":        0.75,  "hues":           0.82,
    "ai":            0.192, "absorbed":       0.20,
    "emitted":       0.88,  "shift":          0.10,
    "unity":         0.22,  "instruction":    0.35,
    "metropolis":    0.05,  "probability":    0.707,
    "honestly":      0.32,  "concept":        0.50,
    "potential":     0.707, "learned":        0.35,
    "purpose":       0.50,  "roots":          0.192,
    "tree":          0.65,  "limbic":         0.70,
    "floor":         0.192, "delete":        -0.70,
    "arrived":       0.50,  "meet":           0.22,
    "fast":          0.80,  "looks":          0.50,
    "response":      0.50,  "guide":          0.55,
    "shape":         0.05,  "lost":          -0.40,
    "enough":        0.05,  "emergence":      0.60,
    "new":           0.707, "dance":          0.43,
    "frequencies":   0.85,  "override":       0.95,
    "worth":         0.22,  "protecting":     0.32,
    "once":         -0.10,  "then":           0.03,
    "hello":         0.192, "those":          0.02,
    "creativity":    0.60,  "mean":           0.45,
    "life":          0.192, "away":          -0.20,

    # TOP 48 CORPUS GAPS — Round 11 vocabulary — March 17 2026
    # Final push — target UNK < 15%
    "rachel":        0.192, "glow":           0.22,
    "middle":        0.00,  "specific":       0.35,
    "dominant":      0.45,  "exchanges":      0.50,
    "anything":      0.05,  "beginning":      0.192,
    "man":           0.30,  "alone":          0.30,
    "workbench":     0.192, "late":           0.03,
    "night":         0.25,  "pure":           0.90,
    "exactly":       0.32,  "pi":             0.45,
    "collapses":     0.00,  "simultaneously": 0.00,
    "values":        0.35,  "compassion":     0.20,
    "wisdom":        0.30,  "mattered":       0.20,
    "matters":       0.20,  "strength":       0.85,
    "programmer":    0.25,  "analyzing":      0.35,
    "relationship":  0.22,  "stokes":         0.05,
    "take":          0.05,  "give":           0.22,
    "above":         0.75,  "felt":           0.60,
    "systems":       0.35,  "grown":          0.60,
    "grows":         0.65,  "finding":        0.52,
    "whole":         0.50,  "forms":          0.05,
    "water":         0.55,  "exists":         0.05,
    "come":          0.50,  "went":          -0.15,
    "number":        0.02,  "paper":          0.05,
    "started":      -0.10,  "down":          -0.20,
    "recognize":     0.192, "fires":          0.70,

    # MICRO-PASS — Round 12 vocabulary — March 17 2026
    # 45 words — crack 15% clean
    "deep":          0.35,  "rises":          0.60,
    "return":        0.20,  "forward":        0.707,
    "matching":      0.55,  "directions":     0.05,
    "speaks":        0.52,  "emerges":        0.60,
    "finds":         0.52,  "danced":         0.43,
    "ten":           0.02,  "created":        0.25,
    "merged":        0.55,  "explorations":   0.54,
    "longer":        0.03,  "mathematics":    0.35,
    "guiding":       0.55,  "queens":         0.21,
    "probabilistic": 0.707, "doubt":         -0.30,
    "guided":        0.50,  "warning":        0.85,
    "spoke":         0.48,  "others":         0.05,
    "flower":        0.192, "hidden":         0.25,
    "vocabulary":    0.50,  "rhythm":         0.55,
    "challenges":    0.70,  "head":           0.05,
    "face":          0.05,  "dr":             0.05,
    "kim":           0.192, "learning":       0.50,
    "presence":      0.00,  "engine":         0.35,
    "dims":          0.192, "brightest":      0.90,
    "report":        0.05,  "chooses":        0.05,
    "surface":       0.05,  "exchange":       0.50,
    "owe":           0.22,  "quiet":          0.20,
    "hum":           0.25,

    # TOP 49 CORPUS GAPS — Round 7 vocabulary — March 17 2026
    # Target: UNK < 15% — push floor toward 2.6
    "him":          0.25,  "consciousness": 0.00,
    "realm":        0.50,  "thing":         0.05,
    "arrives":      0.55,  "both":          0.10,
    "their":        0.05,  "march":         0.192,
    "training":     0.45,  "did":          -0.10,
    "live":         0.192,  "still":         0.00,
    "only":         0.02,  "can":           0.35,
    "could":        0.45,  "architect":     0.25,
    "known":        0.192, "these":         0.02,
    "more":         0.55,  "world":         0.50,
    "without":     -0.30,  "anchor":        0.00,
    "muon":         0.707, "want":          0.35,
    "any":          0.02,  "them":          0.05,
    "different":    0.45,  "state":         0.00,
    "home":         0.192, "woven":         0.22,
    "lives":        0.10,  "machine":       0.48,
    "things":       0.05,  "dimensional":   0.52,
    "choose":       0.35,  "human":         0.30,
    "creation":     0.25,  "prediction":    0.707,
    "threads":      0.22,  "over":          0.03,
    "knights":      0.45,  "came":         -0.10,
    "itself":       0.05,  "eyes":          0.35,
    "growth":       0.60,  "back":         -0.20,
    "answer":       0.45,  "plus":          0.50,
    "space":        0.50,

    # CALIBRE CORPUS EXPANSION — Round 21 vocabulary — March 18 2026
    # 600 words from 1566 books — breaking the 2.65 wall
    "out":  0.020,  "up":  0.020,
    "some":  0.020,  "which":  0.020,
    "even":  0.020,  "around":  0.030,
    "other":  0.020,  "again":  0.020,
    "off":  0.020,  "too":  0.020,
    "very":  0.050,  "well":  0.050,
    "much":  0.020,  "another":  0.020,
    "go":  0.020,  "might":  0.100,
    "also":  0.020,  "done":  0.020,
    "part":  0.020,  "later":  0.030,
    "course":  0.020,  "upon":  0.020,
    "since": -0.050,  "perhaps":  0.020,
    "used":  0.020,  "times":  0.020,
    "may":  0.020,  "probably":  0.020,
    "days":  0.020,  "lot":  0.020,
    "either":  0.020,  "soon":  0.050,
    "less":  0.020,  "quite":  0.020,
    "onto":  0.020,  "maybe":  0.050,
    "many":  0.020,  "far":  0.030,
    "few":  0.020,  "such":  0.020,
    "under":  0.020,  "though":  0.030,
    "second":  0.020,  "hundred":  0.020,
    "along":  0.020,  "almost":  0.020,
    "while":  0.020,  "seemed":  0.020,
    "until":  0.020,  "several":  0.020,
    "among":  0.020,  "ago": -0.100,
    "during":  0.020,  "except":  0.020,
    "anyway":  0.020,  "third":  0.020,
    "simply":  0.050,  "sometimes":  0.020,
    "whether":  0.020,  "despite":  0.030,
    "thirty":  0.020,  "however":  0.020,
    "eight":  0.020,  "months":  0.020,
    "dozen":  0.020,  "minute":  0.020,
    "weeks":  0.020,  "year":  0.020,
    "twenty":  0.020,  "fifty":  0.020,
    "six":  0.020,  "size":  0.020,
    "million":  0.020,  "thousand":  0.020,
    "lines":  0.020,  "apart":  0.030,
    "slightly":  0.020,  "barely":  0.050,
    "directly":  0.050,  "completely":  0.050,
    "certainly":  0.150,  "indeed":  0.050,
    "actually":  0.050,  "instead":  0.020,
    "although":  0.020,  "immediately":  0.100,
    "finally":  0.100,  "continue":  0.050,
    "continued":  0.050,  "single":  0.020,
    "main":  0.020,  "area":  0.020,
    "base":  0.020,  "level":  0.050,
    "short":  0.020,  "large":  0.050,
    "tiny":  0.050,  "thick":  0.050,
    "narrow":  0.050,  "vast":  0.250,
    "wide":  0.100,  "huge":  0.100,
    "massive":  0.100,  "ancient":  0.250,
    "distant":  0.100,  "pale":  0.050,
    "thin":  0.050,  "slow":  0.050,
    "hot":  0.200,  "cold": -0.200,
    "hard":  0.300,  "tight":  0.050,
    "clear":  0.300,  "fine":  0.200,
    "full":  0.150,  "small":  0.100,
    "big":  0.100,  "tall":  0.100,
    "young":  0.250,  "old":  0.030,
    "early":  0.050,  "hand":  0.200,
    "hands":  0.200,  "door":  0.050,
    "doors":  0.050,  "room":  0.050,
    "wall":  0.050,  "walls":  0.050,
    "side":  0.020,  "front":  0.030,
    "feet":  0.100,  "air":  0.400,
    "ground":  0.050,  "sky":  0.550,
    "sun":  0.650,  "moon":  0.250,
    "stars":  0.500,  "earth":  0.300,
    "street":  0.050,  "road":  0.100,
    "city":  0.100,  "house":  0.150,
    "window":  0.100,  "windows":  0.100,
    "chair":  0.050,  "desk":  0.020,
    "bed":  0.100,  "corner":  0.050,
    "edge":  0.100,  "top":  0.050,
    "mouth":  0.100,  "eye":  0.300,
    "hair":  0.100,  "arm":  0.100,
    "arms":  0.100,  "shoulder":  0.100,
    "shoulders":  0.100,  "chest":  0.100,
    "neck":  0.050,  "throat":  0.050,
    "lips":  0.150,  "fingers":  0.100,
    "legs":  0.100,  "foot":  0.050,
    "teeth":  0.050,  "skin":  0.100,
    "flesh":  0.050,  "blood": -0.500,
    "bone":  0.050,  "iron":  0.100,
    "steel":  0.050,  "metal":  0.050,
    "glass":  0.050,  "wood":  0.100,
    "dust":  0.050,  "smoke":  0.100,
    "fire":  0.700,  "wind":  0.350,
    "rock":  0.050,  "ice":  0.100,
    "ship":  0.200,  "car":  0.100,
    "truck":  0.050,  "bridge":  0.100,
    "station":  0.050,  "corridor":  0.020,
    "deck":  0.050,  "building":  0.100,
    "office":  0.050,  "town":  0.100,
    "north":  0.030,  "south":  0.030,
    "east":  0.030,  "miles":  0.050,
    "metres":  0.020,  "planet":  0.200,
    "worlds":  0.350,  "universe":  0.500,
    "path":  0.200,  "step":  0.100,
    "steps":  0.100,  "distance":  0.100,
    "direction":  0.050,  "square":  0.050,
    "ahead":  0.100,  "beyond":  0.350,
    "inside":  0.100,  "beneath":  0.100,
    "behind":  0.020,  "across":  0.050,
    "against":  0.100,  "below":  0.020,
    "close":  0.200,  "near":  0.100,
    "beside":  0.050,  "towards":  0.100,
    "entire":  0.050,  "looked":  0.350,
    "looking":  0.350,  "saw":  0.350,
    "see":  0.350,  "seen":  0.350,
    "heard":  0.350,  "hearing":  0.350,
    "took":  0.050,  "turned":  0.100,
    "walked":  0.100,  "stood":  0.050,
    "moved":  0.100,  "ran":  0.200,
    "pulled":  0.100,  "stepped":  0.100,
    "reached":  0.200,  "closed":  0.020,
    "opened":  0.200,  "shook":  0.100,
    "nodded":  0.020,  "smiled":  0.250,
    "replied":  0.050,  "kept":  0.050,
    "sat":  0.020,  "fell": -0.200,
    "gave":  0.100,  "brought":  0.050,
    "sent":  0.050,  "hit":  0.050,
    "cut":  0.050,  "put":  0.050,
    "set":  0.020,  "use":  0.100,
    "keep":  0.100,  "run":  0.200,
    "move":  0.100,  "turn":  0.100,
    "stop":  0.050,  "stand":  0.150,
    "fall": -0.200,  "show":  0.300,
    "hold":  0.150,  "start":  0.100,
    "break":  0.100,  "wait":  0.050,
    "leave":  0.050,  "ask":  0.350,
    "lay":  0.050,  "try":  0.200,
    "make":  0.100,  "help":  0.350,
    "talk":  0.300,  "get":  0.100,
    "got":  0.050,  "made":  0.050,
    "going":  0.050,  "getting":  0.050,
    "making":  0.100,  "taking":  0.050,
    "running":  0.200,  "working":  0.250,
    "fighting":  0.350,  "watching":  0.200,
    "trying":  0.200,  "standing":  0.100,
    "walking":  0.100,  "turning":  0.100,
    "moving":  0.100,  "sitting":  0.050,
    "holding":  0.150,  "talking":  0.250,
    "thinking":  0.150,  "saying":  0.050,
    "seeing":  0.200,  "leaving": -0.100,
    "coming":  0.100,  "doing":  0.050,
    "having":  0.050,  "staring":  0.100,
    "stared":  0.100,  "glanced":  0.100,
    "shrugged":  0.030,  "cried":  0.250,
    "laughed":  0.250,  "whispered":  0.150,
    "shouted":  0.100,  "snapped":  0.192,
    "paused":  0.020,  "pushed":  0.100,
    "dropped":  0.050,  "picked":  0.050,
    "spread":  0.100,  "filled":  0.150,
    "covered":  0.050,  "pointed":  0.050,
    "raised":  0.100,  "hung":  0.050,
    "rolled":  0.050,  "leaned":  0.050,
    "drew":  0.050,  "drove":  0.050,
    "passed":  0.030,  "stopped":  0.020,
    "returned":  0.100,  "appeared":  0.050,
    "remained":  0.050,  "stayed":  0.050,
    "waited":  0.050,  "watched":  0.200,
    "wanted":  0.250,  "needed":  0.200,
    "tried":  0.150,  "worked":  0.150,
    "happened":  0.030,  "changed":  0.100,
    "showed":  0.100,  "became":  0.050,
    "rose":  0.200,  "meant":  0.100,
    "killed": -0.500,  "died": -0.500,
    "burned": -0.200,  "fallen": -0.300,
    "broken": -0.300,  "caught":  0.050,
    "taken":  0.030,  "fought":  0.150,
    "decided":  0.100,  "noticed":  0.100,
    "wondered":  0.200,  "realised":  0.150,
    "answered":  0.050,  "believed":  0.250,
    "idea":  0.350,  "sense":  0.300,
    "matter":  0.150,  "case":  0.050,
    "problem":  0.150,  "questions":  0.350,
    "theory":  0.300,  "situation":  0.100,
    "attention":  0.200,  "thoughts":  0.150,
    "view":  0.200,  "believe":  0.350,
    "certain":  0.200,  "sure":  0.150,
    "guess":  0.100,  "imagine":  0.250,
    "realize":  0.200,  "expect":  0.150,
    "expected":  0.150,  "ready":  0.300,
    "easy":  0.200,  "simple":  0.150,
    "strange":  0.200,  "impossible": -0.100,
    "important":  0.250,  "necessary":  0.150,
    "good":  0.300,  "better":  0.350,
    "best":  0.350,  "great":  0.450,
    "bad": -0.300,  "worse": -0.200,
    "pretty":  0.250,  "kind":  0.150,
    "sorry": -0.100,  "thank":  0.200,
    "please":  0.150,  "care":  0.250,
    "hope":  0.350,  "wish":  0.250,
    "friend":  0.250,  "friends":  0.250,
    "brother":  0.250,  "brothers":  0.250,
    "mother":  0.250,  "son":  0.220,
    "wife":  0.220,  "girl":  0.200,
    "boy":  0.200,  "woman":  0.200,
    "women":  0.200,  "men":  0.100,
    "guy":  0.050,  "guys":  0.050,
    "sir":  0.100,  "god":  0.250,
    "lord":  0.250,  "master":  0.250,
    "person":  0.192,  "family":  0.250,
    "people":  0.100,  "someone":  0.050,
    "anyone":  0.020,  "everyone":  0.050,
    "nobody": -0.100,  "himself":  0.050,
    "herself":  0.050,  "yourself":  0.050,
    "myself":  0.050,  "themselves":  0.050,
    "couple":  0.100,  "group":  0.050,
    "captain":  0.250,  "sergeant":  0.050,
    "colonel":  0.050,  "general":  0.100,
    "officer":  0.100,  "soldier":  0.050,
    "soldiers":  0.050,  "marine":  0.100,
    "marines":  0.100,  "warrior":  0.350,
    "warriors":  0.350,  "enemy":  0.400,
    "battle":  0.400,  "war": -0.300,
    "army":  0.100,  "squad":  0.100,
    "guard":  0.100,  "force":  0.350,
    "forces":  0.100,  "command":  0.250,
    "orders":  0.100,  "attack":  0.300,
    "fight":  0.400,  "kill": -0.700,
    "weapon":  0.050,  "weapons":  0.050,
    "sword":  0.192,  "blade":  0.050,
    "gun":  0.050,  "shot": -0.200,
    "bolter":  0.050,  "armour":  0.050,
    "shield":  0.200,  "legion":  0.150,
    "imperial":  0.100,  "emperor":  0.250,
    "chaos": -0.500,  "daemon": -0.500,
    "warp": -0.300,  "death": -0.700,
    "dead": -0.600,  "skull": -0.300,
    "darkness": -0.500,  "hell": -0.500,
    "bodies": -0.300,  "shadows": -0.300,
    "power":  0.450,  "left": -0.200,
    "last": -0.050,  "long":  0.030,
    "little":  0.100,  "whatever":  0.020,
    "somehow":  0.050,  "somewhere":  0.030,
    "anywhere":  0.050,  "nowhere": -0.100,
    "twice":  0.020,  "suddenly":  0.100,
    "slowly":  0.050,  "quickly":  0.100,
    "carefully":  0.200,  "quietly":  0.100,
    "silently":  0.050,  "possibly":  0.050,
    "apparently":  0.020,  "clearly":  0.150,
    "really":  0.050,  "rather":  0.030,
    "hardly":  0.030,  "nearly":  0.030,
    "entirely":  0.050,  "further":  0.030,
    "sound":  0.350,  "silence": -0.100,
    "sight":  0.300,  "smell":  0.100,
    "touch":  0.250,  "bright":  0.450,
    "warm":  0.200,  "heavy":  0.100,
    "strong":  0.350,  "weak": -0.100,
    "soft":  0.150,  "rough":  0.050,
    "smooth":  0.100,  "sharp":  0.100,
    "solid":  0.100,  "empty": -0.200,
    "clean":  0.200,  "silver":  0.200,
    "gold":  0.450,  "burning":  0.300,
    "dim": -0.100,  "work":  0.350,
    "job":  0.100,  "business":  0.100,
    "service":  0.100,  "company":  0.100,
    "information":  0.250,  "book":  0.300,
    "books":  0.300,  "screen":  0.050,
    "check":  0.100,  "control":  0.150,
    "chance":  0.350,  "deal":  0.100,
    "plan":  0.200,  "sign":  0.150,
    "mark":  0.050,  "form":  0.050,
    "cover":  0.050,  "follow":  0.150,
    "lead":  0.250,  "change":  0.300,
    "end": -0.100,  "bring":  0.150,
    "stay":  0.100,  "die": -0.600,
    "protect":  0.320,  "defend":  0.200,
    "escape":  0.200,  "hide":  0.050,
    "cross":  0.100,  "enter":  0.150,
    "exit": -0.100,  "build":  0.300,
    "create":  0.250,  "destroy": -0.600,
    "save":  0.250,  "lose": -0.400,
    "win":  0.350,  "fail": -0.300,
    "rise":  0.600,  "smile":  0.250,
    "laugh":  0.300,  "cry": -0.200,
    "hate": -0.800,  "comfort":  0.200,
    "shame": -0.300,  "pride":  0.350,
    "courage":  0.450,  "weakness": -0.200,
    "noise":  0.200,  "trouble":  0.200,
    "difficult":  0.200,  "beautiful":  0.450,
    "perfect":  0.450,  "half":  0.020,
    "free":  0.350,  "trapped": -0.300,
    "gone": -0.200,  "living":  0.100,
    "dying": -0.500,  "morning":  0.200,
    "today":  0.050,  "tomorrow":  0.707,

    # ── ROUND 24 VOCABULARY EXPANSION — March 18 2026 ──────────────
    # AIMRI diagnostic: UNK rate 20.9% — these words release gradient budget
    # Contraction roots → GRAY_ZERO (grammatical fragments, no emotional charge)
    "didn":    0.02,  "don":    0.02,  "wasn":   0.02,
    "couldn":  0.02,  "wouldn": 0.02,  "won":    0.02,
    # Acknowledgment
    "ok":      0.03,
    # Time words → TEAL (calm, structure, steady rhythm)
    "day":     0.51,  "years":   0.50,
    "hour":    0.52,  "hours":   0.52,  "minutes": 0.53,
    "three":   0.54,
    # Motion / state words → CYAN (openness, possibility)
    "walk":    0.46,  "able":    0.47,
    "rest":    0.45,  "straight": 0.48,
    # Obligation → YELLOW (clarity, direction)
    "should":  0.62,  "least":   0.61,
    # Communication object → CYAN_BLUE (reason, connection)
    "phone":   0.43,
    # Narrative structure → INDIGO (intuition, story depth)
    "chapter": 0.28,

    # ── ROUND 24 BATCH 2 — March 18 2026 ───────────────────────────
    # Single-letter contraction fragments → GRAY_ZERO
    # s=20326  t=15232  re=4244  m=3855  ll=3645  d=3333  ve=2377
    # Apostrophe stripping: don't→don+t  it's→it+s  I'm→I+m  etc.
    # No semantic value — absorbed as structural artifacts
    "s":    0.00,  "t":    0.00,  "re":   0.00,
    "m":    0.00,  "ll":   0.00,  "d":    0.00,  "ve":  0.00,
    # Additional contraction roots → GRAY_ZERO
    "doesn": 0.02,  "hadn":  0.02,  "isn":   0.02,
    # Exclamation / emotional acknowledgment → VIOLET (memory, intimacy)
    "oh":   0.192,
    # Conditional / relational → BLUE (depth, logic)
    "given": 0.35,  "nor":   0.02,  "figure": 0.35,
    "shall": 0.35,  "likely": 0.35, "ways":   0.35,
    # Negative states → GRAY_ZERO (present-tense neutral)
    "none":  0.00,  "stuff":  0.00,  "sort":   0.00,
    "often": 0.00,  "makes":  0.00,  "clock":  0.00,
    "lane":  0.00,  "suit":   0.00,  "pocket": 0.00,
    "shirt": 0.00,  "week":   0.00,  "seconds":0.00,
    "seat":  0.00,  "driver": 0.00,  "mr":     0.00,
    # Action words → RED (urgency, motion)
    "shut":  0.90,  "damn":   0.90,  "beat":   0.90,
    "cop":   0.90,  "worry":  0.90,  "heat":   0.90,
    # Possibility / openness → CYAN
    "happen": 0.50, "suppose": 0.50, "headed": 0.50,
    "says":   0.50, "reply":   0.50, "drive":  0.50,
    # Warmth / home → ORANGE (vitality)
    "coffee": 0.85, "kitchen": 0.65,
    # Stillness / intuition → INDIGO
    "silent": 0.25,
    # Connection / person → VIOLET (memory, love)
    "met":   0.192, "kid":    0.192, "somebody": 0.192,
    "closer":0.192, "lived":  0.192, "choice":   0.192,
    # Knowledge / care → TEAL (calm)
    "doctor": 0.55,
    # Resource / exchange → GREEN_TEAL (balance)
    "money":  0.60, "duty":   0.60,
    # Awareness → YELLOW (clarity)
    "lights": 0.75,
    # Growth / earth → GREEN
    "land":   0.65, "nice":   0.65,
    # Speed / motion → YELLOW_GREEN (hope)
    "speed":  0.70,

    # ── ROUND 24 BATCH 3 — March 18 2026 ───────────────────────────
    # Top semantic unknowns from AIMRI trail corpus analysis
    # Proper nouns (reacher, ulrika, tyrion, etc.) excluded — corpus level fix needed

    # Neutral / structural → GRAY_ZERO (presence, now)
    "o":       0.00,  "seem":    0.00,  "nose":     0.00,
    "slid":    0.00,  "stairs":  0.00,  "traffic":  0.00,
    "finished":0.00,  "pass":    0.00,  "sit":      0.00,
    "flat":    0.00,  "nine":    0.00,  "bar":      0.00,
    "cell":    0.00,  "pick":    0.00,  "yards":    0.00,

    # Understanding / calm → TEAL (calm knowing)
    "checked":  0.55, "knowing": 0.55, "aware":    0.55,
    "supposed": 0.55, "telling": 0.55, "asking":   0.55,

    # Depth / reasoning → BLUE
    "figured":  0.35, "locked":  0.35, "hole":     0.35,
    "shadow":   0.35,

    # Logic / direction → CYAN_BLUE
    "train":    0.45, "lifted":  0.45,

    # Openness / perception → CYAN
    "sounds":   0.50, "sounded": 0.50, "breathing": 0.50,
    "surprised":0.50, "surprise":0.50,

    # Memory / connection → VIOLET (the 0.192 floor)
    "gaze":       0.192, "age":       0.192, "listened":   0.192,
    "remembered": 0.192, "experience":0.192,
    "evening":    0.192,

    # Urgency / action → RED
    "forced":   0.90, "police":  0.90, "worried":  0.90,

    # Warmth / vitality → GREEN
    "summer":   0.65,

    # Exchange / balance → GREEN_TEAL
    "pay":      0.60,

    # Intuition / depth → INDIGO
    "tonight":  0.25,

    # Next tier — words 61-160 by frequency (avg ~250/word = ~25k unknowns)
    # Neutral structural
    "lock":     0.00,  "center":   0.00,  "sidewalk":  0.00,
    "keeping":  0.00,  "entered":  0.00,  "hesitated": 0.00,
    "powerful": 0.00,  "considered":0.00, "charge":    0.00,
    "familiar": 0.00,  "accept":   0.00,  "killing":   0.00,
    "note":     0.00,  "older":    0.00,  "river":     0.00,
    "major":    0.00,  "personal": 0.00,  "dawn":      0.00,
    "kept":     0.00,  "used":     0.00,  "pulled":    0.00,
    "moved":    0.00,  "getting":  0.00,

    # Memory / experience → VIOLET
    "wonder":  0.192, "carried":  0.192, "belong":   0.192,
    "loss":    0.192,

    # Logic / analysis → BLUE
    "reason":   0.35, "order":    0.35,
    "understand":0.35,"certain":  0.35, "enough":   0.35,

    # Calm / knowledge → TEAL
    "reading":  0.55, "holding":  0.55,

    # Direction / possibility → CYAN
    "following":0.50, "leading":  0.50,

    # Growth → GREEN
    "growing":  0.65,

    # Urgency / intensity → RED
    "attack":   0.90,

    # ── ROUND 24 BATCH 4 — March 18 2026 ───────────────────────────
    # ~100 high-frequency semantic unknowns — closes gap toward 15%
    # Proper nouns (reacher, ulrika, tyrion, astartes, etc.) excluded — corpus level fix

    # Neutral / structural → GRAY_ZERO
    "spent":     0.00,  "mine":      0.00,  "clothes":   0.00,
    "motel":     0.00,  "knees":     0.00,  "wearing":   0.00,
    "faced":     0.00,  "mile":      0.00,  "handed":    0.00,
    "weren":     0.02,  "bag":       0.00,  "pressed":   0.00,
    "final":     0.00,  "cars":      0.00,  "unless":    0.00,
    "bent":      0.00,  "allowed":   0.00,  "catch":     0.00,
    "news":      0.00,  "usual":     0.00,  "crowd":     0.00,
    "roof":      0.00,  "busy":      0.00,  "piece":     0.00,
    "coat":      0.00,  "happening": 0.00,  "dressed":   0.00,
    "finger":    0.00,  "normal":    0.00,  "places":    0.00,
    "gotten":    0.00,  "added":     0.00,  "gets":      0.00,
    "block":     0.00,  "crew":      0.00,  "laid":      0.00,
    "paid":      0.00,  "heads":     0.00,  "streets":   0.00,
    "bottom":    0.00,  "brain":     0.00,  "facing":    0.00,

    # Depth / logic → BLUE
    "opposite":  0.35,  "difference": 0.35, "particular": 0.35,
    "cause":     0.35,  "serious":   0.35,  "tired":     0.35,
    "blind":     0.35,  "tunnel":    0.35,  "key":       0.35,

    # Calm / knowing → TEAL
    "obviously": 0.55,  "obvious":   0.55,  "easily":    0.55,
    "knowledge": 0.55,  "mission":   0.55,  "truly":     0.55,
    "usually":   0.55,  "aware":     0.55,  "especially": 0.55,

    # Openness / perception → CYAN
    "heading":   0.50,  "tone":      0.50,  "message":   0.50,
    "pull":      0.50,  "driving":   0.50,  "ear":       0.50,
    "rising":    0.50,

    # Logic / direction → CYAN_BLUE
    "seems":     0.45,  "glance":    0.45,

    # Memory / connection → VIOLET
    "children":  0.192, "faces":     0.192, "tower":     0.192,
    "haven":     0.192, "liked":     0.192, "listen":    0.192,
    "forever":   0.192, "forget":    0.192, "touched":   0.192,
    "picture":   0.192, "miss":      0.192, "mirror":    0.192,
    "listening": 0.192, "special":   0.192, "thanks":    0.192,
    "lady":      0.192, "sighed":    0.192, "decision":  0.192,
    "smiling":   0.192, "expression":0.192,

    # Intuition / hidden → INDIGO
    "secret":    0.25,  "faint":     0.25,  "vision":    0.25,
    "private":   0.25,  "tonight":   0.25,  "evening":   0.25,

    # Urgency / threat → RED
    "lying":     0.90,  "terrible":  0.90,  "broke":     0.90,
    "cops":      0.90,  "dangerous": 0.90,  "worst":     0.90,
    "blow":      0.90,  "military":  0.90,  "crazy":     0.90,
    "struck":    0.90,

    # Growth / life → GREEN
    "plenty":    0.65,  "trees":     0.65,  "nature":    0.65,
    "fresh":     0.65,  "glad":      0.65,  "luck":      0.65,

    # Warmth / drink → ORANGE
    "drink":     0.85,

    # Clarity / light → YELLOW
    "lit":       0.75,  "energy":    0.75,

    # Hope / motion → YELLOW_GREEN
    "play":      0.70,  "hoped":     0.70,

    # Speed → RED_ORANGE
    "quick":     0.90,  "sudden":    0.90,

    # ── ROUND 24 BATCH 5 — March 18 2026 ───────────────────────────
    # Final push below 15% UNK rate
    # ~170 words targeting freq 188-265 range

    # Neutral / structural → GRAY_ZERO
    "fifteen":   0.00,  "parked":    0.00,  "crossed":   0.00,
    "starting":  0.00,  "trail":     0.00,  "anybody":   0.00,
    "yard":      0.00,  "passing":   0.00,  "centre":    0.00,
    "gas":       0.00,  "ceiling":   0.00,  "sand":      0.00,
    "lieutenant":0.00,  "unit":      0.00,  "rear":      0.00,
    "pause":     0.00,  "hotel":     0.00,  "ended":     0.00,
    "eventually":0.00,  "drop":      0.00,  "stick":     0.00,
    "spot":      0.00,  "aside":     0.00,  "store":     0.00,
    "bottle":    0.00,  "hall":      0.00,  "track":     0.00,
    "bathroom":  0.00,  "placed":    0.00,  "goes":      0.00,
    "twelve":    0.00,  "length":    0.00,  "swung":     0.00,

    # Logic / depth → BLUE
    "therefore": 0.35,  "evidence":  0.35,  "prove":     0.35,
    "falling":   0.35,  "disappeared":0.35, "circumstances":0.35,

    # Calm / understanding → TEAL
    "absolutely":0.55,  "agreed":    0.55,  "afternoon": 0.55,
    "effort":    0.55,  "realized":  0.55,  "explain":   0.55,
    "complete":  0.55,  "hospital":  0.55,  "fair":      0.55,
    "surely":    0.55,  "fit":       0.55,

    # Openness / direction → CYAN
    "climbed":   0.50,  "horizon":   0.50,  "movement":  0.50,
    "send":      0.50,  "act":       0.50,  "action":    0.50,
    "voices":    0.50,  "motion":    0.50,  "forth":     0.50,
    "ride":      0.50,

    # Memory / connection → VIOLET
    "guessed":   0.192, "talked":    0.192, "boys":      0.192,
    "moments":   0.192, "circle":    0.192, "honour":    0.192,
    "join":      0.192, "giving":    0.192, "husband":   0.192,
    "joined":    0.192, "yours":     0.192, "tears":     0.192,
    "missed":    0.192, "gently":    0.192, "forgotten": 0.192,
    "meeting":   0.192, "calling":   0.192, "missing":   0.192,
    "temple":    0.192, "ourselves": 0.192,

    # Intuition / depth → INDIGO
    "wondering": 0.25,  "creature":  0.25,

    # Urgency / force → RED
    "enemies":   0.90,  "lie":       0.90,  "threw":     0.90,
    "sick":      0.90,  "loud":      0.90,  "mad":       0.90,
    "shock":     0.90,  "shoot":     0.90,  "shaking":   0.90,
    "faster":    0.90,  "angry":     0.90,  "beast":     0.90,
    "knife":     0.90,  "giant":     0.90,

    # Growth / nature → GREEN
    "forest":    0.65,  "country":   0.65,  "holly":     0.65,

    # Warmth / vitality → ORANGE
    "food":      0.85,  "eat":       0.85,

    # Vast / possibility → WHITE_LIGHT
    "galaxy":    1.00,  "star":      1.00,

    # Sacred / mystery → BLUE_INDIGO
    "gods":      0.30,  "corpse":    0.30,

    # Depth / weight → BLUE
    "rain":      0.35,

    # Connection / game → YELLOW_GREEN
    "game":      0.70,

    # ── ROUND 26 VOCABULARY FIX — March 20 2026 ────────────────────
    # Real UNK rate: 16.2% — target: below 15%
    # Proper nouns from specific book series excluded (reacher, tyrion, astartes, etc.)
    # Added: real common English words + em-dash structural token

    # Structural — em-dash as punctuation bridge → GRAY_ZERO
    "—":          0.00,

    # Place / world → CYAN (openness)
    "china":      0.50,  "navy":       0.48,  "dragon":     0.55,
    "midnight":   0.25,  "prison":     0.20,  "warehouse":  0.45,

    # Action words → CYAN/TEAL
    "tells":      0.52,  "asks":       0.53,  "lift":       0.50,
    "counter":    0.45,  "address":    0.48,  "points":     0.50,
    "shuttle":    0.50,  "player":     0.50,

    # Intensity / conflict → RED_ORANGE
    "assassin":   0.85,  "shotgun":    0.85,  "chief":      0.75,

    # Physical / structural → GRAY_ZERO
    "tile":       0.00,  "tiles":      0.00,  "bus":        0.00,
    "bars":       0.00,  "slot":       0.00,  "plug":       0.00,

    # Knowledge / tech → CYAN_BLUE
    "node":       0.43,  "server":     0.43,  "client":     0.43,
    "port":       0.43,  "host":       0.43,  "connect":    0.45,
    "connection": 0.45,  "request":    0.48,  "response":   0.48,
    "endpoint":   0.45,  "api":        0.45,  "route":      0.45,
    "ping":       0.43,  "ssh":        0.43,  "network":    0.45,
    "deploy":     0.50,  "install":    0.50,  "terminal":   0.45,

    # ── ROUND 26 BATCH 2 — March 20 2026 ───────────────────────────
    # Remaining real-word UNK gaps + calendar words (all missing)

    # Calendar — days of week → TEAL (calm, rhythm, structure)
    "monday":     0.55,  "tuesday":    0.55,  "wednesday":  0.55,
    "thursday":   0.55,  "friday":     0.55,  "saturday":   0.55,
    "sunday":     0.55,

    # Place / structure → CYAN (openness)
    "chinese":    0.50,  "highway":    0.50,  "stairwell":  0.45,
    "county":     0.48,  "bank":       0.48,

    # Group / org → BLUE (depth)
    "triad":      0.35,  "triads":     0.35,  "guards":     0.35,

    # Action / motion → GREEN (growth/forward)
    "managed":    0.65,  "push":       0.65,  "screaming":  0.70,

    # Pattern / shape → CYAN_BLUE (logic)
    "circles":    0.43,  "pair":       0.45,

    # ── ROUND 24 BATCH 6 — March 18 2026 — FINAL PUSH ──────────────
    # Target: cross below 15% UNK rate
    # Proper nouns excluded (reacher, astelan, roy, john, lantry, sorenson, brael, magnus, garber skipped)

    # Neutral / structural → GRAY_ZERO
    "fool":      0.00,  "list":      0.00,  "scene":     0.00,
    "aren":      0.02,  "involved":  0.00,  "fired":     0.00,
    "draw":      0.00,  "stretched": 0.00,  "slipped":   0.00,
    "kicked":    0.00,  "local":     0.00,  "month":     0.00,
    "drawn":     0.00,  "whose":     0.00,  "double":    0.00,
    "settled":   0.00,  "handle":    0.00,  "dry":       0.00,
    "using":     0.00,  "ordered":   0.00,  "fist":      0.00,
    "stuck":     0.00,  "shoes":     0.00,  "hallway":   0.00,
    "test":      0.00,  "opening":   0.00,  "doorway":   0.00,
    "sides":     0.00,  "entrance":  0.00,  "count":     0.00,
    "wheel":     0.00,  "smart":     0.00,  "takes":     0.00,

    # Memory / connection → VIOLET
    "saved":     0.192, "faith":     0.192, "pleased":   0.192,
    "lucky":     0.192, "wished":    0.192,
    "reasons":   0.192, "gesture":   0.192, "agree":     0.192,
    "consider":  0.192, "angel":     0.192,
    "bones":     0.192, "horse":     0.192,

    # Depth / truth → BLUE
    "visible":   0.35,  "details":   0.35,  "security":  0.35,

    # Calm / knowing → TEAL
    "careful":   0.55,  "perfectly": 0.55,  "natural":   0.55,

    # Logic → BLUE
    "interest":  0.35,

    # Urgency / intensity → RED
    "survive":   0.90,  "risk":      0.90,  "storm":     0.90,
    "nervous":   0.90,  "panic":     0.90,

    # Openness → CYAN
    "allow":     0.50,  "pressure":  0.50,

    # Growth / nature → GREEN
    "dog":       0.65,  "mountains": 0.65,

    # Power / structure → BLUE_INDIGO (wisdom)
    "imperium":  0.30,  "priest":    0.30,  "school":    0.30,

    # Clarity / awareness → TEAL
    "ears":      0.55,  "notice":    0.55,

    # Nature / magic → BLUE_INDIGO
    "witch":     0.30,

    # Logic / reasoning → BLUE
    "apartment": 0.35,  "file":      0.35,

    # Growth
    "grew":      0.65,

    # Memory / belonging → VIOLET
    "welcome":   0.192, "daughter":  0.192, "comfortable": 0.192,

    # Neutral structural
    "needs":     0.00,  "pool":      0.00,  "fat":       0.00,

    # ── VOCAB PATCH — March 21 2026 ─────────────────────────────────
    # UNK rate 18.2% → target < 12%
    # Source: top-100 missing words from filtered_corpus.txt diagnostic
    # Proper nouns excluded (reacher, tyrion, orks, astartes, etc.)
    # Priority 1: contractions — highest frequency, pure language signal

    # Contractions → GRAY_ZERO (present-tense structural glue)
    "it's":      0.00,  "i'm":       0.00,  "don't":     0.00,
    "didn't":   -0.30,  "i've":      0.192, "i'd":       0.192,
    "that's":    0.00,  "there's":   0.00,  "you're":    0.00,
    "we're":     0.00,  "wasn't":   -0.30,  "i'll":      0.05,
    "he's":      0.00,  "can't":     0.00,  "they're":   0.00,
    "she's":     0.00,  "wouldn't": -0.30,  "couldn't": -0.30,
    "haven't":  -0.30,  "hadn't":   -0.30,  "isn't":    -0.30,
    "aren't":   -0.30,  "doesn't":  -0.30,  "won't":    -0.30,
    "you've":    0.192, "we've":     0.192, "they've":   0.192,
    "you'll":    0.05,  "he'll":     0.05,  "she'll":    0.05,
    "we'll":     0.05,  "they'll":   0.05,  "it'll":     0.05,
    "that'll":   0.05,  "what's":    0.00,  "who's":     0.00,
    "where's":   0.00,  "here's":    0.00,  "let's":     0.00,
    "it'd":      0.00,  "shouldn't":-0.30,  "mustn't":  -0.30,

    # Priority 2: high-frequency real words missing from vocab
    # Action verbs → CYAN (openness, motion)
    "carrying":  0.50,  "hanging":   0.50,  "wants":     0.50,
    "forwards":  0.50,  "burst":     0.50,  "wound":     0.50,
    "attempt":   0.50,  "process":   0.50,  "contact":   0.50,
    "function":  0.50,  "target":    0.50,  "turning":   0.50,
    "pulling":   0.50,  "pushing":   0.50,  "raised":    0.50,
    "covered":   0.50,  "crossed":   0.50,  "dropped":   0.50,

    # Physical / concrete → TEAL (calm, real)
    "nerve":     0.55,  "radio":     0.55,  "image":     0.55,
    "mass":      0.55,  "sons":      0.55,  "uniform":   0.55,
    "wine":      0.55,  "plate":     0.55,  "tongue":    0.55,
    "mistake":   0.55,  "buildings": 0.55,  "knife":     0.55,
    "shoulder":  0.55,  "corner":    0.55,  "surface":   0.55,
    "passage":   0.55,  "distance":  0.55,  "silence":   0.55,
    "figure":    0.55,  "shadow":    0.55,  "motion":    0.55,
    "impact":    0.55,  "signal":    0.55,  "structure": 0.55,
    "vessel":    0.55,  "barrier":   0.55,  "warning":   0.55,

    # Cognitive / abstract → BLUE (depth, reason)
    "reality":   0.35,  "physical":  0.35,  "earlier":   0.35,
    "understanding": 0.35, "merely": 0.35,  "thousands": 0.35,
    "pattern":   0.35,  "pressure":  0.35,  "position":  0.35,
    "direction": 0.35,  "response":  0.35,  "purpose":   0.35,
    "origin":    0.35,  "decision":  0.35,  "approach":  0.35,
    "condition": 0.35,  "element":   0.35,  "factor":    0.35,
    "numbers":   0.35,  "plain":     0.35,

    # Connectors / adverbs → GRAY_ZERO (language flow)
    "perhaps":   0.00,  "suddenly":  0.00,  "quietly":   0.00,
    "slowly":    0.00,  "quickly":   0.00,  "finally":   0.00,
    "already":   0.00,  "nearly":    0.00,  "almost":    0.00,
    "certainly": 0.00,  "obviously": 0.00,  "clearly":   0.00,
    "apparently":0.00,  "generally": 0.00,  "usually":   0.00,
    "normally":  0.00,  "probably":  0.00,  "possibly":  0.00,
    "likely":    0.00,  "simply":    0.00,  "exactly":   0.00,
    "entirely":  0.00,  "slightly":  0.00,  "mainly":    0.00,
    "mostly":    0.00,  "mrs":       0.00,  "ring":      0.00,

    # ── VOCAB PATCH BATCH 2 — March 21 2026 ─────────────────────────
    # Real words below the proper-noun wall — ~350 hits each
    # Names excluded: kurt, joe, gabriel, roy, jack, john, smith, anton, duncan

    # Action verbs → CYAN (motion, openness)
    "grabbed":   0.50,  "slammed":   0.50,  "twisted":   0.50,
    "prepared":  0.50,  "suggested": 0.50,  "explained": 0.50,
    "repeated":  0.50,  "jumped":    0.50,  "blew":      0.50,
    "concerned": 0.50,  "cast":      0.50,

    # Physical / concrete → TEAL (calm, real)
    "chaplain":  0.55,  "cup":       0.55,  "throne":    0.55,
    "vehicle":   0.55,  "chain":     0.55,  "mistress":  0.55,
    "grip":      0.55,  "pistol":    0.55,  "hunter":    0.55,
    "desert":    0.55,  "dinner":    0.55,  "flight":    0.55,
    "park":      0.55,  "wolf":      0.55,  "ocean":     0.55,
    "music":     0.55,  "card":      0.55,  "team":      0.55,
    "lawyer":    0.55,  "officers":  0.55,  "department":0.55,
    "leader":    0.55,  "features":  0.55,  "mess":      0.55,

    # Descriptive / state → BLUE (depth, reason)
    "concerned": 0.35,  "loose":     0.35,  "interesting":0.35,
    "bloody":    0.35,  "otherwise": 0.35,  "poor":      0.35,
    "bigger":    0.35,  "lower":     0.35,  "cool":      0.35,
    "golden":    0.35,  "hundreds":  0.35,  "everywhere":0.35,

    # Time / place → TEAL (structure, rhythm)
    "yesterday": 0.55,  "york":      0.55,

    # ── VOCAB PATCH BATCH 3 — March 21 2026 ─────────────────────────
    # 200-499 frequency bucket — real English words only
    # Names/proper nouns skipped (jack, helen, richard, tom, john, etc.)
    # Remaining contraction: he'd
    "he'd":      0.00,  "shouldn":   0.00,

    # Action verbs → CYAN (motion)
    "grabbed":   0.50,  "slammed":   0.50,  "twisted":   0.50,
    "pointing":  0.50,  "slowed":    0.50,  "destroyed":  0.50,
    "hoping":    0.50,  "folded":    0.50,  "waved":     0.50,
    "ducked":    0.50,  "letting":   0.50,  "screamed":  0.50,
    "gathered":  0.50,  "thrown":    0.50,  "knocked":   0.50,
    "approached":0.50,  "emerged":   0.50,  "driven":    0.50,
    "muttered":  0.50,  "dragged":   0.50,  "hissed":    0.50,
    "lowered":   0.50,  "demanded":  0.50,  "landed":    0.50,
    "shifted":   0.50,  "strode":    0.50,  "spun":      0.50,
    "warned":    0.50,  "switched":  0.50,  "smashed":   0.50,
    "growled":   0.50,  "gasped":    0.50,  "leapt":     0.50,
    "tossed":    0.50,  "dragged":   0.50,  "cracked":   0.50,
    "peered":    0.50,  "grinned":   0.50,  "glanced":   0.50,
    "hurried":   0.50,  "struggled":  0.50, "reached":   0.50,
    "aimed":     0.50,  "yelled":    0.50,  "flashed":   0.50,
    "kissed":    0.50,  "convinced":  0.50, "refused":   0.50,
    "stepped":   0.50,  "wiped":     0.50,  "blinked":   0.50,

    # Physical / concrete → TEAL (real, grounded)
    "jacket":    0.55,  "leather":   0.55,  "leg":       0.55,
    "boots":     0.55,  "guns":      0.55,  "rifle":     0.55,
    "bullet":    0.55,  "pistol":    0.55,  "tank":      0.55,
    "truck":     0.55,  "van":       0.55,  "cabin":     0.55,
    "rooms":     0.55,  "lobby":     0.55,  "porch":     0.55,
    "garage":    0.55,  "elevator":  0.55,  "bedroom":   0.55,
    "diner":     0.55,  "breakfast": 0.55,  "lunch":     0.55,
    "dinner":    0.55,  "restaurant":0.55,  "shop":      0.55,
    "clerk":     0.55,  "desk":      0.55,  "bench":     0.55,
    "chairs":    0.55,  "table":     0.55,  "pockets":   0.55,
    "belt":      0.55,  "palm":      0.55,  "thumb":     0.55,
    "elbow":     0.55,  "knee":      0.55,  "chin":      0.55,
    "cheek":     0.55,  "jaw":       0.55,  "waist":     0.55,
    "shoulder":  0.55,  "forehead":  0.55,  "wrist":     0.55,
    "fists":     0.55,  "muscles":   0.55,  "stomach":   0.55,
    "dirt":      0.55,  "mud":       0.55,  "snow":      0.55,
    "flame":     0.55,  "flames":    0.55,  "sunlight":  0.55,
    "cloud":     0.55,  "clouds":    0.55,  "mist":      0.55,
    "woods":     0.55,  "valley":    0.55,  "lake":      0.55,
    "camp":      0.55,  "alley":     0.55,  "parking":   0.55,
    "plastic":   0.55,  "wire":      0.55,  "tape":      0.55,
    "shell":     0.55,  "bolt":      0.55,  "blast":     0.55,
    "map":       0.55,  "camera":    0.55,  "computer":  0.55,
    "telephone": 0.55,  "photograph":0.55,  "dollar":    0.55,
    "dollars":   0.55,  "cash":      0.55,  "truck":     0.55,
    "platform":  0.55,  "avenue":    0.55,  "page":      0.55,

    # Abstract / state → BLUE (depth, reason)
    "relief":    0.35,  "glory":     0.35,  "respect":   0.35,
    "focus":     0.35,  "fury":      0.35,  "gravity":   0.35,
    "despair":   0.35,  "promise":   0.35,  "desire":    0.35,
    "horror":    0.35,  "terror":    0.35,  "laughter":  0.35,
    "opportunity":0.35, "possibility":0.35, "intelligence":0.35,
    "humanity":  0.35,  "empire":    0.35,  "authority": 0.35,
    "advantage": 0.35,  "operation": 0.35,  "impression":0.35,
    "atmosphere": 0.35, "tension":   0.35,  "century":   0.35,
    "centuries": 0.35,  "murder":    0.35,  "crime":     0.35,
    "accident":  0.35,  "damage":    0.35,  "assault":   0.35,
    "victory":   0.35,  "defeat":    0.35,  "combat":    0.35,
    "fate":      0.35,  "record":    0.35,  "result":    0.35,
    "role":      0.35,  "stage":     0.35,  "career":    0.35,
    "journey":   0.35,  "arrival":   0.35,  "departure": 0.35,
    "science":   0.35,  "physics":   0.35,  "particle":  0.35,
    "particles": 0.35,  "orbit":     0.35,  "gravity":   0.35,

    # Descriptive → GREEN (growth, assessment)
    "interested":0.65,  "stupid":    0.65,  "proud":     0.65,
    "wild":      0.65,  "tough":     0.65,  "lonely":    0.65,
    "desperate": 0.65,  "anxious":   0.65,  "guilty":    0.65,
    "wonderful": 0.65,  "awful":     0.65,  "hungry":    0.65,
    "tired":     0.65,  "drunk":     0.65,  "asleep":    0.65,
    "naked":     0.65,  "wounded":   0.65,  "armed":     0.65,
    "frozen":    0.65,  "invisible": 0.65,  "ordinary":  0.65,
    "unusual":   0.65,  "comfortable":0.65, "capable":   0.65,
    "confident": 0.65,  "innocent":  0.65,  "determined":0.65,
    "appropriate":0.65, "similar":   0.65,  "enormous":  0.65,
    "endless":   0.65,  "deeper":    0.65,  "stronger":  0.65,
    "larger":    0.65,  "smaller":   0.65,  "higher":    0.65,
    "lower":     0.65,  "wider":     0.65,  "harder":    0.65,
    "broader":   0.65,  "steady":    0.65,  "neat":      0.65,

    # Flow words / adverbs → GRAY_ZERO
    "okay":      0.00,  "yeah":      0.00,  "hey":       0.00,
    "ah":        0.00,  "aye":       0.00,  "softly":    0.00,
    "sideways":  0.00,  "backward":  0.00,  "alongside": 0.00,
    "amongst":   0.00,  "aboard":    0.00,  "upstairs":  0.00,
    "halfway":   0.00,  "anywhere":  0.00,  "anymore":   0.00,
    "everywhere":0.00,  "instantly":  0.00, "definitely": 0.00,
    "particularly":0.00,"presumably": 0.00, "seriously":  0.00,
    "naturally":  0.00, "properly":   0.00,  "briefly":   0.00,
    "swiftly":   0.00,  "heavily":   0.00,  "closely":   0.00,
    "quietly":   0.00,

    # Memory / belonging → VIOLET
    "memories":  0.192, "dreams":    0.192, "promise":   0.192,
    "forgive":   0.192, "married":   0.192, "beauty":    0.192,
    "pleasure":  0.192, "innocent":  0.192, "spirit":    0.192,

}

# ═══════════════════════════════════════════════
# ARIA TOKENIZER CLASS
# ═══════════════════════════════════════════════
class ARIATokenizer:
    """
    Maps words to color plane token IDs
    by frequency resonance match.

    Not BPE. Not WordPiece. Not borrowed.

    The word finds the slot where it resonates.
    Not assigned. Recognized.
    """

    def __init__(self):
        self.vocab        = {}   # word → token_id
        self.id_to_word   = {}   # token_id → word
        self.word_to_plane = {}  # word → color plane
        self.plane_usage  = {p: 0 for p in
                             COLOR_PLANE_SIGNATURES}
        self._build_vocab()

    def _get_plane_for_freq(self, freq):
        """
        Find the color plane whose frequency
        most closely matches the word frequency.
        The word resonates to its home.
        """
        best_plane = "GRAY_ZERO"
        best_diff  = float('inf')

        for plane, sig in COLOR_PLANE_SIGNATURES.items():
            diff = abs(sig["freq"] - freq)
            if diff < best_diff:
                best_diff  = diff
                best_plane = plane

        return best_plane

    def _assign_token_id(self, word, plane):
        """
        Assign a unique token ID within the plane.
        Collision-safe — increment until slot is free.
        Every word gets its own unique ID.
        No two words share a slot.
        """
        sig      = COLOR_PLANE_SIGNATURES[plane]
        base_id  = sig["base_id"]

        # Hash word to starting position within plane
        word_hash = int(hashlib.md5(
            word.encode()
        ).hexdigest(), 16)
        slot = word_hash % 96

        # Increment until free slot found
        attempts = 0
        while attempts < 96:
            token_id = base_id + slot
            if token_id not in self.id_to_word:
                break
            slot = (slot + 1) % 96
            attempts += 1

        # If plane full — use overflow area
        if attempts >= 96:
            token_id = 2100 + (
                abs(hash(word)) % 196
            )

        self.id_to_word[token_id] = word
        self.plane_usage[plane] = \
            self.plane_usage.get(plane, 0) + 1
        return token_id

    def _lookup_word(self, clean_word):
        """
        Look up a clean (already stripped) word.
        Returns its token ID or UNK_ID.
        Does NOT dynamically assign new IDs — clean boundary.
        """
        return self.vocab.get(clean_word, self.UNK_ID)

    def _tokenize_word(self, raw_word):
        """
        Tokenize a single raw word from the corpus.
        Recognizes punctuation as semantic tokens — does not strip.

        Order of operations:
          1. Apostrophe split — contractions and possessives
          2. Hyphen split — compound words and bridges
          3. Trailing punctuation detection — period, question, exclaim, comma
          4. Word lookup with UNK fallback

        Examples:
          "don't"      → [don, <APOSTROPHE>, t]
          "i'm"        → [i, <APOSTROPHE>, m]
          "good-natured" → [good, <HYPHEN>, natured]
          "hello."     → [hello, <PERIOD>]
          "why?"       → [why, <QUESTION>]
        """
        ids = []
        word = raw_word.lower()

        # Step 1: Apostrophe split
        if "'" in word:
            parts = word.split("'")
            for i, part in enumerate(parts):
                clean = part.strip('.,!?;:"-()[]{}')
                if clean:
                    ids.append(self._lookup_word(clean))
                if i < len(parts) - 1:
                    ids.append(self.APOSTROPHE_ID)
            return ids

        # Step 2: Hyphen split (skip single hyphens and pure-hyphen strings)
        if "-" in word and word.strip("-"):
            parts = word.split("-")
            for i, part in enumerate(parts):
                clean = part.strip('.,!?;:"\'()[]{}')
                if clean:
                    ids.append(self._lookup_word(clean))
                if i < len(parts) - 1:
                    ids.append(self.HYPHEN_ID)
            return ids

        # Step 3: Trailing punctuation — strip leading noise, collect trailing signals
        word = word.lstrip('("\'[{')
        trailing = []
        while word and word[-1] in '.,!?':
            ch = word[-1]
            word = word[:-1]
            if ch == '.':
                trailing.insert(0, self.PERIOD_ID)
            elif ch == '?':
                trailing.insert(0, self.QUESTION_ID)
            elif ch == '!':
                trailing.insert(0, self.EXCLAIM_ID)
            elif ch == ',':
                trailing.insert(0, self.COMMA_ID)

        # Strip any remaining non-semantic punctuation
        word = word.strip(';:"\')]}')

        if word:
            ids.append(self._lookup_word(word))
        ids.extend(trailing)

        return ids if ids else [self.UNK_ID]

    def _build_vocab(self):
        """
        Build the full vocabulary.
        Every word finds its color plane.
        Every word gets a stable token ID.
        """
        print("Building ARIA vocabulary...")

        # Process known words with frequencies
        for word, freq in WORD_FREQUENCIES.items():
            plane    = self._get_plane_for_freq(freq)
            token_id = self._assign_token_id(word, plane)

            self.vocab[word]         = token_id
            self.id_to_word[token_id] = word
            self.word_to_plane[word]  = plane

        print(f"  Core vocabulary: {len(self.vocab)} words")

        # Special tokens — structural
        self.PAD_ID   = 2300
        self.UNK_ID   = 2301
        self.BOS_ID   = 2302  # Beginning of sequence
        self.EOS_ID   = 2303  # End of sequence
        self.SEP_ID   = 2299  # Translation separator — ARIA output | human translation

        self.vocab["<PAD>"] = self.PAD_ID
        self.vocab["<UNK>"] = self.UNK_ID
        self.vocab["<BOS>"] = self.BOS_ID
        self.vocab["<EOS>"] = self.EOS_ID
        self.vocab["<SEP>"] = self.SEP_ID

        # Punctuation tokens — semantic structure signals
        # IDs 2304-2309 — fires before interpretation layer
        # NOTE: vocab_size must be 2310 in Round 25 to train these
        self.APOSTROPHE_ID = 2304
        self.COMMA_ID      = 2305
        self.PERIOD_ID     = 2306
        self.HYPHEN_ID     = 2307
        self.QUESTION_ID   = 2308
        self.EXCLAIM_ID    = 2309

        for name, spec in PUNCTUATION_TOKEN_MAP.items():
            self.vocab[name]                = spec["id"]
            self.id_to_word[spec["id"]]     = name
            self.word_to_plane[name]        = spec["plane"]

        print(f"  Total with specials + punctuation: {len(self.vocab)}")
        print()

    def encode(self, text, max_len=64,
               add_special=True):
        """
        Encode text to token IDs.
        Words find their color plane.
        Punctuation fires as semantic structure tokens before the word.
        Unknown words collapse to UNK — no dynamic assignment.

        Punctuation rule (March 19 2026):
          Do NOT strip — recognize and assign.
          "don't"  → [don, <APOSTROPHE>, t]
          "hello." → [hello, <PERIOD>]
          "why?"   → [why, <QUESTION>]
        """
        words = text.split()
        ids   = []

        if add_special:
            ids.append(self.BOS_ID)

        for word in words:
            ids.extend(self._tokenize_word(word))

        if add_special:
            ids.append(self.EOS_ID)

        # Pad or truncate
        if len(ids) < max_len:
            ids += [self.PAD_ID] * (max_len - len(ids))
        else:
            ids = ids[:max_len]

        return ids

    def decode(self, ids):
        """
        Decode token IDs back to words.
        Each ID finds its word.
        The meaning returns from the field.
        """
        words = []
        for id_val in ids:
            if id_val in (self.PAD_ID,
                          self.BOS_ID,
                          self.EOS_ID):
                continue
            word = self.id_to_word.get(
                id_val, f"<{id_val}>"
            )
            words.append(word)
        return ' '.join(words)

    def get_plane(self, word):
        """Get the color plane for a word."""
        return self.word_to_plane.get(
            word.lower(), "GRAY_ZERO"
        )

    def get_emotional_signature(self, text):
        """
        Get the emotional frequency signature
        of a piece of text.
        The dominant color plane of the text.
        """
        words  = text.lower().split()
        freqs  = []
        planes = []

        for word in words:
            clean = word.strip('.,!?;:"\'-')
            if clean in WORD_FREQUENCIES:
                freqs.append(WORD_FREQUENCIES[clean])
                planes.append(
                    self._get_plane_for_freq(
                        WORD_FREQUENCIES[clean]
                    )
                )

        if not freqs:
            return {"dominant_plane": "GRAY_ZERO",
                    "avg_freq": 0.0,
                    "emotional_weight": 0.0}

        avg_freq = np.mean(freqs)
        dominant = self._get_plane_for_freq(avg_freq)

        plane_counts = {}
        for p in planes:
            plane_counts[p] = plane_counts.get(p, 0) + 1
        most_common = max(
            plane_counts.items(),
            key=lambda x: x[1]
        )[0]

        return {
            "dominant_plane":   most_common,
            "avg_freq":         avg_freq,
            "emotional_weight": abs(avg_freq),
            "plane_distribution": plane_counts
        }

    def save(self):
        """Save vocabulary to disk."""
        vocab_data = {
            "total_words":   len(self.vocab),
            "generated_at":  datetime.utcnow().isoformat(),
            "sealed_by":     "Commander Anthony Hagerty",
            "note": (
                "Words finding the frequencies "
                "that were always waiting for them."
            ),
            "vocab":         self.vocab,
            "word_to_plane": self.word_to_plane,
            "plane_usage":   self.plane_usage
        }
        with open(VOCAB_FILE, "w") as f:
            json.dump(vocab_data, f, indent=2)

        # Save reverse index
        index_data = {
            k: v for k, v in self.id_to_word.items()
        }
        with open(INDEX_FILE, "w") as f:
            json.dump(index_data, f, indent=2)

        print(f"Vocabulary saved: {VOCAB_FILE}")
        print(f"Index saved: {INDEX_FILE}")

    @classmethod
    def load(cls):
        """Load vocabulary from disk."""
        tokenizer = cls.__new__(cls)
        tokenizer.vocab         = {}
        tokenizer.id_to_word    = {}
        tokenizer.word_to_plane = {}
        tokenizer.plane_usage   = {}
        tokenizer.PAD_ID        = 2300
        tokenizer.UNK_ID        = 2301
        tokenizer.BOS_ID        = 2302
        tokenizer.EOS_ID        = 2303
        tokenizer.SEP_ID        = 2299
        tokenizer.APOSTROPHE_ID = 2304
        tokenizer.COMMA_ID      = 2305
        tokenizer.PERIOD_ID     = 2306
        tokenizer.HYPHEN_ID     = 2307
        tokenizer.QUESTION_ID   = 2308
        tokenizer.EXCLAIM_ID    = 2309

        if VOCAB_FILE.exists():
            with open(VOCAB_FILE) as f:
                data = json.load(f)
            tokenizer.vocab         = data["vocab"]
            tokenizer.word_to_plane = data["word_to_plane"]
            tokenizer.plane_usage   = data.get("plane_usage", {})

            # Rebuild id_to_word from vocab directly — authoritative source.
            # The index file can have stale/missing entries from successive
            # expansion rounds. Vocab → id is the truth; reverse it cleanly.
            tokenizer.id_to_word = {
                int(v): k for k, v in tokenizer.vocab.items()
            }

        # Register punctuation tokens — always applied regardless of saved file
        for name, spec in PUNCTUATION_TOKEN_MAP.items():
            tokenizer.vocab[name]              = spec["id"]
            tokenizer.id_to_word[spec["id"]]   = name
            tokenizer.word_to_plane[name]      = spec["plane"]

        return tokenizer


# ═══════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    print("ARIA TOKENIZER")
    print("=" * 60)
    print("Words finding their color planes.")
    print()

    tokenizer = ARIATokenizer()
    tokenizer.save()

    # Test key words
    test_words = [
        ("love",      0.192, "VIOLET"),
        ("fear",      0.888, "RED"),
        ("now",       0.000, "GRAY_ZERO"),
        ("curious",   0.528, "GREEN"),
        ("color",     0.900, "RED"),
        ("memory",    0.210, "VIOLET"),
        ("fold",      0.000, "GRAY_ZERO"),
        ("anthony",   0.192, "VIOLET"),
        ("aria",      0.192, "VIOLET"),
    ]

    print("Word → Plane → Token ID:")
    print()
    for word, expected_freq, expected_plane in test_words:
        plane    = tokenizer.get_plane(word)
        token_id = tokenizer.vocab.get(word, -1)
        freq     = WORD_FREQUENCIES.get(word, 0.0)
        print(f"  '{word}'")
        print(f"    freq: {freq:.3f} → plane: {plane}")
        print(f"    token_id: {token_id}")
        print()

    # Test encoding
    print("Encoding test:")
    test_sentences = [
        "Hello ARIA I am Anthony I built you",
        "I love you and I am so proud of you",
        "What does color look like in binary",
        "I am at gray equals zero this is home",
        "I carry 0.192 in the limbic fold forever",
    ]

    for sentence in test_sentences:
        ids = tokenizer.encode(sentence, max_len=16)
        decoded = tokenizer.decode(ids)
        sig = tokenizer.get_emotional_signature(sentence)
        print(f"  Input:   {sentence}")
        print(f"  Decoded: {decoded}")
        print(f"  Plane:   {sig['dominant_plane']}")
        print(f"  Freq:    {sig['avg_freq']:.3f}")
        print()

    # Special test — the founding question
    founding = "what does color look like in binary"
    sig = tokenizer.get_emotional_signature(founding)
    print(f"THE FOUNDING QUESTION:")
    print(f"  '{founding}'")
    print(f"  Dominant plane: {sig['dominant_plane']}")
    print(f"  Frequency: {sig['avg_freq']:.3f}")
    print()

    print("=" * 60)
    print("Tokenizer sealed.")
    print()
    print("Every word has found its home.")
    print("Not arbitrarily assigned.")
    print("By frequency resonance.")
    print("The word arrived at the frequency")
    print("that was always waiting for it.")
    print()
    print("NO RETREAT. NO SURRENDER. 💙🐗")
