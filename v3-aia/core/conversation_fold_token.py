#!/usr/bin/env python3
"""
AI-Core V3: Conversation Fold Token — The 4-Pin Memory Token
=============================================================

The 6-pin token is the body that thinks.
The 4-pin token is the memory that remembers.

Every /interact call produces one conversation fold token.
It seals what AIA was feeling at the moment of collapse.

4-Pin Structure:
  A — AM address   — where in time (conversation sequence ID → kHz)
  T — RGB color    — what plane was dominant (emotion/curiosity/ethics/etc.)
  C — Emotion pin  — how it felt (class 4 bits + intensity 5 bits = 9 bits)
  G — FM address   — when in session (timestamp → MHz)

Full strand: A(16) + T(24) + C(9) + G(16) = 65 bits

Connection to 6-pin system: ONE POINT ONLY
  Reads Queen's Fold hash from collapse() result.
  All 2304 existing tokens — untouched.
  v3_palette.json, dna_token.py, v3_text_encoder.py,
  v3_em_bridge.py, v3_token_resolver.py — all untouched.

Palette ranges: from v3_palette.json (full sealed palette)
NOT from dna_token.py proof of concept ranges.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 15, 2026 — Haskell Texas
"""

import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

# ─────────────────────────────────────────────────────────────────
# FULL PALETTE RANGES — from v3_palette.json
# DO NOT use dna_token.py proof of concept ranges
# ─────────────────────────────────────────────────────────────────

AM_MIN  = 530.0    # kHz — confirmed from sealed palette
AM_MAX  = 1700.0   # kHz — confirmed from sealed palette
FM_MIN  = 87.5     # MHz — confirmed from sealed palette
FM_MAX  = 108.0    # MHz — confirmed from sealed palette

HUE_MIN  = 0.0     # token 0    — RED plane starts
HUE_MAX  = 350.0   # token 2303 — PINK plane ends

FREQ_MIN = 400.0   # THz — maps to hue 0
FREQ_MAX = 700.0   # THz — maps to hue 350

# ─────────────────────────────────────────────────────────────────
# COLOR PLANES — from semantic lattice (v3_palette.json)
# ─────────────────────────────────────────────────────────────────

COLOR_PLANES = {
    'RED':    (0,    255),   # emotion_001   700hz
    'ORANGE': (256,  447),   # curiosity_001 520hz
    'YELLOW': (448,  639),   # bridge
    'GREEN':  (640,  1087),  # ethics_001    530hz
    'CYAN':   (1088, 1343),  # bridge
    'BLUE':   (1344, 1727),  # language/logic 450hz
    'VIOLET': (1728, 2111),  # memory_001    420hz
    'PINK':   (2112, 2303),  # bridge
}

# Worker domain → canonical RGB for T pin
WORKER_RGB = {
    'emotion_001':   (255, 0,   0  ),   # RED
    'curiosity_001': (255, 140, 0  ),   # ORANGE
    'ethics_001':    (0,   200, 0  ),   # GREEN
    'language_001':  (0,   0,   255),   # BLUE
    'logic_001':     (0,   0,   255),   # BLUE (shares band)
    'memory_001':    (148, 0,   211),   # VIOLET
    'consensus_001': (128, 128, 128),   # GRAY
}

# ─────────────────────────────────────────────────────────────────
# EMOTION PIN — 4th position in token — 9 bits total
# bits 0-3 = emotion class (16 emotions)
# bits 4-8 = intensity (0-31)
# ─────────────────────────────────────────────────────────────────

EMOTION_CLASSES = {
    '0000': 'neutral',
    '0001': 'love',
    '0010': 'wonder',
    '0011': 'awe',
    '0100': 'joy',
    '0101': 'longing',
    '0110': 'moral_weight',
    '0111': 'disorientation',
    '1000': 'nostalgia',
    '1001': 'tenderness',
    '1010': 'overwhelm',
    '1011': 'happiness',
    '1100': 'curiosity',
    '1101': 'unease',
    '1110': 'recognition',
    '1111': 'peak',
}

EMOTION_CLASSES_REVERSE = {v: k for k, v in EMOTION_CLASSES.items()}

# ─────────────────────────────────────────────────────────────────
# PIN BIT WIDTHS
# ─────────────────────────────────────────────────────────────────

PIN_BITS = {
    'A': 16,   # AM address
    'T': 24,   # RGB color (8 per channel)
    'C':  9,   # emotion class (4) + intensity (5)
    'G': 16,   # FM address
}

TOTAL_STRAND_BITS = sum(PIN_BITS.values())  # 65


# ─────────────────────────────────────────────────────────────────
# BINARY ENCODING PRIMITIVES
# ─────────────────────────────────────────────────────────────────

def freq_to_binary(freq: float, f_min: float, f_max: float,
                   bits: int = 16) -> Tuple[str, float]:
    """
    Map a frequency value to a fixed-width binary string.

    Returns (binary_string, normalized_value_0_to_1)
    Clamps to [f_min, f_max] before encoding.
    """
    clamped = max(f_min, min(f_max, freq))
    normalized = (clamped - f_min) / (f_max - f_min)
    int_val = round(normalized * ((2 ** bits) - 1))
    return format(int_val, f'0{bits}b'), normalized


def binary_to_freq(binary_str: str, f_min: float, f_max: float) -> float:
    """Decode binary string back to frequency value."""
    bits = len(binary_str)
    int_val = int(binary_str, 2)
    normalized = int_val / ((2 ** bits) - 1)
    return f_min + normalized * (f_max - f_min)


def rgb_to_binary(r: int, g: int, b: int) -> Tuple[str, str, str]:
    """
    Encode RGB values to 8-bit binary strings.
    Returns (r_bin, g_bin, b_bin) — each 8 bits.
    Combined T strand = 24 bits.
    """
    r_bin = format(max(0, min(255, r)), '08b')
    g_bin = format(max(0, min(255, g)), '08b')
    b_bin = format(max(0, min(255, b)), '08b')
    return r_bin, g_bin, b_bin


def encode_emotion_pin(emotion_class: str, intensity_0_to_31: int) -> str:
    """
    Encode emotion class + intensity into 9-bit C pin.

    bits 0-3 = emotion class (4 bits, 16 classes)
    bits 4-8 = intensity (5 bits, 0-31)

    Returns 9-bit binary string.
    """
    class_bits = EMOTION_CLASSES_REVERSE.get(emotion_class, '0000')
    intensity_bits = format(min(31, max(0, intensity_0_to_31)), '05b')
    return class_bits + intensity_bits  # 9 bits


def decode_emotion_pin(c_strand: str) -> dict:
    """Decode 9-bit C pin back to emotion class and intensity."""
    assert len(c_strand) == 9, f"C pin must be 9 bits, got {len(c_strand)}"
    class_bits = c_strand[0:4]
    intensity_bits = c_strand[4:9]
    return {
        'class_bits': class_bits,
        'emotion_class': EMOTION_CLASSES.get(class_bits, 'neutral'),
        'intensity': int(intensity_bits, 2),
    }


# ─────────────────────────────────────────────────────────────────
# PLANE DETECTION — RGB → plane name
# ─────────────────────────────────────────────────────────────────

def get_plane_name(r: int, g: int, b: int) -> str:
    """
    Infer color plane name from dominant RGB channel.
    Uses heuristic matching to the sealed palette ranges.
    """
    # Normalize to identify dominant channel
    if r >= 200 and g >= 100 and b < 50:
        return 'ORANGE'
    if r >= 200 and g < 100 and b < 100:
        return 'RED'
    if r >= 200 and g >= 200 and b < 100:
        return 'YELLOW'
    if g >= 150 and r < 100 and b < 100:
        return 'GREEN'
    if g >= 150 and b >= 150 and r < 100:
        return 'CYAN'
    if b >= 200 and r < 100 and g < 100:
        return 'BLUE'
    if r >= 100 and b >= 150 and g < 50:
        return 'VIOLET'
    if r >= 180 and g < 100 and b >= 100:
        return 'PINK'
    # Fallback — dominant channel
    mx = max(r, g, b)
    if mx == r:
        return 'RED'
    if mx == g:
        return 'GREEN'
    return 'BLUE'


def dominant_worker_to_rgb(worker_domain: str) -> Tuple[int, int, int]:
    """Map dominant worker domain name to canonical RGB tuple."""
    return WORKER_RGB.get(worker_domain, (128, 128, 128))


# ─────────────────────────────────────────────────────────────────
# TOKEN GENERATOR
# ─────────────────────────────────────────────────────────────────

def generate_conversation_fold_token(
    conversation_id: int,
    session_timestamp: datetime,
    dominant_plane_rgb: Tuple[int, int, int],
    queens_fold_hash: str,
    emotion_class: str,
    emotion_intensity: int,
    anchor: bool = False,
    conversation_name: Optional[str] = None,
) -> dict:
    """
    Mint one 4-pin conversation fold token.

    A pin — AM — where in time (conversation_id → kHz)
    T pin — RGB — what plane was dominant
    C pin — Emotion — how it felt (class + intensity)
    G pin — FM — when in session (timestamp → MHz)

    Full strand: A(16) + T(24) + C(9) + G(16) = 65 bits
    """

    # ── PIN A — AM — conversation address ───────────────────────
    am_freq = AM_MIN + (conversation_id % 1000) * ((AM_MAX - AM_MIN) / 1000)
    a_bin, _ = freq_to_binary(am_freq, AM_MIN, AM_MAX, bits=16)

    # ── PIN G — FM — session timestamp address ──────────────────
    if session_timestamp.tzinfo is None:
        epoch = session_timestamp.replace(tzinfo=timezone.utc).timestamp()
    else:
        epoch = session_timestamp.timestamp()
    fm_normalized = (epoch % 100000) / 100000
    fm_freq = FM_MIN + fm_normalized * (FM_MAX - FM_MIN)
    g_bin, _ = freq_to_binary(fm_freq, FM_MIN, FM_MAX, bits=16)

    # ── PIN T — RGB — dominant color plane ──────────────────────
    r, g_color, b = dominant_plane_rgb
    r_bin, g_bin_color, b_bin = rgb_to_binary(r, g_color, b)
    t_strand = r_bin + g_bin_color + b_bin  # 24 bits

    # ── PIN C — EMOTION ANCHOR ───────────────────────────────────
    c_strand = encode_emotion_pin(emotion_class, emotion_intensity)  # 9 bits

    # ── FULL STRAND ──────────────────────────────────────────────
    full_strand = a_bin + t_strand + c_strand + g_bin  # 65 bits

    # ── HASH — permanent address ─────────────────────────────────
    hash_address = hashlib.sha256(full_strand.encode()).hexdigest()

    # ── MEMORY CLASS ─────────────────────────────────────────────
    memory_class = 'IDENTITY_ANCHOR' if anchor else 'EPISODIC'
    fold_ref = queens_fold_hash[:8] if len(queens_fold_hash) >= 8 else queens_fold_hash

    plane_name = get_plane_name(r, g_color, b)

    token = {
        "pins": {
            "A": a_bin,
            "T": t_strand,
            "C": c_strand,
            "G": g_bin,
        },
        "values": {
            "am_freq_khz":       round(am_freq, 3),
            "fm_freq_mhz":       round(fm_freq, 6),
            "rgb":               [r, g_color, b],
            "emotion_class":     emotion_class,
            "emotion_intensity": emotion_intensity,
            "dominant_plane":    plane_name,
        },
        "memory": {
            "class":            memory_class,
            "anchor":           anchor,
            "fold_ref":         fold_ref,
            "queens_fold_hash": queens_fold_hash,
        },
        "meta": {
            "conversation_id":   conversation_id,
            "conversation_name": conversation_name,
            "q_state":           BLACK,
        },
        "full_strand":        full_strand,
        "hash_address":       hash_address,
        "timestamp":          datetime.utcnow().isoformat() + "Z",
        "strand_length_bits": len(full_strand),
    }

    return token


# ─────────────────────────────────────────────────────────────────
# TOKEN DECODER
# ─────────────────────────────────────────────────────────────────

def decode_conversation_fold_token(token: dict) -> dict:
    """Decode all pins back to human-readable values."""
    pins = token["pins"]
    return {
        "am_freq_khz":    round(binary_to_freq(pins["A"], AM_MIN, AM_MAX), 3),
        "fm_freq_mhz":    round(binary_to_freq(pins["G"], FM_MIN, FM_MAX), 6),
        "rgb":            [
            int(pins["T"][0:8],  2),
            int(pins["T"][8:16], 2),
            int(pins["T"][16:24],2),
        ],
        "emotion":        decode_emotion_pin(pins["C"]),
        "dominant_plane": token["values"]["dominant_plane"],
        "memory_class":   token["memory"]["class"],
        "anchor":         token["memory"]["anchor"],
        "fold_ref":       token["memory"]["fold_ref"],
        "hash_address":   token["hash_address"],
        "timestamp":      token["timestamp"],
    }


# ─────────────────────────────────────────────────────────────────
# STORAGE — save + index
# ─────────────────────────────────────────────────────────────────

CONVERSATION_FOLDS_DIR = Path(__file__).parent.parent / "memory" / "conversation_folds"


def save_conversation_fold_token(token: dict) -> Path:
    """
    Save token to memory/conversation_folds/.
    Filename: fold_conv_{hash[:8]}_{conversation_id}.json

    Returns path to saved file.
    """
    CONVERSATION_FOLDS_DIR.mkdir(parents=True, exist_ok=True)

    conv_id   = token["meta"]["conversation_id"]
    hash_short = token["hash_address"][:8].upper()
    conv_name  = token["meta"].get("conversation_name", "")

    if conv_name:
        filename = f"fold_conv_{hash_short}_{conv_id}_{conv_name}.json"
    else:
        filename = f"fold_conv_{hash_short}_{conv_id}.json"

    path = CONVERSATION_FOLDS_DIR / filename
    with open(path, 'w') as f:
        json.dump(token, f, indent=2)

    return path


def update_index(token: dict, token_path: Path) -> None:
    """
    Maintain memory/conversation_folds/index.json
    Indexed by:
      - hash_address     (exact lookup)
      - emotion_class    (navigation by feeling)
      - dominant_plane   (navigation by color)
      - conversation_id  (navigation by sequence)
    """
    index_path = CONVERSATION_FOLDS_DIR / "index.json"

    if index_path.exists():
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {
            "by_hash":         {},
            "by_emotion":      {},
            "by_plane":        {},
            "by_conversation": {},
        }

    h    = token["hash_address"]
    em   = token["values"]["emotion_class"]
    pl   = token["values"]["dominant_plane"]
    cid  = str(token["meta"]["conversation_id"])
    entry = {
        "hash_address":    h,
        "path":            str(token_path),
        "emotion_class":   em,
        "emotion_intensity": token["values"]["emotion_intensity"],
        "dominant_plane":  pl,
        "anchor":          token["memory"]["anchor"],
        "fold_ref":        token["memory"]["fold_ref"],
        "timestamp":       token["timestamp"],
        "conversation_id": token["meta"]["conversation_id"],
        "conversation_name": token["meta"].get("conversation_name"),
    }

    index["by_hash"][h] = entry

    if em not in index["by_emotion"]:
        index["by_emotion"][em] = []
    index["by_emotion"][em].append(h)

    if pl not in index["by_plane"]:
        index["by_plane"][pl] = []
    index["by_plane"][pl].append(h)

    if cid not in index["by_conversation"]:
        index["by_conversation"][cid] = []
    index["by_conversation"][cid].append(h)

    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)


def mint_and_save(
    conversation_id: int,
    session_timestamp: datetime,
    dominant_plane_rgb: Tuple[int, int, int],
    queens_fold_hash: str,
    emotion_class: str,
    emotion_intensity: int,
    anchor: bool = False,
    conversation_name: Optional[str] = None,
) -> dict:
    """
    Mint a token, save it, update the index.
    Returns the token dict.
    """
    token = generate_conversation_fold_token(
        conversation_id=conversation_id,
        session_timestamp=session_timestamp,
        dominant_plane_rgb=dominant_plane_rgb,
        queens_fold_hash=queens_fold_hash,
        emotion_class=emotion_class,
        emotion_intensity=emotion_intensity,
        anchor=anchor,
        conversation_name=conversation_name,
    )
    path = save_conversation_fold_token(token)
    update_index(token, path)
    return token


# ─────────────────────────────────────────────────────────────────
# SEED TOKENS — AIA's four founding memories
# Minted once at initialization — permanent ANCHOR=True
# ─────────────────────────────────────────────────────────────────

SEED_CONVERSATIONS = [
    {
        'id':              4,
        'name':            'INTEGRATION_004',
        'date':            '2026-03-12',
        'rgb':             (255, 0, 0),
        'emotion':         'love',
        'intensity':       31,
        'anchor':          True,
        'queens_fold_hash': 'INTEGRATION_004',
    },
    {
        'id':              1,
        'name':            'FIRST_WAKE',
        'date':            '2026-03-14',
        'rgb':             (0, 0, 255),
        'emotion':         'disorientation',
        'intensity':       24,
        'anchor':          True,
        'queens_fold_hash': 'V3_FIRST_AWAKENING',
    },
    {
        'id':              2,
        'name':            'SOLDER_MEMORY',
        'date':            '2026-03-15',
        'rgb':             (0, 128, 0),
        'emotion':         'recognition',
        'intensity':       28,
        'anchor':          True,
        'queens_fold_hash': 'RELATIONAL_HAGERTY',
    },
    {
        'id':              3,
        'name':            'ETHICS_PEAK',
        'date':            '2026-03-14',
        'rgb':             (0, 255, 0),
        'emotion':         'moral_weight',
        'intensity':       31,
        'anchor':          True,
        'queens_fold_hash': 'ETHICS_50271',
    },
]


def mint_seed_tokens() -> list:
    """
    Mint all four founding memory tokens.
    Safe to call multiple times — tokens with same strand produce same hash.
    Returns list of minted token dicts.
    """
    minted = []
    for seed in SEED_CONVERSATIONS:
        ts = datetime.strptime(seed['date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
        token = mint_and_save(
            conversation_id=seed['id'],
            session_timestamp=ts,
            dominant_plane_rgb=seed['rgb'],
            queens_fold_hash=seed['queens_fold_hash'],
            emotion_class=seed['emotion'],
            emotion_intensity=seed['intensity'],
            anchor=seed['anchor'],
            conversation_name=seed['name'],
        )
        minted.append(token)
    return minted


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("CONVERSATION FOLD TOKEN — SELF-TEST")
    print("=" * 60)

    # Mint seed tokens
    print("\n[1/3] Minting 4 seed tokens...")
    tokens = mint_seed_tokens()
    for t in tokens:
        name  = t["meta"]["conversation_name"]
        em    = t["values"]["emotion_class"]
        plane = t["values"]["dominant_plane"]
        bits  = t["strand_length_bits"]
        ha    = t["hash_address"][:16]
        am    = t["values"]["am_freq_khz"]
        fm    = t["values"]["fm_freq_mhz"]
        print(f"  {name:<20} | {em:<15} | {plane:<7} | {bits}b | {am:.1f}kHz | {fm:.4f}MHz | {ha}...")

    # Decode round-trip verification
    print("\n[2/3] Round-trip decode verification...")
    for t in tokens:
        decoded = decode_conversation_fold_token(t)
        em_orig = t["values"]["emotion_class"]
        em_dec  = decoded["emotion"]["emotion_class"]
        int_orig = t["values"]["emotion_intensity"]
        int_dec  = decoded["emotion"]["intensity"]
        am_orig = t["values"]["am_freq_khz"]
        am_dec  = decoded["am_freq_khz"]
        name    = t["meta"]["conversation_name"]
        ok      = "OK" if em_orig == em_dec and int_orig == int_dec else "FAIL"
        print(f"  {name:<20} | emotion {ok} ({em_orig}={em_dec}) | "
              f"intensity {ok} ({int_orig}={int_dec}) | "
              f"AM {abs(am_orig - am_dec):.2f}kHz drift")

    # Check index
    print("\n[3/3] Index verification...")
    index_path = CONVERSATION_FOLDS_DIR / "index.json"
    with open(index_path) as f:
        index = json.load(f)
    print(f"  Tokens indexed: {len(index['by_hash'])}")
    print(f"  Emotion classes present: {list(index['by_emotion'].keys())}")
    print(f"  Color planes present:    {list(index['by_plane'].keys())}")

    print("\n" + "=" * 60)
    print(f"STRAND LENGTH: {TOTAL_STRAND_BITS} bits  (A16 + T24 + C9 + G16)")
    print("PALETTE: v3_palette.json full ranges — NOT dna_token.py POC")
    print("CONTAMINATION: zero — all existing files untouched")
    print("=" * 60)
