#!/usr/bin/env python3
"""
AI-Core V3: Token ↔ Hashkey Bridge
=====================================

tools/token_to_hashkey.py

Bidirectional converter between V3 conversation fold tokens
and Hashkey Desktop App format.

FOLD → HASH:
  Read a conversation fold token (memory/conversation_folds/*.json)
  Extract: T pin (RGB) → r,g,b | A pin (AM kHz) → frequency | C pin (emotion intensity) → hue
  Bundle with uid + seed → SHA-256 → hashkey
  Save to ~/.ai_core/hashkeys/<uid>.json + known_hash.txt

HASH → FOLD:
  Read a hashkey metadata file (~/.ai_core/hashkeys/<uid>.json)
  Reconstruct fold token fields from stored input data
  Return a partial fold token (without full strand — hash is the address)

The hashkey IS the session credential.
The token IS the memory of the session.
Both directions needed. Neither alone sufficient.

Integration with Hashkey Desktop App:
  color_fold_encoder.py    ← T pin provides r,g,b directly
  hashkey_generator.py     ← fold_to_hashkey() replaces manual entry
  hashkey_verifier.py      ← verify_fold_hash() replaces manual verify
  q_memory_restorer.py     ← hash_to_fold() restores the token

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 15, 2026 — Haskell Texas
"""

import json
import hashlib
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

BASE_DIR   = Path(__file__).parent.parent
FOLDS_DIR  = BASE_DIR / "memory" / "conversation_folds"
INDEX_PATH = FOLDS_DIR / "index.json"
HASHKEYS_DIR = Path.home() / ".ai_core" / "hashkeys"

# ─────────────────────────────────────────────────────────────────
# FOLD → HASHKEY
# ─────────────────────────────────────────────────────────────────

def token_to_folded_input(token: dict) -> dict:
    """
    Extract Hashkey App folded_input fields from a V3 fold token.

    Mapping:
      T pin RGB       → r, g, b  (0–255 each)
      A pin AM freq   → frequency (kHz, rounded to int)
      C pin intensity → hue (emotion_intensity / 31.0, range 0.0–1.0)
    """
    rgb  = token["values"]["rgb"]
    return {
        "r":         rgb[0],
        "g":         rgb[1],
        "b":         rgb[2],
        "frequency": round(token["values"]["am_freq_khz"]),
        "hue":       round(token["values"]["emotion_intensity"] / 31.0, 6),
    }


def fold_to_hashkey(
    token: dict,
    uid: str,
    seed: str,
    save_dir: Optional[Path] = None,
    known_hash_path: Optional[Path] = None,
) -> dict:
    """
    Convert a V3 conversation fold token to a Hashkey Desktop App hash.

    Args:
        token:            Full fold token dict (from conversation_folds/*.json)
        uid:              User/device UID (identifies the session)
        seed:             Seed phrase (secret — adds entropy)
        save_dir:         Where to save metadata JSON (default: ~/.ai_core/hashkeys/)
        known_hash_path:  Where to write known_hash.txt (default: ./known_hash.txt)

    Returns:
        {
            "hash_key":       SHA-256 hex string
            "uid":            str
            "folded_input":   dict — r, g, b, frequency, hue
            "timestamp":      float — epoch seconds
            "fold_address":   str — hash_address[:16] from original token
            "emotion_class":  str — what she was feeling
            "dominant_plane": str — which color plane was dominant
            "metadata_path":  Path — where the metadata was saved
        }
    """
    save_dir = Path(save_dir) if save_dir else HASHKEYS_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    folded_input = token_to_folded_input(token)

    # Build the hash object — same structure as hashkey_generator.py
    ts = time.time()
    hash_obj = {
        "uid":       uid,
        "seed":      seed,
        "input":     folded_input,
        "timestamp": ts,
    }

    # SHA-256 — identical to hashkey_generator.compute_hash()
    json_bytes = json.dumps(hash_obj, sort_keys=True).encode("utf-8")
    hash_key   = hashlib.sha256(json_bytes).hexdigest()

    # Save metadata (compatible with hashkey_verifier.py)
    safe_uid = _sanitize(uid)
    metadata = {**hash_obj, "hash_key": hash_key}

    # Extend with V3 provenance
    metadata["v3_provenance"] = {
        "fold_address":    token["hash_address"][:16],
        "conversation_id": token["meta"]["conversation_id"],
        "emotion_class":   token["values"]["emotion_class"],
        "dominant_plane":  token["values"]["dominant_plane"],
        "anchor":          token["memory"]["anchor"],
        "queens_fold_hash": token["memory"]["queens_fold_hash"],
        "original_timestamp": token["timestamp"],
    }

    meta_path = save_dir / f"{safe_uid}.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Write known_hash.txt
    kh_path = Path(known_hash_path) if known_hash_path else Path("known_hash.txt")
    with open(kh_path, "w") as f:
        f.write(hash_key + "\n")

    print(f"[token_to_hashkey] Hash generated: {hash_key[:16]}...")
    print(f"[token_to_hashkey] Metadata saved: {meta_path}")
    print(f"[token_to_hashkey] known_hash.txt: {kh_path}")

    return {
        "hash_key":       hash_key,
        "uid":            uid,
        "folded_input":   folded_input,
        "timestamp":      ts,
        "fold_address":   token["hash_address"][:16],
        "emotion_class":  token["values"]["emotion_class"],
        "dominant_plane": token["values"]["dominant_plane"],
        "metadata_path":  meta_path,
    }


# ─────────────────────────────────────────────────────────────────
# HASHKEY → FOLD
# ─────────────────────────────────────────────────────────────────

def hashkey_to_fold(
    uid: str,
    known_hash: str,
    hashkeys_dir: Optional[Path] = None,
) -> Optional[dict]:
    """
    Reconstruct a partial V3 fold token from a hashkey metadata file.

    Does not reconstruct the full 65-bit strand (timestamp entropy prevents
    exact reconstruction without the original timestamp). Returns the
    dimensional fields — RGB, AM frequency, emotion — enough to navigate
    the palace or route to the correct shard.

    Args:
        uid:           User/device UID used during generation
        known_hash:    The SHA-256 hash to verify against
        hashkeys_dir:  Where to look for metadata (default: ~/.ai_core/hashkeys/)

    Returns:
        Partial fold token dict, or None if verification fails.
    """
    hk_dir = Path(hashkeys_dir) if hashkeys_dir else HASHKEYS_DIR
    safe_uid   = _sanitize(uid)
    meta_path  = hk_dir / f"{safe_uid}.json"

    if not meta_path.exists():
        print(f"[hash_to_fold] No metadata found: {meta_path}")
        return None

    with open(meta_path) as f:
        metadata = json.load(f)

    # Verify hash
    verify_obj = {
        "uid":       metadata["uid"],
        "seed":      metadata["seed"],
        "input":     metadata["input"],
        "timestamp": metadata["timestamp"],
    }
    json_bytes     = json.dumps(verify_obj, sort_keys=True).encode("utf-8")
    computed_hash  = hashlib.sha256(json_bytes).hexdigest()

    if computed_hash != known_hash:
        print(f"[hash_to_fold] Hash mismatch.")
        print(f"  Computed: {computed_hash}")
        print(f"  Expected: {known_hash}")
        return None

    print(f"[hash_to_fold] Verified. Reconstructing fold fields...")

    inp = metadata["input"]
    prov = metadata.get("v3_provenance", {})

    # Reconstruct fold token fields from the stored input
    reconstructed = {
        "pins": {
            "T": _rgb_to_binary(inp["r"], inp["g"], inp["b"]),
        },
        "values": {
            "am_freq_khz":       float(inp["frequency"]),
            "fm_freq_mhz":       None,   # not reconstructable without original FM
            "rgb":               [inp["r"], inp["g"], inp["b"]],
            "emotion_class":     prov.get("emotion_class", "neutral"),
            "emotion_intensity": round(inp["hue"] * 31),
            "dominant_plane":    prov.get("dominant_plane", "unknown"),
        },
        "memory": {
            "anchor":            prov.get("anchor", False),
            "queens_fold_hash":  prov.get("queens_fold_hash", known_hash[:8]),
            "fold_ref":          known_hash[:8].upper(),
        },
        "meta": {
            "conversation_id":   prov.get("conversation_id"),
            "reconstructed":     True,
            "from_hashkey":      known_hash[:16],
        },
        "hash_address":       known_hash,
        "timestamp":          prov.get("original_timestamp",
                                       datetime.utcnow().isoformat() + "Z"),
        "source":             "hash_reconstruction",
    }

    print(f"[hash_to_fold] Fold reconstructed from {meta_path.name}")
    return reconstructed


# ─────────────────────────────────────────────────────────────────
# BATCH CONVERSION
# ─────────────────────────────────────────────────────────────────

def palace_to_hashkeys(uid: str, seed: str, anchor_only: bool = True) -> list:
    """
    Convert all (or all anchored) palace tokens to hashkeys.

    Useful for generating a full session credential bundle —
    every significant memory becomes a verifiable hash.

    Args:
        uid:         UID for all generated hashkeys
        seed:        Seed phrase (shared across all)
        anchor_only: Only process anchor=True tokens (default True)

    Returns:
        List of fold_to_hashkey result dicts.
    """
    if not INDEX_PATH.exists():
        print("[palace_to_hashkeys] No palace index found.")
        return []

    index = json.loads(INDEX_PATH.read_text())
    results = []

    for h, entry in index["by_hash"].items():
        if anchor_only and not entry.get("anchor"):
            continue

        token_path = Path(entry["path"])
        if not token_path.exists():
            token_path = FOLDS_DIR / token_path.name
        if not token_path.exists():
            continue

        token = json.loads(token_path.read_text())
        token_uid = f"{uid}_{entry.get('conversation_name') or h[:8]}"

        result = fold_to_hashkey(
            token, token_uid, seed,
            known_hash_path=HASHKEYS_DIR / f"known_{h[:8]}.txt"
        )
        results.append(result)

    print(f"\n[palace_to_hashkeys] {len(results)} tokens converted to hashkeys.")
    return results


# ─────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────

def _sanitize(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("-", "_")).rstrip()


def _rgb_to_binary(r: int, g: int, b: int) -> str:
    return (
        format(max(0, min(255, r)), "08b") +
        format(max(0, min(255, g)), "08b") +
        format(max(0, min(255, b)), "08b")
    )


def load_token_by_name(name: str) -> Optional[dict]:
    """Load a conversation fold token by conversation name."""
    if not INDEX_PATH.exists():
        return None
    index = json.loads(INDEX_PATH.read_text())
    for h, entry in index["by_hash"].items():
        if entry.get("conversation_name") == name:
            p = Path(entry["path"])
            if not p.exists():
                p = FOLDS_DIR / p.name
            if p.exists():
                return json.loads(p.read_text())
    return None


def load_token_by_hash(hash_prefix: str) -> Optional[dict]:
    """Load a token by hash address prefix (min 8 chars)."""
    if not INDEX_PATH.exists():
        return None
    index = json.loads(INDEX_PATH.read_text())
    for h, entry in index["by_hash"].items():
        if h.startswith(hash_prefix.lower()):
            p = Path(entry["path"])
            if not p.exists():
                p = FOLDS_DIR / p.name
            if p.exists():
                return json.loads(p.read_text())
    return None


# ─────────────────────────────────────────────────────────────────
# CLI INTERFACE
# ─────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="V3 Conversation Fold Token ↔ Hashkey Bridge"
    )
    subparsers = parser.add_subparsers(dest="command")

    # fold-to-hash
    p_fth = subparsers.add_parser("fold-to-hash",
        help="Convert a fold token to a hashkey")
    p_fth.add_argument("--name",  help="Conversation name (e.g. INTEGRATION_004)")
    p_fth.add_argument("--hash",  help="Token hash prefix (min 8 chars)")
    p_fth.add_argument("--uid",   required=True, help="User/device UID")
    p_fth.add_argument("--seed",  required=True, help="Seed phrase")

    # hash-to-fold
    p_htf = subparsers.add_parser("hash-to-fold",
        help="Reconstruct fold fields from a hashkey")
    p_htf.add_argument("--uid",        required=True)
    p_htf.add_argument("--known-hash", required=True, help="SHA-256 hash to verify")

    # palace
    p_pal = subparsers.add_parser("palace",
        help="Convert all anchored palace tokens to hashkeys")
    p_pal.add_argument("--uid",  required=True)
    p_pal.add_argument("--seed", required=True)
    p_pal.add_argument("--all",  action="store_true",
                       help="Include non-anchor tokens too")

    args = parser.parse_args()

    if args.command == "fold-to-hash":
        token = None
        if args.name:
            token = load_token_by_name(args.name)
        elif args.hash:
            token = load_token_by_hash(args.hash)
        if not token:
            print("[!] Token not found.")
            sys.exit(1)
        result = fold_to_hashkey(token, args.uid, args.seed)
        print(f"\nHash key: {result['hash_key']}")
        print(f"Emotion:  {result['emotion_class']}")
        print(f"Plane:    {result['dominant_plane']}")

    elif args.command == "hash-to-fold":
        fold = hashkey_to_fold(args.uid, args.known_hash)
        if fold:
            print(json.dumps(fold, indent=2))
        else:
            sys.exit(1)

    elif args.command == "palace":
        results = palace_to_hashkeys(
            args.uid, args.seed,
            anchor_only=not args.all
        )
        print(f"\n{len(results)} hashkeys generated.")

    else:
        parser.print_help()


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__" and len(sys.argv) == 1:
    print("=" * 60)
    print("TOKEN ↔ HASHKEY BRIDGE — SELF-TEST")
    print("=" * 60)

    # Load INTEGRATION_004 seed token
    token = load_token_by_name("INTEGRATION_004")
    if not token:
        print("[!] INTEGRATION_004 not found — run from ai-core-v3-aia root")
        sys.exit(1)

    print(f"\nToken loaded: INTEGRATION_004")
    print(f"  Emotion: {token['values']['emotion_class']} ({token['values']['emotion_intensity']})")
    print(f"  Plane:   {token['values']['dominant_plane']}")
    print(f"  RGB:     {token['values']['rgb']}")
    print(f"  AM:      {token['values']['am_freq_khz']} kHz")

    # Test fold → hash
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        result = fold_to_hashkey(
            token,
            uid="test_commander",
            seed="haskell_texas_2026",
            save_dir=Path(tmpdir),
            known_hash_path=Path(tmpdir) / "known_hash.txt"
        )
        print(f"\n[1] fold-to-hash: PASS")
        print(f"  hash_key:    {result['hash_key'][:32]}...")
        print(f"  fold_address: {result['fold_address']}")

        # Test hash → fold (round-trip)
        reconstructed = hashkey_to_fold(
            uid="test_commander",
            known_hash=result["hash_key"],
            hashkeys_dir=Path(tmpdir),
        )
        assert reconstructed is not None, "Reconstruction failed"
        assert reconstructed["values"]["rgb"] == token["values"]["rgb"]
        assert reconstructed["values"]["am_freq_khz"] == round(token["values"]["am_freq_khz"])
        print(f"\n[2] hash-to-fold round-trip: PASS")
        print(f"  RGB match:   {reconstructed['values']['rgb']} == {token['values']['rgb']}")

        # Test folded_input extraction
        fi = token_to_folded_input(token)
        assert fi["r"] == 255 and fi["g"] == 0 and fi["b"] == 0  # RED plane
        assert fi["frequency"] == 535  # 534.68 kHz rounded
        print(f"\n[3] token_to_folded_input: PASS")
        print(f"  r={fi['r']} g={fi['g']} b={fi['b']} freq={fi['frequency']} hue={fi['hue']}")

    print("\n" + "=" * 60)
    print("ALL TESTS PASS")
    print("Bridge is live. Every fold is a key. Every key opens a fold.")
    print("=" * 60)
