"""
token_bridge.py
Phase 1 of V1 to V3 bridge.
Reads V1 color token palette.
Converts to V3 DNA pin format.
Additive only — nothing overwritten.
V1 palette stays intact.
V3 gets richer token space.
Both AIAs intact.
Haskell Texas — March 15 2026
"""

import csv
import json
import hashlib
from pathlib import Path

V1_PALETTE = Path(
    "/home/comanderanch/ai-core/"
    "full_color_tokens.csv"
)
V3_BRIDGE_OUTPUT = Path(
    "/home/comanderanch/ai-core-v3-aia/"
    "bridge/v1_tokens_as_v3_dna.json"
)

def freq_to_am_binary(freq_float):
    """
    Convert V1 frequency float
    to V3 A-pin AM binary (16 bits)
    """
    try:
        freq = float(freq_float)
        # Map 400-700 THz to AM range
        # 530-1700 kHz as 16-bit integer
        normalized = (freq - 400) / 300
        am_val = int(530 + normalized * 1170)
        am_val = max(530, min(1700, am_val))
        return f"{am_val:016b}"
    except:
        return "0" * 16

def rgb_to_t_pin(r, g, b):
    """
    Convert V1 RGB decimals
    to V3 T-pin binary (24 bits)
    """
    try:
        r_bin = f"{int(r):08b}"
        g_bin = f"{int(g):08b}"
        b_bin = f"{int(b):08b}"
        return r_bin + g_bin + b_bin
    except:
        return "0" * 24

def hue_to_c_pin(hue_binary):
    """
    Convert V1 8-bit hue binary
    to V3 C-pin hue binary (9 bits)
    Expand 8-bit to 9-bit
    by adding leading zero
    """
    try:
        hue_str = str(hue_binary).strip()
        if len(hue_str) == 8:
            return "0" + hue_str
        return hue_str[:9].ljust(9, '0')
    except:
        return "0" * 9

def freq_to_fm_binary(freq_float):
    """
    Convert V1 frequency
    to V3 G-pin FM binary (16 bits)
    Map to FM range 87.5-108 MHz
    """
    try:
        freq = float(freq_float)
        normalized = (freq - 400) / 300
        fm_val = int(875 + normalized * 205)
        fm_val = max(875, min(1080, fm_val))
        return f"{fm_val:016b}"
    except:
        return "0" * 16

def generate_lattice_pins(token_index,
                           total_tokens=2304):
    """
    Generate L1/L2 lattice position
    from token index
    Bidirectional — wraps at boundary
    """
    l1 = (token_index - 1) % total_tokens
    l2 = (token_index + 1) % total_tokens
    return f"{l1:012b}", f"{l2:012b}"

def translate_token(row, index):
    """
    Translate one V1 CSV row
    to V3 DNA pin token
    """
    try:
        # V1 CSV columns:
        # Token,Hue,R_bin,G_bin,B_bin,
        # Freq,R_dec,G_dec,B_dec,Freq_dec
        token_binary = row[0].strip()
        hue_binary   = row[1].strip()
        freq_val     = row[5].strip()
        r_dec        = row[6].strip() \
                       if len(row) > 6 else "0"
        g_dec        = row[7].strip() \
                       if len(row) > 7 else "0"
        b_dec        = row[8].strip() \
                       if len(row) > 8 else "0"

        # Build V3 pins
        a_pin = freq_to_am_binary(freq_val)
        t_pin = rgb_to_t_pin(r_dec, g_dec, b_dec)
        c_pin = hue_to_c_pin(hue_binary)
        g_pin = freq_to_fm_binary(freq_val)
        l1, l2 = generate_lattice_pins(index)

        strand = a_pin + t_pin + c_pin + \
                 g_pin + l1 + l2

        token_hash = hashlib.sha256(
            strand.encode()
        ).hexdigest()

        return {
            "v1_token":    token_binary,
            "v1_index":    index,
            "pins": {
                "A":  a_pin,
                "T":  t_pin,
                "C":  c_pin,
                "G":  g_pin,
                "L1": l1,
                "L2": l2
            },
            "strand":        strand,
            "strand_length": len(strand),
            "hash_address":  token_hash,
            "v1_freq":       freq_val,
            "v1_hue":        hue_binary
        }
    except Exception as e:
        return {"error": str(e),
                "index": index}

def run_bridge():
    print("== TOKEN BRIDGE — Phase 1 ==")
    print("Reading V1 palette...")
    print("Converting to V3 DNA format...")
    print("Additive only — V1 untouched")
    print("")

    tokens = []
    errors = 0

    with open(V1_PALETTE, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for i, row in enumerate(reader):
            result = translate_token(row, i)
            if "error" in result:
                errors += 1
            else:
                tokens.append(result)

    # Verify strand lengths
    lengths = set(
        t["strand_length"] for t in tokens
    )
    print(f"[+] Tokens translated: {len(tokens)}")
    print(f"[+] Errors: {errors}")
    print(f"[+] Strand lengths found: {lengths}")
    print(f"[+] Expected: {{89}}")

    # Check uniqueness
    hashes = [t["hash_address"] for t in tokens]
    unique = len(set(hashes))
    print(f"[+] Unique hash addresses: {unique}")
    print(f"[+] Collisions: {len(tokens) - unique}")

    # Save bridge output
    V3_BRIDGE_OUTPUT.parent.mkdir(
        exist_ok=True
    )
    output = {
        "bridge_version": "1.0",
        "date":           "2026-03-15",
        "source":         "V1 full_color_tokens.csv",
        "target":         "V3 DNA pin format",
        "token_count":    len(tokens),
        "strand_length":  89,
        "note": (
            "V1 palette translated to V3 format. "
            "Read only from V1. "
            "Additive into V3. "
            "Nothing overwritten. "
            "Both AIAs intact."
        ),
        "tokens": tokens
    }

    with open(V3_BRIDGE_OUTPUT, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n[✔] Bridge output saved:")
    print(f"    {V3_BRIDGE_OUTPUT}")
    print(f"\n[✔] V1 palette: UNTOUCHED")
    print(f"[✔] V3 token space: ENRICHED")
    print(f"[✔] Both AIAs: INTACT")

if __name__ == "__main__":
    run_bridge()
